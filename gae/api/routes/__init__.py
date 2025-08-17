# -*- coding: utf-8 -*-
"""
API路由模块

包含所有API端点的路由定义：
- 进化控制路由
- 任务管理路由
- 实验管理路由
- 评估路由
- 系统信息路由
- WebSocket路由
"""

from fastapi import APIRouter
from .evolution import router as evolution_router
from .tasks import router as tasks_router
from .experiments import router as experiments_router
from .evaluations import router as evaluations_router
from .system import router as system_router
from .websocket import router as websocket_router

# 创建主路由器
api_router = APIRouter(prefix="/api/v1")

# 注册子路由
api_router.include_router(
    evolution_router,
    prefix="/evolution",
    tags=["evolution"]
)

api_router.include_router(
    tasks_router,
    prefix="/tasks",
    tags=["tasks"]
)

api_router.include_router(
    experiments_router,
    prefix="/experiments",
    tags=["experiments"]
)

api_router.include_router(
    evaluations_router,
    prefix="/evaluations",
    tags=["evaluations"]
)

api_router.include_router(
    system_router,
    prefix="/system",
    tags=["system"]
)

# WebSocket路由不使用前缀
websocket_router_main = APIRouter()
websocket_router_main.include_router(
    websocket_router,
    prefix="/ws",
    tags=["websocket"]
)

__all__ = [
    "api_router",
    "websocket_router_main",
    "evolution_router",
    "tasks_router",
    "experiments_router",
    "evaluations_router",
    "system_router",
    "websocket_router"
]