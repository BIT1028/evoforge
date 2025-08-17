#!/usr/bin/env python3
"""
SiliconFlow API集成服务 - 甲骨文
"""
import aiohttp
import json
import time
from typing import Optional
import structlog

from app.core.config import settings
from app.schemas.evaluation import OracleEvaluationResult
from app.models.evaluation import ApiCost
from app.core.database import SessionLocal

logger = structlog.get_logger()

class OracleService:
    """SiliconFlow API集成服务"""
    
    def __init__(self):
        self.api_key = settings.SILICONFLOW_API_KEY
        self.base_url = settings.SILICONFLOW_BASE_URL
        self.model = settings.SILICONFLOW_MODEL
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """获取HTTP会话"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def evaluate_code(self, code: str, task_description: str) -> OracleEvaluationResult:
        """使用甲骨文评估代码质量"""
        if not self.api_key:
            logger.warning("SiliconFlow API密钥未配置，使用模拟评估")
            return self._mock_evaluation(code, task_description)
        
        try:
            prompt = self._build_evaluation_prompt(code, task_description)
            start_time = time.time()
            
            response_data = await self._call_api(prompt)
            
            execution_time = time.time() - start_time
            
            # 解析响应
            result = self._parse_evaluation_response(response_data)
            
            # 记录API成本
            await self._record_api_cost(response_data, execution_time)
            
            logger.info("代码评估完成", 
                       overall_score=result.overall_score,
                       cost=result.cost,
                       execution_time=execution_time)
            
            return result
            
        except Exception as e:
            logger.error("代码评估失败", error=str(e))
            # 返回默认评估结果
            return OracleEvaluationResult(
                scores={"correctness": 50, "quality": 50, "efficiency": 50, "innovation": 50},
                overall_score=50.0,
                feedback=f"评估失败: {str(e)}",
                cost=0.0,
                input_tokens=0,
                output_tokens=0
            )
    
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
    
    async def _call_api(self, prompt: str) -> dict:
        """调用SiliconFlow API"""
        session = await self._get_session()
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个专业的代码评估专家，专门评估Python代码的质量和正确性。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1,
            "max_tokens": 1000,
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
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"API调用失败: {response.status} - {error_text}")
            
            return await response.json()
    
    def _parse_evaluation_response(self, response_data: dict) -> OracleEvaluationResult:
        """解析评估响应"""
        try:
            # 提取响应内容
            content = response_data["choices"][0]["message"]["content"]
            
            # 尝试解析JSON
            try:
                # 清理响应内容，移除可能的markdown标记
                content = content.strip()
                if content.startswith("```json"):
                    content = content[7:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()
                
                evaluation_data = json.loads(content)
            except json.JSONDecodeError:
                # 如果JSON解析失败，尝试提取数字
                logger.warning("JSON解析失败，使用默认评估")
                evaluation_data = {
                    "scores": {"correctness": 60, "quality": 60, "efficiency": 60, "innovation": 60},
                    "overall_score": 60,
                    "feedback": "评估响应格式错误"
                }
            
            # 计算成本
            usage = response_data.get("usage", {})
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            
            # SiliconFlow定价（示例，实际价格请参考官方文档）
            input_cost_per_token = 0.0000005  # $0.0005 per 1K tokens
            output_cost_per_token = 0.0000015  # $0.0015 per 1K tokens
            
            total_cost = (input_tokens * input_cost_per_token + 
                         output_tokens * output_cost_per_token)
            
            return OracleEvaluationResult(
                scores=evaluation_data.get("scores", {}),
                overall_score=float(evaluation_data.get("overall_score", 0)),
                feedback=evaluation_data.get("feedback", "无反馈"),
                cost=total_cost,
                input_tokens=input_tokens,
                output_tokens=output_tokens
            )
            
        except Exception as e:
            logger.error("解析评估响应失败", error=str(e))
            return OracleEvaluationResult(
                scores={"correctness": 50, "quality": 50, "efficiency": 50, "innovation": 50},
                overall_score=50.0,
                feedback=f"响应解析失败: {str(e)}",
                cost=0.0,
                input_tokens=0,
                output_tokens=0
            )
    
    def _mock_evaluation(self, code: str, task_description: str) -> OracleEvaluationResult:
        """模拟评估（当API密钥未配置时使用）"""
        import random
        
        # 基于代码长度和复杂度的简单评估
        code_length = len(code)
        line_count = len(code.split('\n'))
        
        # 模拟评分
        base_score = 60
        length_bonus = min(20, code_length // 10)
        complexity_bonus = min(15, line_count * 2)
        
        correctness = base_score + length_bonus + random.randint(-10, 10)
        quality = base_score + complexity_bonus + random.randint(-10, 10)
        efficiency = base_score + random.randint(-15, 15)
        innovation = base_score + random.randint(-20, 20)
        
        # 确保分数在合理范围内
        correctness = max(0, min(100, correctness))
        quality = max(0, min(100, quality))
        efficiency = max(0, min(100, efficiency))
        innovation = max(0, min(100, innovation))
        
        overall_score = (correctness + quality + efficiency + innovation) / 4
        
        return OracleEvaluationResult(
            scores={
                "correctness": correctness,
                "quality": quality,
                "efficiency": efficiency,
                "innovation": innovation
            },
            overall_score=overall_score,
            feedback=f"模拟评估结果。代码长度: {code_length}, 行数: {line_count}",
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
            
            # 计算成本
            input_cost_per_token = 0.0000005
            output_cost_per_token = 0.0000015
            total_cost = (input_tokens * input_cost_per_token + 
                         output_tokens * output_cost_per_token)
            
            # 保存到数据库
            db = SessionLocal()
            try:
                api_cost = ApiCost(
                    service_name="SiliconFlow",
                    model_name=self.model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost_usd=total_cost
                )
                db.add(api_cost)
                db.commit()
                
                logger.debug("API成本记录完成", 
                           cost=total_cost,
                           input_tokens=input_tokens,
                           output_tokens=output_tokens)
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error("记录API成本失败", error=str(e))
    
    async def close(self):
        """关闭HTTP会话"""
        if self.session:
            await self.session.close()
            self.session = None