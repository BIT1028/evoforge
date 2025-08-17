# -*- coding: utf-8 -*-
"""
实验管理API路由

提供实验管理的RESTful API端点：
- 创建实验
- 获取实验
- 更新实验
- 删除实验
- 克隆实验
- 实验配置管理
- 实验统计和分析
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime
from uuid import uuid4

from ..models.requests import (
    CreateExperimentRequest,
    UpdateExperimentRequest,
    CloneExperimentRequest,
    QueryRequest
)
from ..models.responses import (
    SuccessResponse,
    ErrorResponse,
    PaginatedResponse,
    ExperimentResponse,
    StatisticsResponse
)
from ..models.dtos import ExperimentDTO, ExperimentSummaryDTO, GenerationDTO
from ..models.validators import (
    validate_uuid,
    validate_experiment_config,
    validate_create_experiment_request,
    validate_update_experiment_request,
    ValidationError
)
from ...database.data_access_layer import DataAccessLayer
from ...core.error_handler import EvoForgeError, ErrorType
from ...core.module_coordinator import ModuleCoordinator

# 创建路由器
router = APIRouter()
logger = logging.getLogger(__name__)

# 依赖注入
async def get_data_access_layer() -> DataAccessLayer:
    """获取数据访问层"""
    # 这里应该从应用状态中获取
    return None

async def get_module_coordinator() -> ModuleCoordinator:
    """获取模块协调器"""
    # 这里应该从应用状态中获取
    return None

@router.post("/", response_model=SuccessResponse[ExperimentDTO])
async def create_experiment(
    request: CreateExperimentRequest,
    dal: DataAccessLayer = Depends(get_data_access_layer),
    coordinator: ModuleCoordinator = Depends(get_module_coordinator)
):
    """
    创建新实验
    
    Args:
        request: 创建实验请求
        dal: 数据访问层
        coordinator: 模块协调器
    
    Returns:
        创建的实验信息
    """
    try:
        logger.info(f"Creating experiment: {request.name}")
        
        # 验证请求
        validate_create_experiment_request(request)
        
        # 验证实验配置
        validate_experiment_config(request.config)
        
        # 检查实验名称是否已存在
        existing_experiment = await dal.get_experiment_by_name(request.name)
        if existing_experiment:
            raise HTTPException(
                status_code=400,
                detail=f"Experiment with name '{request.name}' already exists"
            )
        
        # 生成实验ID
        experiment_id = str(uuid4())
        
        # 准备实验数据
        experiment_data = {
            'id': experiment_id,
            'name': request.name,
            'description': request.description,
            'config': request.config,
            'status': 'created',
            'population_size': request.config.get('population_size', 100),
            'max_generations': request.config.get('max_generations', 1000),
            'current_generation': 0,
            'best_fitness': None,
            'average_fitness': None,
            'diversity_score': None,
            'convergence_rate': None,
            'total_evaluations': 0,
            'elapsed_time': 0,
            'estimated_remaining': None,
            'created_at': datetime.utcnow(),
            'created_by': request.created_by,
            'tags': request.tags or [],
            'metadata': request.metadata or {}
        }
        
        # 创建实验
        experiment = await dal.create_experiment(experiment_data)
        
        # 初始化实验环境
        try:
            await coordinator.initialize_experiment(experiment_id, request.config)
        except Exception as e:
            # 如果初始化失败，删除已创建的实验
            await dal.delete_experiment(experiment_id)
            raise EvoForgeError(
                error_type=ErrorType.INITIALIZATION_ERROR,
                message=f"Failed to initialize experiment: {str(e)}"
            )
        
        logger.info(f"Experiment created successfully: {experiment_id}")
        
        return SuccessResponse(
            data=experiment,
            message="Experiment created successfully"
        )
        
    except ValidationError as e:
        logger.error(f"Validation error creating experiment: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    
    except EvoForgeError as e:
        logger.error(f"EvoForge error creating experiment: {e.message}")
        raise HTTPException(status_code=500, detail=e.message)
    
    except Exception as e:
        logger.error(f"Unexpected error creating experiment: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{experiment_id}", response_model=SuccessResponse[ExperimentDTO])
async def get_experiment(
    experiment_id: str,
    include_generations: bool = Query(False, description="是否包含代际信息"),
    include_statistics: bool = Query(False, description="是否包含统计信息"),
    dal: DataAccessLayer = Depends(get_data_access_layer)
):
    """
    获取实验详情
    
    Args:
        experiment_id: 实验ID
        include_generations: 是否包含代际信息
        include_statistics: 是否包含统计信息
        dal: 数据访问层
    
    Returns:
        实验详情
    """
    try:
        # 验证实验ID
        validate_uuid(experiment_id)
        
        # 获取实验
        experiment = await dal.get_experiment(experiment_id)
        if not experiment:
            raise HTTPException(
                status_code=404,
                detail=f"Experiment {experiment_id} not found"
            )
        
        # 如果需要包含代际信息
        if include_generations:
            generations = await dal.get_experiment_generations(experiment_id)
            experiment.generations = generations
        
        # 如果需要包含统计信息
        if include_statistics:
            statistics = await dal.get_experiment_statistics(experiment_id)
            experiment.statistics = statistics
        
        return SuccessResponse(
            data=experiment,
            message="Experiment retrieved successfully"
        )
        
    except ValidationError as e:
        logger.error(f"Validation error getting experiment: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    
    except Exception as e:
        logger.error(f"Unexpected error getting experiment: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/{experiment_id}", response_model=SuccessResponse[ExperimentDTO])
async def update_experiment(
    experiment_id: str,
    request: UpdateExperimentRequest,
    dal: DataAccessLayer = Depends(get_data_access_layer),
    coordinator: ModuleCoordinator = Depends(get_module_coordinator)
):
    """
    更新实验
    
    Args:
        experiment_id: 实验ID
        request: 更新实验请求
        dal: 数据访问层
        coordinator: 模块协调器
    
    Returns:
        更新后的实验信息
    """
    try:
        logger.info(f"Updating experiment: {experiment_id}")
        
        # 验证实验ID
        validate_uuid(experiment_id)
        
        # 验证请求
        validate_update_experiment_request(request)
        
        # 检查实验是否存在
        existing_experiment = await dal.get_experiment(experiment_id)
        if not existing_experiment:
            raise HTTPException(
                status_code=404,
                detail=f"Experiment {experiment_id} not found"
            )
        
        # 检查是否可以更新
        if existing_experiment.status == 'running':
            # 运行中的实验只能更新某些字段
            allowed_fields = ['description', 'tags', 'metadata']
            if any(getattr(request, field) is not None for field in ['name', 'config'] if hasattr(request, field)):
                raise HTTPException(
                    status_code=400,
                    detail="Cannot update name or config of running experiment"
                )
        
        # 验证配置（如果提供）
        if request.config:
            validate_experiment_config(request.config)
        
        # 检查名称冲突（如果更新名称）
        if request.name and request.name != existing_experiment.name:
            name_conflict = await dal.get_experiment_by_name(request.name)
            if name_conflict:
                raise HTTPException(
                    status_code=400,
                    detail=f"Experiment with name '{request.name}' already exists"
                )
        
        # 准备更新数据
        update_data = {}
        
        if request.name is not None:
            update_data['name'] = request.name
        if request.description is not None:
            update_data['description'] = request.description
        if request.config is not None:
            update_data['config'] = request.config
            # 更新相关配置字段
            if 'population_size' in request.config:
                update_data['population_size'] = request.config['population_size']
            if 'max_generations' in request.config:
                update_data['max_generations'] = request.config['max_generations']
        if request.tags is not None:
            update_data['tags'] = request.tags
        if request.metadata is not None:
            update_data['metadata'] = {**(existing_experiment.metadata or {}), **request.metadata}
        
        update_data['updated_at'] = datetime.utcnow()
        update_data['updated_by'] = request.updated_by
        
        # 更新实验
        updated_experiment = await dal.update_experiment(experiment_id, update_data)
        
        # 如果配置发生变化，通知协调器
        if request.config and existing_experiment.status != 'running':
            try:
                await coordinator.update_experiment_config(experiment_id, request.config)
            except Exception as e:
                logger.warning(f"Failed to update experiment config in coordinator: {str(e)}")
        
        logger.info(f"Experiment updated successfully: {experiment_id}")
        
        return SuccessResponse(
            data=updated_experiment,
            message="Experiment updated successfully"
        )
        
    except ValidationError as e:
        logger.error(f"Validation error updating experiment: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    
    except EvoForgeError as e:
        logger.error(f"EvoForge error updating experiment: {e.message}")
        raise HTTPException(status_code=500, detail=e.message)
    
    except Exception as e:
        logger.error(f"Unexpected error updating experiment: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/{experiment_id}", response_model=SuccessResponse[Dict[str, str]])
async def delete_experiment(
    experiment_id: str,
    force: bool = Query(False, description="强制删除（即使正在运行）"),
    dal: DataAccessLayer = Depends(get_data_access_layer),
    coordinator: ModuleCoordinator = Depends(get_module_coordinator)
):
    """
    删除实验
    
    Args:
        experiment_id: 实验ID
        force: 是否强制删除
        dal: 数据访问层
        coordinator: 模块协调器
    
    Returns:
        删除确认信息
    """
    try:
        logger.info(f"Deleting experiment: {experiment_id}")
        
        # 验证实验ID
        validate_uuid(experiment_id)
        
        # 检查实验是否存在
        experiment = await dal.get_experiment(experiment_id)
        if not experiment:
            raise HTTPException(
                status_code=404,
                detail=f"Experiment {experiment_id} not found"
            )
        
        # 检查实验状态
        if experiment.status == 'running' and not force:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete running experiment without force flag"
            )
        
        # 如果实验正在运行，先停止它
        if experiment.status == 'running':
            try:
                evolution_engine = coordinator.get_evolution_engine()
                await evolution_engine.stop_evolution(experiment_id)
            except Exception as e:
                logger.warning(f"Failed to stop evolution before deletion: {str(e)}")
        
        # 清理实验资源
        try:
            await coordinator.cleanup_experiment(experiment_id)
        except Exception as e:
            logger.warning(f"Failed to cleanup experiment resources: {str(e)}")
        
        # 删除实验（级联删除相关数据）
        await dal.delete_experiment(experiment_id)
        
        logger.info(f"Experiment deleted successfully: {experiment_id}")
        
        return SuccessResponse(
            data={"experiment_id": experiment_id, "status": "deleted"},
            message="Experiment deleted successfully"
        )
        
    except ValidationError as e:
        logger.error(f"Validation error deleting experiment: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    
    except Exception as e:
        logger.error(f"Unexpected error deleting experiment: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/", response_model=PaginatedResponse[ExperimentSummaryDTO])
async def list_experiments(
    status: Optional[str] = Query(None, description="状态过滤"),
    created_by: Optional[str] = Query(None, description="创建者过滤"),
    tags: Optional[str] = Query(None, description="标签过滤（逗号分隔）"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="排序顺序"),
    dal: DataAccessLayer = Depends(get_data_access_layer)
):
    """
    获取实验列表
    
    Args:
        status: 状态过滤
        created_by: 创建者过滤
        tags: 标签过滤
        page: 页码
        page_size: 每页大小
        sort_by: 排序字段
        sort_order: 排序顺序
        dal: 数据访问层
    
    Returns:
        分页的实验列表
    """
    try:
        # 构建过滤条件
        filters = {}
        if status:
            filters['status'] = status
        if created_by:
            filters['created_by'] = created_by
        if tags:
            tag_list = [tag.strip() for tag in tags.split(',')]
            filters['tags'] = tag_list
        
        # 获取实验列表
        experiments, total_count = await dal.list_experiments(
            filters=filters,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        # 转换为摘要DTO
        experiment_summaries = [
            ExperimentSummaryDTO(
                id=exp.id,
                name=exp.name,
                description=exp.description,
                status=exp.status,
                current_generation=exp.current_generation,
                max_generations=exp.max_generations,
                population_size=exp.population_size,
                best_fitness=exp.best_fitness,
                created_at=exp.created_at,
                updated_at=exp.updated_at,
                created_by=exp.created_by,
                tags=exp.tags
            )
            for exp in experiments
        ]
        
        return PaginatedResponse(
            data=experiment_summaries,
            total=total_count,
            page=page,
            page_size=page_size,
            total_pages=(total_count + page_size - 1) // page_size
        )
        
    except ValidationError as e:
        logger.error(f"Validation error listing experiments: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    
    except Exception as e:
        logger.error(f"Unexpected error listing experiments: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/{experiment_id}/clone", response_model=SuccessResponse[ExperimentDTO])
async def clone_experiment(
    experiment_id: str,
    request: CloneExperimentRequest,
    dal: DataAccessLayer = Depends(get_data_access_layer),
    coordinator: ModuleCoordinator = Depends(get_module_coordinator)
):
    """
    克隆实验
    
    Args:
        experiment_id: 源实验ID
        request: 克隆请求
        dal: 数据访问层
        coordinator: 模块协调器
    
    Returns:
        克隆的实验信息
    """
    try:
        logger.info(f"Cloning experiment: {experiment_id}")
        
        # 验证实验ID
        validate_uuid(experiment_id)
        
        # 获取源实验
        source_experiment = await dal.get_experiment(experiment_id)
        if not source_experiment:
            raise HTTPException(
                status_code=404,
                detail=f"Source experiment {experiment_id} not found"
            )
        
        # 检查新名称是否已存在
        existing_experiment = await dal.get_experiment_by_name(request.new_name)
        if existing_experiment:
            raise HTTPException(
                status_code=400,
                detail=f"Experiment with name '{request.new_name}' already exists"
            )
        
        # 生成新实验ID
        new_experiment_id = str(uuid4())
        
        # 准备克隆数据
        clone_data = {
            'id': new_experiment_id,
            'name': request.new_name,
            'description': request.description or f"Clone of {source_experiment.name}",
            'config': {**source_experiment.config, **(request.config_overrides or {})},
            'status': 'created',
            'population_size': source_experiment.population_size,
            'max_generations': source_experiment.max_generations,
            'current_generation': 0,
            'best_fitness': None,
            'average_fitness': None,
            'diversity_score': None,
            'convergence_rate': None,
            'total_evaluations': 0,
            'elapsed_time': 0,
            'estimated_remaining': None,
            'created_at': datetime.utcnow(),
            'created_by': request.created_by,
            'tags': request.tags or source_experiment.tags,
            'metadata': {
                **(request.metadata or {}),
                'cloned_from': experiment_id,
                'clone_timestamp': datetime.utcnow().isoformat()
            }
        }
        
        # 应用配置覆盖
        if request.config_overrides:
            if 'population_size' in request.config_overrides:
                clone_data['population_size'] = request.config_overrides['population_size']
            if 'max_generations' in request.config_overrides:
                clone_data['max_generations'] = request.config_overrides['max_generations']
        
        # 创建克隆实验
        cloned_experiment = await dal.create_experiment(clone_data)
        
        # 如果需要克隆数据
        if request.clone_data:
            try:
                if request.clone_generations:
                    # 克隆代际数据
                    await dal.clone_experiment_generations(
                        experiment_id, 
                        new_experiment_id,
                        max_generations=request.clone_generations
                    )
                
                if request.clone_individuals:
                    # 克隆个体数据
                    await dal.clone_experiment_individuals(
                        experiment_id,
                        new_experiment_id
                    )
                
            except Exception as e:
                # 如果克隆数据失败，删除已创建的实验
                await dal.delete_experiment(new_experiment_id)
                raise EvoForgeError(
                    error_type=ErrorType.DATA_ERROR,
                    message=f"Failed to clone experiment data: {str(e)}"
                )
        
        # 初始化克隆实验环境
        try:
            await coordinator.initialize_experiment(new_experiment_id, clone_data['config'])
        except Exception as e:
            # 如果初始化失败，删除已创建的实验
            await dal.delete_experiment(new_experiment_id)
            raise EvoForgeError(
                error_type=ErrorType.INITIALIZATION_ERROR,
                message=f"Failed to initialize cloned experiment: {str(e)}"
            )
        
        logger.info(f"Experiment cloned successfully: {experiment_id} -> {new_experiment_id}")
        
        return SuccessResponse(
            data=cloned_experiment,
            message="Experiment cloned successfully"
        )
        
    except ValidationError as e:
        logger.error(f"Validation error cloning experiment: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    
    except EvoForgeError as e:
        logger.error(f"EvoForge error cloning experiment: {e.message}")
        raise HTTPException(status_code=500, detail=e.message)
    
    except Exception as e:
        logger.error(f"Unexpected error cloning experiment: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{experiment_id}/statistics", response_model=SuccessResponse[StatisticsResponse])
async def get_experiment_statistics(
    experiment_id: str,
    include_trends: bool = Query(True, description="是否包含趋势数据"),
    include_distributions: bool = Query(True, description="是否包含分布数据"),
    dal: DataAccessLayer = Depends(get_data_access_layer)
):
    """
    获取实验统计信息
    
    Args:
        experiment_id: 实验ID
        include_trends: 是否包含趋势数据
        include_distributions: 是否包含分布数据
        dal: 数据访问层
    
    Returns:
        实验统计信息
    """
    try:
        # 验证实验ID
        validate_uuid(experiment_id)
        
        # 检查实验是否存在
        experiment = await dal.get_experiment(experiment_id)
        if not experiment:
            raise HTTPException(
                status_code=404,
                detail=f"Experiment {experiment_id} not found"
            )
        
        # 获取统计信息
        statistics = await dal.get_experiment_statistics(
            experiment_id,
            include_trends=include_trends,
            include_distributions=include_distributions
        )
        
        return SuccessResponse(
            data=statistics,
            message="Experiment statistics retrieved successfully"
        )
        
    except ValidationError as e:
        logger.error(f"Validation error getting experiment statistics: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    
    except Exception as e:
        logger.error(f"Unexpected error getting experiment statistics: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/query", response_model=PaginatedResponse[ExperimentDTO])
async def query_experiments(
    request: QueryRequest,
    dal: DataAccessLayer = Depends(get_data_access_layer)
):
    """
    高级实验查询
    
    Args:
        request: 查询请求
        dal: 数据访问层
    
    Returns:
        查询结果
    """
    try:
        logger.info(f"Performing advanced experiment query")
        
        # 执行查询
        experiments, total_count = await dal.query_experiments(
            filters=request.filters,
            search_text=request.search_text,
            date_range=request.date_range,
            aggregations=request.aggregations,
            page=request.pagination.page if request.pagination else 1,
            page_size=request.pagination.page_size if request.pagination else 20,
            sort_by=request.sort.field if request.sort else "created_at",
            sort_order=request.sort.order if request.sort else "desc"
        )
        
        return PaginatedResponse(
            data=experiments,
            total=total_count,
            page=request.pagination.page if request.pagination else 1,
            page_size=request.pagination.page_size if request.pagination else 20,
            total_pages=(total_count + (request.pagination.page_size if request.pagination else 20) - 1) // (request.pagination.page_size if request.pagination else 20)
        )
        
    except ValidationError as e:
        logger.error(f"Validation error in experiment query: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    
    except Exception as e:
        logger.error(f"Unexpected error in experiment query: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")