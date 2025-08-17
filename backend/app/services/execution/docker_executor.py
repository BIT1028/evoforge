#!/usr/bin/env python3
"""
Docker代码执行服务
"""
import asyncio
import docker
import tempfile
import os
import time
from typing import Optional, Dict, Any
import structlog

from app.core.config import settings
from app.schemas.evaluation import ExecutionResult

logger = structlog.get_logger()

class DockerExecutor:
    """Docker代码执行器"""
    
    def __init__(self):
        self.client: Optional[docker.DockerClient] = None
        self.image = settings.DOCKER_SANDBOX_IMAGE
        self.memory_limit = settings.DOCKER_MEMORY_LIMIT
        self.cpu_limit = settings.DOCKER_CPU_LIMIT
        self.timeout = settings.DOCKER_TIMEOUT
    
    def _get_client(self) -> docker.DockerClient:
        """获取Docker客户端"""
        if not self.client:
            try:
                self.client = docker.from_env()
                # 测试连接
                self.client.ping()
                logger.info("Docker客户端连接成功")
            except Exception as e:
                logger.error("Docker客户端连接失败", error=str(e))
                raise Exception(f"无法连接到Docker: {str(e)}")
        return self.client
    
    async def execute_code(self, code: str, test_input: str = "") -> ExecutionResult:
        """执行Python代码"""
        try:
            # 在线程池中执行Docker操作
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                self._execute_code_sync, 
                code, 
                test_input
            )
            return result
            
        except Exception as e:
            logger.error("代码执行失败", error=str(e))
            return ExecutionResult(
                success=False,
                output="",
                error=f"执行失败: {str(e)}",
                execution_time=0.0,
                memory_usage=0,
                exit_code=-1
            )
    
    def _execute_code_sync(self, code: str, test_input: str = "") -> ExecutionResult:
        """同步执行代码"""
        client = self._get_client()
        
        # 创建临时文件
        with tempfile.TemporaryDirectory() as temp_dir:
            # 写入代码文件
            code_file = os.path.join(temp_dir, "main.py")
            with open(code_file, "w", encoding="utf-8") as f:
                f.write(code)
            
            # 写入输入文件（如果有）
            input_file = os.path.join(temp_dir, "input.txt")
            if test_input:
                with open(input_file, "w", encoding="utf-8") as f:
                    f.write(test_input)
            
            # 准备执行命令
            if test_input:
                command = "python main.py < input.txt"
            else:
                command = "python main.py"
            
            start_time = time.time()
            
            try:
                # 运行容器
                container = client.containers.run(
                    image=self.image,
                    command=f"sh -c '{command}'",
                    volumes={temp_dir: {"bind": "/workspace", "mode": "rw"}},
                    working_dir="/workspace",
                    mem_limit=self.memory_limit,
                    cpu_quota=int(self.cpu_limit * 100000),  # CPU限制
                    cpu_period=100000,
                    network_disabled=True,  # 禁用网络访问
                    remove=True,  # 执行完成后自动删除容器
                    detach=False,
                    stdout=True,
                    stderr=True,
                    timeout=self.timeout
                )
                
                execution_time = time.time() - start_time
                
                # 获取输出
                output = container.decode('utf-8') if isinstance(container, bytes) else str(container)
                
                return ExecutionResult(
                    success=True,
                    output=output,
                    error="",
                    execution_time=execution_time,
                    memory_usage=0,  # Docker stats需要额外API调用
                    exit_code=0
                )
                
            except docker.errors.ContainerError as e:
                execution_time = time.time() - start_time
                
                # 容器执行错误
                stderr_output = e.stderr.decode('utf-8') if e.stderr else ""
                stdout_output = e.stdout.decode('utf-8') if e.stdout else ""
                
                return ExecutionResult(
                    success=False,
                    output=stdout_output,
                    error=stderr_output or f"容器执行错误: {str(e)}",
                    execution_time=execution_time,
                    memory_usage=0,
                    exit_code=e.exit_status
                )
                
            except Exception as e:
                execution_time = time.time() - start_time
                
                return ExecutionResult(
                    success=False,
                    output="",
                    error=f"执行异常: {str(e)}",
                    execution_time=execution_time,
                    memory_usage=0,
                    exit_code=-1
                )
    
    async def validate_code_syntax(self, code: str) -> Dict[str, Any]:
        """验证代码语法"""
        try:
            # 使用compile检查语法
            compile(code, '<string>', 'exec')
            return {
                "valid": True,
                "error": None
            }
        except SyntaxError as e:
            return {
                "valid": False,
                "error": f"语法错误: {str(e)}",
                "line": e.lineno,
                "offset": e.offset
            }
        except Exception as e:
            return {
                "valid": False,
                "error": f"验证失败: {str(e)}"
            }
    
    async def execute_with_tests(self, code: str, test_cases: list) -> Dict[str, Any]:
        """使用测试用例执行代码"""
        results = []
        total_passed = 0
        
        for i, test_case in enumerate(test_cases):
            test_input = test_case.get("input", "")
            expected_output = test_case.get("expected", "")
            
            # 执行代码
            result = await self.execute_code(code, test_input)
            
            # 检查输出是否匹配
            actual_output = result.output.strip()
            expected_output = expected_output.strip()
            
            passed = actual_output == expected_output
            if passed:
                total_passed += 1
            
            results.append({
                "test_case": i + 1,
                "input": test_input,
                "expected": expected_output,
                "actual": actual_output,
                "passed": passed,
                "execution_time": result.execution_time,
                "error": result.error
            })
        
        return {
            "total_tests": len(test_cases),
            "passed_tests": total_passed,
            "success_rate": total_passed / len(test_cases) if test_cases else 0,
            "results": results
        }
    
    def ensure_image_available(self) -> bool:
        """确保Docker镜像可用"""
        try:
            client = self._get_client()
            
            # 检查镜像是否存在
            try:
                client.images.get(self.image)
                logger.info("Docker镜像已存在", image=self.image)
                return True
            except docker.errors.ImageNotFound:
                logger.info("Docker镜像不存在，开始拉取", image=self.image)
                
                # 拉取镜像
                client.images.pull(self.image)
                logger.info("Docker镜像拉取完成", image=self.image)
                return True
                
        except Exception as e:
            logger.error("Docker镜像检查失败", error=str(e))
            return False
    
    def close(self):
        """关闭Docker客户端"""
        if self.client:
            self.client.close()
            self.client = None
            logger.info("Docker客户端已关闭")


class MockExecutor:
    """模拟执行器（当Docker不可用时使用）"""
    
    async def execute_code(self, code: str, test_input: str = "") -> ExecutionResult:
        """模拟代码执行"""
        import random
        
        # 简单的语法检查
        try:
            compile(code, '<string>', 'exec')
            syntax_valid = True
        except SyntaxError:
            syntax_valid = False
        
        if not syntax_valid:
            return ExecutionResult(
                success=False,
                output="",
                error="语法错误",
                execution_time=0.1,
                memory_usage=0,
                exit_code=1
            )
        
        # 模拟执行时间
        execution_time = random.uniform(0.1, 2.0)
        
        # 模拟成功率（基于代码复杂度）
        code_complexity = len(code.split('\n'))
        success_probability = max(0.3, min(0.9, 1.0 - code_complexity * 0.02))
        
        if random.random() < success_probability:
            return ExecutionResult(
                success=True,
                output=f"模拟输出 - 代码行数: {code_complexity}",
                error="",
                execution_time=execution_time,
                memory_usage=random.randint(1000, 10000),
                exit_code=0
            )
        else:
            return ExecutionResult(
                success=False,
                output="",
                error="模拟运行时错误",
                execution_time=execution_time,
                memory_usage=0,
                exit_code=1
            )
    
    async def validate_code_syntax(self, code: str) -> Dict[str, Any]:
        """验证代码语法"""
        try:
            compile(code, '<string>', 'exec')
            return {"valid": True, "error": None}
        except SyntaxError as e:
            return {
                "valid": False,
                "error": f"语法错误: {str(e)}",
                "line": e.lineno,
                "offset": e.offset
            }
    
    def ensure_image_available(self) -> bool:
        """模拟镜像检查"""
        return True
    
    def close(self):
        """关闭模拟执行器"""
        pass