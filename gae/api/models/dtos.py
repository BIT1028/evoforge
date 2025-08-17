# -*- coding: utf-8 -*-
"""
API数据传输对象(DTOs)

定义业务实体的数据传输结构：
- 个体DTO
- 实验DTO
- 任务DTO
- 指标DTO
- 代际DTO
- 种群DTO
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum

# 个体相关DTO
class IndividualStatus(str, Enum):
    """个体状态"""
    ACTIVE = "active"
    EVALUATED = "evaluated"
    SELECTED = "selected"
    MUTATED = "mutated"
    CROSSED = "crossed"
    ARCHIVED = "archived"

class IndividualDTO(BaseModel):
    """个体数据传输对象"""
    id: str = Field(..., description="个体ID")
    experiment_id: str = Field(..., description="实验ID")
    generation: int = Field(..., description="代数")
    genome: Dict[str, Any] = Field(..., description="基因组")
    phenotype: Optional[Dict[str, Any]] = Field(None, description="表型")
    fitness_scores: Optional[Dict[str, float]] = Field(None, description="适应度分数")
    overall_fitness: Optional[float] = Field(None, description="总体适应度")
    status: IndividualStatus = Field(..., description="个体状态")
    parent_ids: Optional[List[str]] = Field(None, description="父代ID列表")
    mutation_history: Optional[List[Dict[str, Any]]] = Field(None, description="变异历史")
    evaluation_time: Optional[float] = Field(None, description="评估耗时")
    created_at: datetime = Field(..., description="创建时间")
    evaluated_at: Optional[datetime] = Field(None, description="评估时间")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class IndividualSummaryDTO(BaseModel):
    """个体摘要DTO"""
    id: str = Field(..., description="个体ID")
    generation: int = Field(..., description="代数")
    overall_fitness: Optional[float] = Field(None, description="总体适应度")
    status: IndividualStatus = Field(..., description="个体状态")
    created_at: datetime = Field(..., description="创建时间")

# 实验相关DTO
class ExperimentDTO(BaseModel):
    """实验数据传输对象"""
    id: str = Field(..., description="实验ID")
    name: str = Field(..., description="实验名称")
    description: Optional[str] = Field(None, description="实验描述")
    status: str = Field(..., description="实验状态")
    config: Dict[str, Any] = Field(..., description="实验配置")
    current_generation: int = Field(0, description="当前代数")
    max_generations: int = Field(..., description="最大代数")
    population_size: int = Field(..., description="种群大小")
    best_fitness: Optional[float] = Field(None, description="最佳适应度")
    average_fitness: Optional[float] = Field(None, description="平均适应度")
    diversity_score: Optional[float] = Field(None, description="多样性分数")
    convergence_rate: Optional[float] = Field(None, description="收敛率")
    total_evaluations: int = Field(0, description="总评估次数")
    elapsed_time: float = Field(0, description="已运行时间")
    estimated_remaining: Optional[float] = Field(None, description="预计剩余时间")
    tags: Optional[List[str]] = Field(None, description="标签")
    created_at: datetime = Field(..., description="创建时间")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    last_checkpoint: Optional[datetime] = Field(None, description="最后检查点")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")

class ExperimentSummaryDTO(BaseModel):
    """实验摘要DTO"""
    id: str = Field(..., description="实验ID")
    name: str = Field(..., description="实验名称")
    status: str = Field(..., description="实验状态")
    current_generation: int = Field(..., description="当前代数")
    max_generations: int = Field(..., description="最大代数")
    best_fitness: Optional[float] = Field(None, description="最佳适应度")
    created_at: datetime = Field(..., description="创建时间")
    elapsed_time: float = Field(..., description="已运行时间")

# 任务相关DTO
class TaskDTO(BaseModel):
    """任务数据传输对象"""
    id: str = Field(..., description="任务ID")
    name: str = Field(..., description="任务名称")
    description: Optional[str] = Field(None, description="任务描述")
    task_type: str = Field(..., description="任务类型")
    status: str = Field(..., description="任务状态")
    priority: str = Field(..., description="任务优先级")
    progress: float = Field(0, description="任务进度")
    parameters: Dict[str, Any] = Field(..., description="任务参数")
    dependencies: Optional[List[str]] = Field(None, description="依赖任务")
    result: Optional[Dict[str, Any]] = Field(None, description="任务结果")
    error_message: Optional[str] = Field(None, description="错误信息")
    retry_count: int = Field(0, description="重试次数")
    max_retries: int = Field(0, description="最大重试次数")
    timeout: Optional[int] = Field(None, description="超时时间")
    tags: Optional[List[str]] = Field(None, description="标签")
    created_at: datetime = Field(..., description="创建时间")
    scheduled_at: Optional[datetime] = Field(None, description="计划时间")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    worker_id: Optional[str] = Field(None, description="工作者ID")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")

class TaskSummaryDTO(BaseModel):
    """任务摘要DTO"""
    id: str = Field(..., description="任务ID")
    name: str = Field(..., description="任务名称")
    task_type: str = Field(..., description="任务类型")
    status: str = Field(..., description="任务状态")
    progress: float = Field(..., description="任务进度")
    created_at: datetime = Field(..., description="创建时间")
    elapsed_time: Optional[float] = Field(None, description="运行时间")

# 指标相关DTO
class MetricDTO(BaseModel):
    """指标数据传输对象"""
    id: str = Field(..., description="指标ID")
    experiment_id: str = Field(..., description="实验ID")
    individual_id: Optional[str] = Field(None, description="个体ID")
    generation: int = Field(..., description="代数")
    metric_type: str = Field(..., description="指标类型")
    metric_name: str = Field(..., description="指标名称")
    value: float = Field(..., description="指标值")
    unit: Optional[str] = Field(None, description="单位")
    category: Optional[str] = Field(None, description="分类")
    tags: Optional[Dict[str, str]] = Field(None, description="标签")
    timestamp: datetime = Field(..., description="时间戳")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")

class MetricAggregationDTO(BaseModel):
    """指标聚合DTO"""
    metric_name: str = Field(..., description="指标名称")
    metric_type: str = Field(..., description="指标类型")
    count: int = Field(..., description="数据点数量")
    min_value: float = Field(..., description="最小值")
    max_value: float = Field(..., description="最大值")
    avg_value: float = Field(..., description="平均值")
    std_value: Optional[float] = Field(None, description="标准差")
    percentiles: Optional[Dict[str, float]] = Field(None, description="百分位数")
    trend: Optional[str] = Field(None, description="趋势")
    period: str = Field(..., description="统计周期")

# 代际相关DTO
class GenerationDTO(BaseModel):
    """代际数据传输对象"""
    experiment_id: str = Field(..., description="实验ID")
    generation: int = Field(..., description="代数")
    population_size: int = Field(..., description="种群大小")
    best_fitness: float = Field(..., description="最佳适应度")
    average_fitness: float = Field(..., description="平均适应度")
    worst_fitness: float = Field(..., description="最差适应度")
    fitness_std: float = Field(..., description="适应度标准差")
    diversity_score: float = Field(..., description="多样性分数")
    selection_pressure: float = Field(..., description="选择压力")
    mutation_rate: float = Field(..., description="变异率")
    crossover_rate: float = Field(..., description="交叉率")
    elite_count: int = Field(..., description="精英个体数")
    new_individuals: int = Field(..., description="新个体数")
    evaluation_time: float = Field(..., description="评估总时间")
    generation_time: float = Field(..., description="代际总时间")
    convergence_metric: Optional[float] = Field(None, description="收敛指标")
    created_at: datetime = Field(..., description="创建时间")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")

class GenerationSummaryDTO(BaseModel):
    """代际摘要DTO"""
    generation: int = Field(..., description="代数")
    best_fitness: float = Field(..., description="最佳适应度")
    average_fitness: float = Field(..., description="平均适应度")
    diversity_score: float = Field(..., description="多样性分数")
    evaluation_time: float = Field(..., description="评估时间")
    created_at: datetime = Field(..., description="创建时间")

# 种群相关DTO
class PopulationDTO(BaseModel):
    """种群数据传输对象"""
    experiment_id: str = Field(..., description="实验ID")
    generation: int = Field(..., description="代数")
    individuals: List[IndividualSummaryDTO] = Field(..., description="个体列表")
    population_size: int = Field(..., description="种群大小")
    fitness_distribution: Dict[str, float] = Field(..., description="适应度分布")
    diversity_metrics: Dict[str, float] = Field(..., description="多样性指标")
    species_count: Optional[int] = Field(None, description="物种数量")
    species_distribution: Optional[Dict[str, int]] = Field(None, description="物种分布")
    genealogy_info: Optional[Dict[str, Any]] = Field(None, description="谱系信息")
    created_at: datetime = Field(..., description="创建时间")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")

class PopulationStatsDTO(BaseModel):
    """种群统计DTO"""
    generation: int = Field(..., description="代数")
    population_size: int = Field(..., description="种群大小")
    evaluated_count: int = Field(..., description="已评估个体数")
    best_fitness: Optional[float] = Field(None, description="最佳适应度")
    average_fitness: Optional[float] = Field(None, description="平均适应度")
    fitness_variance: Optional[float] = Field(None, description="适应度方差")
    diversity_score: Optional[float] = Field(None, description="多样性分数")
    age_distribution: Optional[Dict[str, int]] = Field(None, description="年龄分布")
    complexity_stats: Optional[Dict[str, float]] = Field(None, description="复杂度统计")

# 评估相关DTO
class EvaluationDTO(BaseModel):
    """评估数据传输对象"""
    id: str = Field(..., description="评估ID")
    individual_id: str = Field(..., description="个体ID")
    experiment_id: str = Field(..., description="实验ID")
    evaluation_type: str = Field(..., description="评估类型")
    fitness_scores: Dict[str, float] = Field(..., description="适应度分数")
    overall_fitness: float = Field(..., description="总体适应度")
    evaluation_time: float = Field(..., description="评估耗时")
    parameters: Optional[Dict[str, Any]] = Field(None, description="评估参数")
    details: Optional[Dict[str, Any]] = Field(None, description="评估详情")
    error_info: Optional[Dict[str, Any]] = Field(None, description="错误信息")
    worker_id: Optional[str] = Field(None, description="工作者ID")
    cache_hit: bool = Field(False, description="是否命中缓存")
    created_at: datetime = Field(..., description="评估时间")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")

class EvaluationSummaryDTO(BaseModel):
    """评估摘要DTO"""
    id: str = Field(..., description="评估ID")
    individual_id: str = Field(..., description="个体ID")
    overall_fitness: float = Field(..., description="总体适应度")
    evaluation_time: float = Field(..., description="评估耗时")
    created_at: datetime = Field(..., description="评估时间")

# 系统相关DTO
class SystemStatusDTO(BaseModel):
    """系统状态DTO"""
    version: str = Field(..., description="系统版本")
    uptime: float = Field(..., description="运行时间")
    status: str = Field(..., description="系统状态")
    active_experiments: int = Field(..., description="活跃实验数")
    active_tasks: int = Field(..., description="活跃任务数")
    total_individuals: int = Field(..., description="总个体数")
    total_evaluations: int = Field(..., description="总评估数")
    cpu_usage: float = Field(..., description="CPU使用率")
    memory_usage: float = Field(..., description="内存使用率")
    disk_usage: float = Field(..., description="磁盘使用率")
    database_status: str = Field(..., description="数据库状态")
    components: Dict[str, str] = Field(..., description="组件状态")
    last_updated: datetime = Field(..., description="最后更新时间")

class ComponentStatusDTO(BaseModel):
    """组件状态DTO"""
    name: str = Field(..., description="组件名称")
    status: str = Field(..., description="组件状态")
    version: Optional[str] = Field(None, description="组件版本")
    health_score: float = Field(..., description="健康分数")
    last_check: datetime = Field(..., description="最后检查时间")
    metrics: Optional[Dict[str, Any]] = Field(None, description="组件指标")
    errors: Optional[List[str]] = Field(None, description="错误列表")
    warnings: Optional[List[str]] = Field(None, description="警告列表")