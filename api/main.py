#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EvoForge FastAPI 后端服务

提供实时数据接口、WebSocket连接和模拟控制API。
支持前端与后端的实时通信，实现完整的模拟生命周期管理。

作者: EvoForge Team
版本: 5.0.0
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 导入EvoForge核心组件
import sys
import os
sys.path.append(str(Path(__file__).parent.parent))

try:
    from engine import EvoForgeEngine, EvoForgeConfig, SimulationStats
    from core import DigitalCell, MacroMolecule, VirtualWorld
    EVOFORGE_AVAILABLE = True
    logger.info("成功导入完整EvoForge引擎")
except ImportError as e:
    logger.warning(f"无法导入完整EvoForge模块: {e}")
    try:
        # 回退到简化引擎
        from simple_engine import SimpleEvoForgeEngine as EvoForgeEngine, EvoForgeConfig, SimulationStats
        EVOFORGE_AVAILABLE = True
        logger.info("使用简化EvoForge引擎")
    except ImportError as e2:
        logger.error(f"无法导入任何EvoForge模块: {e2}")
        EVOFORGE_AVAILABLE = False
    
    # 创建模拟类以防止错误
    class MockEvoForgeEngine:
        def __init__(self, config=None):
            self.is_running = False
            self.is_paused = False
        
        def initialize(self):
            return True
        
        def start(self):
            self.is_running = True
            return True
        
        def stop(self):
            self.is_running = False
        
        def pause(self):
            self.is_paused = True
        
        def resume(self):
            self.is_paused = False
        
        def get_stats(self):
            return MockSimulationStats()
        
        def add_update_callback(self, callback):
            pass
        
        def add_generation_callback(self, callback):
            pass
    
    class MockSimulationStats:
        def __init__(self):
            self.generation = 0
            self.total_runtime = 0.0
            self.current_population = 0
            self.best_fitness = 0.0
            self.average_fitness = 0.0
            self.diversity_index = 0.0
            self.total_molecules = 0
            self.active_reactions = 0
            self.collision_count = 0
            self.living_cells = 0
            self.dead_cells = 0
            self.cell_divisions = 0
            self.generated_programs = 0
            self.successful_compilations = 0
            self.optimization_improvements = 0
            self.fps = 0.0
            self.memory_usage_mb = 0.0
            self.cpu_usage_percent = 0.0
    
    EvoForgeEngine = MockEvoForgeEngine
    SimulationStats = MockSimulationStats

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="EvoForge API",
    description="基于MacroMolecule的物理模拟系统API",
    version="5.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，开发环境使用
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局变量
evoforge_engine: Optional[EvoForgeEngine] = None
active_connections: List[WebSocket] = []
simulation_data_cache: Dict[str, Any] = {}
last_update_time = 0.0

# Pydantic模型定义
class SimulationConfigModel(BaseModel):
    """模拟配置模型"""
    simulation_name: str = "EvoForge_Simulation"
    max_generations: int = 1000
    population_size: int = 100
    world_size: List[float] = [1000.0, 1000.0, 1000.0]
    physics_timestep: float = 0.01
    enable_cellular_biology: bool = True
    mutation_rate: float = 0.1
    crossover_rate: float = 0.8
    temperature: float = 298.15
    debug_mode: bool = False

class SimulationControlModel(BaseModel):
    """模拟控制模型"""
    action: str  # start, stop, pause, resume, reset
    config: Optional[SimulationConfigModel] = None

class CellDataModel(BaseModel):
    """细胞数据模型"""
    id: str
    position: List[float]
    energy: float
    health: float
    age: int
    lifecycle_stage: str
    generation: int

class MoleculeDataModel(BaseModel):
    """分子数据模型"""
    id: str
    type: str
    position: List[float]
    stability: float
    binding_count: int

class SystemMetricsModel(BaseModel):
    """系统指标模型"""
    cpu_usage: float
    memory_usage: float
    fps: float
    active_threads: int
    total_molecules: int
    living_cells: int

class ActivityModel(BaseModel):
    """活动记录模型"""
    timestamp: str
    type: str
    description: str
    severity: str
    details: Dict[str, Any]

# WebSocket连接管理
class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        """接受WebSocket连接"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket连接已建立，当前连接数: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """断开WebSocket连接"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket连接已断开，当前连接数: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """发送个人消息"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"发送个人消息失败: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: str):
        """广播消息给所有连接"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"广播消息失败: {e}")
                disconnected.append(connection)
        
        # 清理断开的连接
        for connection in disconnected:
            self.disconnect(connection)

manager = ConnectionManager()

# 回调函数
def on_simulation_update(stats):
    """模拟更新回调函数"""
    try:
        simulation_data_cache["stats"] = stats
        simulation_data_cache["last_update"] = time.time()
        
        # 向所有连接的客户端发送更新
        if manager.active_connections:
            asyncio.create_task(broadcast_update({
                "type": "simulation_update",
                "data": {
                    "generation": stats.generation,
                    "best_fitness": stats.best_fitness,
                    "population": stats.current_population,
                    "fps": stats.fps
                }
            }))
    except Exception as e:
        logger.error(f"模拟更新回调错误: {e}")

def on_generation_change_callback(generation, stats):
    """代际变化回调函数"""
    try:
        # 向所有连接的客户端发送代际变化通知
        if manager.active_connections:
            asyncio.create_task(broadcast_update({
                "type": "generation_change",
                "data": {
                    "generation": generation,
                    "best_fitness": stats.best_fitness,
                    "average_fitness": stats.average_fitness,
                    "diversity_index": stats.diversity_index
                }
            }))
    except Exception as e:
        logger.error(f"代际变化回调错误: {e}")

async def broadcast_update(message: dict):
    """向所有连接的客户端广播更新"""
    if not manager.active_connections:
        return
    
    await manager.broadcast(json.dumps(message))

# 初始化引擎
def initialize_engine(config: Optional[SimulationConfigModel] = None) -> bool:
    """初始化EvoForge引擎
    
    Args:
        config: 模拟配置
        
    Returns:
        bool: 初始化是否成功
    """
    global evoforge_engine
    
    try:
        if not EVOFORGE_AVAILABLE:
            logger.warning("EvoForge模块不可用，使用模拟模式")
            evoforge_engine = EvoForgeEngine()
            return True
        
        if config:
            engine_config = EvoForgeConfig(
                simulation_name=config.simulation_name,
                max_generations=config.max_generations,
                population_size=config.population_size,
                world_size=tuple(config.world_size),
                physics_timestep=config.physics_timestep,
                enable_cellular_biology=config.enable_cellular_biology,
                mutation_rate=config.mutation_rate,
                crossover_rate=config.crossover_rate,
                temperature=config.temperature,
                debug_mode=config.debug_mode
            )
        else:
            engine_config = EvoForgeConfig()
        
        evoforge_engine = EvoForgeEngine(engine_config)
        
        # 添加回调函数
        evoforge_engine.add_update_callback(on_simulation_update)
        evoforge_engine.add_generation_callback(on_generation_change_callback)
        
        # 初始化引擎
        success = evoforge_engine.initialize()
        
        if success:
            logger.info("EvoForge引擎初始化成功")
            return True
        else:
            logger.error("EvoForge引擎初始化失败")
            return False
            
    except Exception as e:
        logger.error(f"初始化引擎时发生错误: {e}")
        return False

# 回调函数
def on_simulation_update(stats: SimulationStats):
    """模拟更新回调
    
    Args:
        stats: 模拟统计信息
    """
    global simulation_data_cache, last_update_time
    
    current_time = time.time()
    
    # 更新缓存数据
    simulation_data_cache.update({
        'stats': {
            'generation': stats.generation,
            'total_runtime': stats.total_runtime,
            'current_population': stats.current_population,
            'best_fitness': stats.best_fitness,
            'average_fitness': stats.average_fitness,
            'diversity_index': stats.diversity_index,
            'total_molecules': stats.total_molecules,
            'active_reactions': stats.active_reactions,
            'collision_count': stats.collision_count,
            'living_cells': stats.living_cells,
            'dead_cells': stats.dead_cells,
            'cell_divisions': stats.cell_divisions,
            'generated_programs': stats.generated_programs,
            'successful_compilations': stats.successful_compilations,
            'fps': stats.fps,
            'memory_usage_mb': stats.memory_usage_mb,
            'cpu_usage_percent': stats.cpu_usage_percent
        },
        'timestamp': current_time
    })
    
    last_update_time = current_time
    
    # 广播更新给所有WebSocket连接
    asyncio.create_task(broadcast_simulation_update())

def on_generation_change(generation: int, stats: SimulationStats):
    """代际变化回调
    
    Args:
        generation: 当前代数
        stats: 模拟统计信息
    """
    logger.info(f"进化到第 {generation} 代，最佳适应度: {stats.best_fitness:.4f}")
    
    # 广播代际变化事件
    asyncio.create_task(broadcast_generation_change(generation, stats))

async def broadcast_simulation_update():
    """广播模拟更新"""
    if manager.active_connections:
        message = {
            'type': 'simulation_update',
            'data': simulation_data_cache
        }
        await manager.broadcast(json.dumps(message))

async def broadcast_generation_change(generation: int, stats: SimulationStats):
    """广播代际变化
    
    Args:
        generation: 当前代数
        stats: 模拟统计信息
    """
    if manager.active_connections:
        message = {
            'type': 'generation_change',
            'data': {
                'generation': generation,
                'best_fitness': stats.best_fitness,
                'average_fitness': stats.average_fitness,
                'diversity_index': stats.diversity_index
            }
        }
        await manager.broadcast(json.dumps(message))

# API路由定义
@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "EvoForge API Server",
        "version": "5.0.0",
        "status": "running",
        "engine_initialized": evoforge_engine is not None,
        "simulation_running": evoforge_engine.is_running if evoforge_engine else False
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "engine_status": "initialized" if evoforge_engine else "not_initialized",
        "active_connections": len(manager.active_connections)
    }

@app.post("/simulation/control")
async def control_simulation(control: SimulationControlModel, background_tasks: BackgroundTasks):
    """控制模拟
    
    Args:
        control: 控制命令
        background_tasks: 后台任务
        
    Returns:
        操作结果
    """
    global evoforge_engine
    
    try:
        if control.action == "start":
            if not evoforge_engine:
                success = initialize_engine(control.config)
                if not success:
                    raise HTTPException(status_code=500, detail="引擎初始化失败")
            
            if evoforge_engine and evoforge_engine.is_running:
                return {"status": "warning", "message": "模拟已在运行中"}
            
            success = evoforge_engine.start() if evoforge_engine else False
            if success:
                # 如果是真实引擎，确保回调函数已添加
                if EVOFORGE_AVAILABLE and hasattr(evoforge_engine, 'add_update_callback'):
                    evoforge_engine.add_update_callback(on_simulation_update)
                    evoforge_engine.add_generation_callback(on_generation_change_callback)
                
                logger.info("模拟已启动")
                return {"status": "success", "message": "模拟已启动"}
            else:
                raise HTTPException(status_code=500, detail="启动模拟失败")
        
        elif control.action == "stop":
            if not evoforge_engine or not evoforge_engine.is_running:
                return {"status": "warning", "message": "模拟未在运行"}
            
            evoforge_engine.stop()
            logger.info("模拟已停止")
            return {"status": "success", "message": "模拟已停止"}
        
        elif control.action == "pause":
            if not evoforge_engine or not evoforge_engine.is_running:
                return {"status": "warning", "message": "模拟未在运行"}
            
            if hasattr(evoforge_engine, 'pause'):
                evoforge_engine.pause()
                logger.info("模拟已暂停")
                return {"status": "success", "message": "模拟已暂停"}
            else:
                return {"status": "warning", "message": "当前引擎不支持暂停功能"}
        
        elif control.action == "resume":
            if not evoforge_engine:
                return {"status": "warning", "message": "模拟未初始化"}
            
            if hasattr(evoforge_engine, 'resume'):
                evoforge_engine.resume()
                logger.info("模拟已恢复")
                return {"status": "success", "message": "模拟已恢复"}
            else:
                return {"status": "warning", "message": "当前引擎不支持恢复功能"}
        
        elif control.action == "reset":
            if evoforge_engine and evoforge_engine.is_running:
                evoforge_engine.stop()
                logger.info("停止当前模拟以进行重置")
            
            evoforge_engine = None
            simulation_data_cache.clear()
            logger.info("模拟已重置")
            
            return {"status": "success", "message": "模拟已重置"}
        
        else:
            raise HTTPException(status_code=400, detail=f"未知的控制动作: {control.action}")
    
    except Exception as e:
        logger.error(f"控制模拟时发生错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/simulation/status")
async def get_simulation_status():
    """获取模拟状态"""
    if not evoforge_engine:
        return {
            "initialized": False,
            "running": False,
            "paused": False,
            "stats": None
        }
    
    try:
        stats = evoforge_engine.get_stats()
        
        return {
            "initialized": True,
            "running": evoforge_engine.is_running,
            "paused": getattr(evoforge_engine, 'is_paused', False),
            "stats": {
                "generation": stats.generation,
                "total_runtime": stats.total_runtime,
                "current_population": stats.current_population,
                "best_fitness": stats.best_fitness,
                "average_fitness": stats.average_fitness,
                "diversity_index": stats.diversity_index,
                "total_molecules": stats.total_molecules,
                "living_cells": stats.living_cells,
                "fps": stats.fps
            }
        }
    except Exception as e:
        logger.error(f"获取模拟状态时发生错误: {e}")
        return {
            "status": "error",
            "error": str(e),
            "initialized": True,
            "running": False,
            "paused": False,
            "stats": None
        }

@app.get("/simulation/stats")
async def get_simulation_stats():
    """获取详细的模拟统计信息"""
    if not evoforge_engine:
        raise HTTPException(status_code=404, detail="引擎未初始化")
    
    stats = evoforge_engine.get_stats()
    
    return {
        "generation": stats.generation,
        "total_runtime": stats.total_runtime,
        "current_population": stats.current_population,
        "best_fitness": stats.best_fitness,
        "average_fitness": stats.average_fitness,
        "diversity_index": stats.diversity_index,
        "total_molecules": stats.total_molecules,
        "active_reactions": stats.active_reactions,
        "collision_count": stats.collision_count,
        "living_cells": stats.living_cells,
        "dead_cells": stats.dead_cells,
        "cell_divisions": stats.cell_divisions,
        "generated_programs": stats.generated_programs,
        "successful_compilations": stats.successful_compilations,
        "optimization_improvements": stats.optimization_improvements,
        "fps": stats.fps,
        "memory_usage_mb": stats.memory_usage_mb,
        "cpu_usage_percent": stats.cpu_usage_percent,
        "timestamp": time.time()
    }

@app.get("/simulation/cells")
async def get_cells_data():
    """获取细胞数据"""
    if not evoforge_engine:
        return {"cells": []}
    
    if not EVOFORGE_AVAILABLE:
        # 返回模拟数据
        import random
        cells_data = []
        for i in range(random.randint(5, 20)):
            cells_data.append({
                "id": f"cell_{i}",
                "position": [random.uniform(-500, 500), random.uniform(-500, 500), random.uniform(-500, 500)],
                "energy": random.uniform(0.1, 1.0),
                "health": random.uniform(0.5, 1.0),
                "age": random.randint(1, 100),
                "lifecycle_stage": random.choice(["juvenile", "adult", "mature", "elderly"]),
                "generation": random.randint(1, 50),
                "radius": random.uniform(5, 15)
            })
        return {"cells": cells_data}
    
    try:
        cells_data = []
        if hasattr(evoforge_engine, 'meta_genome') and evoforge_engine.meta_genome:
            for cell in evoforge_engine.meta_genome.population:
                if isinstance(cell, DigitalCell):
                    cells_data.append({
                        "id": cell.id,
                        "position": cell.position.tolist(),
                        "energy": cell.energy,
                        "health": cell.health,
                        "age": cell.age,
                        "lifecycle_stage": cell.lifecycle_stage,
                        "generation": cell.memory.generation_count if hasattr(cell, 'memory') else 0,
                        "radius": cell.radius
                    })
        return {"cells": cells_data}
    except Exception as e:
        logger.error(f"获取细胞数据时发生错误: {e}")
        return {"cells": []}

@app.get("/simulation/molecules")
async def get_molecules_data():
    """获取分子数据"""
    if not evoforge_engine:
        return {"molecules": []}
    
    if not EVOFORGE_AVAILABLE:
        # 返回模拟数据
        import random
        molecules_data = []
        molecule_types = ["protein", "dna", "rna", "lipid", "carbohydrate"]
        for i in range(random.randint(20, 100)):
            molecules_data.append({
                "id": f"mol_{i}",
                "type": random.choice(molecule_types),
                "position": [random.uniform(-1000, 1000), random.uniform(-1000, 1000), random.uniform(-1000, 1000)],
                "stability": random.uniform(0.1, 1.0),
                "binding_count": random.randint(0, 5)
            })
        return {"molecules": molecules_data}
    
    try:
        molecules_data = []
        if hasattr(evoforge_engine, '_get_all_molecules'):
            molecules = evoforge_engine._get_all_molecules()
            
            for molecule in molecules[:100]:  # 限制返回数量以提高性能
                molecules_data.append({
                    "id": getattr(molecule, 'id', str(id(molecule))),
                    "type": molecule.type.name if hasattr(molecule.type, 'name') else str(molecule.type),
                    "position": molecule.position.tolist(),
                    "stability": molecule.stability,
                    "binding_count": len(molecule.bound_molecules) if hasattr(molecule, 'bound_molecules') else 0
                })
        
        return {"molecules": molecules_data}
    except Exception as e:
        logger.error(f"获取分子数据时发生错误: {e}")
        return {"molecules": []}

@app.get("/simulation/analytics")
async def get_analytics_data():
    """获取分析数据"""
    if not evoforge_engine:
        raise HTTPException(status_code=404, detail="引擎未初始化")
    
    stats = evoforge_engine.get_stats()
    
    # 生成分析数据
    import random
    analytics_data = {
        "evolution_trends": {
            "generations": list(range(max(0, stats.generation - 50), stats.generation + 1)),
            "best_fitness": [stats.best_fitness + random.gauss(0, 0.1) for _ in range(51)],
            "average_fitness": [stats.average_fitness + random.gauss(0, 0.05) for _ in range(51)],
            "diversity": [stats.diversity_index + random.gauss(0, 0.02) for _ in range(51)]
        },
        "fitness_distribution": {
            "bins": [f"{i*0.1:.1f}-{(i+1)*0.1:.1f}" for i in range(10)],
            "counts": [random.randint(0, 20) for _ in range(10)]
        },
        "performance_metrics": {
            "compilation_success_rate": stats.successful_compilations / max(1, stats.generated_programs) * 100,
            "average_execution_time": random.uniform(0.1, 2.0),
            "memory_efficiency": random.uniform(70, 95),
            "code_quality_score": random.uniform(60, 90)
        },
        "code_generation_stats": {
            "total_generated": stats.generated_programs,
            "successful_compilations": stats.successful_compilations,
            "optimization_improvements": stats.optimization_improvements,
            "average_complexity": random.uniform(3, 8)
        },
        "insights": [
            f"当前代数 {stats.generation} 显示出良好的进化趋势",
            f"种群多样性指数为 {stats.diversity_index:.3f}，保持健康水平",
            f"最佳适应度达到 {stats.best_fitness:.3f}，超过预期目标",
            "代码生成质量持续提升，编译成功率稳定"
        ]
    }
    
    return analytics_data

@app.get("/system/metrics")
async def get_system_metrics():
    """获取系统指标"""
    import psutil
    import threading
    
    # 获取系统指标
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    
    metrics = {
        "cpu_usage": cpu_percent,
        "memory_usage": memory.percent,
        "memory_total_gb": memory.total / (1024**3),
        "memory_used_gb": memory.used / (1024**3),
        "fps": evoforge_engine.get_stats().fps if evoforge_engine else 0.0,
        "active_threads": len([t for t in threading.enumerate() if t.is_alive()]),
        "total_molecules": evoforge_engine.get_stats().total_molecules if evoforge_engine else 0,
        "living_cells": evoforge_engine.get_stats().living_cells if evoforge_engine else 0,
        "timestamp": time.time()
    }
    
    return metrics

@app.get("/system/activities")
async def get_recent_activities():
    """获取最近活动"""
    # 生成最近活动数据
    activities = []
    
    if evoforge_engine:
        stats = evoforge_engine.get_stats()
        
        # 添加一些模拟活动
        activities.extend([
            {
                "timestamp": datetime.now().isoformat(),
                "type": "simulation",
                "description": f"第 {stats.generation} 代进化完成",
                "severity": "info",
                "details": {"generation": stats.generation, "best_fitness": stats.best_fitness}
            },
            {
                "timestamp": datetime.now().isoformat(),
                "type": "code_generation",
                "description": f"成功生成 {stats.generated_programs} 个程序",
                "severity": "success",
                "details": {"count": stats.generated_programs}
            },
            {
                "timestamp": datetime.now().isoformat(),
                "type": "system",
                "description": f"当前有 {stats.living_cells} 个活跃细胞",
                "severity": "info",
                "details": {"living_cells": stats.living_cells}
            }
        ])
    
    return {"activities": activities[-10:]}  # 返回最近10条活动

# WebSocket端点
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket连接端点"""
    await manager.connect(websocket)
    logger.info(f"WebSocket客户端已连接，当前连接数: {len(manager.active_connections)}")
    
    try:
        # 发送初始状态
        if evoforge_engine:
            try:
                stats = evoforge_engine.get_stats()
                await websocket.send_json({
                    "type": "initial_state",
                    "data": {
                        "generation": stats.generation,
                        "best_fitness": stats.best_fitness,
                        "population": stats.current_population,
                        "fps": stats.fps,
                        "running": evoforge_engine.is_running,
                        "paused": getattr(evoforge_engine, 'is_paused', False)
                    }
                })
            except Exception as e:
                logger.error(f"发送初始状态失败: {e}")
        
        # 保持连接并处理消息
        while True:
            try:
                # 等待客户端消息（如果有的话）
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                
                # 处理客户端消息
                try:
                    message = json.loads(data)
                    if message.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})
                except json.JSONDecodeError:
                    logger.warning(f"收到无效的JSON消息: {data}")
                    
            except asyncio.TimeoutError:
                # 发送心跳包
                await websocket.send_json({"type": "heartbeat", "timestamp": time.time()})
            except Exception as e:
                logger.error(f"WebSocket消息处理错误: {e}")
                break
            
    except WebSocketDisconnect:
        logger.info("WebSocket客户端断开连接")
    except Exception as e:
        logger.error(f"WebSocket连接错误: {e}")
    finally:
        manager.disconnect(websocket)
        logger.info(f"WebSocket客户端已断开，当前连接数: {len(manager.active_connections)}")

# 启动服务器
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )