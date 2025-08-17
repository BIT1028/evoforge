"""evoforge.sandbox
-------------------
安全沙盒：在受限 Docker 容器中执行 Python 代码并收集资源使用情况。

⚠️ 注意：
1. 需先安装并启动 Docker Desktop (Windows 下 WSL2 后端或 Hyper-V)。
2. 需向项目依赖中添加 `docker`、`psutil`（仅宿主资源统计备用）。
3. 本实现用于 MVP，后期可替换为 gVisor/Kata/Firecracker。
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import subprocess

# Docker 可能不存在或未运行，尝试导入并在失败时降级为 None
try:
    import docker  # type: ignore
    from docker.errors import DockerException  # type: ignore
except ImportError:  # pragma: no cover
    docker = None
    DockerException = Exception

logger = logging.getLogger("evoforge.sandbox")
logger.setLevel(logging.DEBUG)  # 强制 DEBUG 级别，按照用户要求输出大量调试信息

# ------------------------------ 数据结构 ------------------------------

@dataclass
class SandboxResult:
    """容器执行结果。"""

    exit_code: int
    stdout: str
    stderr: str
    duration_sec: float
    cpu_usage_sec: Optional[float] = None
    max_memory_bytes: Optional[int] = None
    timed_out: bool = False
    meta: Dict[str, str] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            f"exit={self.exit_code} duration={self.duration_sec:.3f}s "
            f"cpu={self.cpu_usage_sec}s mem={self.max_memory_bytes}B timeout={self.timed_out}"
        )

# ------------------------------ 沙盒核心 ------------------------------

class Sandbox:
    """在受限 Docker 容器中运行命令并获取资源使用。"""

    def __init__(
        self,
        image: str = "python:3.10-slim",
        workdir: str = "/workspace",
        cpu_quota: int = 100_000,  # 0.1 CPU (100ms) 配额窗口 100ms
        mem_limit: str = "512m",
        network_disabled: bool = True,
        extra_docker_run_args: Optional[Dict] = None,
    ) -> None:
        # 尝试连接 Docker，并设置降级标志
        self.docker_available = False
        self.client = None
        if docker is not None:
            try:
                self.client = docker.from_env()
                _ = self.client.ping()
                self.docker_available = True
            except DockerException as conn_err:  # pragma: no cover
                logger.warning("无法连接 Docker，降级为本地执行模式: %s", conn_err)
        else:
            logger.warning("未安装 docker SDK，Sandbox 将使用本地执行模式")

        self.image = image
        self.workdir = workdir
        self.cpu_quota = cpu_quota
        self.mem_limit = mem_limit
        self.network_disabled = network_disabled
        self.extra_docker_run_args = extra_docker_run_args or {}
        logger.debug(
            "Sandbox 初始化: image=%s workdir=%s cpu_quota=%s mem_limit=%s network_disable=%s",
            image,
            workdir,
            cpu_quota,
            mem_limit,
            network_disabled,
        )

    # -----------------------------------------------------------------
    # 公共 API
    # -----------------------------------------------------------------

    def run_code(
        self,
        code: str,
        timeout_sec: float = 5.0,
        command: Optional[List[str]] = None,
    ) -> SandboxResult:
        """给定 python 源码字符串，在容器中执行并返回 SandboxResult。"""

        command = command or ["python", "main.py"]
        logger.debug("运行代码，超时 %.2fs，command=%s", timeout_sec, command)

        with tempfile.TemporaryDirectory() as tmpdir:
            code_file = Path(tmpdir) / "main.py"
            code_file.write_text(code, encoding="utf-8")
            logger.debug("源码已写入临时文件 %s (大小 %.1fkB)", code_file, code_file.stat().st_size / 1024)

            if not self.docker_available:
                # 本地执行回退
                start_time = time.perf_counter()
                try:
                    proc = subprocess.run(
                        command,
                        cwd=tmpdir,
                        capture_output=True,
                        text=True,
                        timeout=timeout_sec,
                    )
                    duration = time.perf_counter() - start_time
                    result = SandboxResult(
                        exit_code=proc.returncode,
                        stdout=proc.stdout,
                        stderr=proc.stderr,
                        duration_sec=duration,
                        timed_out=False,
                    )
                except subprocess.TimeoutExpired as te:
                    duration = time.perf_counter() - start_time
                    result = SandboxResult(
                        exit_code=-1,
                        stdout=te.stdout or "",
                        stderr=str(te),
                        duration_sec=duration,
                        timed_out=True,
                    )
            else:
                result = self._run_container(tmpdir, command, timeout_sec)
        logger.debug("运行结束: %s", result.summary())
        return result

    # -----------------------------------------------------------------
    # 内部实现
    # -----------------------------------------------------------------

    def _run_container(
        self, local_dir: str | Path, command: List[str], timeout_sec: float
    ) -> SandboxResult:
        """将宿主目录挂载到容器，执行命令并收集资源使用。"""

        local_dir = Path(local_dir).resolve()
        logger.debug("准备运行容器，挂载目录=%s", local_dir)

        start_time = time.perf_counter()
        container = None
        timed_out = False
        try:
            # 预拉取镜像（若未本地存在）
            logger.debug("拉取镜像 %s（若本地不存在）", self.image)
            self.client.images.pull(self.image)

            host_config = self.client.api.create_host_config(
                binds={
                    str(local_dir): {
                        "bind": self.workdir,
                        "mode": "ro",  # 只读
                    }
                },
                cpu_quota=self.cpu_quota,
                mem_limit=self.mem_limit,
                network_mode="none" if self.network_disabled else None,
            )

            container = self.client.api.create_container(
                image=self.image,
                command=command,
                working_dir=self.workdir,
                host_config=host_config,
                stdout=True,
                stderr=True,
                **self.extra_docker_run_args,
            )
            container_id = container.get("Id")
            logger.debug("容器已创建 id=%s", container_id)

            self.client.api.start(container_id)
            logger.debug("容器启动完成，等待输出 ...")

            exit_code: Optional[int] = None
            stdout = b""
            stderr = b""

            # 实时读取日志，同时检查超时
            start_mon = time.time()
            while True:
                if (time.time() - start_mon) > timeout_sec:
                    timed_out = True
                    logger.debug("检测到超时 %.2fs，准备停止容器", timeout_sec)
                    self.client.api.stop(container_id)
                    break
                # stream=False 获取当前全部日志
                stdout = self.client.api.logs(container_id, stdout=True, stderr=False)
                stderr = self.client.api.logs(container_id, stdout=False, stderr=True)
                inspect = self.client.api.inspect_container(container_id)
                exit_code = inspect.get("State", {}).get("ExitCode")
                if exit_code is not None and exit_code != 0:
                    logger.debug("容器已退出，exit_code=%s", exit_code)
                    break
                if inspect.get("State", {}).get("Running"):
                    time.sleep(0.1)
                    continue
                else:
                    exit_code = inspect.get("State", {}).get("ExitCode")
                    break

            duration = time.perf_counter() - start_time
            # 获取最大内存
            mem_bytes = None
            try:
                stats = self.client.api.stats(container_id, stream=False)
                mem_bytes = stats.get("memory_stats", {}).get("max_usage")
                cpu_delta = stats.get("cpu_stats", {}).get("cpu_usage", {}).get("total_usage")
            except Exception as stats_err:  # pragma: no cover
                logger.debug("获取 stats 失败: %s", stats_err)
                cpu_delta = None

            return SandboxResult(
                exit_code=exit_code if exit_code is not None else -1,
                stdout=stdout.decode(errors="replace"),
                stderr=stderr.decode(errors="replace"),
                duration_sec=duration,
                cpu_usage_sec=cpu_delta,
                max_memory_bytes=mem_bytes,
                timed_out=timed_out,
            )
        finally:
            if container is not None:
                try:
                    self.client.api.remove_container(container.get("Id"), force=True)
                    logger.debug("容器已删除")
                except Exception as rm_err:  # pragma: no cover
                    logger.debug("删除容器失败: %s", rm_err)