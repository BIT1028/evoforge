#!/usr/bin/env python3
"""
模拟控制API
提供模拟状态、统计数据和控制功能
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/simulation", tags=["simulation"])

# 数据模型
class SimulationStatus(BaseModel):
    """模拟状态"""
    is_running: bool
    current_generation: int
    total_generations: int
    population_size: int
    start_time: Optional[datetime]
    elapsed_time: float
    status: str  # "idle", "running", "paused", "completed", "error"
    last_updated: datetime

class SimulationStats(BaseModel):
    """模拟统计数据"""
    generation: int
    best_fitness: float
    average_fitness: float
    worst_fitness: float
    diversity_score: float
    convergence_rate: float
    mutation_rate: float
    crossover_rate: float
    timestamp: datetime

class CellData(BaseModel):
    """细胞数据"""
    id: str
    generation: int
    fitness: float
    code: str
    parent_ids: List[str]
    mutation_count: int
    created_at: datetime
    is_champion: bool = False

class MoleculeData(BaseModel):
    """分子数据"""
    id: str
    type: str
    properties: Dict[str, Any]
    concentration: float
    stability: float
    interactions: List[str]
    timestamp: datetime

class AnalyticsData(BaseModel):
    """分析数据"""
    metric_name: str
    value: float
    trend: str  # "increasing", "decreasing", "stable"
    confidence: float
    timestamp: datetime
    metadata: Dict[str, Any] = {}

# 全局状态存储
current_simulation_status = SimulationStatus(
    is_running=False,
    current_generation=0,
    total_generations=100,
    population_size=50,
    start_time=None,
    elapsed_time=0.0,
    status="idle",
    last_updated=datetime.now()
)

# 模拟统计历史
stats_history: List[SimulationStats] = []
cells_data: List[CellData] = []
molecules_data: List[MoleculeData] = []
analytics_data: List[AnalyticsData] = []

# 初始化示例数据
def init_sample_data():
    """初始化示例数据"""
    global stats_history, cells_data, molecules_data, analytics_data
    
    # 示例统计数据
    for i in range(10):
        stats = SimulationStats(
            generation=i,
            best_fitness=85.0 + i * 1.5,
            average_fitness=60.0 + i * 0.8,
            worst_fitness=30.0 + i * 0.3,
            diversity_score=0.8 - i * 0.02,
            convergence_rate=0.1 + i * 0.01,
            mutation_rate=0.05,
            crossover_rate=0.8,
            timestamp=datetime.now() - timedelta(minutes=10-i)
        )
        stats_history.append(stats)
    
    # 示例细胞数据
    for i in range(5):
        cell = CellData(
            id=f"cell_{i:03d}",
            generation=i // 2,
            fitness=85.0 + i * 2.0,
            code=f"def solution_{i}():\n    return {i} * 2 + 1",
            parent_ids=[f"cell_{max(0, i-1):03d}"] if i > 0 else [],
            mutation_count=i,
            created_at=datetime.now() - timedelta(minutes=5-i),
            is_champion=(i == 4)
        )
        cells_data.append(cell)
    
    # 示例分子数据
    for i in range(3):
        molecule = MoleculeData(
            id=f"mol_{i:03d}",
            type=f"protein_{i}",
            properties={"size": 100 + i * 10, "charge": i - 1},
            concentration=0.5 + i * 0.1,
            stability=0.8 + i * 0.05,
            interactions=[f"mol_{j:03d}" for j in range(i)],
            timestamp=datetime.now() - timedelta(minutes=3-i)
        )
        molecules_data.append(molecule)
    
    # 示例分析数据
    metrics = ["fitness_trend", "diversity_index", "convergence_speed"]
    for i, metric in enumerate(metrics):
        analytics = AnalyticsData(
            metric_name=metric,
            value=0.7 + i * 0.1,
            trend="increasing" if i % 2 == 0 else "stable",
            confidence=0.85 + i * 0.05,
            timestamp=datetime.now() - timedelta(minutes=2-i),
            metadata={"calculation_method": "statistical", "sample_size": 100}
        )
        analytics_data.append(analytics)
    
    logger.info("初始化模拟示例数据完成")

# 初始化数据
init_sample_data()

@router.get("/status", response_model=SimulationStatus)
async def get_simulation_status():
    """获取模拟状态"""
    logger.info("API调用: 获取模拟状态")
    
    try:
        # 更新运行时间
        if current_simulation_status.is_running and current_simulation_status.start_time:
            current_simulation_status.elapsed_time = (
                datetime.now() - current_simulation_status.start_time
            ).total_seconds()
        
        current_simulation_status.last_updated = datetime.now()
        return current_simulation_status
        
    except Exception as e:
        logger.error("获取模拟状态失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取模拟状态失败: {str(e)}")

@router.get("/stats", response_model=List[SimulationStats])
async def get_simulation_stats(
    limit: int = Query(default=20, ge=1, le=100, description="返回的统计数据数量"),
    generation: Optional[int] = Query(default=None, description="特定代数过滤")
):
    """获取模拟统计数据"""
    logger.info("API调用: 获取模拟统计", limit=limit, generation=generation)
    
    try:
        filtered_stats = stats_history
        
        if generation is not None:
            filtered_stats = [s for s in stats_history if s.generation == generation]
        
        # 按时间倒序排列，返回最新的数据
        result = sorted(filtered_stats, key=lambda x: x.timestamp, reverse=True)[:limit]
        
        logger.info(f"返回 {len(result)} 条统计数据")
        return result
        
    except Exception as e:
        logger.error("获取模拟统计失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取模拟统计失败: {str(e)}")

@router.get("/cells", response_model=List[CellData])
async def get_simulation_cells(
    limit: int = Query(default=20, ge=1, le=100, description="返回的细胞数量"),
    generation: Optional[int] = Query(default=None, description="特定代数过滤"),
    champion_only: bool = Query(default=False, description="只返回冠军细胞")
):
    """获取模拟细胞数据"""
    logger.info("API调用: 获取细胞数据", limit=limit, generation=generation, champion_only=champion_only)
    
    try:
        filtered_cells = cells_data
        
        if generation is not None:
            filtered_cells = [c for c in cells_data if c.generation == generation]
        
        if champion_only:
            filtered_cells = [c for c in filtered_cells if c.is_champion]
        
        # 按适应度倒序排列
        result = sorted(filtered_cells, key=lambda x: x.fitness, reverse=True)[:limit]
        
        logger.info(f"返回 {len(result)} 条细胞数据")
        return result
        
    except Exception as e:
        logger.error("获取细胞数据失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取细胞数据失败: {str(e)}")

@router.get("/molecules", response_model=List[MoleculeData])
async def get_simulation_molecules(
    limit: int = Query(default=20, ge=1, le=100, description="返回的分子数量"),
    molecule_type: Optional[str] = Query(default=None, description="分子类型过滤")
):
    """获取模拟分子数据"""
    logger.info("API调用: 获取分子数据", limit=limit, molecule_type=molecule_type)
    
    try:
        filtered_molecules = molecules_data
        
        if molecule_type:
            filtered_molecules = [m for m in molecules_data if m.type == molecule_type]
        
        # 按时间倒序排列
        result = sorted(filtered_molecules, key=lambda x: x.timestamp, reverse=True)[:limit]
        
        logger.info(f"返回 {len(result)} 条分子数据")
        return result
        
    except Exception as e:
        logger.error("获取分子数据失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取分子数据失败: {str(e)}")

@router.get("/analytics", response_model=List[AnalyticsData])
async def get_simulation_analytics(
    limit: int = Query(default=20, ge=1, le=100, description="返回的分析数据数量"),
    metric_name: Optional[str] = Query(default=None, description="指标名称过滤")
):
    """获取模拟分析数据"""
    logger.info("API调用: 获取分析数据", limit=limit, metric_name=metric_name)
    
    try:
        filtered_analytics = analytics_data
        
        if metric_name:
            filtered_analytics = [a for a in analytics_data if a.metric_name == metric_name]
        
        # 按时间倒序排列
        result = sorted(filtered_analytics, key=lambda x: x.timestamp, reverse=True)[:limit]
        
        logger.info(f"返回 {len(result)} 条分析数据")
        return result
        
    except Exception as e:
        logger.error("获取分析数据失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取分析数据失败: {str(e)}")

@router.post("/start")
async def start_simulation(
    generations: int = Query(default=100, ge=1, le=1000, description="进化代数"),
    population_size: int = Query(default=50, ge=10, le=500, description="种群大小")
):
    """启动模拟"""
    logger.info("API调用: 启动模拟", generations=generations, population_size=population_size)
    
    try:
        global current_simulation_status
        
        if current_simulation_status.is_running:
            raise HTTPException(status_code=400, detail="模拟已在运行中")
        
        # 更新状态
        current_simulation_status.is_running = True
        current_simulation_status.current_generation = 0
        current_simulation_status.total_generations = generations
        current_simulation_status.population_size = population_size
        current_simulation_status.start_time = datetime.now()
        current_simulation_status.elapsed_time = 0.0
        current_simulation_status.status = "running"
        current_simulation_status.last_updated = datetime.now()
        
        logger.info("模拟启动成功")
        return {"message": "模拟启动成功", "status": current_simulation_status.dict()}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("启动模拟失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"启动模拟失败: {str(e)}")

@router.post("/pause")
async def pause_simulation():
    """暂停模拟"""
    logger.info("API调用: 暂停模拟")
    
    try:
        global current_simulation_status
        
        if not current_simulation_status.is_running:
            raise HTTPException(status_code=400, detail="模拟未在运行中")
        
        current_simulation_status.status = "paused"
        current_simulation_status.last_updated = datetime.now()
        
        logger.info("模拟暂停成功")
        return {"message": "模拟暂停成功", "status": current_simulation_status.dict()}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("暂停模拟失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"暂停模拟失败: {str(e)}")

@router.post("/stop")
async def stop_simulation():
    """停止模拟"""
    logger.info("API调用: 停止模拟")
    
    try:
        global current_simulation_status
        
        current_simulation_status.is_running = False
        current_simulation_status.status = "idle"
        current_simulation_status.start_time = None
        current_simulation_status.elapsed_time = 0.0
        current_simulation_status.last_updated = datetime.now()
        
        logger.info("模拟停止成功")
        return {"message": "模拟停止成功", "status": current_simulation_status.dict()}
        
    except Exception as e:
        logger.error("停止模拟失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"停止模拟失败: {str(e)}")

@router.post("/reset")
async def reset_simulation():
    """重置模拟"""
    logger.info("API调用: 重置模拟")
    
    try:
        global current_simulation_status, stats_history, cells_data, molecules_data, analytics_data
        
        # 重置状态
        current_simulation_status.is_running = False
        current_simulation_status.current_generation = 0
        current_simulation_status.status = "idle"
        current_simulation_status.start_time = None
        current_simulation_status.elapsed_time = 0.0
        current_simulation_status.last_updated = datetime.now()
        
        # 清空历史数据
        stats_history.clear()
        cells_data.clear()
        molecules_data.clear()
        analytics_data.clear()
        
        # 重新初始化示例数据
        init_sample_data()
        
        logger.info("模拟重置成功")
        return {"message": "模拟重置成功", "status": current_simulation_status.dict()}
        
    except Exception as e:
        logger.error("重置模拟失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"重置模拟失败: {str(e)}")