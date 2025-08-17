"""evoforge.evaluation
-------------------
评估模块：负责执行个体代码、运行测试用例并收集性能指标。

主要功能：
1. 将个体（Python 代码）与测试用例结合
2. 在 Sandbox 中安全执行并收集结果
3. 解析 pytest 输出的 JSON 报告
4. 计算适应度分数
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from sandbox import Sandbox, SandboxResult

logger = logging.getLogger("evoforge.evaluation")
logger.setLevel(logging.DEBUG)  # 强制 DEBUG 级别，输出大量调试信息

# ------------------------------ 数据结构 ------------------------------

@dataclass
class TestResult:
    """测试结果数据结构。"""
    passed: int = 0
    failed: int = 0
    error: int = 0
    skipped: int = 0
    total: int = 0
    duration: float = 0.0
    cases: List[Dict[str, Any]] = None  # 详细的测试用例结果

    def __post_init__(self):
        if self.cases is None:
            self.cases = []
        self.total = self.passed + self.failed + self.error + self.skipped

    def success_rate(self) -> float:
        """计算测试成功率。"""
        if self.total == 0:
            return 0.0
        return self.passed / self.total

    def summary(self) -> str:
        """生成测试结果摘要。"""
        return (
            f"测试结果: {self.passed}/{self.total} 通过 "
            f"({self.success_rate():.1%}), "
            f"耗时 {self.duration:.3f}s"
        )

# ------------------------------ 测试准备 ------------------------------

def _create_test_files(tempdir: Path, code: str, test_code: str) -> Tuple[Path, Path]:
    """在临时目录中创建待测代码和测试文件。
    
    Args:
        tempdir: 临时目录路径
        code: 被测代码内容
        test_code: 测试代码内容
        
    Returns:
        包含代码文件和测试文件路径的元组
    """
    # 创建解决方案代码文件
    solution_file = tempdir / "solution.py"
    solution_file.write_text(code, encoding="utf-8")
    logger.debug("写入解决方案代码到 %s (大小 %.1fkB)", solution_file, solution_file.stat().st_size / 1024)
    
    # 创建测试文件
    test_file = tempdir / "test_solution.py"
    test_file.write_text(test_code, encoding="utf-8")
    logger.debug("写入测试代码到 %s (大小 %.1fkB)", test_file, test_file.stat().st_size / 1024)
    
    # 创建一个空的 __init__.py 文件，使目录成为一个包
    init_file = tempdir / "__init__.py"
    init_file.touch()
    
    # 创建 conftest.py 配置 pytest
    conftest = tempdir / "conftest.py"
    conftest.write_text(
        """
# pytest 配置文件
def pytest_configure(config):
    config.option.verbose = 2
    """,
        encoding="utf-8",
    )
    
    return solution_file, test_file

# ------------------------------ 评估核心 ------------------------------

def evaluate_individual(
    code: str,
    test_code: str,
    timeout_sec: float = 10.0,
    install_deps: Optional[List[str]] = None,
) -> Tuple[TestResult, SandboxResult]:
    """评估个体代码，执行测试用例，并返回测试结果。
    
    Args:
        code: 待评估的 Python 代码
        test_code: 测试代码（pytest 格式）
        timeout_sec: 执行超时时间（秒）
        install_deps: 需要安装的额外依赖包列表
        
    Returns:
        包含测试结果和沙盒执行结果的元组
    """
    logger.debug("开始评估个体代码 (代码长度=%d, 测试代码长度=%d)", len(code), len(test_code))
    
    # 创建一个沙盒实例
    # 若用户传入依赖，需要开启网络以便 pip install；否则保持网络隔离
    sandbox = Sandbox(
        mem_limit="1g",  # 给测试多分配一些内存
        cpu_quota=200_000,  # 0.2 CPU
        network_disabled=not bool(install_deps),
    )
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tempdir = Path(tmpdir)
        _create_test_files(tempdir, code, test_code)
        
        # 创建主脚本，用于安装依赖、运行测试并输出 JSON 结果
        main_script = tempdir / "run_tests.py"
        main_script.write_text(
            f"""
#!/usr/bin/env python3
import json
import os
import sys
import pytest

# 先安装依赖
deps = {install_deps or []}
if deps:
    import subprocess
    print(f"安装依赖: {{deps}}")
    for dep in deps:
        subprocess.check_call([sys.executable, "-m", "pip", "install", dep])

# 设置环境变量
os.environ["PYTHONPATH"] = os.getcwd()

# 运行测试并输出 JSON 报告
result = pytest.main(["--json-report", "--json-report-file=report.json", "test_solution.py"])

# 如果 JSON 报告文件存在，打印报告内容到标准输出
if os.path.exists("report.json"):
    with open("report.json", "r") as f:
        print(json.dumps(json.load(f)))

sys.exit(result)
""",
            encoding="utf-8",
        )
        
        # 创建依赖安装脚本
        requirements_file = tempdir / "requirements.txt"
        requirements_file.write_text(
            "pytest==7.4.0\npytest-json-report==1.5.0\n", encoding="utf-8"
        )
        
        # 先安装依赖，然后运行测试
        setup_script = tempdir / "setup.sh"
        setup_script.write_text(
            """
#!/bin/bash
pip install -r requirements.txt
python run_tests.py
""",
            encoding="utf-8",
        )
        setup_script.chmod(0o755)  # 确保脚本可执行
        
        logger.debug("准备在沙盒中执行测试，超时时间 %.1fs", timeout_sec)
        result = sandbox.run_code(
            code="",  # 我们不需要传递代码，因为已经写入文件
            timeout_sec=timeout_sec,
            command=["bash", "setup.sh"],  # 使用脚本运行
        )
        
        logger.debug("沙盒执行完成: %s", result.summary())
        
        # 解析测试结果
        test_result = _parse_test_result(result)
        logger.debug("测试评估结果: %s", test_result.summary())
        
        return test_result, result

def _parse_test_result(result: SandboxResult) -> TestResult:
    """从沙盒执行结果中解析测试结果。
    
    Args:
        result: 沙盒执行结果
        
    Returns:
        解析后的测试结果对象
    """
    # 初始化默认测试结果
    test_result = TestResult()
    test_result.duration = result.duration_sec
    
    # 检查执行是否成功
    if result.exit_code != 0 or result.timed_out:
        logger.debug("测试执行失败: exit_code=%d, timed_out=%s", result.exit_code, result.timed_out)
        test_result.error = 1  # 标记为错误
        return test_result
    
    # 尝试从输出中提取 JSON 报告
    try:
        # 在输出中查找 JSON 块
        output = result.stdout
        json_start = output.find('{')
        if json_start >= 0:
            json_content = output[json_start:]
            report_data = json.loads(json_content)
            logger.debug("成功解析测试 JSON 报告，大小 %.1fkB", len(json_content) / 1024)
            
            # 从报告提取信息
            summary = report_data.get('summary', {})
            test_result.passed = summary.get('passed', 0)
            test_result.failed = summary.get('failed', 0)
            test_result.error = summary.get('error', 0)
            test_result.skipped = summary.get('skipped', 0)
            test_result.total = test_result.passed + test_result.failed + test_result.error + test_result.skipped
            
            # 获取详细的测试用例结果
            tests = report_data.get('tests', [])
            test_result.cases = []
            for test in tests:
                test_result.cases.append({
                    'name': test.get('name', ''),
                    'outcome': test.get('outcome', ''),
                    'duration': test.get('duration', 0),
                    'call': test.get('call', {}),
                })
            
            logger.debug(
                "解析到 %d 个测试用例: 通过=%d, 失败=%d, 错误=%d, 跳过=%d",
                test_result.total, test_result.passed, test_result.failed,
                test_result.error, test_result.skipped
            )
    except Exception as parse_err:
        logger.debug("解析测试结果失败: %s", parse_err)
        # 解析失败也视为测试错误
        test_result.error = 1
    
    return test_result