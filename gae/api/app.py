# -*- coding: utf-8 -*-
"""
FastAPI应用主文件

实现FastAPI应用的创建和配置：
- 应用工厂模式
- 中间件配置
- 路由注册
- 异常处理
- CORS配置
- API文档配置
"""

import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

from ..config.config_manager import ConfigManager
from ..database.database_manager import DatabaseManager
from ..core.logging_system import LoggingSystem
from ..core.error_handler import ErrorHandler, EvoForgeError

from .routes import (
    evolution_router,
    task_router,
    evaluation_router,
    system_router,
    experiment_router
)
from .websocket import websocket_router
from .middleware import setup_middleware
from .models.responses import ErrorResponse

logger = logging.getLogger(__name__)

# 全局应用状态
app_state: Dict[str, Any] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("启动EvoForge API服务")
    
    try:
        # 初始化配置管理器
        config_manager = ConfigManager()
        await config_manager.initialize()
        app_state['config_manager'] = config_manager
        
        # 初始化数据库管理器
        db_manager = DatabaseManager(config_manager)
        await db_manager.initialize()
        app_state['db_manager'] = db_manager
        
        # 初始化日志系统
        logging_system = LoggingSystem(config_manager)
        await logging_system.initialize()
        app_state['logging_system'] = logging_system
        
        # 初始化错误处理器
        error_handler = ErrorHandler()
        app_state['error_handler'] = error_handler
        
        logger.info("EvoForge API服务启动完成")
        
        yield
        
    except Exception as e:
        logger.error(f"启动EvoForge API服务失败: {e}")
        raise
    finally:
        # 清理资源
        logger.info("关闭EvoForge API服务")
        
        if 'db_manager' in app_state:
            await app_state['db_manager'].close()
        
        if 'logging_system' in app_state:
            await app_state['logging_system'].close()
        
        logger.info("EvoForge API服务已关闭")

def create_app(config_override: Dict[str, Any] = None) -> FastAPI:
    """
    创建FastAPI应用实例
    
    Args:
        config_override: 配置覆盖参数
        
    Returns:
        FastAPI应用实例
    """
    
    # 创建FastAPI应用
    app = FastAPI(
        title="EvoForge API",
        description="EvoForge数字细胞进化系统API接口",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan
    )
    
    # 配置CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",  # React开发服务器
            "http://localhost:5173",  # Vite开发服务器
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173"
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 添加Gzip压缩中间件
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # 设置自定义中间件
    setup_middleware(app)
    
    # 注册路由
    app.include_router(evolution_router, prefix="/api/v1/evolution", tags=["进化控制"])
    app.include_router(task_router, prefix="/api/v1/tasks", tags=["任务管理"])
    app.include_router(evaluation_router, prefix="/api/v1/evaluation", tags=["适应度评估"])
    app.include_router(experiment_router, prefix="/api/v1/experiments", tags=["实验管理"])
    app.include_router(system_router, prefix="/api/v1/system", tags=["系统管理"])
    app.include_router(websocket_router, prefix="/ws", tags=["WebSocket"])
    
    # 全局异常处理器
    @app.exception_handler(EvoForgeError)
    async def evoforge_exception_handler(request: Request, exc: EvoForgeError):
        """EvoForge自定义异常处理"""
        logger.error(f"EvoForge错误: {exc.message}", extra={
            "error_code": exc.error_code,
            "details": exc.details,
            "url": str(request.url),
            "method": request.method
        })
        
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error_code=exc.error_code,
                message=exc.message,
                details=exc.details,
                timestamp=exc.timestamp.isoformat()
            ).dict()
        )
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """HTTP异常处理"""
        logger.warning(f"HTTP异常: {exc.detail}", extra={
            "status_code": exc.status_code,
            "url": str(request.url),
            "method": request.method
        })
        
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error_code=f"HTTP_{exc.status_code}",
                message=exc.detail,
                details={"status_code": exc.status_code}
            ).dict()
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """通用异常处理"""
        logger.error(f"未处理的异常: {str(exc)}", extra={
            "exception_type": type(exc).__name__,
            "url": str(request.url),
            "method": request.method
        }, exc_info=True)
        
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error_code="INTERNAL_SERVER_ERROR",
                message="服务器内部错误",
                details={"exception_type": type(exc).__name__}
            ).dict()
        )
    
    # 健康检查端点
    @app.get("/health", tags=["健康检查"])
    async def health_check():
        """健康检查端点"""
        try:
            # 检查数据库连接
            db_status = "unknown"
            if 'db_manager' in app_state:
                db_manager = app_state['db_manager']
                if await db_manager.health_check():
                    db_status = "healthy"
                else:
                    db_status = "unhealthy"
            
            return {
                "status": "healthy",
                "timestamp": logging_system.get_current_time().isoformat() if 'logging_system' in app_state else None,
                "version": "1.0.0",
                "components": {
                    "database": db_status,
                    "api": "healthy"
                }
            }
        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "error": str(e)
                }
            )
    
    # 自定义OpenAPI文档
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        
        openapi_schema = get_openapi(
            title="EvoForge API",
            version="1.0.0",
            description="EvoForge数字细胞进化系统API接口文档",
            routes=app.routes,
        )
        
        # 添加自定义信息
        openapi_schema["info"]["contact"] = {
            "name": "EvoForge Team",
            "email": "support@evoforge.ai"
        }
        
        openapi_schema["info"]["license"] = {
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT"
        }
        
        app.openapi_schema = openapi_schema
        return app.openapi_schema
    
    app.openapi = custom_openapi
    
    return app

def get_app_state() -> Dict[str, Any]:
    """获取应用状态"""
    return app_state

def get_config_manager() -> ConfigManager:
    """获取配置管理器"""
    return app_state.get('config_manager')

def get_db_manager() -> DatabaseManager:
    """获取数据库管理器"""
    return app_state.get('db_manager')

def get_error_handler() -> ErrorHandler:
    """获取错误处理器"""
    return app_state.get('error_handler')