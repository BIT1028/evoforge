# -*- coding: utf-8 -*-
"""
日志中间件

提供请求/响应日志记录和性能监控功能。
"""

import logging
import time
import uuid
from typing import Dict, Any, Optional, Set

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    """
    日志中间件
    
    记录请求和响应的基本信息
    """
    
    def __init__(self, app, config: Dict[str, Any] = None):
        super().__init__(app)
        self.config = config or {}
        
        # 配置选项
        self.log_requests = self.config.get('log_requests', True)
        self.log_responses = self.config.get('log_responses', True)
        self.log_body = self.config.get('log_body', False)
        self.exclude_paths = set(self.config.get('exclude_paths', []))
        self.max_body_size = self.config.get('max_body_size', 1024)  # 1KB
        
        # 性能阈值
        self.slow_request_threshold = self.config.get('slow_request_threshold', 1.0)  # 1秒
        
        logger.info("Logging middleware initialized")
    
    async def dispatch(self, request: Request, call_next):
        """
        处理请求并记录日志
        
        Args:
            request: HTTP请求
            call_next: 下一个中间件或路由处理器
            
        Returns:
            Response: HTTP响应
        """
        # 检查是否需要排除此路径
        if self._should_exclude_path(request.url.path):
            return await call_next(request)
        
        # 生成请求ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # 记录请求开始时间
        start_time = time.time()
        
        # 记录请求日志
        if self.log_requests:
            await self._log_request(request, request_id)
        
        # 处理请求
        try:
            response = await call_next(request)
            
            # 计算处理时间
            process_time = time.time() - start_time
            
            # 添加响应头
            response.headers['X-Request-ID'] = request_id
            response.headers['X-Process-Time'] = f"{process_time:.3f}"
            
            # 记录响应日志
            if self.log_responses:
                await self._log_response(request, response, request_id, process_time)
            
            # 检查慢请求
            if process_time > self.slow_request_threshold:
                self._log_slow_request(request, process_time, request_id)
            
            return response
            
        except Exception as e:
            # 记录异常
            process_time = time.time() - start_time
            self._log_request_exception(request, e, request_id, process_time)
            raise
    
    def _should_exclude_path(self, path: str) -> bool:
        """
        检查是否应该排除此路径
        
        Args:
            path: 请求路径
            
        Returns:
            bool: 是否排除
        """
        # 精确匹配
        if path in self.exclude_paths:
            return True
        
        # 前缀匹配
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return True
        
        return False
    
    async def _log_request(self, request: Request, request_id: str):
        """
        记录请求日志
        
        Args:
            request: HTTP请求
            request_id: 请求ID
        """
        try:
            # 基本请求信息
            log_data = {
                'request_id': request_id,
                'method': request.method,
                'path': str(request.url.path),
                'query_params': str(request.query_params) if request.query_params else None,
                'user_agent': request.headers.get('user-agent'),
                'content_type': request.headers.get('content-type'),
                'content_length': request.headers.get('content-length'),
                'client_ip': self._get_client_ip(request),
                'timestamp': time.time()
            }
            
            # 记录请求体（如果启用且大小合适）
            if self.log_body and self._should_log_body(request):
                try:
                    body = await request.body()
                    if len(body) <= self.max_body_size:
                        log_data['body'] = body.decode('utf-8', errors='ignore')
                    else:
                        log_data['body'] = f"<body too large: {len(body)} bytes>"
                except Exception as e:
                    log_data['body'] = f"<failed to read body: {str(e)}>"
            
            logger.info(
                f"Request: {request.method} {request.url.path}",
                extra=log_data
            )
            
        except Exception as e:
            logger.error(f"Failed to log request: {str(e)}")
    
    async def _log_response(self, request: Request, response: Response, 
                           request_id: str, process_time: float):
        """
        记录响应日志
        
        Args:
            request: HTTP请求
            response: HTTP响应
            request_id: 请求ID
            process_time: 处理时间
        """
        try:
            log_data = {
                'request_id': request_id,
                'method': request.method,
                'path': str(request.url.path),
                'status_code': response.status_code,
                'content_type': response.headers.get('content-type'),
                'content_length': response.headers.get('content-length'),
                'process_time': f"{process_time:.3f}s",
                'timestamp': time.time()
            }
            
            # 根据状态码选择日志级别
            if response.status_code >= 500:
                log_level = logging.ERROR
                message = f"Server Error: {request.method} {request.url.path} -> {response.status_code}"
            elif response.status_code >= 400:
                log_level = logging.WARNING
                message = f"Client Error: {request.method} {request.url.path} -> {response.status_code}"
            else:
                log_level = logging.INFO
                message = f"Response: {request.method} {request.url.path} -> {response.status_code}"
            
            logger.log(log_level, message, extra=log_data)
            
        except Exception as e:
            logger.error(f"Failed to log response: {str(e)}")
    
    def _log_slow_request(self, request: Request, process_time: float, request_id: str):
        """
        记录慢请求日志
        
        Args:
            request: HTTP请求
            process_time: 处理时间
            request_id: 请求ID
        """
        logger.warning(
            f"Slow request detected: {request.method} {request.url.path} took {process_time:.3f}s",
            extra={
                'request_id': request_id,
                'method': request.method,
                'path': str(request.url.path),
                'process_time': f"{process_time:.3f}s",
                'threshold': f"{self.slow_request_threshold:.3f}s",
                'type': 'slow_request'
            }
        )
    
    def _log_request_exception(self, request: Request, exception: Exception, 
                              request_id: str, process_time: float):
        """
        记录请求异常日志
        
        Args:
            request: HTTP请求
            exception: 异常对象
            request_id: 请求ID
            process_time: 处理时间
        """
        logger.error(
            f"Request exception: {request.method} {request.url.path} - {str(exception)}",
            exc_info=exception,
            extra={
                'request_id': request_id,
                'method': request.method,
                'path': str(request.url.path),
                'process_time': f"{process_time:.3f}s",
                'exception_type': type(exception).__name__,
                'type': 'request_exception'
            }
        )
    
    def _get_client_ip(self, request: Request) -> str:
        """
        获取客户端IP地址
        
        Args:
            request: HTTP请求
            
        Returns:
            str: 客户端IP地址
        """
        # 检查代理头
        forwarded_for = request.headers.get('x-forwarded-for')
        if forwarded_for:
            # 取第一个IP（原始客户端IP）
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get('x-real-ip')
        if real_ip:
            return real_ip
        
        # 使用客户端地址
        if hasattr(request, 'client') and request.client:
            return request.client.host
        
        return 'unknown'
    
    def _should_log_body(self, request: Request) -> bool:
        """
        检查是否应该记录请求体
        
        Args:
            request: HTTP请求
            
        Returns:
            bool: 是否记录请求体
        """
        # 只记录POST、PUT、PATCH请求的body
        if request.method not in ['POST', 'PUT', 'PATCH']:
            return False
        
        # 检查内容类型
        content_type = request.headers.get('content-type', '')
        
        # 只记录文本类型的内容
        text_types = [
            'application/json',
            'application/xml',
            'text/',
            'application/x-www-form-urlencoded'
        ]
        
        return any(content_type.startswith(t) for t in text_types)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    请求日志中间件
    
    提供更详细的请求日志记录
    """
    
    def __init__(self, app, config: Dict[str, Any] = None):
        super().__init__(app)
        self.config = config or {}
        
        # 配置选项
        self.log_headers = self.config.get('log_headers', False)
        self.log_cookies = self.config.get('log_cookies', False)
        self.sensitive_headers = set(self.config.get('sensitive_headers', [
            'authorization', 'cookie', 'x-api-key', 'x-auth-token'
        ]))
        
        # 统计信息
        self.request_count = 0
        self.total_process_time = 0.0
        
        logger.info("Request logging middleware initialized")
    
    async def dispatch(self, request: Request, call_next):
        """
        处理请求并记录详细日志
        
        Args:
            request: HTTP请求
            call_next: 下一个中间件或路由处理器
            
        Returns:
            Response: HTTP响应
        """
        start_time = time.time()
        
        # 更新统计
        self.request_count += 1
        
        # 记录详细请求信息
        await self._log_detailed_request(request)
        
        # 处理请求
        response = await call_next(request)
        
        # 计算处理时间
        process_time = time.time() - start_time
        self.total_process_time += process_time
        
        # 记录详细响应信息
        await self._log_detailed_response(request, response, process_time)
        
        return response
    
    async def _log_detailed_request(self, request: Request):
        """
        记录详细请求信息
        
        Args:
            request: HTTP请求
        """
        try:
            log_data = {
                'method': request.method,
                'url': str(request.url),
                'path': str(request.url.path),
                'query_params': dict(request.query_params),
                'path_params': getattr(request, 'path_params', {}),
                'client_ip': self._get_client_ip(request),
                'user_agent': request.headers.get('user-agent'),
                'referer': request.headers.get('referer'),
                'content_type': request.headers.get('content-type'),
                'content_length': request.headers.get('content-length'),
                'timestamp': time.time()
            }
            
            # 记录请求头（如果启用）
            if self.log_headers:
                headers = {}
                for name, value in request.headers.items():
                    if name.lower() in self.sensitive_headers:
                        headers[name] = '<redacted>'
                    else:
                        headers[name] = value
                log_data['headers'] = headers
            
            # 记录Cookie（如果启用）
            if self.log_cookies and request.cookies:
                log_data['cookies'] = dict(request.cookies)
            
            logger.debug(
                f"Detailed request: {request.method} {request.url.path}",
                extra=log_data
            )
            
        except Exception as e:
            logger.error(f"Failed to log detailed request: {str(e)}")
    
    async def _log_detailed_response(self, request: Request, response: Response, 
                                   process_time: float):
        """
        记录详细响应信息
        
        Args:
            request: HTTP请求
            response: HTTP响应
            process_time: 处理时间
        """
        try:
            log_data = {
                'method': request.method,
                'path': str(request.url.path),
                'status_code': response.status_code,
                'process_time': f"{process_time:.3f}s",
                'content_type': response.headers.get('content-type'),
                'content_length': response.headers.get('content-length'),
                'timestamp': time.time()
            }
            
            # 记录响应头（如果启用）
            if self.log_headers:
                log_data['response_headers'] = dict(response.headers)
            
            logger.debug(
                f"Detailed response: {request.method} {request.url.path} -> {response.status_code}",
                extra=log_data
            )
            
        except Exception as e:
            logger.error(f"Failed to log detailed response: {str(e)}")
    
    def _get_client_ip(self, request: Request) -> str:
        """
        获取客户端IP地址
        
        Args:
            request: HTTP请求
            
        Returns:
            str: 客户端IP地址
        """
        # 检查代理头
        forwarded_for = request.headers.get('x-forwarded-for')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get('x-real-ip')
        if real_ip:
            return real_ip
        
        if hasattr(request, 'client') and request.client:
            return request.client.host
        
        return 'unknown'
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取请求统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        avg_process_time = (
            self.total_process_time / self.request_count 
            if self.request_count > 0 else 0
        )
        
        return {
            'total_requests': self.request_count,
            'total_process_time': f"{self.total_process_time:.3f}s",
            'average_process_time': f"{avg_process_time:.3f}s"
        }

# 日志格式化器
class StructuredFormatter(logging.Formatter):
    """
    结构化日志格式化器
    
    将日志记录格式化为结构化格式（JSON）
    """
    
    def format(self, record):
        """
        格式化日志记录
        
        Args:
            record: 日志记录
            
        Returns:
            str: 格式化后的日志
        """
        import json
        
        # 基本日志信息
        log_data = {
            'timestamp': record.created,
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # 添加额外的字段
        if hasattr(record, '__dict__'):
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 
                              'pathname', 'filename', 'module', 'lineno', 
                              'funcName', 'created', 'msecs', 'relativeCreated', 
                              'thread', 'threadName', 'processName', 'process',
                              'getMessage', 'exc_info', 'exc_text', 'stack_info']:
                    log_data[key] = value
        
        # 添加异常信息
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, default=str, ensure_ascii=False)

def setup_logging_middleware(app, config_manager=None):
    """
    设置日志中间件
    
    Args:
        app: FastAPI应用实例
        config_manager: 配置管理器
    """
    # 获取日志配置
    if config_manager:
        debug_config = config_manager.get_debug_config()
        log_config = {
            'log_requests': debug_config.debug_enabled if debug_config else True,
            'log_responses': debug_config.debug_enabled if debug_config else True,
            'log_body': debug_config.log_level == 'DEBUG' if debug_config else False,
            'exclude_paths': ['/health', '/metrics', '/docs', '/redoc', '/openapi.json']
        }
    else:
        log_config = {
            'log_requests': True,
            'log_responses': True,
            'log_body': False,
            'exclude_paths': ['/health', '/metrics', '/docs', '/redoc', '/openapi.json']
        }
    
    # 添加日志中间件
    app.add_middleware(RequestLoggingMiddleware, config=log_config)
    app.add_middleware(LoggingMiddleware, config=log_config)
    
    logger.info("Logging middleware configured")