# -*- coding: utf-8 -*-
"""
限流中间件

提供API请求频率限制和防护功能。
"""

import logging
import time
from collections import defaultdict, deque
from typing import Dict, Any, Optional, Tuple, List
from threading import Lock
import hashlib

from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

class TokenBucket:
    """
    令牌桶算法实现
    
    用于平滑的速率限制
    """
    
    def __init__(self, capacity: int, refill_rate: float):
        """
        初始化令牌桶
        
        Args:
            capacity: 桶容量（最大令牌数）
            refill_rate: 令牌补充速率（每秒补充的令牌数）
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
        self.lock = Lock()
    
    def consume(self, tokens: int = 1) -> bool:
        """
        消费令牌
        
        Args:
            tokens: 需要消费的令牌数
            
        Returns:
            bool: 是否成功消费
        """
        with self.lock:
            now = time.time()
            
            # 补充令牌
            time_passed = now - self.last_refill
            self.tokens = min(
                self.capacity,
                self.tokens + time_passed * self.refill_rate
            )
            self.last_refill = now
            
            # 检查是否有足够的令牌
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取令牌桶状态
        
        Returns:
            Dict[str, Any]: 状态信息
        """
        with self.lock:
            return {
                'capacity': self.capacity,
                'current_tokens': self.tokens,
                'refill_rate': self.refill_rate,
                'last_refill': self.last_refill
            }

class SlidingWindowCounter:
    """
    滑动窗口计数器
    
    用于精确的时间窗口内请求计数
    """
    
    def __init__(self, window_size: int, max_requests: int):
        """
        初始化滑动窗口计数器
        
        Args:
            window_size: 窗口大小（秒）
            max_requests: 窗口内最大请求数
        """
        self.window_size = window_size
        self.max_requests = max_requests
        self.requests = deque()
        self.lock = Lock()
    
    def is_allowed(self) -> bool:
        """
        检查是否允许请求
        
        Returns:
            bool: 是否允许
        """
        with self.lock:
            now = time.time()
            
            # 移除过期的请求记录
            while self.requests and self.requests[0] <= now - self.window_size:
                self.requests.popleft()
            
            # 检查是否超过限制
            if len(self.requests) >= self.max_requests:
                return False
            
            # 记录当前请求
            self.requests.append(now)
            return True
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取窗口状态
        
        Returns:
            Dict[str, Any]: 状态信息
        """
        with self.lock:
            now = time.time()
            
            # 清理过期记录
            while self.requests and self.requests[0] <= now - self.window_size:
                self.requests.popleft()
            
            return {
                'window_size': self.window_size,
                'max_requests': self.max_requests,
                'current_requests': len(self.requests),
                'remaining_requests': max(0, self.max_requests - len(self.requests))
            }

class RateLimiter:
    """
    速率限制器
    
    管理多个客户端的速率限制
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.lock = Lock()
        
        # 客户端限制器存储
        self.client_limiters = defaultdict(dict)
        
        # 清理任务配置
        self.cleanup_interval = config.get('cleanup_interval', 300)  # 5分钟
        self.last_cleanup = time.time()
        
        # 限制规则
        self.rules = config.get('rules', {})
        
        logger.info(f"Rate limiter initialized with rules: {self.rules}")
    
    def is_allowed(self, client_id: str, rule_name: str = 'default') -> Tuple[bool, Dict[str, Any]]:
        """
        检查客户端是否允许请求
        
        Args:
            client_id: 客户端标识
            rule_name: 规则名称
            
        Returns:
            Tuple[bool, Dict[str, Any]]: (是否允许, 状态信息)
        """
        # 获取规则配置
        rule = self.rules.get(rule_name, self.rules.get('default', {}))
        if not rule:
            return True, {}
        
        with self.lock:
            # 定期清理过期的限制器
            self._cleanup_if_needed()
            
            # 获取或创建客户端限制器
            if client_id not in self.client_limiters:
                self.client_limiters[client_id] = {}
            
            client_limiter = self.client_limiters[client_id]
            
            # 检查令牌桶限制
            if 'token_bucket' in rule:
                bucket_config = rule['token_bucket']
                if 'bucket' not in client_limiter:
                    client_limiter['bucket'] = TokenBucket(
                        capacity=bucket_config['capacity'],
                        refill_rate=bucket_config['refill_rate']
                    )
                
                if not client_limiter['bucket'].consume():
                    return False, {
                        'rule': rule_name,
                        'type': 'token_bucket',
                        'bucket_status': client_limiter['bucket'].get_status()
                    }
            
            # 检查滑动窗口限制
            if 'sliding_window' in rule:
                window_config = rule['sliding_window']
                if 'window' not in client_limiter:
                    client_limiter['window'] = SlidingWindowCounter(
                        window_size=window_config['window_size'],
                        max_requests=window_config['max_requests']
                    )
                
                if not client_limiter['window'].is_allowed():
                    return False, {
                        'rule': rule_name,
                        'type': 'sliding_window',
                        'window_status': client_limiter['window'].get_status()
                    }
            
            return True, {'rule': rule_name, 'allowed': True}
    
    def _cleanup_if_needed(self):
        """
        如果需要，清理过期的限制器
        """
        now = time.time()
        if now - self.last_cleanup < self.cleanup_interval:
            return
        
        # 清理逻辑：移除长时间未使用的客户端限制器
        clients_to_remove = []
        for client_id, limiters in self.client_limiters.items():
            # 检查是否所有限制器都已过期
            should_remove = True
            
            if 'bucket' in limiters:
                bucket = limiters['bucket']
                if now - bucket.last_refill < self.cleanup_interval:
                    should_remove = False
            
            if 'window' in limiters and should_remove:
                window = limiters['window']
                if window.requests and now - window.requests[-1] < self.cleanup_interval:
                    should_remove = False
            
            if should_remove:
                clients_to_remove.append(client_id)
        
        # 移除过期的客户端
        for client_id in clients_to_remove:
            del self.client_limiters[client_id]
        
        self.last_cleanup = now
        
        if clients_to_remove:
            logger.debug(f"Cleaned up {len(clients_to_remove)} expired client limiters")
    
    def get_client_status(self, client_id: str) -> Dict[str, Any]:
        """
        获取客户端状态
        
        Args:
            client_id: 客户端标识
            
        Returns:
            Dict[str, Any]: 客户端状态
        """
        with self.lock:
            if client_id not in self.client_limiters:
                return {'exists': False}
            
            client_limiter = self.client_limiters[client_id]
            status = {'exists': True}
            
            if 'bucket' in client_limiter:
                status['bucket'] = client_limiter['bucket'].get_status()
            
            if 'window' in client_limiter:
                status['window'] = client_limiter['window'].get_status()
            
            return status
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取限流器统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        with self.lock:
            return {
                'total_clients': len(self.client_limiters),
                'rules': list(self.rules.keys()),
                'cleanup_interval': self.cleanup_interval,
                'last_cleanup': self.last_cleanup
            }

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    限流中间件
    
    对API请求进行速率限制
    """
    
    def __init__(self, app, config: Dict[str, Any] = None):
        super().__init__(app)
        self.config = config or {}
        
        # 配置选项
        self.enabled = self.config.get('enabled', True)
        self.exclude_paths = set(self.config.get('exclude_paths', []))
        
        # 客户端识别配置
        self.client_id_header = self.config.get('client_id_header', 'X-Client-ID')
        self.use_ip_as_fallback = self.config.get('use_ip_as_fallback', True)
        
        # 路径规则映射
        self.path_rules = self.config.get('path_rules', {})
        
        # 创建速率限制器
        self.rate_limiter = RateLimiter(self.config)
        
        # 统计信息
        self.blocked_requests = 0
        self.total_requests = 0
        
        logger.info("Rate limit middleware initialized")
    
    async def dispatch(self, request: Request, call_next):
        """
        处理请求并应用速率限制
        
        Args:
            request: HTTP请求
            call_next: 下一个中间件或路由处理器
            
        Returns:
            Response: HTTP响应
        """
        # 检查是否启用限流
        if not self.enabled:
            return await call_next(request)
        
        # 检查是否需要排除此路径
        if self._should_exclude_path(request.url.path):
            return await call_next(request)
        
        self.total_requests += 1
        
        # 获取客户端标识
        client_id = self._get_client_id(request)
        
        # 确定适用的规则
        rule_name = self._get_rule_for_path(request.url.path)
        
        # 检查速率限制
        allowed, status = self.rate_limiter.is_allowed(client_id, rule_name)
        
        if not allowed:
            self.blocked_requests += 1
            
            # 记录限流事件
            logger.warning(
                f"Rate limit exceeded for client {client_id} on path {request.url.path}",
                extra={
                    'client_id': client_id,
                    'path': request.url.path,
                    'rule': rule_name,
                    'status': status
                }
            )
            
            # 返回429错误
            return self._create_rate_limit_response(status)
        
        # 继续处理请求
        response = await call_next(request)
        
        # 添加速率限制头
        self._add_rate_limit_headers(response, client_id, rule_name)
        
        return response
    
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
    
    def _get_client_id(self, request: Request) -> str:
        """
        获取客户端标识
        
        Args:
            request: HTTP请求
            
        Returns:
            str: 客户端标识
        """
        # 首先尝试从头部获取客户端ID
        client_id = request.headers.get(self.client_id_header)
        if client_id:
            return client_id
        
        # 如果启用IP作为后备，使用IP地址
        if self.use_ip_as_fallback:
            # 获取真实IP地址
            forwarded_for = request.headers.get('x-forwarded-for')
            if forwarded_for:
                client_ip = forwarded_for.split(',')[0].strip()
            else:
                client_ip = request.headers.get('x-real-ip')
                if not client_ip and hasattr(request, 'client') and request.client:
                    client_ip = request.client.host
                else:
                    client_ip = 'unknown'
            
            return f"ip:{client_ip}"
        
        # 生成基于请求特征的标识
        user_agent = request.headers.get('user-agent', '')
        accept = request.headers.get('accept', '')
        
        # 创建特征哈希
        features = f"{user_agent}:{accept}"
        client_hash = hashlib.md5(features.encode()).hexdigest()[:16]
        
        return f"hash:{client_hash}"
    
    def _get_rule_for_path(self, path: str) -> str:
        """
        获取路径对应的规则
        
        Args:
            path: 请求路径
            
        Returns:
            str: 规则名称
        """
        # 检查精确匹配
        if path in self.path_rules:
            return self.path_rules[path]
        
        # 检查前缀匹配
        for path_pattern, rule_name in self.path_rules.items():
            if path.startswith(path_pattern):
                return rule_name
        
        # 返回默认规则
        return 'default'
    
    def _create_rate_limit_response(self, status: Dict[str, Any]) -> JSONResponse:
        """
        创建速率限制响应
        
        Args:
            status: 限制状态信息
            
        Returns:
            JSONResponse: 429响应
        """
        response_data = {
            'error': 'Rate limit exceeded',
            'message': 'Too many requests. Please try again later.',
            'type': status.get('type', 'unknown'),
            'rule': status.get('rule', 'default')
        }
        
        # 添加重试建议
        if status.get('type') == 'token_bucket':
            bucket_status = status.get('bucket_status', {})
            if bucket_status.get('refill_rate'):
                retry_after = max(1, int(1 / bucket_status['refill_rate']))
                response_data['retry_after'] = retry_after
        elif status.get('type') == 'sliding_window':
            window_status = status.get('window_status', {})
            if window_status.get('window_size'):
                response_data['retry_after'] = window_status['window_size']
        
        headers = {}
        if 'retry_after' in response_data:
            headers['Retry-After'] = str(response_data['retry_after'])
        
        return JSONResponse(
            status_code=429,
            content=response_data,
            headers=headers
        )
    
    def _add_rate_limit_headers(self, response: Response, client_id: str, rule_name: str):
        """
        添加速率限制头
        
        Args:
            response: HTTP响应
            client_id: 客户端标识
            rule_name: 规则名称
        """
        try:
            client_status = self.rate_limiter.get_client_status(client_id)
            
            if 'window' in client_status:
                window_status = client_status['window']
                response.headers['X-RateLimit-Limit'] = str(window_status['max_requests'])
                response.headers['X-RateLimit-Remaining'] = str(window_status['remaining_requests'])
                response.headers['X-RateLimit-Window'] = str(window_status['window_size'])
            
            if 'bucket' in client_status:
                bucket_status = client_status['bucket']
                response.headers['X-RateLimit-Bucket-Capacity'] = str(bucket_status['capacity'])
                response.headers['X-RateLimit-Bucket-Tokens'] = str(int(bucket_status['current_tokens']))
            
            response.headers['X-RateLimit-Rule'] = rule_name
            
        except Exception as e:
            logger.error(f"Failed to add rate limit headers: {str(e)}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取中间件统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        limiter_stats = self.rate_limiter.get_stats()
        
        block_rate = (
            self.blocked_requests / self.total_requests 
            if self.total_requests > 0 else 0
        )
        
        return {
            'enabled': self.enabled,
            'total_requests': self.total_requests,
            'blocked_requests': self.blocked_requests,
            'block_rate': f"{block_rate:.2%}",
            'limiter_stats': limiter_stats
        }

def setup_rate_limit_middleware(app, config_manager=None):
    """
    设置限流中间件
    
    Args:
        app: FastAPI应用实例
        config_manager: 配置管理器
    """
    # 默认限流配置
    default_config = {
        'enabled': True,
        'exclude_paths': ['/health', '/metrics', '/docs', '/redoc', '/openapi.json'],
        'client_id_header': 'X-Client-ID',
        'use_ip_as_fallback': True,
        'cleanup_interval': 300,
        'rules': {
            'default': {
                'sliding_window': {
                    'window_size': 60,  # 1分钟
                    'max_requests': 100  # 每分钟100个请求
                }
            },
            'strict': {
                'token_bucket': {
                    'capacity': 10,
                    'refill_rate': 1.0  # 每秒1个令牌
                },
                'sliding_window': {
                    'window_size': 60,
                    'max_requests': 30
                }
            },
            'lenient': {
                'sliding_window': {
                    'window_size': 60,
                    'max_requests': 300
                }
            }
        },
        'path_rules': {
            '/api/auth/': 'strict',
            '/api/system/': 'strict',
            '/api/experiments/': 'default',
            '/api/tasks/': 'default',
            '/api/evaluations/': 'lenient'
        }
    }
    
    # 从配置管理器获取配置（如果可用）
    if config_manager:
        try:
            # 这里可以从配置管理器获取限流配置
            # rate_limit_config = config_manager.get_rate_limit_config()
            # 暂时使用默认配置
            rate_limit_config = default_config
        except Exception as e:
            logger.warning(f"Failed to get rate limit config: {str(e)}, using default")
            rate_limit_config = default_config
    else:
        rate_limit_config = default_config
    
    # 添加限流中间件
    app.add_middleware(RateLimitMiddleware, config=rate_limit_config)
    
    logger.info("Rate limit middleware configured")