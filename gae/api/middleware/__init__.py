# -*- coding: utf-8 -*-
"""
API中间件模块

提供FastAPI应用的中间件组件：
- 请求验证和认证
- 错误处理和异常捕获
- 请求/响应日志记录
- 性能监控和指标收集
- CORS处理
- 请求限流
- 安全头设置
"""

from .auth import AuthMiddleware, get_current_user, require_auth
from .cors import setup_cors
from .error_handler import ErrorHandlerMiddleware, setup_exception_handlers
from .logging import LoggingMiddleware, RequestLoggingMiddleware
from .metrics import MetricsMiddleware, PrometheusMiddleware
from .rate_limit import RateLimitMiddleware
from .security import SecurityHeadersMiddleware
from .validation import ValidationMiddleware

__all__ = [
    # 认证中间件
    'AuthMiddleware',
    'get_current_user',
    'require_auth',
    
    # CORS设置
    'setup_cors',
    
    # 错误处理
    'ErrorHandlerMiddleware',
    'setup_exception_handlers',
    
    # 日志中间件
    'LoggingMiddleware',
    'RequestLoggingMiddleware',
    
    # 指标中间件
    'MetricsMiddleware',
    'PrometheusMiddleware',
    
    # 限流中间件
    'RateLimitMiddleware',
    
    # 安全中间件
    'SecurityHeadersMiddleware',
    
    # 验证中间件
    'ValidationMiddleware'
]

# 中间件配置
MIDDLEWARE_CONFIG = {
    'auth': {
        'enabled': True,
        'secret_key': None,  # 从配置中获取
        'algorithm': 'HS256',
        'access_token_expire_minutes': 30
    },
    'cors': {
        'enabled': True,
        'allow_origins': ['*'],
        'allow_credentials': True,
        'allow_methods': ['*'],
        'allow_headers': ['*']
    },
    'rate_limit': {
        'enabled': True,
        'default_rate': '100/minute',
        'burst_rate': '200/minute'
    },
    'security': {
        'enabled': True,
        'hsts_max_age': 31536000,
        'content_type_nosniff': True,
        'frame_options': 'DENY',
        'xss_protection': True
    },
    'logging': {
        'enabled': True,
        'log_requests': True,
        'log_responses': True,
        'log_body': False,  # 出于性能考虑默认关闭
        'exclude_paths': ['/health', '/metrics']
    },
    'metrics': {
        'enabled': True,
        'prometheus_enabled': True,
        'collect_request_metrics': True,
        'collect_response_metrics': True
    }
}

def setup_middleware(app, config_manager=None):
    """
    设置所有中间件
    
    Args:
        app: FastAPI应用实例
        config_manager: 配置管理器
    """
    # 更新配置
    if config_manager:
        update_middleware_config(config_manager)
    
    # 按顺序添加中间件（注意：FastAPI中间件是LIFO顺序）
    
    # 1. 安全头中间件（最外层）
    if MIDDLEWARE_CONFIG['security']['enabled']:
        app.add_middleware(SecurityHeadersMiddleware, config=MIDDLEWARE_CONFIG['security'])
    
    # 2. CORS中间件
    if MIDDLEWARE_CONFIG['cors']['enabled']:
        setup_cors(app, MIDDLEWARE_CONFIG['cors'])
    
    # 3. 指标收集中间件
    if MIDDLEWARE_CONFIG['metrics']['enabled']:
        app.add_middleware(MetricsMiddleware, config=MIDDLEWARE_CONFIG['metrics'])
        if MIDDLEWARE_CONFIG['metrics']['prometheus_enabled']:
            app.add_middleware(PrometheusMiddleware)
    
    # 4. 限流中间件
    if MIDDLEWARE_CONFIG['rate_limit']['enabled']:
        app.add_middleware(RateLimitMiddleware, config=MIDDLEWARE_CONFIG['rate_limit'])
    
    # 5. 日志中间件
    if MIDDLEWARE_CONFIG['logging']['enabled']:
        app.add_middleware(LoggingMiddleware, config=MIDDLEWARE_CONFIG['logging'])
        app.add_middleware(RequestLoggingMiddleware, config=MIDDLEWARE_CONFIG['logging'])
    
    # 6. 验证中间件
    app.add_middleware(ValidationMiddleware)
    
    # 7. 认证中间件
    if MIDDLEWARE_CONFIG['auth']['enabled']:
        app.add_middleware(AuthMiddleware, config=MIDDLEWARE_CONFIG['auth'])
    
    # 8. 错误处理中间件（最内层）
    app.add_middleware(ErrorHandlerMiddleware)
    
    # 设置异常处理器
    setup_exception_handlers(app)

def update_middleware_config(config_manager):
    """
    从配置管理器更新中间件配置
    
    Args:
        config_manager: 配置管理器
    """
    try:
        # 获取API配置
        api_config = getattr(config_manager, 'get_api_config', lambda: {})() or {}
        
        # 更新认证配置
        if 'auth' in api_config:
            MIDDLEWARE_CONFIG['auth'].update(api_config['auth'])
        
        # 更新CORS配置
        if 'cors' in api_config:
            MIDDLEWARE_CONFIG['cors'].update(api_config['cors'])
        
        # 更新限流配置
        if 'rate_limit' in api_config:
            MIDDLEWARE_CONFIG['rate_limit'].update(api_config['rate_limit'])
        
        # 更新安全配置
        if 'security' in api_config:
            MIDDLEWARE_CONFIG['security'].update(api_config['security'])
        
        # 更新日志配置
        debug_config = config_manager.get_debug_config()
        if debug_config:
            MIDDLEWARE_CONFIG['logging']['enabled'] = debug_config.debug_enabled
            MIDDLEWARE_CONFIG['logging']['log_body'] = debug_config.log_level == 'DEBUG'
        
        # 更新指标配置
        if 'metrics' in api_config:
            MIDDLEWARE_CONFIG['metrics'].update(api_config['metrics'])
            
    except Exception as e:
        # 如果配置更新失败，使用默认配置
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to update middleware config: {str(e)}")

def get_middleware_config():
    """
    获取当前中间件配置
    
    Returns:
        dict: 中间件配置字典
    """
    return MIDDLEWARE_CONFIG.copy()

def set_middleware_config(section: str, config: dict):
    """
    设置特定中间件的配置
    
    Args:
        section: 中间件节名称
        config: 配置字典
    """
    if section in MIDDLEWARE_CONFIG:
        MIDDLEWARE_CONFIG[section].update(config)
    else:
        MIDDLEWARE_CONFIG[section] = config