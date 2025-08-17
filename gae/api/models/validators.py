# -*- coding: utf-8 -*-
"""
API数据验证器

定义数据验证规则和业务逻辑验证：
- 基础验证器
- 业务规则验证
- 数据完整性验证
- 自定义验证函数
"""

import re
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union, Callable
from pydantic import validator, ValidationError
from enum import Enum

# 验证错误类型
class ValidationErrorType(str, Enum):
    """验证错误类型"""
    INVALID_FORMAT = "invalid_format"
    OUT_OF_RANGE = "out_of_range"
    MISSING_REQUIRED = "missing_required"
    BUSINESS_RULE = "business_rule"
    DATA_INTEGRITY = "data_integrity"
    PERMISSION_DENIED = "permission_denied"

class ValidationError(Exception):
    """自定义验证错误"""
    def __init__(self, message: str, error_type: ValidationErrorType, field: Optional[str] = None):
        self.message = message
        self.error_type = error_type
        self.field = field
        super().__init__(message)

# 基础验证函数
def validate_uuid(value: str) -> str:
    """验证UUID格式"""
    try:
        uuid.UUID(value)
        return value
    except ValueError:
        raise ValidationError(
            f"Invalid UUID format: {value}",
            ValidationErrorType.INVALID_FORMAT,
            "uuid"
        )

def validate_positive_number(value: Union[int, float], field_name: str = "value") -> Union[int, float]:
    """验证正数"""
    if value <= 0:
        raise ValidationError(
            f"{field_name} must be positive, got: {value}",
            ValidationErrorType.OUT_OF_RANGE,
            field_name
        )
    return value

def validate_non_negative_number(value: Union[int, float], field_name: str = "value") -> Union[int, float]:
    """验证非负数"""
    if value < 0:
        raise ValidationError(
            f"{field_name} must be non-negative, got: {value}",
            ValidationErrorType.OUT_OF_RANGE,
            field_name
        )
    return value

def validate_percentage(value: float, field_name: str = "percentage") -> float:
    """验证百分比(0-100)"""
    if not 0 <= value <= 100:
        raise ValidationError(
            f"{field_name} must be between 0 and 100, got: {value}",
            ValidationErrorType.OUT_OF_RANGE,
            field_name
        )
    return value

def validate_probability(value: float, field_name: str = "probability") -> float:
    """验证概率(0-1)"""
    if not 0 <= value <= 1:
        raise ValidationError(
            f"{field_name} must be between 0 and 1, got: {value}",
            ValidationErrorType.OUT_OF_RANGE,
            field_name
        )
    return value

def validate_string_length(value: str, min_length: int = 0, max_length: int = 1000, field_name: str = "string") -> str:
    """验证字符串长度"""
    if len(value) < min_length:
        raise ValidationError(
            f"{field_name} must be at least {min_length} characters, got: {len(value)}",
            ValidationErrorType.OUT_OF_RANGE,
            field_name
        )
    if len(value) > max_length:
        raise ValidationError(
            f"{field_name} must be at most {max_length} characters, got: {len(value)}",
            ValidationErrorType.OUT_OF_RANGE,
            field_name
        )
    return value

def validate_email(value: str) -> str:
    """验证邮箱格式"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, value):
        raise ValidationError(
            f"Invalid email format: {value}",
            ValidationErrorType.INVALID_FORMAT,
            "email"
        )
    return value

def validate_datetime_range(value: datetime, min_date: Optional[datetime] = None, max_date: Optional[datetime] = None, field_name: str = "datetime") -> datetime:
    """验证日期时间范围"""
    if min_date and value < min_date:
        raise ValidationError(
            f"{field_name} must be after {min_date}, got: {value}",
            ValidationErrorType.OUT_OF_RANGE,
            field_name
        )
    if max_date and value > max_date:
        raise ValidationError(
            f"{field_name} must be before {max_date}, got: {value}",
            ValidationErrorType.OUT_OF_RANGE,
            field_name
        )
    return value

def validate_json_structure(value: Dict[str, Any], required_keys: Optional[List[str]] = None, field_name: str = "json") -> Dict[str, Any]:
    """验证JSON结构"""
    if required_keys:
        missing_keys = [key for key in required_keys if key not in value]
        if missing_keys:
            raise ValidationError(
                f"{field_name} missing required keys: {missing_keys}",
                ValidationErrorType.MISSING_REQUIRED,
                field_name
            )
    return value

# 业务规则验证
def validate_experiment_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """验证实验配置"""
    required_keys = ['population_size', 'max_generations', 'mutation_rate', 'crossover_rate']
    validate_json_structure(config, required_keys, "experiment_config")
    
    # 验证种群大小
    population_size = config.get('population_size', 0)
    if not isinstance(population_size, int) or population_size < 10 or population_size > 10000:
        raise ValidationError(
            f"Population size must be between 10 and 10000, got: {population_size}",
            ValidationErrorType.BUSINESS_RULE,
            "population_size"
        )
    
    # 验证最大代数
    max_generations = config.get('max_generations', 0)
    if not isinstance(max_generations, int) or max_generations < 1 or max_generations > 100000:
        raise ValidationError(
            f"Max generations must be between 1 and 100000, got: {max_generations}",
            ValidationErrorType.BUSINESS_RULE,
            "max_generations"
        )
    
    # 验证变异率
    mutation_rate = config.get('mutation_rate', 0)
    validate_probability(mutation_rate, "mutation_rate")
    
    # 验证交叉率
    crossover_rate = config.get('crossover_rate', 0)
    validate_probability(crossover_rate, "crossover_rate")
    
    return config

def validate_genome_structure(genome: Dict[str, Any]) -> Dict[str, Any]:
    """验证基因组结构"""
    required_keys = ['nodes', 'connections']
    validate_json_structure(genome, required_keys, "genome")
    
    # 验证节点
    nodes = genome.get('nodes', [])
    if not isinstance(nodes, list) or len(nodes) == 0:
        raise ValidationError(
            "Genome must contain at least one node",
            ValidationErrorType.BUSINESS_RULE,
            "nodes"
        )
    
    # 验证连接
    connections = genome.get('connections', [])
    if not isinstance(connections, list):
        raise ValidationError(
            "Connections must be a list",
            ValidationErrorType.BUSINESS_RULE,
            "connections"
        )
    
    return genome

def validate_fitness_scores(scores: Dict[str, float]) -> Dict[str, float]:
    """验证适应度分数"""
    if not scores:
        raise ValidationError(
            "Fitness scores cannot be empty",
            ValidationErrorType.MISSING_REQUIRED,
            "fitness_scores"
        )
    
    for metric_name, score in scores.items():
        if not isinstance(score, (int, float)):
            raise ValidationError(
                f"Fitness score for {metric_name} must be a number, got: {type(score)}",
                ValidationErrorType.INVALID_FORMAT,
                f"fitness_scores.{metric_name}"
            )
        
        if score < 0:
            raise ValidationError(
                f"Fitness score for {metric_name} must be non-negative, got: {score}",
                ValidationErrorType.OUT_OF_RANGE,
                f"fitness_scores.{metric_name}"
            )
    
    return scores

def validate_task_parameters(task_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """验证任务参数"""
    if task_type == "evolution":
        required_keys = ['experiment_id', 'generations']
        validate_json_structure(parameters, required_keys, "task_parameters")
        
        generations = parameters.get('generations', 0)
        validate_positive_number(generations, "generations")
        
    elif task_type == "evaluation":
        required_keys = ['individual_ids', 'evaluation_type']
        validate_json_structure(parameters, required_keys, "task_parameters")
        
        individual_ids = parameters.get('individual_ids', [])
        if not isinstance(individual_ids, list) or len(individual_ids) == 0:
            raise ValidationError(
                "Individual IDs must be a non-empty list",
                ValidationErrorType.BUSINESS_RULE,
                "individual_ids"
            )
        
        for individual_id in individual_ids:
            validate_uuid(individual_id)
    
    elif task_type == "analysis":
        required_keys = ['experiment_id', 'analysis_type']
        validate_json_structure(parameters, required_keys, "task_parameters")
    
    return parameters

def validate_generation_consistency(experiment_id: str, generation: int, current_generation: int) -> bool:
    """验证代际一致性"""
    if generation < 0:
        raise ValidationError(
            f"Generation must be non-negative, got: {generation}",
            ValidationErrorType.OUT_OF_RANGE,
            "generation"
        )
    
    if generation > current_generation + 1:
        raise ValidationError(
            f"Generation {generation} is too far ahead of current generation {current_generation}",
            ValidationErrorType.BUSINESS_RULE,
            "generation"
        )
    
    return True

def validate_population_size_consistency(individuals_count: int, expected_size: int, tolerance: float = 0.1) -> bool:
    """验证种群大小一致性"""
    min_size = int(expected_size * (1 - tolerance))
    max_size = int(expected_size * (1 + tolerance))
    
    if not min_size <= individuals_count <= max_size:
        raise ValidationError(
            f"Population size {individuals_count} is not within tolerance of expected size {expected_size}",
            ValidationErrorType.DATA_INTEGRITY,
            "population_size"
        )
    
    return True

# 数据完整性验证
def validate_parent_child_relationship(parent_ids: List[str], child_generation: int, parent_generation: int) -> bool:
    """验证父子关系"""
    if child_generation != parent_generation + 1:
        raise ValidationError(
            f"Child generation {child_generation} must be exactly one more than parent generation {parent_generation}",
            ValidationErrorType.DATA_INTEGRITY,
            "generation"
        )
    
    if len(parent_ids) > 2:
        raise ValidationError(
            f"Individual cannot have more than 2 parents, got: {len(parent_ids)}",
            ValidationErrorType.DATA_INTEGRITY,
            "parent_ids"
        )
    
    return True

def validate_evaluation_consistency(individual_id: str, fitness_scores: Dict[str, float], overall_fitness: float) -> bool:
    """验证评估一致性"""
    if not fitness_scores:
        raise ValidationError(
            "Fitness scores cannot be empty for evaluated individual",
            ValidationErrorType.DATA_INTEGRITY,
            "fitness_scores"
        )
    
    # 检查总体适应度是否与分项分数一致
    calculated_fitness = sum(fitness_scores.values()) / len(fitness_scores)
    tolerance = 0.001
    
    if abs(overall_fitness - calculated_fitness) > tolerance:
        raise ValidationError(
            f"Overall fitness {overall_fitness} does not match calculated fitness {calculated_fitness}",
            ValidationErrorType.DATA_INTEGRITY,
            "overall_fitness"
        )
    
    return True

def validate_metric_consistency(metric_type: str, metric_name: str, value: float, unit: Optional[str] = None) -> bool:
    """验证指标一致性"""
    # 定义指标类型和预期范围
    metric_ranges = {
        'fitness': (0, float('inf')),
        'diversity': (0, 1),
        'complexity': (0, float('inf')),
        'performance': (0, float('inf')),
        'time': (0, float('inf')),
        'memory': (0, float('inf')),
        'accuracy': (0, 1),
        'precision': (0, 1),
        'recall': (0, 1),
        'f1_score': (0, 1)
    }
    
    if metric_type in metric_ranges:
        min_val, max_val = metric_ranges[metric_type]
        if not min_val <= value <= max_val:
            raise ValidationError(
                f"Metric {metric_name} of type {metric_type} must be between {min_val} and {max_val}, got: {value}",
                ValidationErrorType.DATA_INTEGRITY,
                "value"
            )
    
    return True

# 权限验证
def validate_experiment_access(user_id: str, experiment_id: str, action: str) -> bool:
    """验证实验访问权限"""
    # 这里应该实现实际的权限检查逻辑
    # 目前返回True，实际应用中需要查询数据库或权限服务
    return True

def validate_task_permission(user_id: str, task_type: str, parameters: Dict[str, Any]) -> bool:
    """验证任务执行权限"""
    # 这里应该实现实际的权限检查逻辑
    return True

# 复合验证器
class ExperimentValidator:
    """实验验证器"""
    
    @staticmethod
    def validate_create_request(data: Dict[str, Any]) -> Dict[str, Any]:
        """验证创建实验请求"""
        # 验证必需字段
        required_fields = ['name', 'config']
        for field in required_fields:
            if field not in data:
                raise ValidationError(
                    f"Missing required field: {field}",
                    ValidationErrorType.MISSING_REQUIRED,
                    field
                )
        
        # 验证实验名称
        validate_string_length(data['name'], 1, 100, "name")
        
        # 验证实验配置
        validate_experiment_config(data['config'])
        
        return data
    
    @staticmethod
    def validate_update_request(experiment_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """验证更新实验请求"""
        validate_uuid(experiment_id)
        
        # 验证可更新字段
        allowed_fields = ['name', 'description', 'config', 'tags']
        for field in data:
            if field not in allowed_fields:
                raise ValidationError(
                    f"Field {field} is not allowed for update",
                    ValidationErrorType.BUSINESS_RULE,
                    field
                )
        
        # 验证字段值
        if 'name' in data:
            validate_string_length(data['name'], 1, 100, "name")
        
        if 'config' in data:
            validate_experiment_config(data['config'])
        
        return data

class IndividualValidator:
    """个体验证器"""
    
    @staticmethod
    def validate_create_request(data: Dict[str, Any]) -> Dict[str, Any]:
        """验证创建个体请求"""
        required_fields = ['experiment_id', 'generation', 'genome']
        for field in required_fields:
            if field not in data:
                raise ValidationError(
                    f"Missing required field: {field}",
                    ValidationErrorType.MISSING_REQUIRED,
                    field
                )
        
        validate_uuid(data['experiment_id'])
        validate_non_negative_number(data['generation'], "generation")
        validate_genome_structure(data['genome'])
        
        return data
    
    @staticmethod
    def validate_evaluation_request(individual_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """验证评估个体请求"""
        validate_uuid(individual_id)
        
        required_fields = ['fitness_scores']
        for field in required_fields:
            if field not in data:
                raise ValidationError(
                    f"Missing required field: {field}",
                    ValidationErrorType.MISSING_REQUIRED,
                    field
                )
        
        validate_fitness_scores(data['fitness_scores'])
        
        return data

class TaskValidator:
    """任务验证器"""
    
    @staticmethod
    def validate_create_request(data: Dict[str, Any]) -> Dict[str, Any]:
        """验证创建任务请求"""
        required_fields = ['name', 'task_type', 'parameters']
        for field in required_fields:
            if field not in data:
                raise ValidationError(
                    f"Missing required field: {field}",
                    ValidationErrorType.MISSING_REQUIRED,
                    field
                )
        
        validate_string_length(data['name'], 1, 100, "name")
        validate_task_parameters(data['task_type'], data['parameters'])
        
        return data

# 验证装饰器
def validate_request(validator_func: Callable) -> Callable:
    """请求验证装饰器"""
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            # 假设第一个参数是请求数据
            if args:
                try:
                    validated_data = validator_func(args[0])
                    args = (validated_data,) + args[1:]
                except ValidationError as e:
                    raise e
                except Exception as e:
                    raise ValidationError(
                        f"Validation failed: {str(e)}",
                        ValidationErrorType.INVALID_FORMAT
                    )
            return func(*args, **kwargs)
        return wrapper
    return decorator

# 批量验证
def validate_batch_operation(items: List[Dict[str, Any]], validator_func: Callable, max_batch_size: int = 100) -> List[Dict[str, Any]]:
    """批量操作验证"""
    if len(items) > max_batch_size:
        raise ValidationError(
            f"Batch size {len(items)} exceeds maximum allowed size {max_batch_size}",
            ValidationErrorType.BUSINESS_RULE,
            "batch_size"
        )
    
    validated_items = []
    errors = []
    
    for i, item in enumerate(items):
        try:
            validated_item = validator_func(item)
            validated_items.append(validated_item)
        except ValidationError as e:
            errors.append(f"Item {i}: {e.message}")
    
    if errors:
        raise ValidationError(
            f"Batch validation failed: {'; '.join(errors)}",
            ValidationErrorType.BUSINESS_RULE,
            "batch_items"
        )
    
    return validated_items