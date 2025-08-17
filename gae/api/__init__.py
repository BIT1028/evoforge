# -*- coding: utf-8 -*-
"""
EvoForge API模块

提供RESTful API接口和WebSocket实时通信功能：
- FastAPI应用框架
- RESTful API端点
- WebSocket实时通信
- 请求/响应模型
- 中间件和认证
- API文档生成
"""

from .app import create_app
from .models import *
from .routes import *
from .websocket import WebSocketManager
from .middleware import setup_middleware
from .auth import AuthManager

__all__ = [
    'create_app',
    'WebSocketManager',
    'setup_middleware',
    'AuthManager'
]

__version__ = '1.0.0'