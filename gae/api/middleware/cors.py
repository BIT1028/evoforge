# -*- coding: utf-8 -*-
"""
CORS中间件

处理跨域资源共享(CORS)配置。
"""

import logging
from typing import Dict, Any, List, Union

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

def setup_cors(app: FastAPI, config: Dict[str, Any]):
    """
    设置CORS中间件
    
    Args:
        app: FastAPI应用实例
        config: CORS配置
    """
    try:
        # 提取配置参数
        allow_origins = config.get('allow_origins', ['*'])
        allow_credentials = config.get('allow_credentials', True)
        allow_methods = config.get('allow_methods', ['*'])
        allow_headers = config.get('allow_headers', ['*'])
        expose_headers = config.get('expose_headers', [])
        max_age = config.get('max_age', 600)
        
        # 处理特殊的origins配置
        if isinstance(allow_origins, str):
            if allow_origins == '*':
                allow_origins = ['*']
            else:
                allow_origins = [origin.strip() for origin in allow_origins.split(',')]
        
        # 开发环境默认允许本地地址
        if allow_origins == ['*'] or 'localhost' in str(allow_origins):
            development_origins = [
                'http://localhost:3000',
                'http://localhost:5173',
                'http://localhost:8080',
                'http://127.0.0.1:3000',
                'http://127.0.0.1:5173',
                'http://127.0.0.1:8080'
            ]
            
            if allow_origins == ['*']:
                allow_origins = ['*']
            else:
                allow_origins.extend(development_origins)
                allow_origins = list(set(allow_origins))  # 去重
        
        # 添加CORS中间件
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allow_origins,
            allow_credentials=allow_credentials,
            allow_methods=allow_methods,
            allow_headers=allow_headers,
            expose_headers=expose_headers,
            max_age=max_age
        )
        
        logger.info(f"CORS middleware configured with origins: {allow_origins}")
        
    except Exception as e:
        logger.error(f"Failed to setup CORS middleware: {str(e)}")
        # 使用默认配置
        app.add_middleware(
            CORSMiddleware,
            allow_origins=['*'],
            allow_credentials=True,
            allow_methods=['*'],
            allow_headers=['*']
        )
        logger.warning("Using default CORS configuration")

class CustomCORSMiddleware:
    """
    自定义CORS中间件
    
    提供更细粒度的CORS控制
    """
    
    def __init__(self, app, config: Dict[str, Any]):
        self.app = app
        self.config = config
        
        # 解析配置
        self.allow_origins = self._parse_origins(config.get('allow_origins', ['*']))
        self.allow_credentials = config.get('allow_credentials', True)
        self.allow_methods = self._parse_methods(config.get('allow_methods', ['*']))
        self.allow_headers = self._parse_headers(config.get('allow_headers', ['*']))
        self.expose_headers = config.get('expose_headers', [])
        self.max_age = config.get('max_age', 600)
        
        # 预检请求缓存
        self.preflight_cache = {}
        
        logger.info("Custom CORS middleware initialized")
    
    def _parse_origins(self, origins: Union[str, List[str]]) -> List[str]:
        """
        解析允许的源
        
        Args:
            origins: 源配置
            
        Returns:
            List[str]: 解析后的源列表
        """
        if isinstance(origins, str):
            if origins == '*':
                return ['*']
            return [origin.strip() for origin in origins.split(',')]
        
        return origins or ['*']
    
    def _parse_methods(self, methods: Union[str, List[str]]) -> List[str]:
        """
        解析允许的方法
        
        Args:
            methods: 方法配置
            
        Returns:
            List[str]: 解析后的方法列表
        """
        if isinstance(methods, str):
            if methods == '*':
                return ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'HEAD', 'PATCH']
            return [method.strip().upper() for method in methods.split(',')]
        
        return [method.upper() for method in methods] if methods else ['*']
    
    def _parse_headers(self, headers: Union[str, List[str]]) -> List[str]:
        """
        解析允许的头部
        
        Args:
            headers: 头部配置
            
        Returns:
            List[str]: 解析后的头部列表
        """
        if isinstance(headers, str):
            if headers == '*':
                return ['*']
            return [header.strip() for header in headers.split(',')]
        
        return headers or ['*']
    
    def _is_origin_allowed(self, origin: str) -> bool:
        """
        检查源是否被允许
        
        Args:
            origin: 请求源
            
        Returns:
            bool: 是否允许
        """
        if '*' in self.allow_origins:
            return True
        
        if origin in self.allow_origins:
            return True
        
        # 支持通配符匹配
        for allowed_origin in self.allow_origins:
            if '*' in allowed_origin:
                pattern = allowed_origin.replace('*', '.*')
                import re
                if re.match(pattern, origin):
                    return True
        
        return False
    
    def _is_method_allowed(self, method: str) -> bool:
        """
        检查方法是否被允许
        
        Args:
            method: 请求方法
            
        Returns:
            bool: 是否允许
        """
        if '*' in self.allow_methods:
            return True
        
        return method.upper() in self.allow_methods
    
    def _get_cors_headers(self, origin: str, method: str = None) -> Dict[str, str]:
        """
        获取CORS响应头
        
        Args:
            origin: 请求源
            method: 请求方法
            
        Returns:
            Dict[str, str]: CORS头部字典
        """
        headers = {}
        
        # Access-Control-Allow-Origin
        if self._is_origin_allowed(origin):
            if '*' in self.allow_origins and not self.allow_credentials:
                headers['Access-Control-Allow-Origin'] = '*'
            else:
                headers['Access-Control-Allow-Origin'] = origin
        
        # Access-Control-Allow-Credentials
        if self.allow_credentials:
            headers['Access-Control-Allow-Credentials'] = 'true'
        
        # Access-Control-Allow-Methods
        if method and self._is_method_allowed(method):
            if '*' in self.allow_methods:
                headers['Access-Control-Allow-Methods'] = ', '.join([
                    'GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'HEAD', 'PATCH'
                ])
            else:
                headers['Access-Control-Allow-Methods'] = ', '.join(self.allow_methods)
        
        # Access-Control-Allow-Headers
        if '*' in self.allow_headers:
            headers['Access-Control-Allow-Headers'] = '*'
        else:
            headers['Access-Control-Allow-Headers'] = ', '.join(self.allow_headers)
        
        # Access-Control-Expose-Headers
        if self.expose_headers:
            headers['Access-Control-Expose-Headers'] = ', '.join(self.expose_headers)
        
        # Access-Control-Max-Age
        headers['Access-Control-Max-Age'] = str(self.max_age)
        
        return headers
    
    async def __call__(self, scope, receive, send):
        """
        ASGI应用调用
        
        Args:
            scope: ASGI作用域
            receive: 接收函数
            send: 发送函数
        """
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return
        
        # 获取请求信息
        headers = dict(scope.get('headers', []))
        origin = headers.get(b'origin', b'').decode('utf-8')
        method = scope.get('method', 'GET')
        
        # 处理预检请求
        if method == 'OPTIONS':
            await self._handle_preflight(scope, receive, send, origin)
            return
        
        # 处理实际请求
        await self._handle_request(scope, receive, send, origin, method)
    
    async def _handle_preflight(self, scope, receive, send, origin: str):
        """
        处理预检请求
        
        Args:
            scope: ASGI作用域
            receive: 接收函数
            send: 发送函数
            origin: 请求源
        """
        # 获取预检请求头
        headers = dict(scope.get('headers', []))
        requested_method = headers.get(b'access-control-request-method', b'').decode('utf-8')
        requested_headers = headers.get(b'access-control-request-headers', b'').decode('utf-8')
        
        # 检查是否允许
        if not self._is_origin_allowed(origin) or not self._is_method_allowed(requested_method):
            # 拒绝预检请求
            await send({
                'type': 'http.response.start',
                'status': 403,
                'headers': []
            })
            await send({
                'type': 'http.response.body',
                'body': b'CORS policy violation'
            })
            return
        
        # 生成CORS头部
        cors_headers = self._get_cors_headers(origin, requested_method)
        
        # 转换为ASGI格式
        response_headers = [
            (key.encode(), value.encode()) for key, value in cors_headers.items()
        ]
        
        # 发送预检响应
        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': response_headers
        })
        await send({
            'type': 'http.response.body',
            'body': b''
        })
    
    async def _handle_request(self, scope, receive, send, origin: str, method: str):
        """
        处理实际请求
        
        Args:
            scope: ASGI作用域
            receive: 接收函数
            send: 发送函数
            origin: 请求源
            method: 请求方法
        """
        # 检查是否允许
        if not self._is_origin_allowed(origin):
            await send({
                'type': 'http.response.start',
                'status': 403,
                'headers': []
            })
            await send({
                'type': 'http.response.body',
                'body': b'CORS policy violation'
            })
            return
        
        # 包装send函数以添加CORS头部
        async def send_wrapper(message):
            if message['type'] == 'http.response.start':
                # 添加CORS头部
                cors_headers = self._get_cors_headers(origin)
                existing_headers = list(message.get('headers', []))
                
                for key, value in cors_headers.items():
                    existing_headers.append((key.encode(), value.encode()))
                
                message['headers'] = existing_headers
            
            await send(message)
        
        # 调用下一个应用
        await self.app(scope, receive, send_wrapper)

# 预定义的CORS配置
CORS_CONFIGS = {
    'development': {
        'allow_origins': ['*'],
        'allow_credentials': True,
        'allow_methods': ['*'],
        'allow_headers': ['*'],
        'max_age': 600
    },
    'production': {
        'allow_origins': [],  # 需要明确指定
        'allow_credentials': True,
        'allow_methods': ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
        'allow_headers': [
            'Accept',
            'Accept-Language',
            'Content-Language',
            'Content-Type',
            'Authorization',
            'X-Requested-With'
        ],
        'max_age': 86400  # 24小时
    },
    'strict': {
        'allow_origins': [],  # 需要明确指定
        'allow_credentials': False,
        'allow_methods': ['GET', 'POST'],
        'allow_headers': ['Content-Type'],
        'max_age': 3600  # 1小时
    }
}

def get_cors_config(environment: str = 'development') -> Dict[str, Any]:
    """
    获取预定义的CORS配置
    
    Args:
        environment: 环境名称
        
    Returns:
        Dict[str, Any]: CORS配置
    """
    return CORS_CONFIGS.get(environment, CORS_CONFIGS['development']).copy()