#!/usr/bin/env python3
"""
任务管理API路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import structlog

from app.core.database import get_db
from app.schemas.task import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskReorderRequest,
    TaskBatchRequest
)
from app.models.task import Task

logger = structlog.get_logger()

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.post("/", response_model=TaskResponse)
async def create_task(
    task: TaskCreate,
    db: Session = Depends(get_db)
):
    """创建新任务"""
    try:
        # 检查任务名称是否已存在
        existing_task = db.query(Task).filter(Task.name == task.name).first()
        if existing_task:
            raise HTTPException(status_code=400, detail="任务名称已存在")
        
        # 创建任务
        db_task = Task(
            name=task.name,
            description=task.description,
            priority=task.priority,
            category=task.category,
            template=task.template,
            is_active=task.is_active
        )
        
        db.add(db_task)
        db.commit()
        db.refresh(db_task)
        
        logger.info("任务创建成功", task_id=db_task.id, name=task.name)
        
        return TaskResponse(
            id=db_task.id,
            name=db_task.name,
            description=db_task.description,
            priority=db_task.priority,
            category=db_task.category,
            template=db_task.template,
            is_active=db_task.is_active,
            created_at=db_task.created_at,
            updated_at=db_task.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("创建任务失败", error=str(e))
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")

@router.get("/", response_model=List[TaskResponse])
async def get_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    category: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """获取任务列表"""
    try:
        query = db.query(Task)
        
        # 过滤条件
        if category:
            query = query.filter(Task.category == category)
        
        if is_active is not None:
            query = query.filter(Task.is_active == is_active)
        
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                Task.name.ilike(search_pattern) |
                Task.description.ilike(search_pattern)
            )
        
        # 排序和分页
        tasks = query.order_by(Task.priority.desc(), Task.created_at.desc()).offset(skip).limit(limit).all()
        
        return [
            TaskResponse(
                id=task.id,
                name=task.name,
                description=task.description,
                priority=task.priority,
                category=task.category,
                template=task.template,
                is_active=task.is_active,
                created_at=task.created_at,
                updated_at=task.updated_at
            )
            for task in tasks
        ]
        
    except Exception as e:
        logger.error("获取任务列表失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取任务失败: {str(e)}")

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    """获取单个任务"""
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        return TaskResponse(
            id=task.id,
            name=task.name,
            description=task.description,
            priority=task.priority,
            category=task.category,
            template=task.template,
            is_active=task.is_active,
            created_at=task.created_at,
            updated_at=task.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("获取任务失败", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"获取任务失败: {str(e)}")

@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_update: TaskUpdate,
    db: Session = Depends(get_db)
):
    """更新任务"""
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        # 检查名称冲突（如果更新了名称）
        if task_update.name and task_update.name != task.name:
            existing_task = db.query(Task).filter(
                Task.name == task_update.name,
                Task.id != task_id
            ).first()
            if existing_task:
                raise HTTPException(status_code=400, detail="任务名称已存在")
        
        # 更新字段
        update_data = task_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(task, field, value)
        
        db.commit()
        db.refresh(task)
        
        logger.info("任务更新成功", task_id=task_id)
        
        return TaskResponse(
            id=task.id,
            name=task.name,
            description=task.description,
            priority=task.priority,
            category=task.category,
            template=task.template,
            is_active=task.is_active,
            created_at=task.created_at,
            updated_at=task.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("更新任务失败", task_id=task_id, error=str(e))
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新任务失败: {str(e)}")

@router.delete("/{task_id}")
async def delete_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    """删除任务"""
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        db.delete(task)
        db.commit()
        
        logger.info("任务删除成功", task_id=task_id)
        
        return {"message": "任务删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("删除任务失败", task_id=task_id, error=str(e))
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除任务失败: {str(e)}")

@router.post("/reorder")
async def reorder_tasks(
    request: TaskReorderRequest,
    db: Session = Depends(get_db)
):
    """重新排序任务"""
    try:
        # 验证所有任务ID是否存在
        task_ids = [item.task_id for item in request.tasks]
        existing_tasks = db.query(Task).filter(Task.id.in_(task_ids)).all()
        
        if len(existing_tasks) != len(task_ids):
            raise HTTPException(status_code=400, detail="部分任务不存在")
        
        # 更新优先级
        for item in request.tasks:
            task = db.query(Task).filter(Task.id == item.task_id).first()
            if task:
                task.priority = item.priority
        
        db.commit()
        
        logger.info("任务重排序成功", task_count=len(task_ids))
        
        return {"message": "任务重排序成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("任务重排序失败", error=str(e))
        db.rollback()
        raise HTTPException(status_code=500, detail=f"重排序失败: {str(e)}")

@router.post("/batch")
async def batch_operations(
    request: TaskBatchRequest,
    db: Session = Depends(get_db)
):
    """批量操作任务"""
    try:
        if not request.task_ids:
            raise HTTPException(status_code=400, detail="任务ID列表不能为空")
        
        # 验证任务是否存在
        tasks = db.query(Task).filter(Task.id.in_(request.task_ids)).all()
        
        if len(tasks) != len(request.task_ids):
            raise HTTPException(status_code=400, detail="部分任务不存在")
        
        affected_count = 0
        
        if request.operation == "activate":
            # 批量激活
            for task in tasks:
                task.is_active = True
                affected_count += 1
                
        elif request.operation == "deactivate":
            # 批量停用
            for task in tasks:
                task.is_active = False
                affected_count += 1
                
        elif request.operation == "delete":
            # 批量删除
            for task in tasks:
                db.delete(task)
                affected_count += 1
                
        elif request.operation == "set_category":
            # 批量设置分类
            if not request.category:
                raise HTTPException(status_code=400, detail="分类不能为空")
            
            for task in tasks:
                task.category = request.category
                affected_count += 1
                
        elif request.operation == "set_priority":
            # 批量设置优先级
            if request.priority is None:
                raise HTTPException(status_code=400, detail="优先级不能为空")
            
            for task in tasks:
                task.priority = request.priority
                affected_count += 1
                
        else:
            raise HTTPException(status_code=400, detail=f"未知操作: {request.operation}")
        
        db.commit()
        
        logger.info("批量操作成功", 
                   operation=request.operation, 
                   affected_count=affected_count)
        
        return {
            "message": f"批量{request.operation}成功",
            "affected_count": affected_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("批量操作失败", error=str(e))
        db.rollback()
        raise HTTPException(status_code=500, detail=f"批量操作失败: {str(e)}")

@router.get("/categories/", response_model=List[str])
async def get_task_categories(
    db: Session = Depends(get_db)
):
    """获取所有任务分类"""
    try:
        # 获取所有不同的分类
        categories = db.query(Task.category).distinct().filter(
            Task.category.isnot(None)
        ).all()
        
        return [cat[0] for cat in categories if cat[0]]
        
    except Exception as e:
        logger.error("获取任务分类失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取分类失败: {str(e)}")

@router.get("/stats/")
async def get_task_stats(
    db: Session = Depends(get_db)
):
    """获取任务统计信息"""
    try:
        # 总任务数
        total_tasks = db.query(Task).count()
        
        # 活跃任务数
        active_tasks = db.query(Task).filter(Task.is_active == True).count()
        
        # 按分类统计
        category_stats = db.query(
            Task.category,
            db.func.count(Task.id).label('count')
        ).group_by(Task.category).all()
        
        # 按优先级统计
        priority_stats = db.query(
            Task.priority,
            db.func.count(Task.id).label('count')
        ).group_by(Task.priority).order_by(Task.priority.desc()).all()
        
        return {
            "total_tasks": total_tasks,
            "active_tasks": active_tasks,
            "inactive_tasks": total_tasks - active_tasks,
            "category_distribution": [
                {"category": cat or "未分类", "count": count}
                for cat, count in category_stats
            ],
            "priority_distribution": [
                {"priority": priority, "count": count}
                for priority, count in priority_stats
            ]
        }
        
    except Exception as e:
        logger.error("获取任务统计失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")

@router.post("/{task_id}/toggle")
async def toggle_task_status(
    task_id: int,
    db: Session = Depends(get_db)
):
    """切换任务激活状态"""
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        # 切换状态
        task.is_active = not task.is_active
        db.commit()
        
        status = "激活" if task.is_active else "停用"
        logger.info("任务状态切换成功", task_id=task_id, status=status)
        
        return {
            "message": f"任务已{status}",
            "is_active": task.is_active
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("切换任务状态失败", task_id=task_id, error=str(e))
        db.rollback()
        raise HTTPException(status_code=500, detail=f"状态切换失败: {str(e)}")