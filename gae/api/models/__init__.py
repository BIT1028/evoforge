# -*- coding: utf-8 -*-
"""
API模型模块

定义API请求和响应的数据模型：
- 请求模型 (Request Models)
- 响应模型 (Response Models)
- 数据传输对象 (DTOs)
- 验证规则
- 序列化/反序列化
"""

from .requests import *
from .responses import *
from .dtos import *
from .validators import *

__all__ = [
    # 请求模型
    'StartEvolutionRequest',
    'CreateTaskRequest',
    'UpdateTaskRequest',
    'CreateExperimentRequest',
    'EvaluationRequest',
    'SystemConfigRequest',
    
    # 响应模型
    'BaseResponse',
    'ErrorResponse',
    'SuccessResponse',
    'PaginatedResponse',
    'EvolutionStatusResponse',
    'TaskResponse',
    'ExperimentResponse',
    'EvaluationResponse',
    'SystemInfoResponse',
    
    # 数据传输对象
    'IndividualDTO',
    'ExperimentDTO',
    'TaskDTO',
    'MetricDTO',
    'GenerationDTO',
    'PopulationDTO',
    
    # 验证器
    'validate_experiment_config',
    'validate_task_parameters',
    'validate_evolution_settings'
]