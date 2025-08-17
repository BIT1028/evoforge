#!/usr/bin/env python3
"""
简化版沙箱执行器（不依赖Docker）
用于开发和测试阶段
"""
import subprocess
import tempfile
import os
from pathlib import Path
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger()

class SandboxResult:
    """沙箱执行结果"""
    def __init__(self, exit_code: int, stdout: str, stderr: str, duration_sec: float):
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.duration_sec = duration_sec
        self.timed_out = False

class SandboxExecutor:
    """简化版沙箱执行器"""
    
    def __init__(self):
        """初始化沙箱执行器"""
        logger.info("初始化简化版沙箱执行器")
    
    def run_code(self, code: str, timeout_sec: float = 5.0) -> SandboxResult:
        """执行Python代码
        
        Args:
            code: 要执行的Python代码
            timeout_sec: 超时时间（秒）
            
        Returns:
            SandboxResult: 执行结果
        """
        logger.debug("执行代码", code_length=len(code), timeout=timeout_sec)
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # 执行Python代码
            import time
            start_time = time.time()
            
            result = subprocess.run(
                ['python', temp_file],
                capture_output=True,
                text=True,
                timeout=timeout_sec
            )
            
            duration = time.time() - start_time
            
            return SandboxResult(
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                duration_sec=duration
            )
            
        except subprocess.TimeoutExpired:
            logger.warning("代码执行超时", timeout=timeout_sec)
            result = SandboxResult(
                exit_code=-1,
                stdout="",
                stderr="执行超时",
                duration_sec=timeout_sec
            )
            result.timed_out = True
            return result
            
        except Exception as e:
            logger.error("代码执行失败", error=str(e))
            return SandboxResult(
                exit_code=-1,
                stdout="",
                stderr=f"执行失败: {str(e)}",
                duration_sec=0.0
            )
            
        finally:
            # 清理临时文件
            try:
                os.unlink(temp_file)
            except:
                pass