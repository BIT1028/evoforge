# -*- coding: utf-8 -*-
"""
评估管理API路由

提供评估管理的RESTful API端点：
- 创建评估
- 获取评估
- 批量评估
- 评估结果分析
- 评估性能监控
"""

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime
from uuid import uuid4
import asyncio

from ..models.requests import (
    CreateEvaluationRequest,
    BatchEvaluationRequest,
    QueryRequest
)
from ..models.responses import (
    SuccessResponse,
    ErrorResponse,
    PaginatedResponse,
    EvaluationResponse,
    StatisticsResponse
)
from ..models.dtos import EvaluationDTO, EvaluationSummaryDTO
from ..models.validators import (
    validate_uuid,
    validate_fitness_scores,
    validate_evaluation_request,
    ValidationError
)
from ...database.data_access_layer import DataAccessLayer
from ...core.error_handler import EvoForgeError, ErrorType
from ...llm_oracle.fitness import FitnessEvaluator
from ...sandbox.secure_executor import SecureExecutor

# 创建路由器
router = APIRouter()
logger = logging.getLogger(__name__)

# 依赖注入
async def get_data_access_layer() -> DataAccessLayer:
    """获取数据访问层"""
    # 这里应该从应用状态中获取
    return None

async def get_fitness_evaluator() -> FitnessEvaluator:
    """获取适应度评估器"""
    # 这里应该从应用状态中获取
    return None

async def get_secure_executor() -> SecureExecutor:
    """获取安全执行器"""
    # 这里应该从应用状态中获取
    return None

@router.post("/", response_model=SuccessResponse[EvaluationDTO])
async def create_evaluation(
    request: CreateEvaluationRequest,
    background_tasks: BackgroundTasks,
    dal: DataAccessLayer = Depends(get_data_access_layer),
    fitness_evaluator: FitnessEvaluator = Depends(get_fitness_evaluator),
    secure_executor: SecureExecutor = Depends(get_secure_executor)
):
    """
    创建单个评估
    
    Args:
        request: 创建评估请求
        background_tasks: 后台任务
        dal: 数据访问层
        fitness_evaluator: 适应度评估器
        secure_executor: 安全执行器
    
    Returns:
        创建的评估信息
    """
    try:
        logger.info(f"Creating evaluation for individual: {request.individual_id}")
        
        # 验证请求
        validate_evaluation_request(request)
        
        # 验证个体是否存在
        individual = await dal.get_individual(request.individual_id)
        if not individual:
            raise HTTPException(
                status_code=404,
                detail=f"Individual {request.individual_id} not found"
            )
        
        # 验证实验是否存在
        experiment = await dal.get_experiment(request.experiment_id)
        if not experiment:
            raise HTTPException(
                status_code=404,
                detail=f"Experiment {request.experiment_id} not found"
            )
        
        # 生成评估ID
        evaluation_id = str(uuid4())
        
        # 准备评估数据
        evaluation_data = {
            'id': evaluation_id,
            'individual_id': request.individual_id,
            'experiment_id': request.experiment_id,
            'generation': request.generation,
            'evaluation_type': request.evaluation_type,
            'status': 'pending',
            'fitness_scores': None,
            'detailed_metrics': None,
            'execution_time': None,
            'memory_usage': None,
            'error_message': None,
            'created_at': datetime.utcnow(),
            'started_at': None,
            'completed_at': None,
            'metadata': request.metadata or {}
        }
        
        # 创建评估记录
        evaluation = await dal.create_evaluation(evaluation_data)
        
        # 如果是同步评估，立即执行
        if request.async_evaluation:
            # 异步评估 - 添加到后台任务
            background_tasks.add_task(
                _execute_evaluation_async,
                evaluation_id,
                individual,
                experiment,
                request,
                dal,
                fitness_evaluator,
                secure_executor
            )
        else:
            # 同步评估 - 立即执行
            evaluation = await _execute_evaluation_sync(
                evaluation_id,
                individual,
                experiment,
                request,
                dal,
                fitness_evaluator,
                secure_executor
            )
        
        logger.info(f"Evaluation created successfully: {evaluation_id}")
        
        return SuccessResponse(
            data=evaluation,
            message="Evaluation created successfully"
        )
        
    except ValidationError as e:
        logger.error(f"Validation error creating evaluation: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    
    except EvoForgeError as e:
        logger.error(f"EvoForge error creating evaluation: {e.message}")
        raise HTTPException(status_code=500, detail=e.message)
    
    except Exception as e:
        logger.error(f"Unexpected error creating evaluation: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/batch", response_model=SuccessResponse[List[EvaluationDTO]])
async def create_batch_evaluation(
    request: BatchEvaluationRequest,
    background_tasks: BackgroundTasks,
    dal: DataAccessLayer = Depends(get_data_access_layer),
    fitness_evaluator: FitnessEvaluator = Depends(get_fitness_evaluator),
    secure_executor: SecureExecutor = Depends(get_secure_executor)
):
    """
    创建批量评估
    
    Args:
        request: 批量评估请求
        background_tasks: 后台任务
        dal: 数据访问层
        fitness_evaluator: 适应度评估器
        secure_executor: 安全执行器
    
    Returns:
        创建的评估列表
    """
    try:
        logger.info(f"Creating batch evaluation for {len(request.individual_ids)} individuals")
        
        # 验证实验是否存在
        experiment = await dal.get_experiment(request.experiment_id)
        if not experiment:
            raise HTTPException(
                status_code=404,
                detail=f"Experiment {request.experiment_id} not found"
            )
        
        # 验证个体是否存在
        individuals = await dal.get_individuals_batch(request.individual_ids)
        if len(individuals) != len(request.individual_ids):
            missing_ids = set(request.individual_ids) - {ind.id for ind in individuals}
            raise HTTPException(
                status_code=404,
                detail=f"Individuals not found: {list(missing_ids)}"
            )
        
        # 创建评估记录
        evaluations = []
        evaluation_tasks = []
        
        for individual in individuals:
            evaluation_id = str(uuid4())
            
            evaluation_data = {
                'id': evaluation_id,
                'individual_id': individual.id,
                'experiment_id': request.experiment_id,
                'generation': request.generation,
                'evaluation_type': request.evaluation_type,
                'status': 'pending',
                'fitness_scores': None,
                'detailed_metrics': None,
                'execution_time': None,
                'memory_usage': None,
                'error_message': None,
                'created_at': datetime.utcnow(),
                'started_at': None,
                'completed_at': None,
                'metadata': request.metadata or {}
            }
            
            evaluation = await dal.create_evaluation(evaluation_data)
            evaluations.append(evaluation)
            
            # 准备评估任务
            if request.parallel_execution:
                evaluation_tasks.append(
                    _execute_evaluation_async(
                        evaluation_id,
                        individual,
                        experiment,
                        request,
                        dal,
                        fitness_evaluator,
                        secure_executor
                    )
                )
        
        # 执行评估
        if request.parallel_execution:
            # 并行执行
            if request.async_evaluation:
                # 异步并行执行
                for task in evaluation_tasks:
                    background_tasks.add_task(task)
            else:
                # 同步并行执行
                batch_size = request.batch_size or 10
                for i in range(0, len(evaluation_tasks), batch_size):
                    batch_tasks = evaluation_tasks[i:i + batch_size]
                    await asyncio.gather(*batch_tasks, return_exceptions=True)
        else:
            # 串行执行
            for i, evaluation_task in enumerate(evaluation_tasks):
                if request.async_evaluation:
                    background_tasks.add_task(evaluation_task)
                else:
                    try:
                        await evaluation_task
                        # 更新评估状态
                        evaluations[i] = await dal.get_evaluation(evaluations[i].id)
                    except Exception as e:
                        logger.error(f"Error in evaluation {evaluations[i].id}: {str(e)}")
        
        logger.info(f"Batch evaluation created successfully: {len(evaluations)} evaluations")
        
        return SuccessResponse(
            data=evaluations,
            message=f"Batch evaluation created successfully for {len(evaluations)} individuals"
        )
        
    except ValidationError as e:
        logger.error(f"Validation error creating batch evaluation: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    
    except EvoForgeError as e:
        logger.error(f"EvoForge error creating batch evaluation: {e.message}")
        raise HTTPException(status_code=500, detail=e.message)
    
    except Exception as e:
        logger.error(f"Unexpected error creating batch evaluation: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{evaluation_id}", response_model=SuccessResponse[EvaluationDTO])
async def get_evaluation(
    evaluation_id: str,
    include_details: bool = Query(True, description="是否包含详细指标"),
    dal: DataAccessLayer = Depends(get_data_access_layer)
):
    """
    获取评估详情
    
    Args:
        evaluation_id: 评估ID
        include_details: 是否包含详细指标
        dal: 数据访问层
    
    Returns:
        评估详情
    """
    try:
        # 验证评估ID
        validate_uuid(evaluation_id)
        
        # 获取评估
        evaluation = await dal.get_evaluation(evaluation_id)
        if not evaluation:
            raise HTTPException(
                status_code=404,
                detail=f"Evaluation {evaluation_id} not found"
            )
        
        # 如果需要详细信息
        if include_details and evaluation.detailed_metrics:
            # 获取详细指标
            detailed_metrics = await dal.get_evaluation_detailed_metrics(evaluation_id)
            evaluation.detailed_metrics = detailed_metrics
        
        return SuccessResponse(
            data=evaluation,
            message="Evaluation retrieved successfully"
        )
        
    except ValidationError as e:
        logger.error(f"Validation error getting evaluation: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    
    except Exception as e:
        logger.error(f"Unexpected error getting evaluation: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/experiment/{experiment_id}", response_model=PaginatedResponse[EvaluationSummaryDTO])
async def list_experiment_evaluations(
    experiment_id: str,
    generation: Optional[int] = Query(None, description="代际过滤"),
    status: Optional[str] = Query(None, description="状态过滤"),
    evaluation_type: Optional[str] = Query(None, description="评估类型过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="排序顺序"),
    dal: DataAccessLayer = Depends(get_data_access_layer)
):
    """
    获取实验的评估列表
    
    Args:
        experiment_id: 实验ID
        generation: 代际过滤
        status: 状态过滤
        evaluation_type: 评估类型过滤
        page: 页码
        page_size: 每页大小
        sort_by: 排序字段
        sort_order: 排序顺序
        dal: 数据访问层
    
    Returns:
        分页的评估列表
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
        
        # 构建过滤条件
        filters = {'experiment_id': experiment_id}
        if generation is not None:
            filters['generation'] = generation
        if status:
            filters['status'] = status
        if evaluation_type:
            filters['evaluation_type'] = evaluation_type
        
        # 获取评估列表
        evaluations, total_count = await dal.list_evaluations(
            filters=filters,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        # 转换为摘要DTO
        evaluation_summaries = [
            EvaluationSummaryDTO(
                id=eval.id,
                individual_id=eval.individual_id,
                experiment_id=eval.experiment_id,
                generation=eval.generation,
                evaluation_type=eval.evaluation_type,
                status=eval.status,
                fitness_scores=eval.fitness_scores,
                execution_time=eval.execution_time,
                created_at=eval.created_at,
                completed_at=eval.completed_at
            )
            for eval in evaluations
        ]
        
        return PaginatedResponse(
            data=evaluation_summaries,
            total=total_count,
            page=page,
            page_size=page_size,
            total_pages=(total_count + page_size - 1) // page_size
        )
        
    except ValidationError as e:
        logger.error(f"Validation error listing evaluations: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    
    except Exception as e:
        logger.error(f"Unexpected error listing evaluations: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/experiment/{experiment_id}/statistics", response_model=SuccessResponse[StatisticsResponse])
async def get_evaluation_statistics(
    experiment_id: str,
    generation: Optional[int] = Query(None, description="代际过滤"),
    evaluation_type: Optional[str] = Query(None, description="评估类型过滤"),
    include_trends: bool = Query(True, description="是否包含趋势数据"),
    include_distributions: bool = Query(True, description="是否包含分布数据"),
    dal: DataAccessLayer = Depends(get_data_access_layer)
):
    """
    获取评估统计信息
    
    Args:
        experiment_id: 实验ID
        generation: 代际过滤
        evaluation_type: 评估类型过滤
        include_trends: 是否包含趋势数据
        include_distributions: 是否包含分布数据
        dal: 数据访问层
    
    Returns:
        评估统计信息
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
        statistics = await dal.get_evaluation_statistics(
            experiment_id,
            generation=generation,
            evaluation_type=evaluation_type,
            include_trends=include_trends,
            include_distributions=include_distributions
        )
        
        return SuccessResponse(
            data=statistics,
            message="Evaluation statistics retrieved successfully"
        )
        
    except ValidationError as e:
        logger.error(f"Validation error getting evaluation statistics: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    
    except Exception as e:
        logger.error(f"Unexpected error getting evaluation statistics: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/{evaluation_id}", response_model=SuccessResponse[Dict[str, str]])
async def delete_evaluation(
    evaluation_id: str,
    dal: DataAccessLayer = Depends(get_data_access_layer)
):
    """
    删除评估
    
    Args:
        evaluation_id: 评估ID
        dal: 数据访问层
    
    Returns:
        删除确认信息
    """
    try:
        logger.info(f"Deleting evaluation: {evaluation_id}")
        
        # 验证评估ID
        validate_uuid(evaluation_id)
        
        # 检查评估是否存在
        evaluation = await dal.get_evaluation(evaluation_id)
        if not evaluation:
            raise HTTPException(
                status_code=404,
                detail=f"Evaluation {evaluation_id} not found"
            )
        
        # 检查评估状态
        if evaluation.status == 'running':
            raise HTTPException(
                status_code=400,
                detail="Cannot delete running evaluation"
            )
        
        # 删除评估
        await dal.delete_evaluation(evaluation_id)
        
        logger.info(f"Evaluation deleted successfully: {evaluation_id}")
        
        return SuccessResponse(
            data={"evaluation_id": evaluation_id, "status": "deleted"},
            message="Evaluation deleted successfully"
        )
        
    except ValidationError as e:
        logger.error(f"Validation error deleting evaluation: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    
    except Exception as e:
        logger.error(f"Unexpected error deleting evaluation: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# 辅助函数

async def _execute_evaluation_sync(
    evaluation_id: str,
    individual: Any,
    experiment: Any,
    request: CreateEvaluationRequest,
    dal: DataAccessLayer,
    fitness_evaluator: FitnessEvaluator,
    secure_executor: SecureExecutor
) -> Any:
    """
    同步执行评估
    
    Args:
        evaluation_id: 评估ID
        individual: 个体
        experiment: 实验
        request: 评估请求
        dal: 数据访问层
        fitness_evaluator: 适应度评估器
        secure_executor: 安全执行器
    
    Returns:
        更新后的评估
    """
    try:
        # 更新状态为运行中
        await dal.update_evaluation(evaluation_id, {
            'status': 'running',
            'started_at': datetime.utcnow()
        })
        
        # 执行评估
        start_time = datetime.utcnow()
        
        # 使用安全执行器执行个体代码
        execution_result = await secure_executor.execute_individual(
            individual.genome,
            experiment.config.get('test_cases', []),
            timeout=experiment.config.get('evaluation_timeout', 30)
        )
        
        # 使用适应度评估器计算适应度
        fitness_result = await fitness_evaluator.evaluate_individual(
            individual,
            execution_result,
            experiment.config
        )
        
        end_time = datetime.utcnow()
        execution_time = (end_time - start_time).total_seconds()
        
        # 更新评估结果
        update_data = {
            'status': 'completed',
            'fitness_scores': fitness_result.fitness_scores,
            'detailed_metrics': fitness_result.detailed_metrics,
            'execution_time': execution_time,
            'memory_usage': execution_result.memory_usage,
            'completed_at': end_time
        }
        
        return await dal.update_evaluation(evaluation_id, update_data)
        
    except Exception as e:
        logger.error(f"Error executing evaluation {evaluation_id}: {str(e)}")
        
        # 更新错误状态
        await dal.update_evaluation(evaluation_id, {
            'status': 'failed',
            'error_message': str(e),
            'completed_at': datetime.utcnow()
        })
        
        raise

async def _execute_evaluation_async(
    evaluation_id: str,
    individual: Any,
    experiment: Any,
    request: Any,
    dal: DataAccessLayer,
    fitness_evaluator: FitnessEvaluator,
    secure_executor: SecureExecutor
):
    """
    异步执行评估
    
    Args:
        evaluation_id: 评估ID
        individual: 个体
        experiment: 实验
        request: 评估请求
        dal: 数据访问层
        fitness_evaluator: 适应度评估器
        secure_executor: 安全执行器
    """
    try:
        await _execute_evaluation_sync(
            evaluation_id,
            individual,
            experiment,
            request,
            dal,
            fitness_evaluator,
            secure_executor
        )
    except Exception as e:
        logger.error(f"Async evaluation failed for {evaluation_id}: {str(e)}")