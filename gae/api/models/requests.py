# -*- coding: utf-8 -*-
"""
API请求模型

定义API请求的数据结构：
- 进化控制请求
- 任务管理请求
- 实验管理请求
- 评估请求
- 系统配置请求
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, validator
from enum import Enum

# 进化相关请求模型
class EvolutionAlgorithm(str, Enum):
    """进化算法类型"""
    NEAT = "neat"
    NSGA_II = "nsga_ii"
    QD = "quality_diversity"
    HYBRID = "hybrid"

class StartEvolutionRequest(BaseModel):
    """启动进化请求"""
    experiment_id: str = Field(..., description="实验ID")
    algorithm: EvolutionAlgorithm = Field(EvolutionAlgorithm.NEAT, description="进化算法")
    population_size: int = Field(100, ge=10, le=10000, description="种群大小")
    max_generations: int = Field(1000, ge=1, le=100000, description="最大代数")
    target_fitness: Optional[float] = Field(None, ge=0.0, description="目标适应度")
    mutation_rate: float = Field(0.1, ge=0.0, le=1.0, description="变异率")
    crossover_rate: float = Field(0.8, ge=0.0, le=1.0, description="交叉率")
    elitism_rate: float = Field(0.1, ge=0.0, le=1.0, description="精英保留率")
    parallel_evaluations: int = Field(4, ge=1, le=64, description="并行评估数")
    save_interval: int = Field(10, ge=1, description="保存间隔(代数)")
    config: Optional[Dict[str, Any]] = Field(None, description="额外配置")
    
    @validator('config')
    def validate_config(cls, v):
        if v is not None and not isinstance(v, dict):
            raise ValueError('配置必须是字典类型')
        return v

class StopEvolutionRequest(BaseModel):
    """停止进化请求"""
    experiment_id: str = Field(..., description="实验ID")
    save_progress: bool = Field(True, description="是否保存进度")
    reason: Optional[str] = Field(None, description="停止原因")

class PauseEvolutionRequest(BaseModel):
    """暂停进化请求"""
    experiment_id: str = Field(..., description="实验ID")
    save_checkpoint: bool = Field(True, description="是否保存检查点")

class ResumeEvolutionRequest(BaseModel):
    """恢复进化请求"""
    experiment_id: str = Field(..., description="实验ID")
    from_checkpoint: bool = Field(True, description="是否从检查点恢复")
    config_override: Optional[Dict[str, Any]] = Field(None, description="配置覆盖")

# 任务相关请求模型
class TaskType(str, Enum):
    """任务类型"""
    EVOLUTION = "evolution"
    EVALUATION = "evaluation"
    ANALYSIS = "analysis"
    EXPORT = "export"
    CLEANUP = "cleanup"
    BACKUP = "backup"

class TaskPriority(str, Enum):
    """任务优先级"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class CreateTaskRequest(BaseModel):
    """创建任务请求"""
    name: str = Field(..., min_length=1, max_length=255, description="任务名称")
    description: Optional[str] = Field(None, max_length=1000, description="任务描述")
    task_type: TaskType = Field(..., description="任务类型")
    priority: TaskPriority = Field(TaskPriority.NORMAL, description="任务优先级")
    parameters: Dict[str, Any] = Field(..., description="任务参数")
    dependencies: Optional[List[str]] = Field(None, description="依赖任务ID列表")
    scheduled_at: Optional[datetime] = Field(None, description="计划执行时间")
    timeout: Optional[int] = Field(None, ge=1, description="超时时间(秒)")
    retry_count: int = Field(0, ge=0, le=10, description="重试次数")
    tags: Optional[List[str]] = Field(None, description="任务标签")

class UpdateTaskRequest(BaseModel):
    """更新任务请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="任务名称")
    description: Optional[str] = Field(None, max_length=1000, description="任务描述")
    priority: Optional[TaskPriority] = Field(None, description="任务优先级")
    parameters: Optional[Dict[str, Any]] = Field(None, description="任务参数")
    scheduled_at: Optional[datetime] = Field(None, description="计划执行时间")
    timeout: Optional[int] = Field(None, ge=1, description="超时时间(秒)")
    tags: Optional[List[str]] = Field(None, description="任务标签")

class BatchTaskRequest(BaseModel):
    """批量任务操作请求"""
    task_ids: List[str] = Field(..., min_items=1, description="任务ID列表")
    action: str = Field(..., description="操作类型: start, stop, cancel, delete")
    parameters: Optional[Dict[str, Any]] = Field(None, description="操作参数")
    
    @validator('action')
    def validate_action(cls, v):
        allowed_actions = ['start', 'stop', 'cancel', 'delete', 'retry']
        if v not in allowed_actions:
            raise ValueError(f'操作类型必须是: {", ".join(allowed_actions)}')
        return v

# 实验相关请求模型
class CreateExperimentRequest(BaseModel):
    """创建实验请求"""
    name: str = Field(..., min_length=1, max_length=255, description="实验名称")
    description: Optional[str] = Field(None, max_length=2000, description="实验描述")
    config: Dict[str, Any] = Field(..., description="实验配置")
    tags: Optional[List[str]] = Field(None, description="实验标签")
    template_id: Optional[str] = Field(None, description="模板ID")
    parent_experiment_id: Optional[str] = Field(None, description="父实验ID")
    
    @validator('config')
    def validate_config(cls, v):
        required_keys = ['algorithm', 'population_size', 'max_generations']
        for key in required_keys:
            if key not in v:
                raise ValueError(f'配置中缺少必需字段: {key}')
        return v

class UpdateExperimentRequest(BaseModel):
    """更新实验请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="实验名称")
    description: Optional[str] = Field(None, max_length=2000, description="实验描述")
    config: Optional[Dict[str, Any]] = Field(None, description="实验配置")
    tags: Optional[List[str]] = Field(None, description="实验标签")
    status: Optional[str] = Field(None, description="实验状态")

class CloneExperimentRequest(BaseModel):
    """克隆实验请求"""
    source_experiment_id: str = Field(..., description="源实验ID")
    new_name: str = Field(..., min_length=1, max_length=255, description="新实验名称")
    config_override: Optional[Dict[str, Any]] = Field(None, description="配置覆盖")
    copy_data: bool = Field(False, description="是否复制数据")

# 评估相关请求模型
class EvaluationRequest(BaseModel):
    """评估请求"""
    individual_ids: List[str] = Field(..., min_items=1, description="个体ID列表")
    evaluation_type: str = Field("fitness", description="评估类型")
    parameters: Optional[Dict[str, Any]] = Field(None, description="评估参数")
    priority: TaskPriority = Field(TaskPriority.NORMAL, description="评估优先级")
    timeout: Optional[int] = Field(None, ge=1, description="超时时间(秒)")
    parallel: bool = Field(True, description="是否并行评估")
    cache_results: bool = Field(True, description="是否缓存结果")

class BatchEvaluationRequest(BaseModel):
    """批量评估请求"""
    experiment_id: str = Field(..., description="实验ID")
    generation: Optional[int] = Field(None, description="指定代数")
    individual_count: Optional[int] = Field(None, ge=1, description="个体数量")
    evaluation_type: str = Field("fitness", description="评估类型")
    parameters: Optional[Dict[str, Any]] = Field(None, description="评估参数")
    parallel_workers: int = Field(4, ge=1, le=32, description="并行工作者数")

# 系统相关请求模型
class SystemConfigRequest(BaseModel):
    """系统配置请求"""
    config_type: str = Field(..., description="配置类型")
    config_data: Dict[str, Any] = Field(..., description="配置数据")
    validate_only: bool = Field(False, description="仅验证不保存")
    backup_current: bool = Field(True, description="备份当前配置")

class SystemActionRequest(BaseModel):
    """系统操作请求"""
    action: str = Field(..., description="操作类型")
    parameters: Optional[Dict[str, Any]] = Field(None, description="操作参数")
    confirm: bool = Field(False, description="确认执行")
    
    @validator('action')
    def validate_action(cls, v):
        allowed_actions = [
            'restart', 'shutdown', 'cleanup', 'backup', 'restore',
            'clear_cache', 'optimize_db', 'export_logs', 'health_check'
        ]
        if v not in allowed_actions:
            raise ValueError(f'操作类型必须是: {", ".join(allowed_actions)}')
        return v

# 查询相关请求模型
class QueryRequest(BaseModel):
    """查询请求"""
    filters: Optional[Dict[str, Any]] = Field(None, description="过滤条件")
    sort_by: Optional[str] = Field(None, description="排序字段")
    sort_order: str = Field("asc", description="排序顺序: asc, desc")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=1000, description="每页大小")
    include_deleted: bool = Field(False, description="包含已删除记录")
    
    @validator('sort_order')
    def validate_sort_order(cls, v):
        if v not in ['asc', 'desc']:
            raise ValueError('排序顺序必须是: asc, desc')
        return v

class ExportRequest(BaseModel):
    """导出请求"""
    export_type: str = Field(..., description="导出类型")
    format: str = Field("json", description="导出格式: json, csv, xlsx")
    filters: Optional[Dict[str, Any]] = Field(None, description="过滤条件")
    fields: Optional[List[str]] = Field(None, description="导出字段")
    compress: bool = Field(False, description="是否压缩")
    
    @validator('format')
    def validate_format(cls, v):
        allowed_formats = ['json', 'csv', 'xlsx', 'xml']
        if v not in allowed_formats:
            raise ValueError(f'导出格式必须是: {", ".join(allowed_formats)}')
        return v

# WebSocket相关请求模型
class WebSocketSubscribeRequest(BaseModel):
    """WebSocket订阅请求"""
    channels: List[str] = Field(..., min_items=1, description="订阅频道列表")
    filters: Optional[Dict[str, Any]] = Field(None, description="过滤条件")
    client_info: Optional[Dict[str, Any]] = Field(None, description="客户端信息")

class WebSocketUnsubscribeRequest(BaseModel):
    """WebSocket取消订阅请求"""
    channels: List[str] = Field(..., min_items=1, description="取消订阅频道列表")