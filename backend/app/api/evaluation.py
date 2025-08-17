#!/usr/bin/env python3
"""
评估API路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import structlog
from datetime import datetime, timedelta

from app.core.database import get_db
from app.schemas.evaluation import (
    EvaluationResponse,
    ApiCostResponse,
    OracleEvaluationRequest,
    OracleEvaluationResult
)
from app.models.evaluation import EvaluationLog, ApiCost
from app.models.digital_cell import DigitalCell
from app.models.task import Task
from app.services.oracle.siliconflow import OracleService
from app.services.execution.docker_executor import DockerExecutor, MockExecutor

logger = structlog.get_logger()

router = APIRouter(prefix="/evaluation", tags=["evaluation"])

@router.post("/oracle", response_model=OracleEvaluationResult)
async def evaluate_with_oracle(
    request: OracleEvaluationRequest,
    db: Session = Depends(get_db)
):
    """使用甲骨文评估代码"""
    try:
        # 验证任务是否存在（如果提供了task_id）
        task_description = request.task_description
        if request.task_id:
            task = db.query(Task).filter(Task.id == request.task_id).first()
            if not task:
                raise HTTPException(status_code=404, detail="任务不存在")
            task_description = task.description
        
        # 使用甲骨文服务评估
        async with OracleService() as oracle:
            result = await oracle.evaluate_code(request.code, task_description)
        
        # 记录评估日志（如果提供了cell_id）
        if request.cell_id:
            cell = db.query(DigitalCell).filter(DigitalCell.id == request.cell_id).first()
            if cell:
                evaluation_log = EvaluationLog(
                    digital_cell_id=request.cell_id,
                    task_id=request.task_id,
                    oracle_request=request.code,
                    oracle_response=result.feedback,
                    fitness_score=result.overall_score,
                    api_cost=result.cost,
                    execution_time=0.0  # Oracle评估时间
                )
                db.add(evaluation_log)
                
                # 更新细胞的适应度分数
                cell.fitness_score = result.overall_score
                
                db.commit()
        
        logger.info("甲骨文评估完成", 
                   overall_score=result.overall_score,
                   cost=result.cost)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("甲骨文评估失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"评估失败: {str(e)}")

@router.post("/execute")
async def execute_code(
    code: str,
    test_input: str = "",
    use_docker: bool = True
):
    """执行代码"""
    try:
        if use_docker:
            executor = DockerExecutor()
            # 检查Docker是否可用
            if not executor.ensure_image_available():
                logger.warning("Docker不可用，使用模拟执行器")
                executor = MockExecutor()
        else:
            executor = MockExecutor()
        
        result = await executor.execute_code(code, test_input)
        
        logger.info("代码执行完成", 
                   success=result.success,
                   execution_time=result.execution_time)
        
        return {
            "success": result.success,
            "output": result.output,
            "error": result.error,
            "execution_time": result.execution_time,
            "memory_usage": result.memory_usage,
            "exit_code": result.exit_code
        }
        
    except Exception as e:
        logger.error("代码执行失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"执行失败: {str(e)}")

@router.post("/validate")
async def validate_code_syntax(
    code: str
):
    """验证代码语法"""
    try:
        executor = MockExecutor()  # 语法验证不需要Docker
        result = await executor.validate_code_syntax(code)
        
        return result
        
    except Exception as e:
        logger.error("代码验证失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"验证失败: {str(e)}")

@router.get("/logs", response_model=List[EvaluationResponse])
async def get_evaluation_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    cell_id: Optional[int] = Query(None),
    task_id: Optional[int] = Query(None),
    min_fitness: Optional[float] = Query(None),
    max_fitness: Optional[float] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db)
):
    """获取评估日志"""
    try:
        query = db.query(EvaluationLog)
        
        # 过滤条件
        if cell_id:
            query = query.filter(EvaluationLog.digital_cell_id == cell_id)
        
        if task_id:
            query = query.filter(EvaluationLog.task_id == task_id)
        
        if min_fitness is not None:
            query = query.filter(EvaluationLog.fitness_score >= min_fitness)
        
        if max_fitness is not None:
            query = query.filter(EvaluationLog.fitness_score <= max_fitness)
        
        if start_date:
            query = query.filter(EvaluationLog.created_at >= start_date)
        
        if end_date:
            query = query.filter(EvaluationLog.created_at <= end_date)
        
        # 排序和分页
        logs = query.order_by(EvaluationLog.created_at.desc()).offset(skip).limit(limit).all()
        
        return [
            EvaluationResponse(
                id=log.id,
                digital_cell_id=log.digital_cell_id,
                task_id=log.task_id,
                oracle_request=log.oracle_request,
                oracle_response=log.oracle_response,
                fitness_score=log.fitness_score,
                api_cost=log.api_cost,
                execution_time=log.execution_time,
                created_at=log.created_at
            )
            for log in logs
        ]
        
    except Exception as e:
        logger.error("获取评估日志失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取日志失败: {str(e)}")

@router.get("/costs", response_model=List[ApiCostResponse])
async def get_api_costs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service_name: Optional[str] = Query(None),
    model_name: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db)
):
    """获取API成本记录"""
    try:
        query = db.query(ApiCost)
        
        # 过滤条件
        if service_name:
            query = query.filter(ApiCost.service_name == service_name)
        
        if model_name:
            query = query.filter(ApiCost.model_name == model_name)
        
        if start_date:
            query = query.filter(ApiCost.created_at >= start_date)
        
        if end_date:
            query = query.filter(ApiCost.created_at <= end_date)
        
        # 排序和分页
        costs = query.order_by(ApiCost.created_at.desc()).offset(skip).limit(limit).all()
        
        return [
            ApiCostResponse(
                id=cost.id,
                service_name=cost.service_name,
                model_name=cost.model_name,
                input_tokens=cost.input_tokens,
                output_tokens=cost.output_tokens,
                cost_usd=cost.cost_usd,
                created_at=cost.created_at
            )
            for cost in costs
        ]
        
    except Exception as e:
        logger.error("获取API成本失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取成本失败: {str(e)}")

@router.get("/stats")
async def get_evaluation_stats(
    days: int = Query(7, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """获取评估统计信息"""
    try:
        # 计算时间范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # 基本统计
        total_evaluations = db.query(EvaluationLog).filter(
            EvaluationLog.created_at >= start_date
        ).count()
        
        # 平均适应度
        avg_fitness_result = db.query(
            db.func.avg(EvaluationLog.fitness_score)
        ).filter(
            EvaluationLog.created_at >= start_date
        ).scalar()
        
        avg_fitness = float(avg_fitness_result) if avg_fitness_result else 0.0
        
        # 最高适应度
        max_fitness_result = db.query(
            db.func.max(EvaluationLog.fitness_score)
        ).filter(
            EvaluationLog.created_at >= start_date
        ).scalar()
        
        max_fitness = float(max_fitness_result) if max_fitness_result else 0.0
        
        # 总成本
        total_cost_result = db.query(
            db.func.sum(ApiCost.cost_usd)
        ).filter(
            ApiCost.created_at >= start_date
        ).scalar()
        
        total_cost = float(total_cost_result) if total_cost_result else 0.0
        
        # 按服务统计成本
        service_costs = db.query(
            ApiCost.service_name,
            db.func.sum(ApiCost.cost_usd).label('total_cost'),
            db.func.sum(ApiCost.input_tokens).label('total_input_tokens'),
            db.func.sum(ApiCost.output_tokens).label('total_output_tokens')
        ).filter(
            ApiCost.created_at >= start_date
        ).group_by(ApiCost.service_name).all()
        
        # 每日评估趋势
        daily_stats = db.query(
            db.func.date(EvaluationLog.created_at).label('date'),
            db.func.count(EvaluationLog.id).label('count'),
            db.func.avg(EvaluationLog.fitness_score).label('avg_fitness')
        ).filter(
            EvaluationLog.created_at >= start_date
        ).group_by(
            db.func.date(EvaluationLog.created_at)
        ).order_by('date').all()
        
        return {
            "period_days": days,
            "total_evaluations": total_evaluations,
            "average_fitness": avg_fitness,
            "max_fitness": max_fitness,
            "total_cost_usd": total_cost,
            "service_costs": [
                {
                    "service_name": service,
                    "total_cost": float(cost),
                    "input_tokens": int(input_tokens),
                    "output_tokens": int(output_tokens)
                }
                for service, cost, input_tokens, output_tokens in service_costs
            ],
            "daily_trends": [
                {
                    "date": str(date),
                    "evaluation_count": count,
                    "average_fitness": float(avg_fitness) if avg_fitness else 0.0
                }
                for date, count, avg_fitness in daily_stats
            ]
        }
        
    except Exception as e:
        logger.error("获取评估统计失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")

@router.get("/performance")
async def get_performance_metrics(
    hours: int = Query(24, ge=1, le=168),  # 最多7天
    db: Session = Depends(get_db)
):
    """获取性能指标"""
    try:
        # 计算时间范围
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        # 平均执行时间
        avg_execution_time = db.query(
            db.func.avg(EvaluationLog.execution_time)
        ).filter(
            EvaluationLog.created_at >= start_time
        ).scalar()
        
        # 评估频率（每小时）
        evaluation_rate = db.query(EvaluationLog).filter(
            EvaluationLog.created_at >= start_time
        ).count() / hours
        
        # 成功率（假设fitness_score > 0表示成功）
        total_evaluations = db.query(EvaluationLog).filter(
            EvaluationLog.created_at >= start_time
        ).count()
        
        successful_evaluations = db.query(EvaluationLog).filter(
            EvaluationLog.created_at >= start_time,
            EvaluationLog.fitness_score > 0
        ).count()
        
        success_rate = (successful_evaluations / total_evaluations * 100) if total_evaluations > 0 else 0
        
        # 每小时统计
        hourly_stats = db.query(
            db.func.date_trunc('hour', EvaluationLog.created_at).label('hour'),
            db.func.count(EvaluationLog.id).label('count'),
            db.func.avg(EvaluationLog.fitness_score).label('avg_fitness'),
            db.func.avg(EvaluationLog.execution_time).label('avg_execution_time')
        ).filter(
            EvaluationLog.created_at >= start_time
        ).group_by(
            db.func.date_trunc('hour', EvaluationLog.created_at)
        ).order_by('hour').all()
        
        return {
            "period_hours": hours,
            "average_execution_time": float(avg_execution_time) if avg_execution_time else 0.0,
            "evaluation_rate_per_hour": evaluation_rate,
            "success_rate_percent": success_rate,
            "total_evaluations": total_evaluations,
            "successful_evaluations": successful_evaluations,
            "hourly_metrics": [
                {
                    "hour": hour.isoformat(),
                    "evaluation_count": count,
                    "average_fitness": float(avg_fitness) if avg_fitness else 0.0,
                    "average_execution_time": float(avg_exec_time) if avg_exec_time else 0.0
                }
                for hour, count, avg_fitness, avg_exec_time in hourly_stats
            ]
        }
        
    except Exception as e:
        logger.error("获取性能指标失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取性能指标失败: {str(e)}")

@router.delete("/logs/{log_id}")
async def delete_evaluation_log(
    log_id: int,
    db: Session = Depends(get_db)
):
    """删除评估日志"""
    try:
        log = db.query(EvaluationLog).filter(EvaluationLog.id == log_id).first()
        
        if not log:
            raise HTTPException(status_code=404, detail="评估日志不存在")
        
        db.delete(log)
        db.commit()
        
        logger.info("评估日志删除成功", log_id=log_id)
        
        return {"message": "评估日志删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("删除评估日志失败", log_id=log_id, error=str(e))
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")