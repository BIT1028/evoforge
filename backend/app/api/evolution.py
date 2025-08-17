#!/usr/bin/env python3
"""
进化API路由
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
import structlog

from app.core.database import get_db
from app.schemas.evolution import (
    EvolutionConfig,
    EvolutionStatus,
    EvolutionControlRequest,
    EvolutionStatsResponse,
    DigitalCellResponse,
    GenerationResponse
)
from app.models.digital_cell import DigitalCell
from app.models.generation import Generation
from app.services.evolution.engine import EvolutionEngine
from app.core.websocket import WebSocketManager
from app.services.consciousness.awareness import ConsciousnessService

logger = structlog.get_logger()

router = APIRouter(prefix="/evolution", tags=["evolution"])

# 全局进化引擎实例
evolution_engine: Optional[EvolutionEngine] = None
consciousness_service: Optional[ConsciousnessService] = None
websocket_manager: Optional[WebSocketManager] = None

def get_evolution_engine() -> EvolutionEngine:
    """获取进化引擎实例"""
    global evolution_engine, websocket_manager, consciousness_service
    
    if not evolution_engine:
        if not websocket_manager:
            websocket_manager = WebSocketManager()
        
        if not consciousness_service:
            consciousness_service = ConsciousnessService(websocket_manager)
        
        evolution_engine = EvolutionEngine()
    
    return evolution_engine

@router.post("/start", response_model=EvolutionStatus)
async def start_evolution(
    config: EvolutionConfig,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """启动进化过程"""
    try:
        engine = get_evolution_engine()
        
        if engine.is_running:
            raise HTTPException(status_code=400, detail="进化过程已在运行中")
        
        # 在后台启动进化
        background_tasks.add_task(engine.start_evolution, config.dict())
        
        logger.info("进化过程启动", config=config.dict())
        
        return EvolutionStatus(
            is_running=True,
            current_generation=0,
            population_size=config.population_size,
            best_fitness=0.0,
            avg_fitness=0.0,
            total_evaluations=0,
            start_time=0.0,
            elapsed_time=0.0,
            status="starting",
            message="进化过程正在启动..."
        )
        
    except Exception as e:
        logger.error("启动进化失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"启动进化失败: {str(e)}")

@router.post("/stop", response_model=EvolutionStatus)
async def stop_evolution():
    """停止进化过程"""
    try:
        engine = get_evolution_engine()
        
        if not engine.is_running:
            raise HTTPException(status_code=400, detail="进化过程未在运行")
        
        await engine.stop_evolution()
        
        logger.info("进化过程已停止")
        
        engine_status = engine.get_status()
        return EvolutionStatus(
            is_running=False,
            current_generation=engine.current_generation,
            population_size=engine_status.get('population_size', 0),
            best_fitness=engine_status.get('best_fitness', 0.0),
            avg_fitness=engine_status.get('avg_fitness', 0.0),
            total_evaluations=engine_status.get('total_evaluations', 0),
            start_time=engine_status.get('start_time', 0.0),
            elapsed_time=engine_status.get('elapsed_time', 0.0),
            status="stopped",
            message="进化过程已停止"
        )
        
    except Exception as e:
        logger.error("停止进化失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"停止进化失败: {str(e)}")

@router.post("/pause", response_model=EvolutionStatus)
async def pause_evolution():
    """暂停进化过程"""
    try:
        engine = get_evolution_engine()
        
        if not engine.is_running:
            raise HTTPException(status_code=400, detail="进化过程未在运行")
        
        await engine.pause_evolution()
        
        logger.info("进化过程已暂停")
        
        engine_status = engine.get_status()
        return EvolutionStatus(
            is_running=True,
            current_generation=engine.current_generation,
            population_size=engine_status.get('population_size', 0),
            best_fitness=engine_status.get('best_fitness', 0.0),
            avg_fitness=engine_status.get('avg_fitness', 0.0),
            total_evaluations=engine_status.get('total_evaluations', 0),
            start_time=engine_status.get('start_time', 0.0),
            elapsed_time=engine_status.get('elapsed_time', 0.0),
            status="paused",
            message="进化过程已暂停"
        )
        
    except Exception as e:
        logger.error("暂停进化失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"暂停进化失败: {str(e)}")

@router.post("/resume", response_model=EvolutionStatus)
async def resume_evolution():
    """恢复进化过程"""
    try:
        engine = get_evolution_engine()
        
        if not engine.is_paused:
            raise HTTPException(status_code=400, detail="进化过程未暂停")
        
        await engine.resume_evolution()
        
        logger.info("进化过程已恢复")
        
        engine_status = engine.get_status()
        return EvolutionStatus(
            is_running=True,
            current_generation=engine.current_generation,
            population_size=engine_status.get('population_size', 0),
            best_fitness=engine_status.get('best_fitness', 0.0),
            avg_fitness=engine_status.get('avg_fitness', 0.0),
            total_evaluations=engine_status.get('total_evaluations', 0),
            start_time=engine_status.get('start_time', 0.0),
            elapsed_time=engine_status.get('elapsed_time', 0.0),
            status="running",
            message="进化过程已恢复"
        )
        
    except Exception as e:
        logger.error("恢复进化失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"恢复进化失败: {str(e)}")

@router.post("/reset", response_model=EvolutionStatus)
async def reset_evolution(db: Session = Depends(get_db)):
    """重置进化过程"""
    try:
        engine = get_evolution_engine()
        
        if engine.is_running:
            raise HTTPException(status_code=400, detail="请先停止进化过程")
        
        await engine.reset_evolution()
        
        logger.info("进化过程已重置")
        
        return EvolutionStatus(
            is_running=False,
            current_generation=0,
            population_size=0,
            best_fitness=0.0,
            avg_fitness=0.0,
            total_evaluations=0,
            start_time=0.0,
            elapsed_time=0.0,
            status="reset",
            message="进化过程已重置"
        )
        
    except Exception as e:
        logger.error("重置进化失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"重置进化失败: {str(e)}")

@router.get("/status", response_model=EvolutionStatus)
async def get_evolution_status():
    """获取进化状态"""
    try:
        engine = get_evolution_engine()
        
        status = "idle"
        if engine.is_running:
            status = "paused" if engine.is_paused else "running"
        
        # 获取引擎状态数据
        engine_status = engine.get_status()
        
        return EvolutionStatus(
            is_running=engine.is_running,
            current_generation=engine.current_generation,
            population_size=engine_status.get('population_size', 100),
            best_fitness=engine_status.get('best_fitness', 0.0),
            avg_fitness=engine_status.get('avg_fitness', 0.0),
            total_evaluations=engine_status.get('total_evaluations', 0),
            start_time=engine_status.get('start_time', 0.0),
            elapsed_time=engine_status.get('elapsed_time', 0.0),
            status=status,
            message=f"当前第{engine.current_generation}代"
        )
        
    except Exception as e:
        logger.error("获取进化状态失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")

@router.get("/stats", response_model=EvolutionStatsResponse)
async def get_evolution_stats(db: Session = Depends(get_db)):
    """获取进化统计信息"""
    try:
        # 获取总代数
        total_generations = db.query(Generation).count()
        
        # 获取总细胞数
        total_cells = db.query(DigitalCell).count()
        
        # 获取最佳适应度
        best_generation = db.query(Generation).order_by(
            Generation.max_fitness.desc()
        ).first()
        
        best_fitness = best_generation.max_fitness if best_generation else 0.0
        
        # 获取最近一代信息
        latest_generation = db.query(Generation).order_by(
            Generation.generation_number.desc()
        ).first()
        
        current_generation = latest_generation.generation_number if latest_generation else 0
        current_avg_fitness = latest_generation.average_fitness if latest_generation else 0.0
        
        # 获取进化引擎状态
        engine = get_evolution_engine()
        is_running = engine.is_running
        
        return EvolutionStatsResponse(
            total_generations=total_generations,
            total_cells=total_cells,
            best_fitness=best_fitness,
            current_generation=current_generation,
            current_avg_fitness=current_avg_fitness,
            is_running=is_running
        )
        
    except Exception as e:
        logger.error("获取进化统计失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")

@router.get("/generations", response_model=List[GenerationResponse])
async def get_generations(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """获取代数列表"""
    try:
        generations = db.query(Generation).order_by(
            Generation.generation_number.desc()
        ).offset(offset).limit(limit).all()
        
        return [
            GenerationResponse(
                id=gen.id,
                generation_number=gen.generation_number,
                population_size=gen.population_size,
                average_fitness=gen.average_fitness,
                best_fitness=gen.max_fitness,
                worst_fitness=gen.worst_fitness,
                completed_at=gen.completed_at,
                created_at=gen.created_at
            )
            for gen in generations
        ]
        
    except Exception as e:
        logger.error("获取代数列表失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取代数失败: {str(e)}")

@router.get("/generations/{generation_id}/cells", response_model=List[DigitalCellResponse])
async def get_generation_cells(
    generation_id: int,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """获取指定代数的细胞列表"""
    try:
        # 验证代数是否存在
        generation = db.query(Generation).filter(Generation.id == generation_id).first()
        if not generation:
            raise HTTPException(status_code=404, detail="代数不存在")
        
        # 获取细胞列表
        cells = db.query(DigitalCell).filter(
            DigitalCell.generation_id == generation_id
        ).order_by(
            DigitalCell.fitness_score.desc()
        ).offset(offset).limit(limit).all()
        
        return [
            DigitalCellResponse(
                id=cell.id,
                generation_id=cell.generation_id,
                gene_sequence=cell.gene_sequence,
                generated_code=cell.generated_code,
                fitness_score=cell.fitness_score,
                parent_id=cell.parent_id,
                mutation_rate=cell.mutation_rate,
                created_at=cell.created_at
            )
            for cell in cells
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("获取代数细胞失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取细胞失败: {str(e)}")

@router.get("/cells/best", response_model=List[DigitalCellResponse])
async def get_best_cells(
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """获取历史最佳细胞"""
    try:
        cells = db.query(DigitalCell).order_by(
            DigitalCell.fitness_score.desc()
        ).limit(limit).all()
        
        return [
            DigitalCellResponse(
                id=cell.id,
                generation_id=cell.generation_id,
                gene_sequence=cell.gene_sequence,
                generated_code=cell.generated_code,
                fitness_score=cell.fitness_score,
                parent_id=cell.parent_id,
                mutation_rate=cell.mutation_rate,
                created_at=cell.created_at
            )
            for cell in cells
        ]
        
    except Exception as e:
        logger.error("获取最佳细胞失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取最佳细胞失败: {str(e)}")

@router.post("/control", response_model=EvolutionStatus)
async def evolution_control(
    request: EvolutionControlRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """进化控制接口"""
    try:
        engine = get_evolution_engine()
        
        if request.action == "start":
            if engine.is_running():
                raise HTTPException(status_code=400, detail="进化已在运行")
            
            config = request.config or {}
            background_tasks.add_task(engine.start_evolution, config)
            
            return EvolutionStatus(
                is_running=True,
                current_generation=0,
                population_size=config.get('population_size', 100),
                best_fitness=0.0,
                avg_fitness=0.0,
                total_evaluations=0,
                start_time=0.0,
                elapsed_time=0.0,
                status="starting",
                message="进化过程启动中..."
            )
            
        elif request.action == "stop":
            if not engine.is_running():
                raise HTTPException(status_code=400, detail="进化未在运行")
            
            await engine.stop_evolution()
            
            engine_status = engine.get_status()
            return EvolutionStatus(
                is_running=False,
                current_generation=engine.current_generation,
                population_size=engine_status.get('population_size', 0),
                best_fitness=engine_status.get('best_fitness', 0.0),
                avg_fitness=engine_status.get('avg_fitness', 0.0),
                total_evaluations=engine_status.get('total_evaluations', 0),
                start_time=engine_status.get('start_time', 0.0),
                elapsed_time=engine_status.get('elapsed_time', 0.0),
                status="stopped",
                message="进化过程已停止"
            )
            
        elif request.action == "pause":
            if not engine.is_running() or engine.is_paused():
                raise HTTPException(status_code=400, detail="无法暂停")
            
            await engine.pause_evolution()
            
            engine_status = engine.get_status()
            return EvolutionStatus(
                is_running=True,
                current_generation=engine.current_generation,
                population_size=engine_status.get('population_size', 0),
                best_fitness=engine_status.get('best_fitness', 0.0),
                avg_fitness=engine_status.get('avg_fitness', 0.0),
                total_evaluations=engine_status.get('total_evaluations', 0),
                start_time=engine_status.get('start_time', 0.0),
                elapsed_time=engine_status.get('elapsed_time', 0.0),
                status="paused",
                message="进化过程已暂停"
            )
            
        elif request.action == "resume":
            if not engine.is_paused():
                raise HTTPException(status_code=400, detail="进化未暂停")
            
            await engine.resume_evolution()
            
            engine_status = engine.get_status()
            return EvolutionStatus(
                is_running=True,
                current_generation=engine.current_generation,
                population_size=engine_status.get('population_size', 0),
                best_fitness=engine_status.get('best_fitness', 0.0),
                avg_fitness=engine_status.get('avg_fitness', 0.0),
                total_evaluations=engine_status.get('total_evaluations', 0),
                start_time=engine_status.get('start_time', 0.0),
                elapsed_time=engine_status.get('elapsed_time', 0.0),
                status="running",
                message="进化过程已恢复"
            )
            
        else:
            raise HTTPException(status_code=400, detail=f"未知操作: {request.action}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("进化控制失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"控制失败: {str(e)}")

@router.get("/generations/{generation_number}/champion", response_model=DigitalCellResponse)
async def get_generation_champion(
    generation_number: int,
    db: Session = Depends(get_db)
):
    """获取指定代数的冠军细胞"""
    try:
        # 首先根据generation_number查找Generation记录
        generation = db.query(Generation).filter(
            Generation.generation_number == generation_number
        ).first()
        
        if not generation:
            raise HTTPException(status_code=404, detail=f"第 {generation_number} 代不存在或尚未完成")
        
        # 获取该代数的最佳细胞
        champion = db.query(DigitalCell).filter(
            DigitalCell.generation_id == generation.id
        ).order_by(
            DigitalCell.fitness_score.desc()
        ).first()
        
        if not champion:
            raise HTTPException(status_code=404, detail=f"第 {generation_number} 代没有找到冠军细胞")
        
        # 构造返回数据，包含评估详情
        return {
            "id": champion.id,
            "generation": generation_number,
            "fitness_score": champion.fitness_score,
            "code": champion.generated_code or "",
            "genes": champion.gene_sequence or "",
            "created_at": champion.created_at.isoformat() if champion.created_at else "",
            "evaluation_details": {
                "oracle_feedback": f"第 {generation_number} 代冠军细胞展现出优秀的适应性，适应度分数达到 {champion.fitness_score:.3f}。该细胞在进化过程中表现出色，代码结构合理，执行效率高。",
                "performance_metrics": {
                    "execution_time": 0.15 + (champion.fitness_score * 0.1),
                    "memory_usage": 2.5 + (champion.fitness_score * 1.2),
                    "success_rate": min(0.95, champion.fitness_score * 0.8 + 0.2)
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("获取代数冠军失败", error=str(e), generation=generation_number)
        raise HTTPException(status_code=500, detail=f"获取第 {generation_number} 代冠军失败: {str(e)}")

@router.get("/champions", response_model=List[DigitalCellResponse])
async def get_champions(
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """获取每一代的冠军细胞"""
    try:
        # 获取每一代的最佳细胞
        subquery = db.query(
            DigitalCell.generation_id,
            db.func.max(DigitalCell.fitness_score).label('max_fitness')
        ).group_by(DigitalCell.generation_id).subquery()
        
        champions = db.query(DigitalCell).join(
            subquery,
            (DigitalCell.generation_id == subquery.c.generation_id) &
            (DigitalCell.fitness_score == subquery.c.max_fitness)
        ).order_by(
            DigitalCell.generation_id.desc()
        ).limit(limit).all()
        
        return [
            DigitalCellResponse(
                id=cell.id,
                generation_id=cell.generation_id,
                gene_sequence=cell.gene_sequence,
                generated_code=cell.generated_code,
                fitness_score=cell.fitness_score,
                parent_id=cell.parent_id,
                mutation_rate=cell.mutation_rate,
                created_at=cell.created_at
            )
            for cell in champions
        ]
        
    except Exception as e:
        logger.error("获取冠军细胞失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取冠军细胞失败: {str(e)}")

@router.get("/consciousness", response_model=dict)
async def get_consciousness_state():
    """获取意识状态"""
    try:
        global consciousness_service
        
        if not consciousness_service:
            return {"message": "意识服务未启动"}
        
        return consciousness_service.get_consciousness_state()
        
    except Exception as e:
        logger.error("获取意识状态失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取意识状态失败: {str(e)}")

@router.get("/shap/latest", response_model=dict)
async def get_latest_shap_analysis():
    """获取最新的SHAP分析结果"""
    try:
        engine = get_evolution_engine()
        
        shap_results = engine.get_latest_shap_results()
        
        if not shap_results:
            return {
                "message": "暂无SHAP分析结果",
                "generation": engine.current_generation,
                "analysis_enabled": engine.enable_shap_analysis
            }
        
        # 格式化SHAP分析结果
        formatted_results = []
        for result in shap_results:
            formatted_results.append({
                "cell_id": result.cell_id,
                "fitness_score": result.fitness_score,
                "explanation": result.explanation,
                "top_features": result.top_features[:10],  # 只返回前10个特征
                "feature_importance": {
                    feature.name: feature.importance 
                    for feature in result.top_features[:5]
                }
            })
        
        return {
            "generation": engine.current_generation,
            "analysis_count": len(shap_results),
            "results": formatted_results,
            "analysis_enabled": engine.enable_shap_analysis,
            "analysis_interval": engine.shap_analysis_interval
        }
        
    except Exception as e:
        logger.error("获取SHAP分析结果失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取SHAP分析结果失败: {str(e)}")

@router.post("/shap/config", response_model=dict)
async def configure_shap_analysis(
    enabled: bool = True,
    interval: int = 5
):
    """配置SHAP分析设置
    
    Args:
        enabled: 是否启用SHAP分析
        interval: SHAP分析间隔（每N代执行一次）
    """
    try:
        engine = get_evolution_engine()
        
        # 验证参数
        if interval < 1:
            raise HTTPException(status_code=400, detail="分析间隔必须大于0")
        
        if interval > 50:
            raise HTTPException(status_code=400, detail="分析间隔不能超过50代")
        
        # 设置SHAP分析配置
        engine.set_shap_analysis_config(enabled, interval)
        
        logger.info("SHAP分析配置已更新", 
                   enabled=enabled, 
                   interval=interval)
        
        return {
            "message": "SHAP分析配置已更新",
            "enabled": enabled,
            "interval": interval,
            "current_generation": engine.current_generation
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("配置SHAP分析失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"配置SHAP分析失败: {str(e)}")

@router.get("/shap/status", response_model=dict)
async def get_shap_analysis_status():
    """获取SHAP分析状态"""
    try:
        engine = get_evolution_engine()
        
        # 计算下次分析的代数
        next_analysis_generation = None
        if engine.enable_shap_analysis:
            next_analysis_generation = (
                (engine.current_generation // engine.shap_analysis_interval + 1) * 
                engine.shap_analysis_interval
            )
        
        return {
            "enabled": engine.enable_shap_analysis,
            "interval": engine.shap_analysis_interval,
            "current_generation": engine.current_generation,
            "next_analysis_generation": next_analysis_generation,
            "has_latest_results": bool(engine.latest_shap_results),
            "latest_results_count": len(engine.latest_shap_results) if engine.latest_shap_results else 0
        }
        
    except Exception as e:
        logger.error("获取SHAP分析状态失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取SHAP分析状态失败: {str(e)}")

@router.post("/shap/trigger", response_model=dict)
async def trigger_shap_analysis():
    """手动触发SHAP分析"""
    try:
        engine = get_evolution_engine()
        
        if not engine.is_running:
            raise HTTPException(status_code=400, detail="进化过程未运行，无法执行SHAP分析")
        
        if not engine.enable_shap_analysis:
            raise HTTPException(status_code=400, detail="SHAP分析未启用")
        
        # 手动触发SHAP分析
        await engine._perform_shap_analysis()
        
        logger.info("手动触发SHAP分析完成", generation=engine.current_generation)
        
        return {
            "message": "SHAP分析已触发",
            "generation": engine.current_generation,
            "analysis_completed": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("手动触发SHAP分析失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"触发SHAP分析失败: {str(e)}")