# -*- coding: utf-8 -*-
"""
指标中间件

提供API性能监控和统计收集功能。
"""

import logging
import time
from collections import defaultdict, deque
from typing import Dict, Any, Optional, List, Tuple
from threading import Lock

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

class MetricsCollector:
    """
    指标收集器
    
    收集和存储API性能指标
    """
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.lock = Lock()
        
        # 基础计数器
        self.request_count = 0
        self.error_count = 0
        self.total_response_time = 0.0
        
        # 按状态码统计
        self.status_code_counts = defaultdict(int)
        
        # 按路径统计
        self.path_stats = defaultdict(lambda: {
            'count': 0,
            'total_time': 0.0,
            'min_time': float('inf'),
            'max_time': 0.0,
            'error_count': 0
        })
        
        # 按方法统计
        self.method_stats = defaultdict(lambda: {
            'count': 0,
            'total_time': 0.0,
            'error_count': 0
        })
        
        # 响应时间历史（用于计算百分位数）
        self.response_time_history = deque(maxlen=max_history)
        
        # 错误历史
        self.error_history = deque(maxlen=max_history)
        
        # 时间窗口统计（最近1分钟、5分钟、15分钟）
        self.time_windows = {
            '1m': deque(maxlen=60),    # 每秒一个数据点
            '5m': deque(maxlen=300),   # 每秒一个数据点
            '15m': deque(maxlen=900)   # 每秒一个数据点
        }
        
        logger.info("Metrics collector initialized")
    
    def record_request(self, method: str, path: str, status_code: int, 
                      response_time: float, error: Optional[str] = None):
        """
        记录请求指标
        
        Args:
            method: HTTP方法
            path: 请求路径
            status_code: 状态码
            response_time: 响应时间
            error: 错误信息（如果有）
        """
        with self.lock:
            current_time = time.time()
            
            # 更新基础计数器
            self.request_count += 1
            self.total_response_time += response_time
            
            # 更新状态码统计
            self.status_code_counts[status_code] += 1
            
            # 更新路径统计
            path_stat = self.path_stats[path]
            path_stat['count'] += 1
            path_stat['total_time'] += response_time
            path_stat['min_time'] = min(path_stat['min_time'], response_time)
            path_stat['max_time'] = max(path_stat['max_time'], response_time)
            
            # 更新方法统计
            method_stat = self.method_stats[method]
            method_stat['count'] += 1
            method_stat['total_time'] += response_time
            
            # 记录错误
            if status_code >= 400 or error:
                self.error_count += 1
                path_stat['error_count'] += 1
                method_stat['error_count'] += 1
                
                if error:
                    self.error_history.append({
                        'timestamp': current_time,
                        'method': method,
                        'path': path,
                        'status_code': status_code,
                        'error': error,
                        'response_time': response_time
                    })
            
            # 记录响应时间历史
            self.response_time_history.append(response_time)
            
            # 更新时间窗口统计
            request_data = {
                'timestamp': current_time,
                'method': method,
                'path': path,
                'status_code': status_code,
                'response_time': response_time,
                'is_error': status_code >= 400 or error is not None
            }
            
            for window in self.time_windows.values():
                window.append(request_data)
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """
        获取汇总统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        with self.lock:
            avg_response_time = (
                self.total_response_time / self.request_count 
                if self.request_count > 0 else 0
            )
            
            error_rate = (
                self.error_count / self.request_count 
                if self.request_count > 0 else 0
            )
            
            return {
                'total_requests': self.request_count,
                'total_errors': self.error_count,
                'error_rate': f"{error_rate:.2%}",
                'average_response_time': f"{avg_response_time:.3f}s",
                'total_response_time': f"{self.total_response_time:.3f}s"
            }
    
    def get_status_code_stats(self) -> Dict[str, int]:
        """
        获取状态码统计
        
        Returns:
            Dict[str, int]: 状态码统计
        """
        with self.lock:
            return dict(self.status_code_counts)
    
    def get_path_stats(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取路径统计（按请求数排序）
        
        Args:
            limit: 返回的路径数量限制
            
        Returns:
            List[Dict[str, Any]]: 路径统计列表
        """
        with self.lock:
            path_list = []
            
            for path, stats in self.path_stats.items():
                avg_time = stats['total_time'] / stats['count'] if stats['count'] > 0 else 0
                error_rate = stats['error_count'] / stats['count'] if stats['count'] > 0 else 0
                
                path_list.append({
                    'path': path,
                    'count': stats['count'],
                    'average_time': f"{avg_time:.3f}s",
                    'min_time': f"{stats['min_time']:.3f}s" if stats['min_time'] != float('inf') else "0.000s",
                    'max_time': f"{stats['max_time']:.3f}s",
                    'error_count': stats['error_count'],
                    'error_rate': f"{error_rate:.2%}"
                })
            
            # 按请求数排序
            path_list.sort(key=lambda x: x['count'], reverse=True)
            
            return path_list[:limit]
    
    def get_method_stats(self) -> List[Dict[str, Any]]:
        """
        获取HTTP方法统计
        
        Returns:
            List[Dict[str, Any]]: 方法统计列表
        """
        with self.lock:
            method_list = []
            
            for method, stats in self.method_stats.items():
                avg_time = stats['total_time'] / stats['count'] if stats['count'] > 0 else 0
                error_rate = stats['error_count'] / stats['count'] if stats['count'] > 0 else 0
                
                method_list.append({
                    'method': method,
                    'count': stats['count'],
                    'average_time': f"{avg_time:.3f}s",
                    'error_count': stats['error_count'],
                    'error_rate': f"{error_rate:.2%}"
                })
            
            # 按请求数排序
            method_list.sort(key=lambda x: x['count'], reverse=True)
            
            return method_list
    
    def get_response_time_percentiles(self) -> Dict[str, str]:
        """
        获取响应时间百分位数
        
        Returns:
            Dict[str, str]: 百分位数统计
        """
        with self.lock:
            if not self.response_time_history:
                return {}
            
            sorted_times = sorted(self.response_time_history)
            length = len(sorted_times)
            
            percentiles = {}
            for p in [50, 75, 90, 95, 99]:
                index = int(length * p / 100) - 1
                if index < 0:
                    index = 0
                elif index >= length:
                    index = length - 1
                
                percentiles[f'p{p}'] = f"{sorted_times[index]:.3f}s"
            
            return percentiles
    
    def get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取最近的错误
        
        Args:
            limit: 返回的错误数量限制
            
        Returns:
            List[Dict[str, Any]]: 错误列表
        """
        with self.lock:
            errors = list(self.error_history)
            errors.sort(key=lambda x: x['timestamp'], reverse=True)
            
            # 格式化时间戳
            for error in errors[:limit]:
                error['timestamp'] = time.strftime(
                    '%Y-%m-%d %H:%M:%S', 
                    time.localtime(error['timestamp'])
                )
            
            return errors[:limit]
    
    def get_time_window_stats(self, window: str = '1m') -> Dict[str, Any]:
        """
        获取时间窗口统计
        
        Args:
            window: 时间窗口（'1m', '5m', '15m'）
            
        Returns:
            Dict[str, Any]: 时间窗口统计
        """
        with self.lock:
            if window not in self.time_windows:
                return {}
            
            window_data = list(self.time_windows[window])
            if not window_data:
                return {}
            
            current_time = time.time()
            window_seconds = {'1m': 60, '5m': 300, '15m': 900}[window]
            
            # 过滤时间窗口内的数据
            recent_data = [
                req for req in window_data 
                if current_time - req['timestamp'] <= window_seconds
            ]
            
            if not recent_data:
                return {}
            
            # 计算统计信息
            total_requests = len(recent_data)
            error_requests = sum(1 for req in recent_data if req['is_error'])
            total_response_time = sum(req['response_time'] for req in recent_data)
            
            avg_response_time = total_response_time / total_requests
            error_rate = error_requests / total_requests
            
            # 计算RPS（每秒请求数）
            time_span = max(1, current_time - recent_data[0]['timestamp'])
            rps = total_requests / time_span
            
            return {
                'window': window,
                'total_requests': total_requests,
                'error_requests': error_requests,
                'error_rate': f"{error_rate:.2%}",
                'average_response_time': f"{avg_response_time:.3f}s",
                'requests_per_second': f"{rps:.2f}",
                'time_span': f"{time_span:.1f}s"
            }
    
    def reset_stats(self):
        """
        重置所有统计信息
        """
        with self.lock:
            self.request_count = 0
            self.error_count = 0
            self.total_response_time = 0.0
            
            self.status_code_counts.clear()
            self.path_stats.clear()
            self.method_stats.clear()
            
            self.response_time_history.clear()
            self.error_history.clear()
            
            for window in self.time_windows.values():
                window.clear()
            
            logger.info("Metrics statistics reset")

class MetricsMiddleware(BaseHTTPMiddleware):
    """
    指标中间件
    
    收集API性能指标
    """
    
    def __init__(self, app, config: Dict[str, Any] = None):
        super().__init__(app)
        self.config = config or {}
        
        # 配置选项
        self.enabled = self.config.get('enabled', True)
        self.exclude_paths = set(self.config.get('exclude_paths', []))
        self.max_history = self.config.get('max_history', 1000)
        
        # 创建指标收集器
        self.collector = MetricsCollector(max_history=self.max_history)
        
        logger.info("Metrics middleware initialized")
    
    async def dispatch(self, request: Request, call_next):
        """
        处理请求并收集指标
        
        Args:
            request: HTTP请求
            call_next: 下一个中间件或路由处理器
            
        Returns:
            Response: HTTP响应
        """
        # 检查是否启用指标收集
        if not self.enabled:
            return await call_next(request)
        
        # 检查是否需要排除此路径
        if self._should_exclude_path(request.url.path):
            return await call_next(request)
        
        # 记录开始时间
        start_time = time.time()
        
        # 处理请求
        error_message = None
        try:
            response = await call_next(request)
            status_code = response.status_code
            
        except Exception as e:
            # 记录异常
            error_message = str(e)
            status_code = 500
            
            # 重新抛出异常
            raise
        
        finally:
            # 计算响应时间
            response_time = time.time() - start_time
            
            # 记录指标
            self.collector.record_request(
                method=request.method,
                path=self._normalize_path(request.url.path),
                status_code=status_code,
                response_time=response_time,
                error=error_message
            )
        
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
    
    def _normalize_path(self, path: str) -> str:
        """
        标准化路径（将路径参数替换为占位符）
        
        Args:
            path: 原始路径
            
        Returns:
            str: 标准化后的路径
        """
        # 简单的路径参数替换
        # 例如：/api/experiments/123 -> /api/experiments/{id}
        import re
        
        # 替换UUID
        path = re.sub(
            r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            '/{uuid}',
            path,
            flags=re.IGNORECASE
        )
        
        # 替换数字ID
        path = re.sub(r'/\d+', '/{id}', path)
        
        return path
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        获取所有指标
        
        Returns:
            Dict[str, Any]: 指标数据
        """
        return {
            'summary': self.collector.get_summary_stats(),
            'status_codes': self.collector.get_status_code_stats(),
            'paths': self.collector.get_path_stats(),
            'methods': self.collector.get_method_stats(),
            'response_time_percentiles': self.collector.get_response_time_percentiles(),
            'recent_errors': self.collector.get_recent_errors(),
            'time_windows': {
                '1m': self.collector.get_time_window_stats('1m'),
                '5m': self.collector.get_time_window_stats('5m'),
                '15m': self.collector.get_time_window_stats('15m')
            }
        }
    
    def reset_metrics(self):
        """
        重置指标
        """
        self.collector.reset_stats()

# 全局指标收集器实例
_global_metrics_middleware: Optional[MetricsMiddleware] = None

def get_metrics_middleware() -> Optional[MetricsMiddleware]:
    """
    获取全局指标中间件实例
    
    Returns:
        Optional[MetricsMiddleware]: 指标中间件实例
    """
    return _global_metrics_middleware

def setup_metrics_middleware(app, config_manager=None):
    """
    设置指标中间件
    
    Args:
        app: FastAPI应用实例
        config_manager: 配置管理器
    """
    global _global_metrics_middleware
    
    # 获取指标配置
    if config_manager:
        debug_config = config_manager.get_debug_config()
        metrics_config = {
            'enabled': debug_config.debug_enabled if debug_config else True,
            'exclude_paths': ['/health', '/metrics', '/docs', '/redoc', '/openapi.json'],
            'max_history': 1000
        }
    else:
        metrics_config = {
            'enabled': True,
            'exclude_paths': ['/health', '/metrics', '/docs', '/redoc', '/openapi.json'],
            'max_history': 1000
        }
    
    # 创建并添加指标中间件
    _global_metrics_middleware = MetricsMiddleware(app, config=metrics_config)
    app.add_middleware(MetricsMiddleware, config=metrics_config)
    
    logger.info("Metrics middleware configured")