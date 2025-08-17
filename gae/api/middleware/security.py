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
            r