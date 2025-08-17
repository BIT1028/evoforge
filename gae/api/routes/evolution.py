# -*- coding: utf-8 -*-
"""
进化控制API路由

提供进化过程控制的RESTful API端点：
- 启动进化
- 停止进化
- 暂停进化
- 恢复进化
- 获取进化状态
- 进化参数调整
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Dict, Any, Optional
import asyncio
import logging
from datetime import datetime

from ..models.requests import (
    StartEvolutionRequest,
    StopEvolutionRequest,
    PauseEvolutionRequest,
    ResumeEvolutionRequest,
    UpdateEvolutionParametersRequest
)
from ..models.responses import (
    SuccessResponse,
    ErrorResponse,
    EvolutionStatusResponse,
    EvolutionControlResponse
)
from ..models.dtos import ExperimentDTO, GenerationDTO
from ..models.validators import (
    validate_uuid,
    validate_experiment_config,
    ValidationError,
    ValidationErrorType
)
from ...core.module_coordinator import ModuleCoordinator
from ...core.error_handler import EvoForgeError, ErrorType
from ...database.data_access_layer import DataAccessLayer

# 创建路由器
router = APIRouter()
logger = logging.getLogger(__name__)

# 依赖注入
async def get_module_coordinator() -> ModuleCoordinator:
    """获取模块协调器"""
    # 这里应该从应用状态中获取
    # 暂时返回None，实际实现时需要修改
    return None

async def get_data_access_layer() -> DataAccessLayer:
    """获取数据访问层"""
    # 这里应该从应用状态中获取
    return None

@router.post("/start", response_model=SuccessResponse[EvolutionControlResponse])
async def start_evolution(
    request: StartEvolutionRequest,
    background_tasks: BackgroundTasks,
    coordinator: ModuleCoordinator = Depends(get_module_coordinator),
    dal: DataAccessLayer = Depends(get_data_access_layer)
):
    """
    启动进化过程
    
    Args:
        request: 启动进化请求
        background_tasks: 后台任务
        coordinator: 模块协调器
        dal: 数据访问层
    
    Returns:
        进化控制响应
    """
    try:
        logger.info(f"Starting evolution for experiment: {request.experiment_id}")
        
        # 验证实验ID
        validate_uuid(request.experiment_id)
        
        # 检查实验是否存在
        experiment = await dal.get_experiment(request.experiment_id)
        if not experiment:
            raise HTTPException(
                status_code=404,
                detail=f"Experiment {request.experiment_id} not found"
            )
        
        # 检查实验状态
        if experiment.status in ['running', 'paused']:
            raise HTTPException(
                status_code=400,
                detail=f"Experiment is already {experiment.status}"
            )
        
        # 验证进化参数
        if request.parameters:
            validate_experiment_config(request.parameters)
        
        # 启动进化引擎
        evolution_engine = coordinator.get_evolution_engine()
        
        # 准备进化参数
        evolution_params = {
            'experiment_id': request.experiment_id,
            'resume_from_generation': request.resume_from_generation,
            'max_generations': request.max_generations,
            'parameters': request.parameters or {}
        }
        
        # 在后台启动进化
        background_tasks.add_task(
            _run_evolution_background,
            evolution_engine,
            evolution_params,
            dal
        )
        
        # 更新实验状态
        await dal.update_experiment(
            request.experiment_id,
            {
                'status': 'running',
                'started_at': datetime.utcnow(),
                'current_generation': request.resume_from_generation or 0
            }
        )
        
        response_data = EvolutionControlResponse(
            experiment_id=request.experiment_id,
            action="start",
            status="running",
            message="Evolution started successfully",
            timestamp=datetime.utcnow()
        )
        
        return SuccessResponse(
            data=response_data,
            message="Evolution started successfully"
        )
        
    except ValidationError as e:
        logger.error(f"Validation error starting evolution: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    
    except EvoForgeError as e:
        logger.error(f"EvoForge error starting evolution: {e.message}")
        raise HTTPException(status_code=500, detail=e.message)
    
    except Exception as e:
        logger.error(f"Unexpected error starting evolution: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/stop", response_model=SuccessResponse[EvolutionControlResponse])
async def stop_evolution(
    request: StopEvolutionRequest,
    coordinator: ModuleCoordinator = Depends(get_module_coordinator),
    dal: DataAccessLayer = Depends(get_data_access_layer)
):
    """
    停止进化过程
    
    Args:
        request: 停止进化请求
        coordinator: 模块协调器
        dal: 数据访问层
    
    Returns:
        进化控制响应
    """
    try:
        logger.info(f"Stopping evolution for experiment: {request.experiment_id}")
        
        # 验证实验ID
        validate_uuid(request.experiment_id)
        
        # 检查实验是否存在
        experiment = await dal.get_experiment(request.experiment_id)
        if not experiment:
            raise HTTPException(
                status_code=404,
                detail=f"Experiment {request.experiment_id} not found"
            )
        
        # 检查实验状态
        if experiment.status not in ['running', 'paused']:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot stop experiment with status: {experiment.status}"
            )
        
        # 停止进化引擎
        evolution_engine = coordinator.get_evolution_engine()
        await evolution_engine.stop_evolution(request.experiment_id)
        
        # 更新实验状态
        update_data = {
            'status': 'stopped',
            'completed_at': datetime.utcnow()
        }
        
        if request.save_checkpoint:
            # 保存检查点
            checkpoint_data = await evolution_engine.create_checkpoint(request.experiment_id)
            update_data['last_checkpoint'] = datetime.utcnow()
            update_data['metadata'] = {
                **(experiment.metadata or {}),
                'last_checkpoint_data': checkpoint_data
            }
        
        await dal.update_experiment(request.experiment_id, update_data)
        
        response_data = EvolutionControlResponse(
            experiment_id=request.experiment_id,
            action="stop",
            status="stopped",
            message="Evolution stopped successfully",
            timestamp=datetime.utcnow(),
            checkpoint_saved=request.save_checkpoint
        )
        
        return SuccessResponse(
            data=response_data,
            message="Evolution stopped successfully"
        )
        
    except ValidationError as e:
        logger.error(f"Validation error stopping evolution: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    
    except EvoForgeError as e:
        logger.error(f"EvoForge error stopping evolution: {e.message}")
        raise HTTPException(status_code=500, detail=e.message)
    
    except Exception as e:
        logger.error(f"Unexpected error stopping evolution: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/pause", response_model=SuccessResponse[EvolutionControlResponse])
async def pause_evolution(
    request: PauseEvolutionRequest,
    coordinator: ModuleCoordinator = Depends(get_module_coordinator),
    dal: DataAccessLayer = Depends(get_data_access_layer)
):
    """
    暂停进化过程
    
    Args:
        request: 暂停进化请求
        coordinator: 模块协调器
        dal: 数据访问层
    
    Returns:
        进化控制响应
    """
    try:
        logger.info(f"Pausing evolution for experiment: {request.experiment_id}")
        
        # 验证实验ID
        validate_uuid(request.experiment_id)
        
        # 检查实验是否存在且正在运行
        experiment = await dal.get_experiment(request.experiment_id)
        if not experiment:
            raise HTTPException(
                status_code=404,
                detail=f"Experiment {request.experiment_id} not found"
            )
        
        if experiment.status != 'running':
            raise HTTPException(
                status_code=400,
                detail=f"Cannot pause experiment with status: {experiment.status}"
            )
        
        # 暂停进化引擎
        evolution_engine = coordinator.get_evolution_engine()
        await evolution_engine.pause_evolution(request.experiment_id)
        
        # 保存检查点
        checkpoint_data = await evolution_engine.create_checkpoint(request.experiment_id)
        
        # 更新实验状态
        await dal.update_experiment(
            request.experiment_id,
            {
                'status': 'paused',
                'last_checkpoint': datetime.utcnow(),
                'metadata': {
                    **(experiment.metadata or {}),
                    'pause_checkpoint': checkpoint_data,
                    'pause_reason': request.reason
                }
            }
        )
        
        response_data = EvolutionControlResponse(
            experiment_id=request.experiment_id,
            action="pause",
            status="paused",
            message="Evolution paused successfully",
            timestamp=datetime.utcnow(),
            checkpoint_saved=True
        )
        
        return SuccessResponse(
            data=response_data,
            message="Evolution paused successfully"
        )
        
    except ValidationError as e:
        logger.error(f"Validation error pausing evolution: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    
    except EvoForgeError as e:
        logger.error(f"EvoForge error pausing evolution: {e.message}")
        raise HTTPException(status_code=500, detail=e.message)
    
    except Exception as e:
        logger.error(f"Unexpected error pausing evolution: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/resume", response_model=SuccessResponse[EvolutionControlResponse])
async def resume_evolution(
    request: ResumeEvolutionRequest,
    background_tasks: BackgroundTasks,
    coordinator: ModuleCoordinator = Depends(get_module_coordinator),
    dal: DataAccessLayer = Depends(get_data_access_layer)
):
    """
    恢复进化过程
    
    Args:
        request: 恢复进化请求
        background_tasks: 后台任务
        coordinator: 模块协调器
        dal: 数据访问层
    
    Returns:
        进化控制响应
    """
    try:
        logger.info(f"Resuming evolution for experiment: {request.experiment_id}")
        
        # 验证实验ID
        validate_uuid(request.experiment_id)
        
        # 检查实验是否存在且已暂停
        experiment = await dal.get_experiment(request.experiment_id)
        if not experiment:
            raise HTTPException(
                status_code=404,
                detail=f"Experiment {request.experiment_id} not found"
            )
        
        if experiment.status != 'paused':
            raise HTTPException(
                status_code=400,
                detail=f"Cannot resume experiment with status: {experiment.status}"
            )
        
        # 恢复进化引擎
        evolution_engine = coordinator.get_evolution_engine()
        
        # 从检查点恢复
        checkpoint_data = None
        if experiment.metadata and 'pause_checkpoint' in experiment.metadata:
            checkpoint_data = experiment.metadata['pause_checkpoint']
        
        # 准备恢复参数
        resume_params = {
            'experiment_id': request.experiment_id,
            'checkpoint_data': checkpoint_data,
            'parameters': request.parameters or {}
        }
        
        # 在后台恢复进化
        background_tasks.add_task(
            _resume_evolution_background,
            evolution_engine,
            resume_params,
            dal
        )
        
        # 更新实验状态
        await dal.update_experiment(
            request.experiment_id,
            {
                'status': 'running',
                'started_at': datetime.utcnow()
            }
        )
        
        response_data = EvolutionControlResponse(
            experiment_id=request.experiment_id,
            action="resume",
            status="running",
            message="Evolution resumed successfully",
            timestamp=datetime.utcnow()
        )
        
        return SuccessResponse(
            data=response_data,
            message="Evolution resumed successfully"
        )
        
    except ValidationError as e:
        logger.error(f"Validation error resuming evolution: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    
    except EvoForgeError as e:
        logger.error(f"EvoForge error resuming evolution: {e.message}")
        raise HTTPException(status_code=500, detail=e.message)
    
    except Exception as e:
        logger.error(f"Unexpected error resuming evolution: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/status/{experiment_id}", response_model=SuccessResponse[EvolutionStatusResponse])
async def get_evolution_status(
    experiment_id: str,
    coordinator: ModuleCoordinator = Depends(get_module_coordinator),
    dal: DataAccessLayer = Depends(get_data_access_layer)
):
    """
    获取进化状态
    
    Args:
        experiment_id: 实验ID
        coordinator: 模块协调器
        dal: 数据访问层
    
    Returns:
        进化状态响应
    """
    try:
        # 验证实验ID
        validate_uuid(experiment_id)
        
        # 获取实验信息
        experiment = await dal.get_experiment(experiment_id)
        if not experiment:
            raise HTTPException(
                status_code=404,
                detail=f"Experiment {experiment_id} not found"
            )
        
        # 获取进化引擎状态
        evolution_engine = coordinator.get_evolution_engine()
        engine_status = await evolution_engine.get_status(experiment_id)
        
        # 获取最新代际信息
        latest_generation = await dal.get_latest_generation(experiment_id)
        
        # 获取种群统计
        population_stats = await dal.get_population_stats(
            experiment_id,
            experiment.current_generation
        )
        
        response_data = EvolutionStatusResponse(
            experiment_id=experiment_id,
            status=experiment.status,
            current_generation=experiment.current_generation,
            max_generations=experiment.max_generations,
            population_size=experiment.population_size,
            best_fitness=experiment.best_fitness,
            average_fitness=experiment.average_fitness,
            diversity_score=experiment.diversity_score,
            convergence_rate=experiment.convergence_rate,
            total_evaluations=experiment.total_evaluations,
            elapsed_time=experiment.elapsed_time,
            estimated_remaining=experiment.estimated_remaining,
            engine_status=engine_status,
            latest_generation=latest_generation,
            population_stats=population_stats,
            last_updated=datetime.utcnow()
        )
        
        return SuccessResponse(
            data=response_data,
            message="Evolution status retrieved successfully"
        )
        
    except ValidationError as e:
        logger.error(f"Validation error getting evolution status: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    
    except EvoForgeError as e:
        logger.error(f"EvoForge error getting evolution status: {e.message}")
        raise HTTPException(status_code=500, detail=e.message)
    
    except Exception as e:
        logger.error(f"Unexpected error getting evolution status: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/parameters/{experiment_id}", response_model=SuccessResponse[EvolutionControlResponse])
async def update_evolution_parameters(
    experiment_id: str,
    request: UpdateEvolutionParametersRequest,
    coordinator: ModuleCoordinator = Depends(get_module_coordinator),
    dal: DataAccessLayer = Depends(get_data_access_layer)
):
    """
    更新进化参数
    
    Args:
        experiment_id: 实验ID
        request: 更新参数请求
        coordinator: 模块协调器
        dal: 数据访问层
    
    Returns:
        进化控制响应
    """
    try:
        logger.info(f"Updating evolution parameters for experiment: {experiment_id}")
        
        # 验证实验ID
        validate_uuid(experiment_id)
        
        # 验证参数
        validate_experiment_config(request.parameters)
        
        # 检查实验是否存在
        experiment = await dal.get_experiment(experiment_id)
        if not experiment:
            raise HTTPException(
                status_code=404,
                detail=f"Experiment {experiment_id} not found"
            )
        
        # 更新进化引擎参数
        evolution_engine = coordinator.get_evolution_engine()
        await evolution_engine.update_parameters(experiment_id, request.parameters)
        
        # 更新实验配置
        updated_config = {**experiment.config, **request.parameters}
        await dal.update_experiment(
            experiment_id,
            {
                'config': updated_config,
                'metadata': {
                    **(experiment.metadata or {}),
                    'parameter_updates': {
                        'timestamp': datetime.utcnow().isoformat(),
                        'updated_parameters': request.parameters,
                        'apply_immediately': request.apply_immediately
                    }
                }
            }
        )
        
        response_data = EvolutionControlResponse(
            experiment_id=experiment_id,
            action="update_parameters",
            status=experiment.status,
            message="Evolution parameters updated successfully",
            timestamp=datetime.utcnow(),
            parameters_updated=request.parameters
        )
        
        return SuccessResponse(
            data=response_data,
            message="Evolution parameters updated successfully"
        )
        
    except ValidationError as e:
        logger.error(f"Validation error updating evolution parameters: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    
    except EvoForgeError as e:
        logger.error(f"EvoForge error updating evolution parameters: {e.message}")
        raise HTTPException(status_code=500, detail=e.message)
    
    except Exception as e:
        logger.error(f"Unexpected error updating evolution parameters: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# 后台任务函数
async def _run_evolution_background(
    evolution_engine,
    evolution_params: Dict[str, Any],
    dal: DataAccessLayer
):
    """
    后台运行进化过程
    
    Args:
        evolution_engine: 进化引擎
        evolution_params: 进化参数
        dal: 数据访问层
    """
    try:
        experiment_id = evolution_params['experiment_id']
        logger.info(f"Starting background evolution for experiment: {experiment_id}")
        
        # 运行进化
        await evolution_engine.run_evolution(**evolution_params)
        
        # 更新实验状态为完成
        await dal.update_experiment(
            experiment_id,
            {
                'status': 'completed',
                'completed_at': datetime.utcnow()
            }
        )
        
        logger.info(f"Evolution completed for experiment: {experiment_id}")
        
    except Exception as e:
        logger.error(f"Error in background evolution: {str(e)}")
        
        # 更新实验状态为错误
        try:
            await dal.update_experiment(
                evolution_params['experiment_id'],
                {
                    'status': 'error',
                    'metadata': {
                        'error_message': str(e),
                        'error_timestamp': datetime.utcnow().isoformat()
                    }
                }
            )
        except Exception as update_error:
            logger.error(f"Failed to update experiment status after error: {str(update_error)}")

async def _resume_evolution_background(
    evolution_engine,
    resume_params: Dict[str, Any],
    dal: DataAccessLayer
):
    """
    后台恢复进化过程
    
    Args:
        evolution_engine: 进化引擎
        resume_params: 恢复参数
        dal: 数据访问层
    """
    try:
        experiment_id = resume_params['experiment_id']
        logger.info(f"Resuming background evolution for experiment: {experiment_id}")
        
        # 恢复进化
        await evolution_engine.resume_evolution(**resume_params)
        
        # 更新实验状态为完成
        await dal.update_experiment(
            experiment_id,
            {
                'status': 'completed',
                'completed_at': datetime.utcnow()
            }
        )
        
        logger.info(f"Evolution resumed and completed for experiment: {experiment_id}")
        
    except Exception as e:
        logger.error(f"Error in background evolution resume: {str(e)}")
        
        # 更新实验状态为错误
        try:
            await dal.update_experiment(
                resume_params['experiment_id'],
                {
                    'status': 'error',
                    'metadata': {
                        'error_message': str(e),
                        'error_timestamp': datetime.utcnow().isoformat()
                    }
                }
            )
        except Exception as update_error:
            logger.error(f"Failed to update experiment status after resume error: {str(update_error)}")