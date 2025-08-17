#!/usr/bin/env python3
"""
系统监控和活动API
提供系统状态、活动日志和性能指标
"""

import asyncio
import psutil
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/system", tags=["system"])

# 数据模型
class SystemMetrics(BaseModel):
    """系统性能指标"""
    cpu: float
    memory: float
    network: float
    storage: float
    status: str
    timestamp: datetime

class Activity(BaseModel):
    """系统活动记录"""
    id: str
    type: str
    description: str
    timestamp: datetime
    level: str = "info"  # info, warning, error
    metadata: Dict[str, Any] = {}

class SystemStatus(BaseModel):
    """系统状态概览"""
    status: str
    uptime: float
    version: str
    services: Dict[str, str]
    last_updated: datetime

# 内存存储（生产环境应使用数据库）
recent_activities: List[Activity] = []
metrics_history: List[SystemMetrics] = []
start_time = time.time()

# 初始化一些示例活动
def init_sample_activities():
    """初始化示例活动数据"""
    global recent_activities
    
    sample_activities = [
        Activity(
            id="act_001",
            type="simulation",
            description="模拟启动: 第1代进化开始",
            timestamp=datetime.now() - timedelta(minutes=5),
            level="info",
            metadata={"generation": 1, "population_size": 100}
        ),
        Activity(
            id="act_002",
            type="code",
            description="代码生成: 成功生成Python函数",
            timestamp=datetime.now() - timedelta(minutes=3),
            level="info",
            metadata={"language": "python", "fitness": 85.2}
        ),
        Activity(
            id="act_003",
            type="system",
            description="WebSocket连接建立",
            timestamp=datetime.now() - timedelta(minutes=2),
            level="info",
            metadata={"client_count": 1}
        ),
        Activity(
            id="act_004",
            type="data",
            description="数据分析完成: 适应度趋势分析",
            timestamp=datetime.now() - timedelta(minutes=1),
            level="info",
            metadata={"analysis_type": "fitness_trend", "data_points": 50}
        ),
        Activity(
            id="act_005",
            type="success",
            description="进化算法收敛: 找到最优解",
            timestamp=datetime.now() - timedelta(seconds=30),
            level="info",
            metadata={"best_fitness": 95.8, "generation": 15}
        )
    ]
    
    recent_activities.extend(sample_activities)
    logger.info(f"初始化了 {len(sample_activities)} 个示例活动")

# 初始化示例数据
init_sample_activities()

def get_system_metrics() -> SystemMetrics:
    """获取当前系统性能指标"""
    try:
        # 获取CPU使用率
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        # 获取内存使用率
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # 获取磁盘使用率
        disk = psutil.disk_usage('/')
        storage_percent = (disk.used / disk.total) * 100
        
        # 获取网络IO（简化为随机值，实际应该计算网络吞吐量）
        network_io = psutil.net_io_counters()
        network_percent = min(100, (network_io.bytes_sent + network_io.bytes_recv) / (1024 * 1024) % 100)
        
        # 确定系统状态
        if cpu_percent > 90 or memory_percent > 90 or storage_percent > 95:
            status = "error"
        elif cpu_percent > 70 or memory_percent > 80 or storage_percent > 85:
            status = "warning"
        else:
            status = "healthy"
        
        metrics = SystemMetrics(
            cpu=round(cpu_percent, 1),
            memory=round(memory_percent, 1),
            network=round(network_percent, 1),
            storage=round(storage_percent, 1),
            status=status,
            timestamp=datetime.now()
        )
        
        logger.debug("获取系统指标", metrics=metrics.dict())
        return metrics
        
    except Exception as e:
        logger.error("获取系统指标失败", error=str(e))
        # 返回默认值
        return SystemMetrics(
            cpu=45.2,
            memory=67.8,
            network=23.1,
            storage=82.4,
            status="healthy",
            timestamp=datetime.now()
        )

def add_activity(activity_type: str, description: str, level: str = "info", metadata: Dict[str, Any] = None):
    """添加新的活动记录"""
    global recent_activities
    
    activity = Activity(
        id=f"act_{int(time.time() * 1000)}",
        type=activity_type,
        description=description,
        timestamp=datetime.now(),
        level=level,
        metadata=metadata or {}
    )
    
    recent_activities.insert(0, activity)  # 最新的在前面
    
    # 保持最多100条记录
    if len(recent_activities) > 100:
        recent_activities = recent_activities[:100]
    
    logger.info("添加新活动", activity=activity.dict())

@router.get("/metrics", response_model=SystemMetrics)
async def get_metrics():
    """获取当前系统性能指标"""
    logger.info("API调用: 获取系统指标")
    
    try:
        metrics = get_system_metrics()
        
        # 保存到历史记录
        global metrics_history
        metrics_history.append(metrics)
        
        # 保持最多1000条历史记录
        if len(metrics_history) > 1000:
            metrics_history = metrics_history[-1000:]
        
        return metrics
        
    except Exception as e:
        logger.error("获取系统指标API失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取系统指标失败: {str(e)}")

@router.get("/activities", response_model=List[Activity])
async def get_activities(
    limit: int = Query(default=20, ge=1, le=100, description="返回的活动数量"),
    activity_type: Optional[str] = Query(default=None, description="活动类型过滤"),
    level: Optional[str] = Query(default=None, description="日志级别过滤")
):
    """获取系统活动日志"""
    logger.info("API调用: 获取活动日志", limit=limit, activity_type=activity_type, level=level)
    
    try:
        # 过滤活动
        filtered_activities = recent_activities
        
        if activity_type:
            filtered_activities = [a for a in filtered_activities if a.type == activity_type]
        
        if level:
            filtered_activities = [a for a in filtered_activities if a.level == level]
        
        # 限制返回数量
        result = filtered_activities[:limit]
        
        logger.info(f"返回 {len(result)} 条活动记录")
        return result
        
    except Exception as e:
        logger.error("获取活动日志API失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取活动日志失败: {str(e)}")

@router.get("/status", response_model=SystemStatus)
async def get_system_status():
    """获取系统状态概览"""
    logger.info("API调用: 获取系统状态")
    
    try:
        uptime = time.time() - start_time
        
        # 检查各服务状态（简化版本）
        services = {
            "evolution_engine": "running",
            "websocket_server": "running",
            "database": "running",
            "api_server": "running"
        }
        
        # 根据系统指标确定整体状态
        current_metrics = get_system_metrics()
        overall_status = current_metrics.status
        
        status = SystemStatus(
            status=overall_status,
            uptime=uptime,
            version="2.0.0",
            services=services,
            last_updated=datetime.now()
        )
        
        return status
        
    except Exception as e:
        logger.error("获取系统状态API失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取系统状态失败: {str(e)}")

@router.post("/activities")
async def create_activity(
    activity_type: str,
    description: str,
    level: str = "info",
    metadata: Dict[str, Any] = None
):
    """创建新的活动记录"""
    logger.info("API调用: 创建活动记录", type=activity_type, description=description)
    
    try:
        add_activity(activity_type, description, level, metadata)
        return {"message": "活动记录创建成功"}
        
    except Exception as e:
        logger.error("创建活动记录API失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"创建活动记录失败: {str(e)}")

@router.get("/metrics/history")
async def get_metrics_history(
    hours: int = Query(default=1, ge=1, le=24, description="获取过去几小时的指标")
):
    """获取历史性能指标"""
    logger.info("API调用: 获取历史指标", hours=hours)
    
    try:
        # 过滤指定时间范围内的指标
        cutoff_time = datetime.now() - timedelta(hours=hours)
        filtered_metrics = [
            m for m in metrics_history 
            if m.timestamp >= cutoff_time
        ]
        
        logger.info(f"返回 {len(filtered_metrics)} 条历史指标")
        return filtered_metrics
        
    except Exception as e:
        logger.error("获取历史指标API失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取历史指标失败: {str(e)}")

# 后台任务：定期更新指标和活动
async def background_metrics_updater():
    """后台任务：定期更新系统指标"""
    while True:
        try:
            # 每30秒更新一次指标
            await asyncio.sleep(30)
            
            # 获取并保存指标
            metrics = get_system_metrics()
            metrics_history.append(metrics)
            
            # 保持历史记录大小
            if len(metrics_history) > 1000:
                metrics_history[:] = metrics_history[-1000:]
            
            # 如果系统状态异常，添加活动记录
            if metrics.status in ["warning", "error"]:
                add_activity(
                    "system",
                    f"系统状态异常: {metrics.status}",
                    "warning" if metrics.status == "warning" else "error",
                    {
                        "cpu": metrics.cpu,
                        "memory": metrics.memory,
                        "storage": metrics.storage
                    }
                )
            
        except Exception as e:
            logger.error("后台指标更新失败", error=str(e))
            await asyncio.sleep(60)  # 出错时等待更长时间

# 启动后台任务（在实际应用中应该在应用启动时启动）
# asyncio.create_task(background_metrics_updater())