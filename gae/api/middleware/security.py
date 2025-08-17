# -*- coding: utf-8 -*-
"""
安全头中间件

提供HTTP安全头设置和安全防护功能。
"""

import logging
import re
import time
from typing import Dict, Any, List, Optional, Set
from urllib.parse import urlparse

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    安全头中间件
    
    自动添加各种安全相关的HTTP头
    """
    
    def __init__(self, app, config: Dict[str, Any] = None):
        super().__init__(app)
        self.config = config or {}
        
        # 配置选项
        self.enabled = self.config.get('enabled', True)
        self.exclude_paths = set(self.config.get('exclude_paths', []))
        
        # 安全头配置
        self.security_headers = self._build_security_headers()
        
        # CSP配置
        self.csp_config = self.config.get('csp', {})
        
        # HSTS配置
        self.hsts_config = self.config.get('hsts', {})
        
        # 其他安全配置
        self.security_config = self.config.get('security', {})
        
        logger.info("Security headers middleware initialized")
    
    def _build_security_headers(self) -> Dict[str, str]:
        """
        构建安全头字典
        
        Returns:
            Dict[str, str]: 安全头映射
        """
        headers = {}
        
        # X-Content-Type-Options
        if self.config.get('x_content_type_options', True):
            headers['X-Content-Type-Options'] = 'nosniff'
        
        # X-Frame-Options
        x_frame_options = self.config.get('x_frame_options', 'DENY')
        if x_frame_options:
            headers['X-Frame-Options'] = x_frame_options
        
        # X-XSS-Protection
        if self.config.get('x_xss_protection', True):
            headers['X-XSS-Protection'] = '1; mode=block'
        
        # Referrer-Policy
        referrer_policy = self.config.get('referrer_policy', 'strict-origin-when-cross-origin')
        if referrer_policy:
            headers['Referrer-Policy'] = referrer_policy
        
        # Permissions-Policy
        permissions_policy = self.config.get('permissions_policy')
        if permissions_policy:
            if isinstance(permissions_policy, dict):
                # 从字典构建策略字符串
                policies = []
                for feature, allowlist in permissions_policy.items():
                    if isinstance(allowlist, list):
                        allowlist_str = ' '.join(f'"{origin}"' for origin in allowlist)
                    else:
                        allowlist_str = str(allowlist)
                    policies.append(f'{feature}=({allowlist_str})')
                headers['Permissions-Policy'] = ', '.join(policies)
            else:
                headers['Permissions-Policy'] = str(permissions_policy)
        
        # Cross-Origin-Embedder-Policy
        coep = self.config.get('cross_origin_embedder_policy')
        if coep:
            headers['Cross-Origin-Embedder-Policy'] = coep
        
        # Cross-Origin-Opener-Policy
        coop = self.config.get('cross_origin_opener_policy')
        if coop:
            headers['Cross-Origin-Opener-Policy'] = coop
        
        # Cross-Origin-Resource-Policy
        corp = self.config.get('cross_origin_resource_policy')
        if corp:
            headers['Cross-Origin-Resource-Policy'] = corp
        
        return headers
    
    async def dispatch(self, request: Request, call_next):
        """
        处理请求并添加安全头
        
        Args:
            request: HTTP请求
            call_next: 下一个中间件或路由处理器
            
        Returns:
            Response: HTTP响应
        """
        # 检查是否启用
        if not self.enabled:
            return await call_next(request)
        
        # 检查是否需要排除此路径
        if self._should_exclude_path(request.url.path):
            return await call_next(request)
        
        # 处理请求
        response = await call_next(request)
        
        # 添加安全头
        self._add_security_headers(response, request)
        
        return response
    
    def _should_exclude_path(self, path: str) -> bool:
        """
        检查是否应该排除此路径
        
        Args:
            path: 请求路径
            
        Returns:
            bool: 是否排除
        """
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return True
        return False
    
    def _add_security_headers(self, response: Response, request: Request):
        """
        添加安全头到响应
        
        Args:
            response: HTTP响应
            request: HTTP请求
        """
        # 添加基础安全头
        for header_name, header_value in self.security_headers.items():
            response.headers[header_name] = header_value
        
        # 添加CSP头
        csp_header = self._build_csp_header(request)
        if csp_header:
            response.headers['Content-Security-Policy'] = csp_header
        
        # 添加HSTS头
        hsts_header = self._build_hsts_header(request)
        if hsts_header:
            response.headers['Strict-Transport-Security'] = hsts_header
        
        # 添加自定义安全头
        custom_headers = self.security_config.get('custom_headers', {})
        for header_name, header_value in custom_headers.items():
            response.headers[header_name] = header_value
    
    def _build_csp_header(self, request: Request) -> Optional[str]:
        """
        构建CSP头
        
        Args:
            request: HTTP请求
            
        Returns:
            Optional[str]: CSP头值
        """
        if not self.csp_config.get('enabled', True):
            return None
        
        # 默认CSP策略
        default_policy = {
            'default-src': ["'self'"],
            'script-src': ["'self'", "'unsafe-inline'"],
            'style-src': ["'self'", "'unsafe-inline'"],
            'img-src': ["'self'", 'data:', 'https:'],
            'font-src': ["'self'", 'https:'],
            'connect-src': ["'self'"],
            'frame-ancestors': ["'none'"],
            'base-uri': ["'self'"],
            'form-action': ["'self'"]
        }
        
        # 合并用户配置
        policy = default_policy.copy()
        user_policy = self.csp_config.get('policy', {})
        for directive, sources in user_policy.items():
            if isinstance(sources, str):
                sources = [sources]
            policy[directive] = sources
        
        # 动态调整策略（基于环境）
        if self.csp_config.get('development_mode', False):
            # 开发模式下放宽限制
            policy['script-src'].extend(["'unsafe-eval'", 'localhost:*'])
            policy['connect-src'].extend(['localhost:*', 'ws:', 'wss:'])
        
        # 构建CSP字符串
        csp_parts = []
        for directive, sources in policy.items():
            if sources:
                sources_str = ' '.join(sources)
                csp_parts.append(f'{directive} {sources_str}')
        
        return '; '.join(csp_parts)
    
    def _build_hsts_header(self, request: Request) -> Optional[str]:
        """
        构建HSTS头
        
        Args:
            request: HTTP请求
            
        Returns:
            Optional[str]: HSTS头值
        """
        if not self.hsts_config.get('enabled', True):
            return None
        
        # 只在HTTPS连接上设置HSTS
        if not request.url.scheme == 'https':
            return None
        
        max_age = self.hsts_config.get('max_age', 31536000)  # 1年
        include_subdomains = self.hsts_config.get('include_subdomains', True)
        preload = self.hsts_config.get('preload', False)
        
        hsts_parts = [f'max-age={max_age}']
        
        if include_subdomains:
            hsts_parts.append('includeSubDomains')
        
        if preload:
            hsts_parts.append('preload')
        
        return '; '.join(hsts_parts)

class SecurityValidationMiddleware(BaseHTTPMiddleware):
    """
    安全验证中间件
    
    提供请求安全验证和防护
    """
    
    def __init__(self, app, config: Dict[str, Any] = None):
        super().__init__(app)
        self.config = config or {}
        
        # 配置选项
        self.enabled = self.config.get('enabled', True)
        self.exclude_paths = set(self.config.get('exclude_paths', []))
        
        # 验证配置
        self.max_request_size = self.config.get('max_request_size', 10 * 1024 * 1024)  # 10MB
        self.max_header_size = self.config.get('max_header_size', 8192)  # 8KB
        self.max_url_length = self.config.get('max_url_length', 2048)
        
        # 恶意模式检测
        self.malicious_patterns = self._compile_malicious_patterns()
        
        # 允许的方法
        self.allowed_methods = set(self.config.get('allowed_methods', [
            'GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'
        ]))
        
        # 主机验证
        self.allowed_hosts = set(self.config.get('allowed_hosts', []))
        
        # 统计信息
        self.blocked_requests = 0
        self.total_requests = 0
        
        logger.info("Security validation middleware initialized")
    
    def _compile_malicious_patterns(self) -> List[re.Pattern]:
        """
        编译恶意模式正则表达式
        
        Returns:
            List[re.Pattern]: 编译后的正则表达式列表
        """
        patterns = [
            # SQL注入模式
            r"(?i)(union|select|insert|update|delete|drop|create|alter)\s+",
            r"(?i)(or|and)\s+\d+\s*=\s*\d+",
            r"(?i)'\s*(or|and)\s*'\w*'\s*=\s*'\w*'",
            
            # XSS模式
            r"(?i)<script[^>]*>.*?</script>",
            r"(?i)javascript:\s*",
            r"(?i)on\w+\s*=\s*['\"].*?['\"]?",
            
            # 路径遍历模式
            r"\.\./",
            r"\\\.\.\\?",
            
            # 命令注入模式
            r"(?i)(;|\||&|`|\$\(|\${).*?(rm|cat|ls|ps|kill|wget|curl)",
            
            # LDAP注入模式
            r"(?i)(\*|\(|\)|\\|\||&).*?(objectclass|cn=|uid=)",
        ]
        
        # 添加用户自定义模式
        user_patterns = self.config.get('malicious_patterns', [])
        patterns.extend(user_patterns)
        
        compiled_patterns = []
        for pattern in patterns:
            try:
                compiled_patterns.append(re.compile(pattern))
            except re.error as e:
                logger.warning(f"Invalid regex pattern '{pattern}': {str(e)}")
        
        return compiled_patterns
    
    async def dispatch(self, request: Request, call_next):
        """
        处理请求并进行安全验证
        
        Args:
            request: HTTP请求
            call_next: 下一个中间件或路由处理器
            
        Returns:
            Response: HTTP响应
        """
        # 检查是否启用
        if not self.enabled:
            return await call_next(request)
        
        # 检查是否需要排除此路径
        if self._should_exclude_path(request.url.path):
            return await call_next(request)
        
        self.total_requests += 1
        
        # 执行安全验证
        validation_result = await self._validate_request(request)
        if not validation_result['valid']:
            self.blocked_requests += 1
            return self._create_security_error_response(validation_result)
        
        # 继续处理请求
        return await call_next(request)
    
    def _should_exclude_path(self, path: str) -> bool:
        """
        检查是否应该排除此路径
        
        Args:
            path: 请求路径
            
        Returns:
            bool: 是否排除
        """
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return True
        return False
    
    async def _validate_request(self, request: Request) -> Dict[str, Any]:
        """
        验证请求安全性
        
        Args:
            request: HTTP请求
            
        Returns:
            Dict[str, Any]: 验证结果
        """
        # 验证HTTP方法
        if request.method not in self.allowed_methods:
            return {
                'valid': False,
                'reason': 'method_not_allowed',
                'message': f'HTTP method {request.method} is not allowed'
            }
        
        # 验证URL长度
        if len(str(request.url)) > self.max_url_length:
            return {
                'valid': False,
                'reason': 'url_too_long',
                'message': f'URL length exceeds maximum of {self.max_url_length} characters'
            }
        
        # 验证主机头
        if self.allowed_hosts and request.headers.get('host'):
            host = request.headers['host'].split(':')[0]  # 移除端口号
            if host not in self.allowed_hosts:
                return {
                    'valid': False,
                    'reason': 'invalid_host',
                    'message': f'Host {host} is not allowed'
                }
        
        # 验证头部大小
        total_header_size = sum(
            len(name) + len(value) 
            for name, value in request.headers.items()
        )
        if total_header_size > self.max_header_size:
            return {
                'valid': False,
                'reason': 'headers_too_large',
                'message': f'Total header size exceeds maximum of {self.max_header_size} bytes'
            }
        
        # 验证请求体大小
        content_length = request.headers.get('content-length')
        if content_length and int(content_length) > self.max_request_size:
            return {
                'valid': False,
                'reason': 'request_too_large',
                'message': f'Request size exceeds maximum of {self.max_request_size} bytes'
            }
        
        # 检测恶意模式
        malicious_check = self._check_malicious_patterns(request)
        if not malicious_check['valid']:
            return malicious_check
        
        return {'valid': True}
    
    def _check_malicious_patterns(self, request: Request) -> Dict[str, Any]:
        """
        检查恶意模式
        
        Args:
            request: HTTP请求
            
        Returns:
            Dict[str, Any]: 检查结果
        """
        # 检查URL
        url_str = str(request.url)
        for pattern in self.malicious_patterns:
            if pattern.search(url_str):
                return {
                    'valid': False,
                    'reason': 'malicious_pattern_in_url',
                    'message': 'Malicious pattern detected in URL',
                    'pattern': pattern.pattern
                }
        
        # 检查查询参数
        for param_name, param_value in request.query_params.items():
            for pattern in self.malicious_patterns:
                if pattern.search(param_value):
                    return {
                        'valid': False,
                        'reason': 'malicious_pattern_in_query',
                        'message': f'Malicious pattern detected in query parameter {param_name}',
                        'pattern': pattern.pattern
                    }
        
        # 检查头部
        for header_name, header_value in request.headers.items():
            # 跳过某些标准头部
            if header_name.lower() in ['authorization', 'cookie', 'user-agent']:
                continue
            
            for pattern in self.malicious_patterns:
                if pattern.search(header_value):
                    return {
                        'valid': False,
                        'reason': 'malicious_pattern_in_header',
                        'message': f'Malicious pattern detected in header {header_name}',
                        'pattern': pattern.pattern
                    }
        
        return {'valid': True}
    
    def _create_security_error_response(self, validation_result: Dict[str, Any]) -> JSONResponse:
        """
        创建安全错误响应
        
        Args:
            validation_result: 验证结果
            
        Returns:
            JSONResponse: 错误响应
        """
        # 记录安全事件
        logger.warning(
            f"Security validation failed: {validation_result['reason']}",
            extra=validation_result
        )
        
        # 根据错误类型确定状态码
        status_code_map = {
            'method_not_allowed': 405,
            'url_too_long': 414,
            'invalid_host': 400,
            'headers_too_large': 431,
            'request_too_large': 413,
            'malicious_pattern_in_url': 400,
            'malicious_pattern_in_query': 400,
            'malicious_pattern_in_header': 400
        }
        
        status_code = status_code_map.get(validation_result['reason'], 400)
        
        response_data = {
            'error': 'Security validation failed',
            'message': validation_result.get('message', 'Request blocked for security reasons'),
            'type': validation_result['reason']
        }
        
        return JSONResponse(
            status_code=status_code,
            content=response_data
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取安全验证统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        block_rate = (
            self.blocked_requests / self.total_requests 
            if self.total_requests > 0 else 0
        )
        
        return {
            'enabled': self.enabled,
            'total_requests': self.total_requests,
            'blocked_requests': self.blocked_requests,
            'block_rate': f"{block_rate:.2%}",
            'patterns_count': len(self.malicious_patterns),
            'allowed_methods': list(self.allowed_methods),
            'allowed_hosts': list(self.allowed_hosts)
        }

def setup_security_middleware(app, config_manager=None):
    """
    设置安全中间件
    
    Args:
        app: FastAPI应用实例
        config_manager: 配置管理器
    """
    # 默认安全配置
    default_security_config = {
        'headers': {
            'enabled': True,
            'exclude_paths': ['/docs', '/redoc', '/openapi.json'],
            'x_content_type_options': True,
            'x_frame_options': 'DENY',
            'x_xss_protection': True,
            'referrer_policy': 'strict-origin-when-cross-origin',
            'permissions_policy': {
                'camera': ['none'],
                'microphone': ['none'],
                'geolocation': ['none'],
                'payment': ['none']
            },
            'csp': {
                'enabled': True,
                'development_mode': False,
                'policy': {
                    'default-src': ["'self'"],
                    'script-src': ["'self'", "'unsafe-inline'"],
                    'style-src': ["'self'", "'unsafe-inline'"],
                    'img-src': ["'self'", 'data:', 'https:'],
                    'connect-src': ["'self'", 'wss:', 'ws:']
                }
            },
            'hsts': {
                'enabled': True,
                'max_age': 31536000,
                'include_subdomains': True,
                'preload': False
            }
        },
        'validation': {
            'enabled': True,
            'exclude_paths': ['/health', '/metrics'],
            'max_request_size': 10 * 1024 * 1024,
            'max_header_size': 8192,
            'max_url_length': 2048,
            'allowed_methods': ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'],
            'allowed_hosts': [],  # 空列表表示允许所有主机
            'malicious_patterns': []
        }
    }
    
    # 从配置管理器获取配置（如果可用）
    if config_manager:
        try:
            # 这里可以从配置管理器获取安全配置
            # security_config = config_manager.get_security_config()
            # 暂时使用默认配置
            security_config = default_security_config
        except Exception as e:
            logger.warning(f"Failed to get security config: {str(e)}, using default")
            security_config = default_security_config
    else:
        security_config = default_security_config
    
    # 添加安全验证中间件（先添加，优先级更高）
    if security_config['validation']['enabled']:
        app.add_middleware(
            SecurityValidationMiddleware, 
            config=security_config['validation']
        )
    
    # 添加安全头中间件
    if security_config['headers']['enabled']:
        app.add_middleware(
            SecurityHeadersMiddleware, 
            config=security_config['headers']
        )
    
    logger.info("Security middleware configured")