#!/usr/bin/env python3
"""
喀迈拉计划 - 进化主系统
主应用入口文件
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import structlog

# 导入配置和核心模块
from app.core.config import settings
from app.core.database import engine, create_tables
from app.core.websocket import websocket_manager

# 配置结构化日志
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("启动喀迈拉计划进化主系统")
    
    # 创建数据库表
    await create_tables()
    
    yield
    
    logger.info("关闭喀迈拉计划进化主系统")

# 创建FastAPI应用
app = FastAPI(
    title="喀迈拉计划 - 进化主系统",
    description="Project Chimera - Evolution Mainframe API",
    version="2.0.0",
    lifespan=lifespan
)

# 添加中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 包含API路由
from app.api import evolution, tasks, evaluation, system, code_generation, simulation

app.include_router(evolution.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")
app.include_router(evaluation.router, prefix="/api/v1")
app.include_router(system.router, prefix="/api/v1")
app.include_router(simulation.router, prefix="/api/v1")
app.include_router(code_generation.router, prefix="/api/v1/code-generation", tags=["code-generation"])

@app.get("/")
async def root():
    """根路径健康检查"""
    return {
        "message": "喀迈拉计划进化主系统运行中",
        "version": "2.0.0",
        "status": "operational"
    }

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "service": "chimera-mainframe",
        "version": "2.0.0"
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket连接端点"""
    import json
    client_id = f"client_{id(websocket)}"
    await websocket_manager.connect(websocket, client_id)
    
    try:
        while True:
            # 接收并处理消息
            data = await websocket.receive_text()
            logger.debug("收到WebSocket消息", client_id=client_id, data=data)
            
            try:
                # 解析JSON消息
                message = json.loads(data)
                message_type = message.get('type', '')
                message_data = message.get('data', {})
                
                # 处理不同类型的消息
                if message_type == 'join_room':
                    room = message_data.get('room', '')
                    if room:
                        await websocket_manager.join_room(client_id, room)
                        # 发送确认消息
                        await websocket_manager.send_to_client(client_id, {
                            'type': 'room_joined',
                            'data': {'room': room},
                            'timestamp': message.get('timestamp', '')
                        })
                        
                elif message_type == 'leave_room':
                    room = message_data.get('room', '')
                    if room:
                        await websocket_manager.leave_room(client_id, room)
                        # 发送确认消息
                        await websocket_manager.send_to_client(client_id, {
                            'type': 'room_left',
                            'data': {'room': room},
                            'timestamp': message.get('timestamp', '')
                        })
                        
                elif message_type == 'ping':
                    # 心跳检测
                    await websocket_manager.send_to_client(client_id, {
                        'type': 'pong',
                        'data': {},
                        'timestamp': message.get('timestamp', '')
                    })
                    
                else:
                    logger.debug("未处理的消息类型", client_id=client_id, message_type=message_type)
                    
            except json.JSONDecodeError:
                logger.warning("收到无效的JSON消息", client_id=client_id, data=data)
            except Exception as e:
                logger.error("处理WebSocket消息失败", client_id=client_id, error=str(e))
            
    except WebSocketDisconnect:
        await websocket_manager.disconnect(client_id)
        logger.info("WebSocket连接断开", client_id=client_id)
    except Exception as e:
        logger.error("WebSocket连接异常", client_id=client_id, error=str(e))
        await websocket_manager.disconnect(client_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="debug"
    )