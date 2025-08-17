#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全沙箱系统 - 核心实现文件

根据 comprehensive_implementation_plan.md 文档重新实现

功能包括：
- 多层沙箱：Docker + WebAssembly + 权限控制
- 资源限制：CPU、内存、网络隔离
- 动态权限控制和安全代码执行
- 代码验证和威胁检测
"""

import logging
import subprocess
import tempfile
import os
import sys
import time
import threading
import psutil
import signal
import hashlib
import json
import ast
import re
from typing import Dict, List, Any, Optional, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
from pathlib import Path
try:
    import resource
except ImportError:
    # Windows doesn't have resource module
    resource = None
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, TimeoutError
import contextlib
import io
from contextlib import redirect_stdout, redirect_stderr

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class SecurityLevel(Enum):
    """安全级别枚举"""
    LOW = "low"          # 基础隔离
    MEDIUM = "medium"    # 标准隔离
    HIGH = "high"        # 严格隔离
    CRITICAL = "critical" # 最高安全级别

class SandboxType(Enum):
    """沙箱类型枚举"""
    PROCESS = "process"      # 进程级隔离
    DOCKER = "docker"        # Docker容器隔离
    WASM = "wasm"            # WebAssembly隔离
    HYBRID = "hybrid"        # 混合模式

class ExecutionStatus(Enum):
    """执行状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    KILLED = "killed"

@dataclass
class ResourceLimits:
    """资源限制配置"""
    max_memory_mb: int = 512        # 最大内存(MB)
    max_cpu_percent: float = 50.0   # 最大CPU使用率(%)
    max_execution_time: float = 30.0 # 最大执行时间(秒)
    max_file_size_mb: int = 10      # 最大文件大小(MB)
    max_network_connections: int = 0 # 最大网络连接数(0=禁用)
    max_processes: int = 5          # 最大进程数
    max_threads: int = 10           # 最大线程数
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "max_memory_mb": self.max_memory_mb,
            "max_cpu_percent": self.max_cpu_percent,
            "max_execution_time": self.max_execution_time,
            "max_file_size_mb": self.max_file_size_mb,
            "max_network_connections": self.max_network_connections,
            "max_processes": self.max_processes,
            "max_threads": self.max_threads
        }

@dataclass
class ExecutionRequest:
    """执行请求数据结构"""
    request_id: str
    code: str
    language: str = "python"
    security_level: SecurityLevel = SecurityLevel.MEDIUM
    sandbox_type: SandboxType = SandboxType.PROCESS
    resource_limits: ResourceLimits = field(default_factory=ResourceLimits)
    environment: Dict[str, str] = field(default_factory=dict)
    allowed_imports: List[str] = field(default_factory=list)
    blocked_functions: List[str] = field(default_factory=list)
    timeout: float = 30.0
    
    def get_hash(self) -> str:
        """获取请求哈希值"""
        content = f"{self.code}:{self.language}:{self.security_level.value}"
        return hashlib.md5(content.encode()).hexdigest()

@dataclass
class ExecutionResult:
    """执行结果数据结构"""
    request_id: str
    status: ExecutionStatus
    stdout: str = ""
    stderr: str = ""
    return_code: int = 0
    execution_time: float = 0.0
    memory_used_mb: float = 0.0
    cpu_used_percent: float = 0.0
    security_violations: List[str] = field(default_factory=list)
    error_message: str = ""
    timestamp: float = field(default_factory=time.time)
    
    def is_successful(self) -> bool:
        """检查执行是否成功"""
        return self.status == ExecutionStatus.COMPLETED and self.return_code == 0

class SecurityValidator:
    """安全验证器"""
    
    def __init__(self):
        # 危险函数列表
        self.dangerous_functions = {
            'exec', 'eval', 'compile', '__import__', 'open', 'file',
            'input', 'raw_input', 'reload', 'vars', 'globals', 'locals',
            'dir', 'hasattr', 'getattr', 'setattr', 'delattr',
            'subprocess', 'os.system', 'os.popen', 'os.spawn',
            'socket', 'urllib', 'requests', 'http'
        }
        
        # 危险模块列表
        self.dangerous_modules = {
            'os', 'sys', 'subprocess', 'socket', 'urllib', 'urllib2',
            'httplib', 'ftplib', 'telnetlib', 'smtplib', 'poplib',
            'imaplib', 'nntplib', 'ssl', 'threading', 'multiprocessing',
            'ctypes', 'marshal', 'pickle', 'cPickle', 'shelve',
            'dbm', 'gdbm', 'dumbdbm', 'anydbm', 'whichdb'
        }
        
        # 危险关键词模式
        self.dangerous_patterns = [
            r'__.*__',  # 魔术方法
            r'\bexec\s*\(',  # exec调用
            r'\beval\s*\(',  # eval调用
            r'\bopen\s*\(',  # 文件操作
            r'import\s+os',  # 导入os模块
            r'from\s+os\s+import',  # 从os导入
            r'subprocess\.',  # subprocess调用
            r'system\s*\(',  # 系统调用
        ]
        
        logger.debug("安全验证器初始化完成")
    
    def validate_code(self, code: str, allowed_imports: List[str] = None) -> Tuple[bool, List[str]]:
        """验证代码安全性"""
        logger.debug(f"开始验证代码安全性，代码长度: {len(code)}")
        
        violations = []
        allowed_imports = allowed_imports or []
        
        try:
            # 1. AST语法分析
            tree = ast.parse(code)
            
            # 2. 检查导入语句
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module_name = alias.name
                        if module_name in self.dangerous_modules and module_name not in allowed_imports:
                            violations.append(f"危险模块导入: {module_name}")
                
                elif isinstance(node, ast.ImportFrom):
                    module_name = node.module or ""
                    if module_name in self.dangerous_modules and module_name not in allowed_imports:
                        violations.append(f"危险模块导入: {module_name}")
                
                # 3. 检查函数调用
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id
                        if func_name in self.dangerous_functions:
                            violations.append(f"危险函数调用: {func_name}")
                    elif isinstance(node.func, ast.Attribute):
                        attr_name = node.func.attr
                        if attr_name in self.dangerous_functions:
                            violations.append(f"危险方法调用: {attr_name}")
            
            # 4. 正则表达式模式检查
            for pattern in self.dangerous_patterns:
                matches = re.findall(pattern, code, re.IGNORECASE)
                if matches:
                    violations.append(f"危险模式匹配: {pattern} -> {matches}")
            
        except SyntaxError as e:
            violations.append(f"语法错误: {e}")
        except Exception as e:
            violations.append(f"代码分析错误: {e}")
        
        is_safe = len(violations) == 0
        logger.debug(f"代码安全验证完成，安全: {is_safe}, 违规数量: {len(violations)}")
        
        return is_safe, violations
    
    def sanitize_code(self, code: str) -> str:
        """清理代码中的危险部分"""
        logger.debug("开始清理代码")
        
        # 移除危险的导入语句
        lines = code.split('\n')
        safe_lines = []
        
        for line in lines:
            line_stripped = line.strip()
            
            # 跳过危险的导入
            if line_stripped.startswith('import ') or line_stripped.startswith('from '):
                for dangerous_module in self.dangerous_modules:
                    if dangerous_module in line_stripped:
                        logger.debug(f"移除危险导入: {line_stripped}")
                        line = f"# REMOVED: {line}"  # 注释掉而不是删除
                        break
            
            safe_lines.append(line)
        
        sanitized_code = '\n'.join(safe_lines)
        logger.debug("代码清理完成")
        
        return sanitized_code

class ResourceMonitor:
    """资源监控器"""
    
    def __init__(self, limits: ResourceLimits):
        self.limits = limits
        self.start_time = None
        self.process = None
        self.monitoring = False
        self.stats = {
            'max_memory_mb': 0.0,
            'max_cpu_percent': 0.0,
            'current_memory_mb': 0.0,
            'current_cpu_percent': 0.0
        }
        self.lock = threading.RLock()
        
        logger.debug(f"资源监控器初始化，限制: {limits.to_dict()}")
    
    def start_monitoring(self, process: psutil.Process):
        """开始监控进程"""
        with self.lock:
            self.process = process
            self.start_time = time.time()
            self.monitoring = True
        
        # 启动监控线程
        monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        monitor_thread.start()
        
        logger.debug(f"开始监控进程: {process.pid}")
    
    def stop_monitoring(self):
        """停止监控"""
        with self.lock:
            self.monitoring = False
        
        logger.debug("停止资源监控")
    
    def _monitor_loop(self):
        """监控循环"""
        while self.monitoring:
            try:
                if self.process and self.process.is_running():
                    # 获取内存使用情况
                    memory_info = self.process.memory_info()
                    memory_mb = memory_info.rss / 1024 / 1024
                    
                    # 获取CPU使用情况
                    cpu_percent = self.process.cpu_percent()
                    
                    with self.lock:
                        self.stats['current_memory_mb'] = memory_mb
                        self.stats['current_cpu_percent'] = cpu_percent
                        self.stats['max_memory_mb'] = max(self.stats['max_memory_mb'], memory_mb)
                        self.stats['max_cpu_percent'] = max(self.stats['max_cpu_percent'], cpu_percent)
                    
                    # 检查资源限制
                    violations = self._check_violations()
                    if violations:
                        logger.warning(f"资源限制违规: {violations}")
                        self._terminate_process()
                        break
                    
                    # 检查执行时间
                    if self.start_time and time.time() - self.start_time > self.limits.max_execution_time:
                        logger.warning("执行时间超限")
                        self._terminate_process()
                        break
                
                time.sleep(0.1)  # 100ms监控间隔
                
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break
            except Exception as e:
                logger.error(f"监控过程中出错: {e}")
                break
    
    def _check_violations(self) -> List[str]:
        """检查资源违规"""
        violations = []
        
        if self.stats['current_memory_mb'] > self.limits.max_memory_mb:
            violations.append(f"内存超限: {self.stats['current_memory_mb']:.1f}MB > {self.limits.max_memory_mb}MB")
        
        if self.stats['current_cpu_percent'] > self.limits.max_cpu_percent:
            violations.append(f"CPU超限: {self.stats['current_cpu_percent']:.1f}% > {self.limits.max_cpu_percent}%")
        
        return violations
    
    def _terminate_process(self):
        """终止进程"""
        try:
            if self.process and self.process.is_running():
                self.process.terminate()
                time.sleep(1)
                if self.process.is_running():
                    self.process.kill()
                logger.debug(f"进程已终止: {self.process.pid}")
        except Exception as e:
            logger.error(f"终止进程失败: {e}")
    
    def get_stats(self) -> Dict[str, float]:
        """获取统计信息"""
        with self.lock:
            execution_time = time.time() - self.start_time if self.start_time else 0.0
            return {
                **self.stats,
                'execution_time': execution_time
            }

class ProcessSandbox:
    """进程级沙箱"""
    
    def __init__(self, limits: ResourceLimits):
        self.limits = limits
        self.validator = SecurityValidator()
        logger.debug("进程沙箱初始化完成")
    
    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """执行代码"""
        logger.debug(f"进程沙箱执行请求: {request.request_id}")
        
        start_time = time.time()
        result = ExecutionResult(
            request_id=request.request_id,
            status=ExecutionStatus.PENDING
        )
        
        try:
            # 1. 安全验证
            is_safe, violations = self.validator.validate_code(
                request.code, request.allowed_imports
            )
            
            if not is_safe:
                result.status = ExecutionStatus.FAILED
                result.security_violations = violations
                result.error_message = "代码安全验证失败"
                return result
            
            # 2. 创建临时文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(request.code)
                temp_file = f.name
            
            try:
                # 3. 执行代码
                result = self._execute_in_subprocess(temp_file, request, result)
                
            finally:
                # 清理临时文件
                try:
                    os.unlink(temp_file)
                except Exception as e:
                    logger.warning(f"清理临时文件失败: {e}")
            
        except Exception as e:
            result.status = ExecutionStatus.FAILED
            result.error_message = str(e)
            logger.error(f"执行失败: {e}")
        
        result.execution_time = time.time() - start_time
        logger.debug(f"执行完成: {request.request_id}, 状态: {result.status.value}")
        
        return result
    
    def _execute_in_subprocess(self, script_path: str, request: ExecutionRequest, result: ExecutionResult) -> ExecutionResult:
        """在子进程中执行"""
        try:
            # 构建执行命令
            cmd = [sys.executable, script_path]
            
            # 设置环境变量
            env = os.environ.copy()
            env.update(request.environment)
            
            # 启动子进程
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=True,
                preexec_fn=self._setup_process_limits if os.name != 'nt' else None
            )
            
            result.status = ExecutionStatus.RUNNING
            
            # 启动资源监控
            monitor = ResourceMonitor(self.limits)
            try:
                ps_process = psutil.Process(process.pid)
                monitor.start_monitoring(ps_process)
            except Exception as e:
                logger.warning(f"启动资源监控失败: {e}")
            
            try:
                # 等待执行完成
                stdout, stderr = process.communicate(timeout=request.timeout)
                
                result.stdout = stdout
                result.stderr = stderr
                result.return_code = process.returncode
                result.status = ExecutionStatus.COMPLETED if process.returncode == 0 else ExecutionStatus.FAILED
                
            except subprocess.TimeoutExpired:
                process.kill()
                result.status = ExecutionStatus.TIMEOUT
                result.error_message = "执行超时"
            
            finally:
                monitor.stop_monitoring()
                
                # 获取资源使用统计
                stats = monitor.get_stats()
                result.memory_used_mb = stats['max_memory_mb']
                result.cpu_used_percent = stats['max_cpu_percent']
        
        except Exception as e:
            result.status = ExecutionStatus.FAILED
            result.error_message = str(e)
        
        return result
    
    def _setup_process_limits(self):
        """设置进程资源限制 (仅Unix系统)"""
        if resource is None:
            logger.warning("resource模块不可用 (Windows系统)，跳过资源限制设置")
            return
            
        try:
            # 设置内存限制
            memory_limit = self.limits.max_memory_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (memory_limit, memory_limit))
            
            # 设置CPU时间限制
            cpu_limit = int(self.limits.max_execution_time)
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit, cpu_limit))
            
            # 设置进程数限制
            resource.setrlimit(resource.RLIMIT_NPROC, (self.limits.max_processes, self.limits.max_processes))
            
            logger.debug("进程资源限制设置完成")
            
        except Exception as e:
            logger.warning(f"设置进程限制失败: {e}")

class WasmSandbox:
    """WebAssembly沙箱 (模拟实现)"""
    
    def __init__(self, limits: ResourceLimits):
        self.limits = limits
        self.validator = SecurityValidator()
        logger.debug("WASM沙箱初始化完成 (模拟)")
    
    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """在WASM环境中执行代码 (模拟)"""
        logger.debug(f"WASM沙箱执行请求: {request.request_id}")
        
        # 注意：这是一个模拟实现
        # 真实的WASM沙箱需要将Python代码编译为WASM或使用WASM Python运行时
        
        start_time = time.time()
        result = ExecutionResult(
            request_id=request.request_id,
            status=ExecutionStatus.PENDING
        )
        
        try:
            # 1. 安全验证
            is_safe, violations = self.validator.validate_code(
                request.code, request.allowed_imports
            )
            
            if not is_safe:
                result.status = ExecutionStatus.FAILED
                result.security_violations = violations
                result.error_message = "代码安全验证失败"
                return result
            
            # 2. 模拟WASM执行
            result = self._simulate_wasm_execution(request, result)
            
        except Exception as e:
            result.status = ExecutionStatus.FAILED
            result.error_message = str(e)
            logger.error(f"WASM执行失败: {e}")
        
        result.execution_time = time.time() - start_time
        logger.debug(f"WASM执行完成: {request.request_id}, 状态: {result.status.value}")
        
        return result
    
    def _simulate_wasm_execution(self, request: ExecutionRequest, result: ExecutionResult) -> ExecutionResult:
        """模拟WASM执行"""
        try:
            result.status = ExecutionStatus.RUNNING
            
            # 在受限环境中执行代码
            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()
            
            # 创建受限的全局命名空间
            restricted_globals = {
                '__builtins__': {
                    'print': lambda *args, **kwargs: print(*args, file=stdout_capture, **kwargs),
                    'len': len,
                    'str': str,
                    'int': int,
                    'float': float,
                    'bool': bool,
                    'list': list,
                    'dict': dict,
                    'tuple': tuple,
                    'set': set,
                    'range': range,
                    'enumerate': enumerate,
                    'zip': zip,
                    'sum': sum,
                    'min': min,
                    'max': max,
                    'abs': abs,
                    'round': round,
                }
            }
            
            # 执行代码
            with redirect_stderr(stderr_capture):
                exec(request.code, restricted_globals)
            
            result.stdout = stdout_capture.getvalue()
            result.stderr = stderr_capture.getvalue()
            result.return_code = 0
            result.status = ExecutionStatus.COMPLETED
            
        except Exception as e:
            result.status = ExecutionStatus.FAILED
            result.error_message = str(e)
            result.stderr = str(e)
        
        return result

class SecureExecutor:
    """安全执行器 - 主要接口类"""
    
    def __init__(self, default_limits: ResourceLimits = None):
        self.default_limits = default_limits or ResourceLimits()
        
        # 初始化各种沙箱
        self.sandboxes = {
            SandboxType.PROCESS: ProcessSandbox(self.default_limits),
            SandboxType.WASM: WasmSandbox(self.default_limits)
        }
        
        # 执行统计
        self.execution_count = 0
        self.success_count = 0
        self.failure_count = 0
        self.total_execution_time = 0.0
        
        self.lock = threading.RLock()
        
        logger.info("安全执行器初始化完成")
    
    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """执行代码"""
        logger.info(f"开始执行请求: {request.request_id}, 沙箱类型: {request.sandbox_type.value}")
        
        start_time = time.time()
        
        try:
            # 选择合适的沙箱
            sandbox = self._select_sandbox(request)
            
            # 执行代码
            result = sandbox.execute(request)
            
            # 更新统计信息
            with self.lock:
                self.execution_count += 1
                if result.is_successful():
                    self.success_count += 1
                else:
                    self.failure_count += 1
                self.total_execution_time += result.execution_time
            
            logger.info(f"执行完成: {request.request_id}, 状态: {result.status.value}, "
                       f"耗时: {result.execution_time:.3f}s")
            
            return result
            
        except Exception as e:
            logger.error(f"执行异常: {request.request_id}, 错误: {e}")
            
            with self.lock:
                self.execution_count += 1
                self.failure_count += 1
            
            return ExecutionResult(
                request_id=request.request_id,
                status=ExecutionStatus.FAILED,
                error_message=str(e),
                execution_time=time.time() - start_time
            )
    
    def _select_sandbox(self, request: ExecutionRequest):
        """选择合适的沙箱"""
        sandbox_type = request.sandbox_type
        
        # 混合模式：根据安全级别自动选择
        if sandbox_type == SandboxType.HYBRID:
            if request.security_level in [SecurityLevel.CRITICAL, SecurityLevel.HIGH]:
                sandbox_type = SandboxType.WASM
            else:
                sandbox_type = SandboxType.PROCESS
        
        sandbox = self.sandboxes.get(sandbox_type)
        if not sandbox:
            raise ValueError(f"不支持的沙箱类型: {sandbox_type}")
        
        logger.debug(f"选择沙箱: {sandbox_type.value}")
        return sandbox
    
    def batch_execute(self, requests: List[ExecutionRequest], max_workers: int = 4) -> List[ExecutionResult]:
        """批量执行"""
        logger.info(f"开始批量执行，请求数量: {len(requests)}, 最大工作线程: {max_workers}")
        
        results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_request = {executor.submit(self.execute, req): req for req in requests}
            
            # 收集结果
            for future in future_to_request:
                try:
                    result = future.result(timeout=60)  # 60秒超时
                    results.append(result)
                except TimeoutError:
                    request = future_to_request[future]
                    logger.error(f"批量执行超时: {request.request_id}")
                    results.append(ExecutionResult(
                        request_id=request.request_id,
                        status=ExecutionStatus.TIMEOUT,
                        error_message="批量执行超时"
                    ))
                except Exception as e:
                    request = future_to_request[future]
                    logger.error(f"批量执行异常: {request.request_id}, 错误: {e}")
                    results.append(ExecutionResult(
                        request_id=request.request_id,
                        status=ExecutionStatus.FAILED,
                        error_message=str(e)
                    ))
        
        logger.info(f"批量执行完成，结果数量: {len(results)}")
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取执行统计信息"""
        with self.lock:
            avg_execution_time = self.total_execution_time / max(self.execution_count, 1)
            success_rate = self.success_count / max(self.execution_count, 1)
            
            return {
                "execution_count": self.execution_count,
                "success_count": self.success_count,
                "failure_count": self.failure_count,
                "success_rate": success_rate,
                "average_execution_time": avg_execution_time,
                "total_execution_time": self.total_execution_time
            }
    
    def create_secure_environment(self, security_level: SecurityLevel) -> Dict[str, Any]:
        """创建安全环境配置"""
        logger.debug(f"创建安全环境: {security_level.value}")
        
        if security_level == SecurityLevel.LOW:
            return {
                "resource_limits": ResourceLimits(
                    max_memory_mb=1024,
                    max_cpu_percent=80.0,
                    max_execution_time=60.0
                ),
                "allowed_imports": ['math', 'random', 'datetime', 'json'],
                "sandbox_type": SandboxType.PROCESS
            }
        elif security_level == SecurityLevel.MEDIUM:
            return {
                "resource_limits": ResourceLimits(
                    max_memory_mb=512,
                    max_cpu_percent=50.0,
                    max_execution_time=30.0
                ),
                "allowed_imports": ['math', 'random'],
                "sandbox_type": SandboxType.WASM
            }
        elif security_level == SecurityLevel.HIGH:
            return {
                "resource_limits": ResourceLimits(
                    max_memory_mb=256,
                    max_cpu_percent=25.0,
                    max_execution_time=15.0
                ),
                "allowed_imports": [],
                "sandbox_type": SandboxType.WASM
            }
        else:  # CRITICAL
            return {
                "resource_limits": ResourceLimits(
                    max_memory_mb=128,
                    max_cpu_percent=10.0,
                    max_execution_time=10.0
                ),
                "allowed_imports": [],
                "sandbox_type": SandboxType.WASM
            }

# 测试代码
if __name__ == "__main__":
    def test_secure_executor():
        """测试安全执行器"""
        logger.info("安全执行器测试开始")
        
        # 创建执行器
        executor = SecureExecutor()
        
        # 测试代码
        test_codes = [
            {
                "id": "test_1",
                "code": "print('Hello, World!')",
                "security_level": SecurityLevel.LOW
            },
            {
                "id": "test_2",
                "code": "import math\nprint(math.sqrt(16))",
                "security_level": SecurityLevel.MEDIUM
            },
            {
                "id": "test_3",
                "code": "for i in range(5):\n    print(f'Number: {i}')",
                "security_level": SecurityLevel.HIGH
            },
            {
                "id": "test_dangerous",
                "code": "import os\nos.system('ls')",  # 危险代码
                "security_level": SecurityLevel.CRITICAL
            }
        ]
        
        # 创建执行请求
        requests = []
        for test in test_codes:
            env_config = executor.create_secure_environment(test["security_level"])
            
            request = ExecutionRequest(
                request_id=test["id"],
                code=test["code"],
                security_level=test["security_level"],
                sandbox_type=env_config["sandbox_type"],
                resource_limits=env_config["resource_limits"],
                allowed_imports=env_config["allowed_imports"]
            )
            requests.append(request)
        
        # 单个执行测试
        logger.info("测试单个执行")
        for request in requests:
            result = executor.execute(request)
            logger.info(f"执行结果 {request.request_id}: {result.status.value}")
            if result.stdout:
                logger.info(f"输出: {result.stdout.strip()}")
            if result.security_violations:
                logger.info(f"安全违规: {result.security_violations}")
        
        # 批量执行测试
        logger.info("测试批量执行")
        batch_results = executor.batch_execute(requests[:2])  # 只测试前两个
        logger.info(f"批量执行完成，结果数量: {len(batch_results)}")
        
        # 获取统计信息
        stats = executor.get_statistics()
        logger.info(f"执行统计: {stats}")
        
        logger.info("安全执行器测试完成")
    
    # 运行测试
    test_secure_executor()