#!/usr/bin/env python3
"""
进化相关的Pydantic schemas
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

class EvolutionConfig(BaseModel):
    """进化配置"""
    population_size: int = Field(default=50, ge=10, le=1000, description="种群大小")
    mutation_rate: float = Field(default=0.1, ge=0.0, le=1.0, description="变异率")
    crossover_rate: float = Field(default=0.8, ge=0.0, le=1.0, description="交叉率")
    elite_size: int = Field(default=5, ge=1, le=50, description="精英个体数量")
    max_generations: Optional[int] = Field(default=None, ge=1, description="最大代数")

class EvolutionStatus(BaseModel):
    """进化状态"""
    is_running: bool = Field(description="是否正在运行")
    current_generation: int = Field(description="当前代数")
    population_size: int = Field(description="种群大小")
    best_fitness: Optional[float] = Field(description="最佳适应度")
    avg_fitness: Optional[float] = Field(description="平均适应度")
    total_evaluations: int = Field(description="总评估次数")
    start_time: Optional[datetime] = Field(description="开始时间")
    elapsed_time: Optional[float] = Field(description="已用时间（秒）")

class DigitalCellResponse(BaseModel):
    """数字细胞响应"""
    id: str = Field(description="细胞ID")
    generation_id: int = Field(description="所属代数ID")
    genome: str = Field(description="基因序列")
    generated_code: Optional[str] = Field(description="生成的代码")
    fitness_score: Optional[float] = Field(description="适应度分数")
    parent1_id: Optional[str] = Field(description="父代1 ID")
    parent2_id: Optional[str] = Field(description="父代2 ID")
    mutation_rate: Optional[float] = Field(description="变异率")
    created_at: datetime = Field(description="创建时间")
    
    class Config:
        from_attributes = True

class GenerationResponse(BaseModel):
    """代数响应"""
    id: int = Field(description="代数ID")
    generation_number: int = Field(description="代数编号")
    population_size: int = Field(description="种群大小")
    avg_fitness: Optional[float] = Field(description="平均适应度")
    max_fitness: Optional[float] = Field(description="最高适应度")
    min_fitness: Optional[float] = Field(description="最低适应度")
    created_at: datetime = Field(description="创建时间")
    completed_at: Optional[datetime] = Field(description="完成时间")
    digital_cells: Optional[List[DigitalCellResponse]] = Field(description="数字细胞列表")
    
    class Config:
        from_attributes = True

class EvolutionControlRequest(BaseModel):
    """进化控制请求"""
    action: str = Field(description="操作类型: start, pause, resume, stop, reset")
    config: Optional[EvolutionConfig] = Field(description="进化配置")

class EvolutionStatsResponse(BaseModel):
    """进化统计响应"""
    total_generations: int = Field(description="总代数")
    total_cells: int = Field(description="总细胞数")
    best_fitness_ever: Optional[float] = Field(description="历史最佳适应度")
    avg_fitness_trend: List[float] = Field(description="平均适应度趋势")
    max_fitness_trend: List[float] = Field(description="最高适应度趋势")
    api_cost_total: float = Field(description="总API成本")
    execution_time_total: float = Field(description="总执行时间")