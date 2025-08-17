#!/usr/bin/env python3
"""
评估相关的Pydantic schemas
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class EvaluationResponse(BaseModel):
    """评估响应"""
    id: str = Field(description="评估日志ID")
    digital_cell_id: str = Field(description="数字细胞ID")
    task_id: str = Field(description="任务ID")
    oracle_request: Optional[str] = Field(description="甲骨文请求")
    oracle_response: Optional[str] = Field(description="甲骨文响应")
    fitness_score: Optional[float] = Field(description="适应度分数")
    api_cost: Optional[float] = Field(description="API成本")
    execution_time: Optional[float] = Field(description="执行时间")
    created_at: datetime = Field(description="创建时间")
    
    class Config:
        from_attributes = True

class ApiCostResponse(BaseModel):
    """API成本响应"""
    id: int = Field(description="成本记录ID")
    service_name: str = Field(description="服务名称")
    model_name: Optional[str] = Field(description="模型名称")
    input_tokens: Optional[int] = Field(description="输入token数")
    output_tokens: Optional[int] = Field(description="输出token数")
    cost_usd: Optional[float] = Field(description="成本（美元）")
    created_at: datetime = Field(description="创建时间")
    
    class Config:
        from_attributes = True

class OracleEvaluationRequest(BaseModel):
    """甲骨文评估请求"""
    code: str = Field(description="待评估的代码")
    task_description: str = Field(description="任务描述")
    cell_id: Optional[int] = Field(None, description="数字细胞ID")
    task_id: Optional[int] = Field(None, description="任务ID")
    provider: Optional[str] = Field(None, description="Oracle提供商 (openai/siliconflow/auto)")
    
class OracleEvaluationResult(BaseModel):
    """甲骨文评估结果"""
    scores: dict = Field(description="各维度评分")
    overall_score: float = Field(description="总体评分")
    feedback: str = Field(description="详细反馈")
    cost: float = Field(description="API调用成本")
    input_tokens: int = Field(description="输入token数")
    output_tokens: int = Field(description="输出token数")
    provider_used: str = Field(description="实际使用的提供商")

class ExecutionResult(BaseModel):
    """代码执行结果"""
    success: bool = Field(description="是否执行成功")
    output: Optional[str] = Field(description="执行输出")
    error: Optional[str] = Field(description="错误信息")
    execution_time: float = Field(description="执行时间")
    memory_usage: Optional[float] = Field(description="内存使用量")