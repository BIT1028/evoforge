# -*- coding: utf-8 -*-
"""
错误处理中间件

提供统一的异常捕获和错误响应格式。
"""

import logging
import traceback
import time
from typing import Dict, Any, Optional, Type

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

# 导入自定义异常
try:
    from ...core.exceptions import (
        EvoForgeError, ValidationError, ConfigurationError,
        DatabaseError, EngineError, SecurityError
    )
except ImportError:
    # 如果导入失败，定义基本异常类
    class EvoForgeError(Exception):
        """EvoForge基础异常"""
        def __init__(self, message: str, error_code: str = None):
            super().__init__(message)
            self.message = message
            self.error_code = error_code or 'EVOFORGE_ERROR'
    
    class ValidationError(EvoForgeError):
        """验证错误"""
        def __init__(self, message: str, field: str = None):
            super().__init__(message, 'VALIDATION_ERROR')
            self.field = field
    
    class ConfigurationError(EvoForgeError):
        """配置错误"""
        def __init__(self, message: str):
            super().__init__(message, 'CONFIG_ERROR')
    
    class DatabaseError(EvoForgeError):
        """数据库错误"""
        def __init__(self, message: str):
            super().__init__(message, 'DATABASE_ERROR')
    
    class EngineError(EvoForgeError):
        """引擎错误"""
        def __init__(self, message: str):
            super().__init__(message, 'ENGINE_ERROR')
    
    class SecurityError(EvoForgeError):
        """安全错误"""
        def __init__(self, message: str):
            super().__init__(message, 'SECURITY_ERROR')

logger = logging.getLogger(__name__)

class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    错误处理中间件
    
    捕获和处理所有未处理的异常
    """
    
    def __init__(self, app, config: Dict[str, Any] = None):
        super().__init__(app)
        self.config = config or {}
        self.debug = self.config.get('debug', False)
        self.log_errors = self.config.get('log_errors', True)
        self.include_traceback = self.config.get('include_traceback', False)
        
        # 错误统计
        self.error_counts = {}
        
        logger.info("Error handler middleware initialized")
    
    async def dispatch(self, request: Request, call_next):
        """
        处理请求并捕获异常
        
        Args:
            request: HTTP请求
            call_next: 下一个中间件或路由处理器
            
        Returns:
            Response: HTTP响应
        """
        start_time = time.time()
        
        try:
            response = await call_next(request)
            return response
            
        except Exception as e:
            # 记录错误统计
            error_type = type(e).__name__
            self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
            
            # 处理异常
            return await self._handle_exception(request, e, start_time)
    
    async def _handle_exception(self, request: Request, exc: Exception, start_time: float) -> JSONResponse:
        """
        处理异常并返回错误响应
        
        Args:
            request: HTTP请求
            exc: 异常对象
            start_time: 请求开始时间
            
        Returns:
            JSONResponse: 错误响应
        """
        process_time = time.time() - start_time
        
        # 确定错误信息
        error_info = self._get_error_info(exc)
        
        # 记录错误日志
        if self.log_errors:
            self._log_error(request, exc, error_info, process_time)
        
        # 构建错误响应
        response_data = {
            'status': 'error',
            'message': error_info['message'],
            'error_code': error_info['error_code'],
            'timestamp': time.time(),
            'path': str(request.url.path),
            'method': request.method
        }
        
        # 在调试模式下包含更多信息
        if self.debug or self.include_traceback:
            response_data.update({
                'detail': error_info.get('detail'),
                'traceback': error_info.get('traceback'),
                'request_id': getattr(request.state, 'request_id', None)
            })
        
        # 添加验证错误的详细信息
        if isinstance(exc, RequestValidationError):
            response_data['validation_errors'] = exc.errors()
        elif isinstance(exc, ValidationError) and hasattr(exc, 'field'):
            response_data['field'] = exc.field
        
        return JSONResponse(
            status_code=error_info['status_code'],
            content=response_data,
            headers={
                'X-Error-Code': error_info['error_code'],
                'X-Process-Time': f"{process_time:.3f}"
            }
        )
    
    def _get_error_info(self, exc: Exception) -> Dict[str, Any]:
        """
        获取异常的错误信息
        
        Args:
            exc: 异常对象
            
        Returns:
            Dict[str, Any]: 错误信息字典
        """
        # HTTP异常
        if isinstance(exc, (HTTPException, StarletteHTTPException)):
            return {
                'status_code': exc.status_code,
                'message': exc.detail,
                'error_code': f'HTTP_{exc.status_code}',
                'detail': getattr(exc, 'detail', None)
            }
        
        # 请求验证错误
        if isinstance(exc, RequestValidationError):
            return {
                'status_code': status.HTTP_422_UNPROCESSABLE_ENTITY,
                'message': 'Validation error',
                'error_code': 'VALIDATION_ERROR',
                'detail': str(exc)
            }
        
        # EvoForge自定义异常
        if isinstance(exc, EvoForgeError):
            status_code = self._get_status_code_for_evoforge_error(exc)
            return {
                'status_code': status_code,
                'message': exc.message,
                'error_code': exc.error_code,
                'detail': str(exc),
                'traceback': traceback.format_exc() if self.debug else None
            }
        
        # 其他异常
        return {
            'status_code': status.HTTP_500_INTERNAL_SERVER_ERROR,
            'message': 'Internal server error',
            'error_code': 'INTERNAL_ERROR',
            'detail': str(exc) if self.debug else None,
            'traceback': traceback.format_exc() if self.debug else None
        }
    
    def _get_status_code_for_evoforge_error(self, exc: EvoForgeError) -> int:
        """
        根据EvoForge异常类型确定HTTP状态码
        
        Args:
            exc: EvoForge异常
            
        Returns:
            int: HTTP状态码
        """
        if isinstance(exc, ValidationError):
            return status.HTTP_400_BAD_REQUEST
        elif isinstance(exc, ConfigurationError):
            return status.HTTP_500_INTERNAL_SERVER_ERROR
        elif isinstance(exc, DatabaseError):
            return status.HTTP_503_SERVICE_UNAVAILABLE
        elif isinstance(exc, EngineError):
            return status.HTTP_500_INTERNAL_SERVER_ERROR
        elif isinstance(exc, SecurityError):
            return status.HTTP_403_FORBIDDEN
        else:
            return status.HTTP_500_INTERNAL_SERVER_ERROR
    
    def _log_error(self, request: Request, exc: Exception, error_info: Dict[str, Any], process_time: float):
        """
        记录错误日志
        
        Args:
            request: HTTP请求
            exc: 异常对象
            error_info: 错误信息
            process_time: 处理时间
        """
        log_data = {
            'method': request.method,
            'path': str(request.url.path),
            'query_params': str(request.query_params),
            'status_code': error_info['status_code'],
            'error_code': error_info['error_code'],
            'message': error_info['message'],
            'process_time': f"{process_time:.3f}s",
            'user_agent': request.headers.get('user-agent'),
            'client_ip': getattr(request.state, 'client_ip', 'unknown')
        }
        
        # 根据错误严重程度选择日志级别
        if error_info['status_code'] >= 500:
            logger.error(
                f"Server error: {error_info['message']}",
                extra=log_data,
                exc_info=exc
            )
        elif error_info['status_code'] >= 400:
            logger.warning(
                f"Client error: {error_info['message']}",
                extra=log_data
            )
        else:
            logger.info(
                f"Request error: {error_info['message']}",
                extra=log_data
            )
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """
        获取错误统计信息
        
        Returns:
            Dict[str, Any]: 错误统计
        """
        return {
            'error_counts': self.error_counts.copy(),
            'total_errors': sum(self.error_counts.values())
        }

def setup_exception_handlers(app: FastAPI):
    """
    设置全局异常处理器
    
    Args:
        app: FastAPI应用实例
    """
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """
        HTTP异常处理器
        """
        return JSONResponse(
            status_code=exc.status_code,
            content={
                'status': 'error',
                'message': exc.detail,
                'error_code': f'HTTP_{exc.status_code}',
                'timestamp': time.time(),
                'path': str(request.url.path),
                'method': request.method
            }
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """
        请求验证异常处理器
        """
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                'status': 'error',
                'message': 'Validation error',
                'error_code': 'VALIDATION_ERROR',
                'validation_errors': exc.errors(),
                'timestamp': time.time(),
                'path': str(request.url.path),
                'method': request.method
            }
        )
    
    @app.exception_handler(EvoForgeError)
    async def evoforge_exception_handler(request: Request, exc: EvoForgeError):
        """
        EvoForge异常处理器
        """
        # 确定状态码
        if isinstance(exc, ValidationError):
            status_code = status.HTTP_400_BAD_REQUEST
        elif isinstance(exc, ConfigurationError):
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        elif isinstance(exc, DatabaseError):
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        elif isinstance(exc, EngineError):
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        elif isinstance(exc, SecurityError):
            status_code = status.HTTP_403_FORBIDDEN
        else:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        
        response_data = {
            'status': 'error',
            'message': exc.message,
            'error_code': exc.error_code,
            'timestamp': time.time(),
            'path': str(request.url.path),
            'method': request.method
        }
        
        # 添加验证错误的字段信息
        if isinstance(exc, ValidationError) and hasattr(exc, 'field'):
            response_data['field'] = exc.field
        
        return JSONResponse(
            status_code=status_code,
            content=response_data
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """
        通用异常处理器
        """
        logger.error(
            f"Unhandled exception: {str(exc)}",
            exc_info=exc,
            extra={
                'method': request.method,
                'path': str(request.url.path),
                'query_params': str(request.query_params)
            }
        )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                'status': 'error',
                'message': 'Internal server error',
                'error_code': 'INTERNAL_ERROR',
                'timestamp': time.time(),
                'path': str(request.url.path),
                'method': request.method
            }
        )
    
    logger.info("Exception handlers configured")

# 错误响应工具函数
def create_error_response(
    message: str,
    error_code: str,
    status_code: int = status.HTTP_400_BAD_REQUEST,
    detail: Optional[str] = None,
    **kwargs
) -> JSONResponse:
    """
    创建标准错误响应
    
    Args:
        message: 错误消息
        error_code: 错误代码
        status_code: HTTP状态码
        detail: 详细信息
        **kwargs: 其他响应数据
        
    Returns:
        JSONResponse: 错误响应
    """
    response_data = {
        'status': 'error',
        'message': message,
        'error_code': error_code,
        'timestamp': time.time()
    }
    
    if detail:
        response_data['detail'] = detail
    
    response_data.update(kwargs)
    
    return JSONResponse(
        status_code=status_code,
        content=response_data
    )

def create_validation_error_response(
    message: str,
    field: Optional[str] = None,
    errors: Optional[list] = None
) -> JSONResponse:
    """
    创建验证错误响应
    
    Args:
        message: 错误消息
        field: 错误字段
        errors: 验证错误列表
        
    Returns:
        JSONResponse: 验证错误响应
    """
    response_data = {
        'status': 'error',
        'message': message,
        'error_code': 'VALIDATION_ERROR',
        'timestamp': time.time()
    }
    
    if field:
        response_data['field'] = field
    
    if errors:
        response_data['validation_errors'] = errors
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=response_data
    )