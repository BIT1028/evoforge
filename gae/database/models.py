# -*- coding: utf-8 -*-
"""
数据模型定义 - EvoForge数据库模型

定义所有数据库表对应的数据模型：
- ExperimentModel: 实验模型
- IndividualModel: 个体模型
- EvaluationModel: 评估模型
- MetricModel: 指标模型
- 数据验证和序列化

作者: EvoForge Team
创建时间: 2024
"""

import json
import logging
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from dataclasses import dataclass, field, asdict
from enum import Enum
from abc import ABC, abstractmethod

from ..core.logging_system import get_logger
from ..core.error_handler import EvoForgeError

logger = get_logger(__name__)

class ExperimentStatus(Enum):
    """实验状态枚举"""
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class EvaluationStatus(Enum):
    """评估状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"

class ModelValidationError(EvoForgeError):
    """模型验证错误"""
    pass

class BaseModel(ABC):
    """基础模型类"""
    
    @abstractmethod
    def validate(self) -> bool:
        """验证模型数据"""
        pass
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        pass
    
    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]):
        """从字典创建实例"""
        pass
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), default=str, ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str: str):
        """从JSON字符串创建实例"""
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except json.JSONDecodeError as e:
            raise ModelValidationError(f"JSON解析失败: {e}")

@dataclass
class ExperimentModel(BaseModel):
    """实验模型"""
    
    # 基础字段
    id: Optional[int] = None
    name: str = ""
    description: str = ""
    config: Dict[str, Any] = field(default_factory=dict)
    status: ExperimentStatus = ExperimentStatus.CREATED
    
    # 时间字段
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # 统计字段
    total_generations: int = 0
    total_individuals: int = 0
    best_fitness: Optional[float] = None
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self) -> bool:
        """验证实验模型"""
        try:
            # 检查必填字段
            if not self.name or not self.name.strip():
                raise ModelValidationError("实验名称不能为空")
            
            if len(self.name) > 255:
                raise ModelValidationError("实验名称长度不能超过255字符")
            
            # 检查状态
            if not isinstance(self.status, ExperimentStatus):
                raise ModelValidationError("无效的实验状态")
            
            # 检查配置
            if not isinstance(self.config, dict):
                raise ModelValidationError("实验配置必须是字典类型")
            
            # 检查统计字段
            if self.total_generations < 0:
                raise ModelValidationError("总代数不能为负数")
            
            if self.total_individuals < 0:
                raise ModelValidationError("总个体数不能为负数")
            
            # 检查时间逻辑
            if self.created_at and self.updated_at:
                if self.updated_at < self.created_at:
                    raise ModelValidationError("更新时间不能早于创建时间")
            
            if self.completed_at and self.created_at:
                if self.completed_at < self.created_at:
                    raise ModelValidationError("完成时间不能早于创建时间")
            
            return True
            
        except ModelValidationError:
            raise
        except Exception as e:
            raise ModelValidationError(f"实验模型验证失败: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['status'] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """从字典创建实例"""
        # 处理状态枚举
        if 'status' in data and isinstance(data['status'], str):
            data['status'] = ExperimentStatus(data['status'])
        
        # 处理时间字段
        for time_field in ['created_at', 'updated_at', 'completed_at']:
            if time_field in data and isinstance(data[time_field], str):
                data[time_field] = datetime.fromisoformat(data[time_field])
        
        return cls(**data)
    
    def update_status(self, new_status: ExperimentStatus):
        """更新实验状态"""
        self.status = new_status
        self.updated_at = datetime.now()
        
        if new_status in [ExperimentStatus.COMPLETED, ExperimentStatus.FAILED, ExperimentStatus.CANCELLED]:
            self.completed_at = datetime.now()
    
    def add_generation(self, individual_count: int = 0):
        """添加新一代"""
        self.total_generations += 1
        self.total_individuals += individual_count
        self.updated_at = datetime.now()
    
    def update_best_fitness(self, fitness: float):
        """更新最佳适应度"""
        if self.best_fitness is None or fitness > self.best_fitness:
            self.best_fitness = fitness
            self.updated_at = datetime.now()

@dataclass
class IndividualModel(BaseModel):
    """个体模型"""
    
    # 基础字段
    id: Optional[int] = None
    experiment_id: int = 0
    generation: int = 0
    
    # 基因组数据
    genome: Dict[str, Any] = field(default_factory=dict)
    
    # 适应度数据
    fitness_scores: Dict[str, float] = field(default_factory=dict)
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 时间字段
    created_at: Optional[datetime] = None
    
    # 统计字段
    evaluation_count: int = 0
    total_execution_time: float = 0.0
    
    def validate(self) -> bool:
        """验证个体模型"""
        try:
            # 检查必填字段
            if self.experiment_id <= 0:
                raise ModelValidationError("实验ID必须大于0")
            
            if self.generation < 0:
                raise ModelValidationError("代数不能为负数")
            
            # 检查基因组
            if not isinstance(self.genome, dict):
                raise ModelValidationError("基因组必须是字典类型")
            
            if not self.genome:
                raise ModelValidationError("基因组不能为空")
            
            # 检查适应度分数
            if not isinstance(self.fitness_scores, dict):
                raise ModelValidationError("适应度分数必须是字典类型")
            
            for key, value in self.fitness_scores.items():
                if not isinstance(value, (int, float)):
                    raise ModelValidationError(f"适应度分数 {key} 必须是数值类型")
            
            # 检查统计字段
            if self.evaluation_count < 0:
                raise ModelValidationError("评估次数不能为负数")
            
            if self.total_execution_time < 0:
                raise ModelValidationError("总执行时间不能为负数")
            
            return True
            
        except ModelValidationError:
            raise
        except Exception as e:
            raise ModelValidationError(f"个体模型验证失败: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """从字典创建实例"""
        # 处理时间字段
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        
        return cls(**data)
    
    def add_fitness_score(self, metric_name: str, score: float):
        """添加适应度分数"""
        self.fitness_scores[metric_name] = score
    
    def get_overall_fitness(self) -> float:
        """获取总体适应度（所有分数的平均值）"""
        if not self.fitness_scores:
            return 0.0
        return sum(self.fitness_scores.values()) / len(self.fitness_scores)
    
    def add_evaluation(self, execution_time: float = 0.0):
        """添加评估记录"""
        self.evaluation_count += 1
        self.total_execution_time += execution_time
    
    def get_avg_execution_time(self) -> float:
        """获取平均执行时间"""
        if self.evaluation_count == 0:
            return 0.0
        return self.total_execution_time / self.evaluation_count

@dataclass
class EvaluationModel(BaseModel):
    """评估模型"""
    
    # 基础字段
    id: Optional[int] = None
    individual_id: int = 0
    task_id: str = ""
    
    # 评估结果
    result: Dict[str, Any] = field(default_factory=dict)
    status: EvaluationStatus = EvaluationStatus.PENDING
    
    # 性能指标
    execution_time: float = 0.0
    memory_usage: int = 0  # 字节
    cpu_usage: float = 0.0  # 百分比
    
    # 错误信息
    error_message: Optional[str] = None
    error_traceback: Optional[str] = None
    
    # 时间字段
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self) -> bool:
        """验证评估模型"""
        try:
            # 检查必填字段
            if self.individual_id <= 0:
                raise ModelValidationError("个体ID必须大于0")
            
            if not self.task_id or not self.task_id.strip():
                raise ModelValidationError("任务ID不能为空")
            
            # 检查状态
            if not isinstance(self.status, EvaluationStatus):
                raise ModelValidationError("无效的评估状态")
            
            # 检查性能指标
            if self.execution_time < 0:
                raise ModelValidationError("执行时间不能为负数")
            
            if self.memory_usage < 0:
                raise ModelValidationError("内存使用量不能为负数")
            
            if self.cpu_usage < 0 or self.cpu_usage > 100:
                raise ModelValidationError("CPU使用率必须在0-100之间")
            
            # 检查时间逻辑
            if self.started_at and self.created_at:
                if self.started_at < self.created_at:
                    raise ModelValidationError("开始时间不能早于创建时间")
            
            if self.completed_at and self.started_at:
                if self.completed_at < self.started_at:
                    raise ModelValidationError("完成时间不能早于开始时间")
            
            return True
            
        except ModelValidationError:
            raise
        except Exception as e:
            raise ModelValidationError(f"评估模型验证失败: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['status'] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """从字典创建实例"""
        # 处理状态枚举
        if 'status' in data and isinstance(data['status'], str):
            data['status'] = EvaluationStatus(data['status'])
        
        # 处理时间字段
        for time_field in ['created_at', 'started_at', 'completed_at']:
            if time_field in data and isinstance(data[time_field], str):
                data[time_field] = datetime.fromisoformat(data[time_field])
        
        return cls(**data)
    
    def start_evaluation(self):
        """开始评估"""
        self.status = EvaluationStatus.RUNNING
        self.started_at = datetime.now()
    
    def complete_evaluation(self, result: Dict[str, Any], execution_time: float = None):
        """完成评估"""
        self.status = EvaluationStatus.COMPLETED
        self.result = result
        self.completed_at = datetime.now()
        
        if execution_time is not None:
            self.execution_time = execution_time
        elif self.started_at:
            self.execution_time = (self.completed_at - self.started_at).total_seconds()
    
    def fail_evaluation(self, error_message: str, error_traceback: str = None):
        """评估失败"""
        self.status = EvaluationStatus.FAILED
        self.error_message = error_message
        self.error_traceback = error_traceback
        self.completed_at = datetime.now()
        
        if self.started_at:
            self.execution_time = (self.completed_at - self.started_at).total_seconds()

@dataclass
class MetricModel(BaseModel):
    """指标模型（时间序列数据）"""
    
    # 时间戳
    time: datetime = field(default_factory=datetime.now)
    
    # 关联字段
    experiment_id: Optional[int] = None
    individual_id: Optional[int] = None
    
    # 指标数据
    metric_name: str = ""
    metric_value: float = 0.0
    metric_unit: str = ""
    
    # 标签和元数据
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self) -> bool:
        """验证指标模型"""
        try:
            # 检查必填字段
            if not self.metric_name or not self.metric_name.strip():
                raise ModelValidationError("指标名称不能为空")
            
            if not isinstance(self.metric_value, (int, float)):
                raise ModelValidationError("指标值必须是数值类型")
            
            # 检查时间
            if not isinstance(self.time, datetime):
                raise ModelValidationError("时间必须是datetime类型")
            
            # 检查标签
            if not isinstance(self.tags, dict):
                raise ModelValidationError("标签必须是字典类型")
            
            for key, value in self.tags.items():
                if not isinstance(key, str) or not isinstance(value, str):
                    raise ModelValidationError("标签的键和值都必须是字符串类型")
            
            return True
            
        except ModelValidationError:
            raise
        except Exception as e:
            raise ModelValidationError(f"指标模型验证失败: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """从字典创建实例"""
        # 处理时间字段
        if 'time' in data and isinstance(data['time'], str):
            data['time'] = datetime.fromisoformat(data['time'])
        
        return cls(**data)
    
    def add_tag(self, key: str, value: str):
        """添加标签"""
        self.tags[key] = value
    
    def remove_tag(self, key: str):
        """移除标签"""
        self.tags.pop(key, None)

# 模型工厂类
class ModelFactory:
    """模型工厂"""
    
    _models = {
        'experiment': ExperimentModel,
        'individual': IndividualModel,
        'evaluation': EvaluationModel,
        'metric': MetricModel
    }
    
    @classmethod
    def create_model(cls, model_type: str, **kwargs) -> BaseModel:
        """创建模型实例"""
        if model_type not in cls._models:
            raise ModelValidationError(f"未知的模型类型: {model_type}")
        
        model_class = cls._models[model_type]
        instance = model_class(**kwargs)
        instance.validate()
        return instance
    
    @classmethod
    def from_dict(cls, model_type: str, data: Dict[str, Any]) -> BaseModel:
        """从字典创建模型实例"""
        if model_type not in cls._models:
            raise ModelValidationError(f"未知的模型类型: {model_type}")
        
        model_class = cls._models[model_type]
        instance = model_class.from_dict(data)
        instance.validate()
        return instance
    
    @classmethod
    def get_available_models(cls) -> List[str]:
        """获取可用的模型类型"""
        return list(cls._models.keys())

# 批量操作辅助函数
def validate_models(models: List[BaseModel]) -> bool:
    """批量验证模型"""
    try:
        for model in models:
            model.validate()
        return True
    except ModelValidationError as e:
        logger.error(f"模型验证失败: {e}")
        return False

def models_to_dict_list(models: List[BaseModel]) -> List[Dict[str, Any]]:
    """将模型列表转换为字典列表"""
    return [model.to_dict() for model in models]

def dict_list_to_models(model_type: str, data_list: List[Dict[str, Any]]) -> List[BaseModel]:
    """将字典列表转换为模型列表"""
    return [ModelFactory.from_dict(model_type, data) for data in data_list]