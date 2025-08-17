#!/usr/bin/env python3
"""
OpenAI Oracle实现
"""
import aiohttp
import json
import time
from typing import Optional, Dict, Any
import structlog

from .base import BaseOracle, ProviderType, ProviderStatus
from app.schemas.evaluation import OracleEvaluationResult
from app.models.evaluation import ApiCost
from app.core.database import SessionLocal

logger = structlog.get_logger()

class OpenAIOracle(BaseOracle):
    """OpenAI Oracle实现"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(ProviderType.OPENAI, config)
        self.api_key = config.get("api_key")
        self.base_url = config.get("base_url", "https://api.openai.com/v1")
        self.model = config.get("model", "gpt-4o-mini")
        self.session: Optional[aiohttp.ClientSession] = None
        
        # OpenAI定价（每1K tokens的价格，USD）
        self.pricing = {
            "gpt-4o": {"input": 0.005, "output": 0.015},
            "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
            "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015}
        }
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """获取HTTP会话"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def health_check(self) -> bool:
        """健康检查"""
        if not self.api_key:
            self.update_status(ProviderStatus.ERROR, "API密钥未配置")
            return False
            
        try:
            session = await self._get_session()
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # 简单的API调用测试
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 5
            }
            
            async with session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    self.update_status(ProviderStatus.AVAILABLE)
                    return True
                else:
                    error_text = await response.text()
                    self.update_status(ProviderStatus.ERROR, f"HTTP {response.status}: {error_text}")
                    return False
                    
        except Exception as e:
            self.update_status(ProviderStatus.ERROR, str(e))
            return False
    
    async def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "provider": "OpenAI",
            "model": self.model,
            "context_length": self._get_context_length(),
            "pricing": self.pricing.get(self.model, {}),
            "capabilities": ["text_generation", "code_evaluation", "reasoning"]
        }
    
    def _get_context_length(self) -> int:
        """获取模型上下文长度"""
        context_lengths = {
            "gpt-4o": 128000,
            "gpt-4o-mini": 128000,
            "gpt-4-turbo": 128000,
            "gpt-3.5-turbo": 16385
        }
        return context_lengths.get(self.model, 4096)
    
    async def evaluate_code(self, code: str, task_description: str) -> OracleEvaluationResult:
        """评估代码质量"""
        if not self.is_available():
            await self.health_check()
            if not self.is_available():
                return self._create_error_result("OpenAI服务不可用")
        
        try:
            prompt = self._build_evaluation_prompt(code, task_description)
            start_time = time.time()
            
            response_data = await self._call_api(prompt, max_tokens=1000)
            execution_time = time.time() - start_time
            
            result = self._parse_evaluation_response(response_data)
            
            # 记录API成本
            await self._record_api_cost(response_data, execution_time)
            
            self.record_request(True, result.cost)
            
            logger.info("OpenAI代码评估完成", 
                       overall_score=result.overall_score,
                       cost=result.cost,
                       execution_time=execution_time)
            
            return result
            
        except Exception as e:
            self.record_request(False)
            logger.error("OpenAI代码评估失败", error=str(e))
            return self._create_error_result(f"评估失败: {str(e)}")
    
    async def generate_code(self, task_description: str, context: Optional[str] = None) -> str:
        """生成代码"""
        if not self.is_available():
            await self.health_check()
            if not self.is_available():
                raise Exception("OpenAI服务不可用")
        
        try:
            prompt = self._build_generation_prompt(task_description, context)
            
            response_data = await self._call_api(prompt, max_tokens=2000)
            
            # 提取生成的代码
            content = response_data["choices"][0]["message"]["content"]
            code = self._extract_code_from_response(content)
            
            # 记录API成本
            await self._record_api_cost(response_data, 0)
            
            self.record_request(True)
            
            logger.info("OpenAI代码生成完成", code_length=len(code))
            
            return code
            
        except Exception as e:
            self.record_request(False)
            logger.error("OpenAI代码生成失败", error=str(e))
            raise
    
    def _build_evaluation_prompt(self, code: str, task_description: str) -> str:
        """构建评估提示词"""
        return f"""
你是一个专业的代码评估专家。请评估以下Python代码解决指定任务的质量。

任务描述：{task_description}

代码：
```python
{code}
```

请从以下维度评分（0-100分）：
1. 功能正确性 (correctness): 代码是否正确实现了任务要求
2. 代码质量 (quality): 代码的可读性、结构和最佳实践
3. 效率性能 (efficiency): 代码的时间和空间复杂度
4. 创新性 (innovation): 解决方案的创新程度和独特性

请严格按照以下JSON格式返回评估结果：
{{
    "scores": {{
        "correctness": 85,
        "quality": 78,
        "efficiency": 82,
        "innovation": 75
    }},
    "overall_score": 80,
    "feedback": "详细的评估反馈，包括优点和改进建议"
}}

注意：
- 只返回JSON格式的结果，不要包含其他文本
- 分数必须是0-100之间的整数
- overall_score应该是各维度分数的加权平均
- feedback应该提供具体的改进建议
"""
    
    def _build_generation_prompt(self, task_description: str, context: Optional[str] = None) -> str:
        """构建代码生成提示词"""
        context_part = f"\n\n上下文信息：\n{context}" if context else ""
        
        return f"""
你是一个专业的Python程序员。请根据以下任务描述生成高质量的Python代码。

任务描述：{task_description}{context_part}

要求：
1. 代码必须是完整的、可执行的Python函数或类
2. 包含适当的类型注解
3. 添加必要的文档字符串
4. 考虑边界情况和错误处理
5. 遵循Python最佳实践和PEP 8规范
6. 优化时间和空间复杂度

请只返回Python代码，不要包含解释文本。代码应该用```python和```包围。
"""
    
    async def _call_api(self, prompt: str, max_tokens: int = 1000) -> dict:
        """调用OpenAI API"""
        session = await self._get_session()
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个专业的代码评估和生成专家，专门处理Python代码相关任务。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1,
            "max_tokens": max_tokens,
            "top_p": 0.9
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        async with session.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            if response.status == 429:
                self.update_status(ProviderStatus.RATE_LIMITED, "API速率限制")
                raise Exception("API速率限制")
            elif response.status != 200:
                error_text = await response.text()
                self.update_status(ProviderStatus.ERROR, f"HTTP {response.status}: {error_text}")
                raise Exception(f"API调用失败: {response.status} - {error_text}")
            
            return await response.json()
    
    def _parse_evaluation_response(self, response_data: dict) -> OracleEvaluationResult:
        """解析评估响应"""
        try:
            content = response_data["choices"][0]["message"]["content"]
            
            # 清理响应内容
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            evaluation_data = json.loads(content)
            
            # 计算成本
            usage = response_data.get("usage", {})
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            
            pricing = self.pricing.get(self.model, {"input": 0.001, "output": 0.002})
            total_cost = (input_tokens * pricing["input"] / 1000 + 
                         output_tokens * pricing["output"] / 1000)
            
            return OracleEvaluationResult(
                scores=evaluation_data.get("scores", {}),
                overall_score=float(evaluation_data.get("overall_score", 0)),
                feedback=evaluation_data.get("feedback", "无反馈"),
                cost=total_cost,
                input_tokens=input_tokens,
                output_tokens=output_tokens
            )
            
        except Exception as e:
            logger.error("解析OpenAI评估响应失败", error=str(e))
            return self._create_error_result(f"响应解析失败: {str(e)}")
    
    def _extract_code_from_response(self, content: str) -> str:
        """从响应中提取代码"""
        # 查找代码块
        if "```python" in content:
            start = content.find("```python") + 9
            end = content.find("```", start)
            if end != -1:
                return content[start:end].strip()
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            if end != -1:
                return content[start:end].strip()
        
        # 如果没有找到代码块，返回整个内容
        return content.strip()
    
    def _create_error_result(self, error_message: str) -> OracleEvaluationResult:
        """创建错误结果"""
        return OracleEvaluationResult(
            scores={"correctness": 0, "quality": 0, "efficiency": 0, "innovation": 0},
            overall_score=0.0,
            feedback=error_message,
            cost=0.0,
            input_tokens=0,
            output_tokens=0
        )
    
    async def _record_api_cost(self, response_data: dict, execution_time: float):
        """记录API成本"""
        try:
            usage = response_data.get("usage", {})
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            
            pricing = self.pricing.get(self.model, {"input": 0.001, "output": 0.002})
            total_cost = (input_tokens * pricing["input"] / 1000 + 
                         output_tokens * pricing["output"] / 1000)
            
            # 保存到数据库
            db = SessionLocal()
            try:
                api_cost = ApiCost(
                    service_name="OpenAI",
                    model_name=self.model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost_usd=total_cost
                )
                db.add(api_cost)
                db.commit()
                
                logger.debug("OpenAI API成本记录完成", 
                           cost=total_cost,
                           input_tokens=input_tokens,
                           output_tokens=output_tokens)
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error("记录OpenAI API成本失败", error=str(e))
    
    async def close(self):
        """关闭HTTP会话"""
        if self.session:
            await self.session.close()
            self.session = None