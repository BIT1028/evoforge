# -*- coding: utf-8 -*-
"""
任务管理API路由

提供任务管理的RESTful API端点：
- 创建任务
- 获取任务
- 更新任务
- 删除任务
- 批量操作
- 任务查询和过滤
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime
from uuid import uuid4

from ..models.requests import (
    CreateTaskRequest,
    UpdateTaskRequest,
    BatchTaskRequest,
    QueryRequest
)
from ..models.responses import (
    SuccessResponse,
    ErrorResponse,
    PaginatedResponse,
    TaskResponse
)
from ..models.dtos import TaskDTO, TaskSummaryDTO
from ..models.validators import (
    validate_uuid,
    validate_task_parameters,
    validate_create_task_request,
    validate_update_task_request,
    ValidationError
)
from ...database.data_access_layer import DataAccessLayer
from ...core.error_handler import EvoForgeError, ErrorType

# 创建路由器
router = APIRouter()
logger = logging.getLogger(__name__)

# 依赖注入
async def get_data_access_layer() -> DataAccessLayer:
    """获取数据访问层"""
    # 这里应该从应用状态中获取
    return None

@router.post("/", response_model=SuccessResponse[TaskDTO])
async def create_task(
    request: CreateTaskRequest,
    dal: DataAccessLayer = Depends(get_data_access_layer)
):
    """
    创建新任务
    
    Args:
        request: 创建任务请求
        dal: 数据访问层
    
    Returns:
        创建的任务信息
    """
    try:
        logger.info(f"Creating task: {request.name}")
        
        # 验证请求
        validate_create_task_request(request)
        
        # 验证实验ID（如果提供）
        if request.experiment_id:
            validate_uuid(request.experiment_id)
            
            # 检查实验是否存在
            experiment = await dal.get_experiment(request.experiment_id)
            if not experiment:
                raise HTTPException(
                    status_code=404,
                    detail=f"Experiment {request.experiment_id} not found"
                )
        
        # 验证任务参数
        if request.parameters:
            validate_task_parameters(request.parameters)
        
        # 生成任务ID
        task_id = str(uuid4())
        
        # 准备任务数据
        task_data = {
            'id': task_id,
            'name': request.name,
            'description': request.description,
            'task_type': request.task_type,
            'experiment_id': request.experiment_id,
            'status': 'pending',
            'priority': request.priority,
            'parameters': request.parameters or {},
            'dependencies': request.dependencies or [],
            'estimated_duration': request.estimated_duration,
            'max_retries': request.max_retries,
            'timeout': request.timeout,
            'created_at': datetime.utcnow(),
            'created_by': request.created_by,
            'tags': request.tags or [],
            'metadata': request.metadata or {}
        }
        
        # 创建任务
        task = await dal.create_task(task_data)
        
        logger.info(f"Task created successfully: {task_id}")
        
        return SuccessResponse(
            data=task,
            message="Task created successfully"
        )
        
    except ValidationError as e:
        logger.error(f"Validation error creating task: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    
    except EvoForgeError as e:
        logger.error(f"EvoForge error creating task: {e.message}")
        raise HTTPException(status_code=500, detail=e.message)
    
    except Exception as e:
        logger.error(f"Unexpected error creating task: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{task_id}", response_model=SuccessResponse[TaskDTO])
async def get_task(
    task_id: str,
    dal: DataAccessLayer = Depends(get_data_access_layer)
):
    """
    获取任务详情
    
    Args:
        task_id: 任务ID
        dal: 数据访问层
    
    Returns:
        任务详情
    """
    try:
        # 验证任务ID
        validate_uuid(task_id)
        
        # 获取任务
        task = await dal.get_task(task_id)
        if not task:
            raise HTTPException(
                status_code=404,
                detail=f"Task {task_id} not found"
            )
        
        return SuccessResponse(
            data=task,
            message="Task retrieved successfully"
        )
        
    except ValidationError as e:
        logger.error(f"Validation error getting task: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    
    except Exception as e:
        logger.error(f"Unexpected error getting task: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/{task_id}", response_model=SuccessResponse[TaskDTO])
async def update_task(
    task_id: str,
    request: UpdateTaskRequest,
    dal: DataAccessLayer = Depends(get_data_access_layer)
):
    """
    更新任务
    
    Args:
        task_id: 任务ID
        request: 更新任务请求
        dal: 数据访问层
    
    Returns:
        更新后的任务信息
    """
    try:
        logger.info(f"Updating task: {task_id}")
        
        # 验证任务ID
        validate_uuid(task_id)
        
        # 验证请求
        validate_update_task_request(request)
        
        # 检查任务是否存在
        existing_task = await dal.get_task(task_id)
        if not existing_task:
            raise HTTPException(
                status_code=404,
                detail=f"Task {task_id} not found"
            )
        
        # 验证状态转换
        if request.status and not _is_valid_status_transition(existing_task.status, request.status):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status transition from {existing_task.status} to {request.status}"
            )
        
        # 验证任务参数
        if request.parameters:
            validate_task_parameters(request.parameters)
        
        # 准备更新数据
        update_data = {}
        
        if request.name is not None:
            update_data['name'] = request.name
        if request.description is not None:
            update_data['description'] = request.description
        if request.status is not None:
            update_data['status'] = request.status
            if request.status == 'running':
                update_data['started_at'] = datetime.utcnow()
            elif request.status in ['completed', 'failed', 'cancelled']:
                update_data['completed_at'] = datetime.utcnow()
        if request.priority is not None:
            update_data['priority'] = request.priority
        if request.parameters is not None:
            update_data['parameters'] = request.parameters
        if request.progress is not None:
            update_data['progress'] = request.progress
        if request.result is not None:
            update_data['result'] = request.result
        if request.error_message is not None:
            update_data['error_message'] = request.error_message
        if request.retry_count is not None:
            update_data['retry_count'] = request.retry_count
        if request.tags is not None:
            update_data['tags'] = request.tags
        if request.metadata is not None:
            update_data['metadata'] = {**(existing_task.metadata or {}), **request.metadata}
        
        update_data['updated_at'] = datetime.utcnow()
        update_data['updated_by'] = request.updated_by
        
        # 更新任务
        updated_task = await dal.update_task(task_id, update_data)
        
        logger.info(f"Task updated successfully: {task_id}")
        
        return SuccessResponse(
            data=updated_task,
            message="Task updated successfully"
        )
        
    except ValidationError as e:
        logger.error(f"Validation error updating task: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    
    except EvoForgeError as e:
        logger.error(f"EvoForge error updating task: {e.message}")
        raise HTTPException(status_code=500, detail=e.message)
    
    except Exception as e:
        logger.error(f"Unexpected error updating task: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/{task_id}", response_model=SuccessResponse[Dict[str, str]])
async def delete_task(
    task_id: str,
    dal: DataAccessLayer = Depends(get_data_access_layer)
):
    """
    删除任务
    
    Args:
        task_id: 任务ID
        dal: 数据访问层
    
    Returns:
        删除确认信息
    """
    try:
        logger.info(f"Deleting task: {task_id}")
        
        # 验证任务ID
        validate_uuid(task_id)
        
        # 检查任务是否存在
        task = await dal.get_task(task_id)
        if not task:
            raise HTTPException(
                status_code=404,
                detail=f"Task {task_id} not found"
            )
        
        # 检查任务状态
        if task.status == 'running':
            raise HTTPException(
                status_code=400,
                detail="Cannot delete running task"
            )
        
        # 删除任务
        await dal.delete_task(task_id)
        
        logger.info(f"Task deleted successfully: {task_id}")
        
        return SuccessResponse(
            data={"task_id": task_id, "status": "deleted"},
            message="Task deleted successfully"
        )
        
    except ValidationError as e:
        logger.error(f"Validation error deleting task: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    
    except Exception as e:
        logger.error(f"Unexpected error deleting task: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/", response_model=PaginatedResponse[TaskSummaryDTO])
async def list_tasks(
    experiment_id: Optional[str] = Query(None, description="实验ID过滤"),
    status: Optional[str] = Query(None, description="状态过滤"),
    task_type: Optional[str] = Query(None, description="任务类型过滤"),
    priority: Optional[str] = Query(None, description="优先级过滤"),
    created_by: Optional[str] = Query(None, description="创建者过滤"),
    tags: Optional[str] = Query(None, description="标签过滤（逗号分隔）"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="排序顺序"),
    dal: DataAccessLayer = Depends(get_data_access_layer)
):
    """
    获取任务列表
    
    Args:
        experiment_id: 实验ID过滤
        status: 状态过滤
        task_type: 任务类型过滤
        priority: 优先级过滤
        created_by: 创建者过滤
        tags: 标签过滤
        page: 页码
        page_size: 每页大小
        sort_by: 排序字段
        sort_order: 排序顺序
        dal: 数据访问层
    
    Returns:
        分页的任务列表
    """
    try:
        # 验证实验ID（如果提供）
        if experiment_id:
            validate_uuid(experiment_id)
        
        # 构建过滤条件
        filters = {}
        if experiment_id:
            filters['experiment_id'] = experiment_id
        if status:
            filters['status'] = status
        if task_type:
            filters['task_type'] = task_type
        if priority:
            filters['priority'] = priority
        if created_by:
            filters['created_by'] = created_by
        if tags:
            tag_list = [tag.strip() for tag in tags.split(',')]
            filters['tags'] = tag_list
        
        # 获取任务列表
        tasks, total_count = await dal.list_tasks(
            filters=filters,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        # 转换为摘要DTO
        task_summaries = [
            TaskSummaryDTO(
                id=task.id,
                name=task.name,
                task_type=task.task_type,
                status=task.status,
                priority=task.priority,
                experiment_id=task.experiment_id,
                progress=task.progress,
                created_at=task.created_at,
                updated_at=task.updated_at,
                created_by=task.created_by,
                tags=task.tags
            )
            for task in tasks
        ]
        
        return PaginatedResponse(
            data=task_summaries,
            total=total_count,
            page=page,
            page_size=page_size,
            total_pages=(total_count + page_size - 1) // page_size
        )
        
    except ValidationError as e:
        logger.error(f"Validation error listing tasks: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    
    except Exception as e:
        logger.error(f"Unexpected error listing tasks: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/batch", response_model=SuccessResponse[List[TaskDTO]])
async def batch_task_operations(
    request: BatchTaskRequest,
    dal: DataAccessLayer = Depends(get_data_access_layer)
):
    """
    批量任务操作
    
    Args:
        request: 批量操作请求
        dal: 数据访问层
    
    Returns:
        操作结果
    """
    try:
        logger.info(f"Performing batch operation: {request.operation}")
        
        # 验证任务ID列表
        for task_id in request.task_ids:
            validate_uuid(task_id)
        
        results = []
        errors = []
        
        if request.operation == "delete":
            # 批量删除
            for task_id in request.task_ids:
                try:
                    task = await dal.get_task(task_id)
                    if not task:
                        errors.append(f"Task {task_id} not found")
                        continue
                    
                    if task.status == 'running':
                        errors.append(f"Cannot delete running task {task_id}")
                        continue
                    
                    await dal.delete_task(task_id)
                    results.append({"task_id": task_id, "status": "deleted"})
                    
                except Exception as e:
                    errors.append(f"Error deleting task {task_id}: {str(e)}")
        
        elif request.operation == "update_status":
            # 批量更新状态
            if not request.parameters or 'status' not in request.parameters:
                raise HTTPException(
                    status_code=400,
                    detail="Status parameter required for update_status operation"
                )
            
            new_status = request.parameters['status']
            
            for task_id in request.task_ids:
                try:
                    task = await dal.get_task(task_id)
                    if not task:
                        errors.append(f"Task {task_id} not found")
                        continue
                    
                    if not _is_valid_status_transition(task.status, new_status):
                        errors.append(f"Invalid status transition for task {task_id}: {task.status} -> {new_status}")
                        continue
                    
                    update_data = {
                        'status': new_status,
                        'updated_at': datetime.utcnow()
                    }
                    
                    if new_status == 'running':
                        update_data['started_at'] = datetime.utcnow()
                    elif new_status in ['completed', 'failed', 'cancelled']:
                        update_data['completed_at'] = datetime.utcnow()
                    
                    updated_task = await dal.update_task(task_id, update_data)
                    results.append(updated_task)
                    
                except Exception as e:
                    errors.append(f"Error updating task {task_id}: {str(e)}")
        
        elif request.operation == "update_priority":
            # 批量更新优先级
            if not request.parameters or 'priority' not in request.parameters:
                raise HTTPException(
                    status_code=400,
                    detail="Priority parameter required for update_priority operation"
                )
            
            new_priority = request.parameters['priority']
            
            for task_id in request.task_ids:
                try:
                    task = await dal.get_task(task_id)
                    if not task:
                        errors.append(f"Task {task_id} not found")
                        continue
                    
                    update_data = {
                        'priority': new_priority,
                        'updated_at': datetime.utcnow()
                    }
                    
                    updated_task = await dal.update_task(task_id, update_data)
                    results.append(updated_task)
                    
                except Exception as e:
                    errors.append(f"Error updating task {task_id}: {str(e)}")
        
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported batch operation: {request.operation}"
            )
        
        # 记录错误
        if errors:
            logger.warning(f"Batch operation completed with errors: {errors}")
        
        logger.info(f"Batch operation completed: {len(results)} successful, {len(errors)} errors")
        
        response_data = {
            "results": results,
            "errors": errors,
            "total_processed": len(request.task_ids),
            "successful": len(results),
            "failed": len(errors)
        }
        
        return SuccessResponse(
            data=response_data,
            message=f"Batch operation completed: {len(results)} successful, {len(errors)} errors"
        )
        
    except ValidationError as e:
        logger.error(f"Validation error in batch operation: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    
    except EvoForgeError as e:
        logger.error(f"EvoForge error in batch operation: {e.message}")
        raise HTTPException(status_code=500, detail=e.message)
    
    except Exception as e:
        logger.error(f"Unexpected error in batch operation: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/query", response_model=PaginatedResponse[TaskDTO])
async def query_tasks(
    request: QueryRequest,
    dal: DataAccessLayer = Depends(get_data_access_layer)
):
    """
    高级任务查询
    
    Args:
        request: 查询请求
        dal: 数据访问层
    
    Returns:
        查询结果
    """
    try:
        logger.info(f"Performing advanced task query")
        
        # 执行查询
        tasks, total_count = await dal.query_tasks(
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
            data=tasks,
            total=total_count,
            page=request.pagination.page if request.pagination else 1,
            page_size=request.pagination.page_size if request.pagination else 20,
            total_pages=(total_count + (request.pagination.page_size if request.pagination else 20) - 1) // (request.pagination.page_size if request.pagination else 20)
        )
        
    except ValidationError as e:
        logger.error(f"Validation error in task query: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    
    except Exception as e:
        logger.error(f"Unexpected error in task query: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# 辅助函数
def _is_valid_status_transition(current_status: str, new_status: str) -> bool:
    """
    验证状态转换是否有效
    
    Args:
        current_status: 当前状态
        new_status: 新状态
    
    Returns:
        是否有效
    """
    valid_transitions = {
        'pending': ['running', 'cancelled'],
        'running': ['completed', 'failed', 'paused', 'cancelled'],
        'paused': ['running', 'cancelled'],
        'completed': [],  # 完成状态不能转换
        'failed': ['pending'],  # 失败可以重置为待处理
        'cancelled': ['pending']  # 取消可以重置为待处理
    }
    
    return new_status in valid_transitions.get(current_status, [])