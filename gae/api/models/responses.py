# -*- coding: utf-8 -*-
"""
API响应模型

定义API响应的数据结构：
- 基础响应模型
- 错误响应模型
- 成功响应模型
- 分页响应模型
- 业务特定响应模型
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Generic, TypeVar
from pydantic import BaseModel, Field
from enum import Enum

T = TypeVar('T')

class ResponseStatus(str, Enum):
    """响应状态枚举"""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

class BaseResponse(BaseModel):
    """基础响应模型"""
    status: ResponseStatus = Field(..., description="响应状态")
    message: str = Field(..., description="响应消息")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间戳")
    request_id: Optional[str] = Field(None, description="请求ID")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ErrorResponse(BaseResponse):
    """错误响应模型"""
    status: ResponseStatus = ResponseStatus.ERROR
    error_code: str = Field(..., description="错误代码")
    details: Optional[Dict[str, Any]] = Field(None, description="错误详情")
    trace_id: Optional[str] = Field(None, description="追踪ID")

class SuccessResponse(BaseResponse, Generic[T]):
    """成功响应模型"""
    status: ResponseStatus = ResponseStatus.SUCCESS
    data: T = Field(..., description="响应数据")
    meta: Optional[Dict[str, Any]] = Field(None, description="元数据")

class PaginatedResponse(BaseResponse, Generic[T]):
    """分页响应模型"""
    status: ResponseStatus = ResponseStatus.SUCCESS
    data: List[T] = Field(..., description="数据列表")
    pagination: Dict[str, Any] = Field(..., description="分页信息")
    
    @classmethod
    def create(
        cls,
        data: List[T],
        page: int,
        page_size: int,
        total: int,
        message: str = "查询成功"
    ):
        """创建分页响应"""
        total_pages = (total + page_size - 1) // page_size
        
        return cls(
            message=message,
            data=data,
            pagination={
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        )

# 进化相关响应模型
class EvolutionStatus(str, Enum):
    """进化状态枚举"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"

class EvolutionStatusResponse(BaseResponse):
    """进化状态响应"""
    status: ResponseStatus = ResponseStatus.SUCCESS
    evolution_status: EvolutionStatus = Field(..., description="进化状态")
    current_generation: int = Field(..., description="当前代数")
    population_size: int = Field(..., description="种群大小")
    best_fitness: Optional[float] = Field(None, description="最佳适应度")
    average_fitness: Optional[float] = Field(None, description="平均适应度")
    elapsed_time: float = Field(..., description="已运行时间(秒)")
    estimated_remaining: Optional[float] = Field(None, description="预计剩余时间(秒)")
    
# 任务相关响应模型
class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskResponse(BaseResponse):
    """任务响应"""
    status: ResponseStatus = ResponseStatus.SUCCESS
    task_id: str = Field(..., description="任务ID")
    task_name: str = Field(..., description="任务名称")
    task_status: TaskStatus = Field(..., description="任务状态")
    progress: float = Field(..., description="任务进度(0-100)")
    created_at: datetime = Field(..., description="创建时间")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    result: Optional[Dict[str, Any]] = Field(None, description="任务结果")
    error_message: Optional[str] = Field(None, description="错误信息")

# 实验相关响应模型
class ExperimentStatus(str, Enum):
    """实验状态枚举"""
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"

class ExperimentResponse(BaseResponse):
    """实验响应"""
    status: ResponseStatus = ResponseStatus.SUCCESS
    experiment_id: str = Field(..., description="实验ID")
    name: str = Field(..., description="实验名称")
    description: Optional[str] = Field(None, description="实验描述")
    experiment_status: ExperimentStatus = Field(..., description="实验状态")
    config: Dict[str, Any] = Field(..., description="实验配置")
    created_at: datetime = Field(..., description="创建时间")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    metrics: Optional[Dict[str, Any]] = Field(None, description="实验指标")
    results: Optional[Dict[str, Any]] = Field(None, description="实验结果")

# 评估相关响应模型
class EvaluationResponse(BaseResponse):
    """评估响应"""
    status: ResponseStatus = ResponseStatus.SUCCESS
    evaluation_id: str = Field(..., description="评估ID")
    individual_id: str = Field(..., description="个体ID")
    fitness_scores: Dict[str, float] = Field(..., description="适应度分数")
    overall_fitness: float = Field(..., description="总体适应度")
    evaluation_time: float = Field(..., description="评估耗时(秒)")
    details: Optional[Dict[str, Any]] = Field(None, description="评估详情")
    created_at: datetime = Field(..., description="评估时间")

# 系统相关响应模型
class SystemInfoResponse(BaseResponse):
    """系统信息响应"""
    status: ResponseStatus = ResponseStatus.SUCCESS
    version: str = Field(..., description="系统版本")
    uptime: float = Field(..., description="运行时间(秒)")
    cpu_usage: float = Field(..., description="CPU使用率(%)")
    memory_usage: float = Field(..., description="内存使用率(%)")
    disk_usage: float = Field(..., description="磁盘使用率(%)")
    active_experiments: int = Field(..., description="活跃实验数")
    active_tasks: int = Field(..., description="活跃任务数")
    database_status: str = Field(..., description="数据库状态")
    components: Dict[str, str] = Field(..., description="组件状态")

# WebSocket消息响应模型
class WebSocketMessageType(str, Enum):
    """WebSocket消息类型"""
    EVOLUTION_UPDATE = "evolution_update"
    TASK_UPDATE = "task_update"
    SYSTEM_ALERT = "system_alert"
    EXPERIMENT_UPDATE = "experiment_update"
    ERROR = "error"
    HEARTBEAT = "heartbeat"

class WebSocketMessage(BaseModel):
    """WebSocket消息模型"""
    type: WebSocketMessageType = Field(..., description="消息类型")
    data: Dict[str, Any] = Field(..., description="消息数据")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")
    client_id: Optional[str] = Field(None, description="客户端ID")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# 统计相关响应模型
class StatisticsResponse(BaseResponse):
    """统计信息响应"""
    status: ResponseStatus = ResponseStatus.SUCCESS
    period: str = Field(..., description="统计周期")
    metrics: Dict[str, Any] = Field(..., description="统计指标")
    charts: Optional[Dict[str, List[Dict[str, Any]]]] = Field(None, description="图表数据")
    summary: Dict[str, Any] = Field(..., description="统计摘要")

# 配置相关响应模型
class ConfigResponse(BaseResponse):
    """配置响应"""
    status: ResponseStatus = ResponseStatus.SUCCESS
    config_type: str = Field(..., description="配置类型")
    config_data: Dict[str, Any] = Field(..., description="配置数据")
    last_modified: datetime = Field(..., description="最后修改时间")
    version: str = Field(..., description="配置版本")