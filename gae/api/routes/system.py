# -*- coding: utf-8 -*-
"""
系统管理API路由

提供系统管理的RESTful API端点：
- 系统状态监控
- 配置管理
- 健康检查
- 性能监控
- 日志管理
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime, timedelta
import psutil
import platform

from ..models.requests import (
    SystemConfigRequest,
    SystemOperationRequest
)
from ..models.responses import (
    SuccessResponse,
    ErrorResponse,
    SystemInfoResponse,
    ConfigResponse
)
from ..models.dtos import SystemStatusDTO, PerformanceMetricsDTO
from ..models.validators import (
    validate_system_config,
    ValidationError
)
from ...config.config_manager import ConfigManager
from ...core.error_handler import EvoForgeError, ErrorType
from ...core.module_coordinator import ModuleCoordinator
from ...database.database_manager import DatabaseManager

# 创建路由器
router = APIRouter()
logger = logging.getLogger(__name__)

# 依赖注入
async def get_config_manager() -> ConfigManager:
    """获取配置管理器"""
    # 这里应该从应用状态中获取
    return None

async def get_module_coordinator() -> ModuleCoordinator:
    """获取模块协调器"""
    # 这里应该从应用状态中获取
    return None

async def get_database_manager() -> DatabaseManager:
    """获取数据库管理器"""
    # 这里应该从应用状态中获取
    return None

@router.get("/health", response_model=SuccessResponse[Dict[str, Any]])
async def health_check(
    config_manager: ConfigManager = Depends(get_config_manager),
    coordinator: ModuleCoordinator = Depends(get_module_coordinator),
    db_manager: DatabaseManager = Depends(get_database_manager)
):
    """
    系统健康检查
    
    Args:
        config_manager: 配置管理器
        coordinator: 模块协调器
        db_manager: 数据库管理器
    
    Returns:
        系统健康状态
    """
    try:
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '2.0.0',
            'uptime': None,
            'components': {}
        }
        
        # 检查数据库连接
        try:
            db_health = await db_manager.health_check()
            health_status['components']['database'] = {
                'status': 'healthy' if db_health else 'unhealthy',
                'details': db_health
            }
        except Exception as e:
            health_status['components']['database'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health_status['status'] = 'degraded'
        
        # 检查模块协调器
        try:
            coordinator_status = await coordinator.get_status()
            health_status['components']['coordinator'] = {
                'status': 'healthy',
                'details': coordinator_status
            }
        except Exception as e:
            health_status['components']['coordinator'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health_status['status'] = 'degraded'
        
        # 检查配置管理器
        try:
            config_status = config_manager.validate_all_configs()
            health_status['components']['config'] = {
                'status': 'healthy' if config_status else 'unhealthy',
                'details': config_status
            }
        except Exception as e:
            health_status['components']['config'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health_status['status'] = 'degraded'
        
        # 检查系统资源
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            resource_status = 'healthy'
            if cpu_percent > 90 or memory.percent > 90 or disk.percent > 90:
                resource_status = 'warning'
                health_status['status'] = 'degraded'
            
            health_status['components']['resources'] = {
                'status': resource_status,
                'details': {
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'disk_percent': disk.percent
                }
            }
        except Exception as e:
            health_status['components']['resources'] = {
                'status': 'unknown',
                'error': str(e)
            }
        
        return SuccessResponse(
            data=health_status,
            message="Health check completed"
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Health check failed")

@router.get("/status", response_model=SuccessResponse[SystemStatusDTO])
async def get_system_status(
    include_performance: bool = Query(True, description="是否包含性能指标"),
    include_modules: bool = Query(True, description="是否包含模块状态"),
    coordinator: ModuleCoordinator = Depends(get_module_coordinator)
):
    """
    获取系统状态
    
    Args:
        include_performance: 是否包含性能指标
        include_modules: 是否包含模块状态
        coordinator: 模块协调器
    
    Returns:
        系统状态信息
    """
    try:
        # 基础系统信息
        system_info = {
            'platform': platform.system(),
            'platform_version': platform.version(),
            'architecture': platform.architecture()[0],
            'python_version': platform.python_version(),
            'hostname': platform.node(),
            'boot_time': datetime.fromtimestamp(psutil.boot_time()).isoformat()
        }
        
        # 性能指标
        performance_metrics = None
        if include_performance:
            cpu_times = psutil.cpu_times()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            network = psutil.net_io_counters()
            
            performance_metrics = PerformanceMetricsDTO(
                cpu_percent=psutil.cpu_percent(interval=1),
                cpu_count=psutil.cpu_count(),
                cpu_times={
                    'user': cpu_times.user,
                    'system': cpu_times.system,
                    'idle': cpu_times.idle
                },
                memory_total=memory.total,
                memory_available=memory.available,
                memory_percent=memory.percent,
                memory_used=memory.used,
                disk_total=disk.total,
                disk_used=disk.used,
                disk_free=disk.free,
                disk_percent=disk.percent,
                network_bytes_sent=network.bytes_sent,
                network_bytes_recv=network.bytes_recv,
                network_packets_sent=network.packets_sent,
                network_packets_recv=network.packets_recv
            )
        
        # 模块状态
        module_status = None
        if include_modules:
            module_status = await coordinator.get_all_module_status()
        
        # 运行时间
        uptime_seconds = (datetime.utcnow() - datetime.fromtimestamp(psutil.boot_time())).total_seconds()
        
        system_status = SystemStatusDTO(
            system_info=system_info,
            uptime_seconds=uptime_seconds,
            performance_metrics=performance_metrics,
            module_status=module_status,
            timestamp=datetime.utcnow()
        )
        
        return SuccessResponse(
            data=system_status,
            message="System status retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Error getting system status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get system status")

@router.get("/info", response_model=SystemInfoResponse)
async def get_system_info(
    config_manager: ConfigManager = Depends(get_config_manager)
):
    """
    获取系统信息
    
    Args:
        config_manager: 配置管理器
    
    Returns:
        系统信息
    """
    try:
        system_info = {
            'name': 'EvoForge',
            'version': '2.0.0',
            'description': 'Advanced Evolution Simulation Platform',
            'platform': platform.system(),
            'python_version': platform.python_version(),
            'architecture': platform.architecture()[0],
            'hostname': platform.node(),
            'startup_time': datetime.utcnow().isoformat(),
            'configuration': {
                'debug_mode': config_manager.get_debug_config().debug_enabled,
                'log_level': config_manager.get_debug_config().log_level,
                'database_type': config_manager.get_database_config().database,
                'llm_providers': list(config_manager.get_llm_config().providers.keys())
            },
            'features': [
                'Digital Cell Simulation',
                'NEAT Evolution Algorithm',
                'LLM-Assisted Fitness Evaluation',
                'Secure Code Execution',
                'Real-time Monitoring',
                'Multi-modal Assessment'
            ],
            'api_version': 'v1',
            'documentation_url': '/docs',
            'health_check_url': '/api/v1/system/health'
        }
        
        return SystemInfoResponse(
            status='success',
            data=system_info,
            message='System information retrieved successfully'
        )
        
    except Exception as e:
        logger.error(f"Error getting system info: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get system info")

@router.get("/config", response_model=SuccessResponse[Dict[str, Any]])
async def get_system_config(
    section: Optional[str] = Query(None, description="配置节名称"),
    config_manager: ConfigManager = Depends(get_config_manager)
):
    """
    获取系统配置
    
    Args:
        section: 配置节名称
        config_manager: 配置管理器
    
    Returns:
        系统配置信息
    """
    try:
        if section:
            # 获取特定配置节
            if section == 'database':
                config_data = config_manager.get_database_config().dict()
                # 隐藏敏感信息
                config_data.pop('password', None)
            elif section == 'llm':
                config_data = config_manager.get_llm_config().dict()
                # 隐藏API密钥
                for provider in config_data.get('providers', {}).values():
                    provider.pop('api_key', None)
            elif section == 'debug':
                config_data = config_manager.get_debug_config().dict()
            elif section == 'evolution':
                config_data = config_manager.get_evolution_config().dict()
            elif section == 'evaluation':
                config_data = config_manager.get_evaluation_config().dict()
            elif section == 'sandbox':
                config_data = config_manager.get_sandbox_config().dict()
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unknown config section: {section}"
                )
        else:
            # 获取所有配置（隐藏敏感信息）
            config_data = {
                'database': {**config_manager.get_database_config().dict()},
                'llm': {**config_manager.get_llm_config().dict()},
                'debug': config_manager.get_debug_config().dict(),
                'evolution': config_manager.get_evolution_config().dict(),
                'evaluation': config_manager.get_evaluation_config().dict(),
                'sandbox': config_manager.get_sandbox_config().dict()
            }
            
            # 隐藏敏感信息
            config_data['database'].pop('password', None)
            for provider in config_data['llm'].get('providers', {}).values():
                provider.pop('api_key', None)
        
        return SuccessResponse(
            data=config_data,
            message="Configuration retrieved successfully"
        )
        
    except ValidationError as e:
        logger.error(f"Validation error getting config: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    
    except Exception as e:
        logger.error(f"Error getting system config: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get system config")

@router.put("/config", response_model=SuccessResponse[Dict[str, Any]])
async def update_system_config(
    request: SystemConfigRequest,
    config_manager: ConfigManager = Depends(get_config_manager),
    coordinator: ModuleCoordinator = Depends(get_module_coordinator)
):
    """
    更新系统配置
    
    Args:
        request: 配置更新请求
        config_manager: 配置管理器
        coordinator: 模块协调器
    
    Returns:
        更新后的配置信息
    """
    try:
        logger.info(f"Updating system config: {request.section}")
        
        # 验证配置
        validate_system_config(request.section, request.config)
        
        # 获取当前配置
        current_config = None
        if request.section == 'database':
            current_config = config_manager.get_database_config()
        elif request.section == 'llm':
            current_config = config_manager.get_llm_config()
        elif request.section == 'debug':
            current_config = config_manager.get_debug_config()
        elif request.section == 'evolution':
            current_config = config_manager.get_evolution_config()
        elif request.section == 'evaluation':
            current_config = config_manager.get_evaluation_config()
        elif request.section == 'sandbox':
            current_config = config_manager.get_sandbox_config()
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown config section: {request.section}"
            )
        
        # 合并配置
        updated_config = {**current_config.dict(), **request.config}
        
        # 更新配置
        if request.section == 'database':
            config_manager.update_database_config(updated_config)
        elif request.section == 'llm':
            config_manager.update_llm_config(updated_config)
        elif request.section == 'debug':
            config_manager.update_debug_config(updated_config)
        elif request.section == 'evolution':
            config_manager.update_evolution_config(updated_config)
        elif request.section == 'evaluation':
            config_manager.update_evaluation_config(updated_config)
        elif request.section == 'sandbox':
            config_manager.update_sandbox_config(updated_config)
        
        # 通知模块协调器配置已更新
        if request.restart_required:
            await coordinator.restart_affected_modules(request.section)
        else:
            await coordinator.reload_module_config(request.section)
        
        # 保存配置到文件
        if request.persist:
            config_manager.save_config_to_file()
        
        logger.info(f"System config updated successfully: {request.section}")
        
        return SuccessResponse(
            data={
                'section': request.section,
                'updated_config': updated_config,
                'restart_required': request.restart_required,
                'persisted': request.persist
            },
            message="Configuration updated successfully"
        )
        
    except ValidationError as e:
        logger.error(f"Validation error updating config: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    
    except EvoForgeError as e:
        logger.error(f"EvoForge error updating config: {e.message}")
        raise HTTPException(status_code=500, detail=e.message)
    
    except Exception as e:
        logger.error(f"Unexpected error updating config: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/operation", response_model=SuccessResponse[Dict[str, Any]])
async def execute_system_operation(
    request: SystemOperationRequest,
    coordinator: ModuleCoordinator = Depends(get_module_coordinator)
):
    """
    执行系统操作
    
    Args:
        request: 系统操作请求
        coordinator: 模块协调器
    
    Returns:
        操作结果
    """
    try:
        logger.info(f"Executing system operation: {request.operation}")
        
        result = None
        
        if request.operation == 'restart_module':
            module_name = request.parameters.get('module_name')
            if not module_name:
                raise HTTPException(
                    status_code=400,
                    detail="module_name parameter is required"
                )
            result = await coordinator.restart_module(module_name)
            
        elif request.operation == 'reload_config':
            section = request.parameters.get('section')
            result = await coordinator.reload_module_config(section)
            
        elif request.operation == 'clear_cache':
            cache_type = request.parameters.get('cache_type', 'all')
            result = await coordinator.clear_cache(cache_type)
            
        elif request.operation == 'garbage_collect':
            import gc
            collected = gc.collect()
            result = {'collected_objects': collected}
            
        elif request.operation == 'get_metrics':
            result = await coordinator.get_system_metrics()
            
        elif request.operation == 'export_logs':
            log_level = request.parameters.get('log_level', 'INFO')
            hours = request.parameters.get('hours', 24)
            result = await coordinator.export_logs(log_level, hours)
            
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown operation: {request.operation}"
            )
        
        logger.info(f"System operation completed: {request.operation}")
        
        return SuccessResponse(
            data={
                'operation': request.operation,
                'parameters': request.parameters,
                'result': result,
                'timestamp': datetime.utcnow().isoformat()
            },
            message=f"Operation '{request.operation}' completed successfully"
        )
        
    except EvoForgeError as e:
        logger.error(f"EvoForge error executing operation: {e.message}")
        raise HTTPException(status_code=500, detail=e.message)
    
    except Exception as e:
        logger.error(f"Unexpected error executing operation: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/logs", response_model=SuccessResponse[List[Dict[str, Any]]])
async def get_system_logs(
    level: Optional[str] = Query(None, description="日志级别过滤"),
    module: Optional[str] = Query(None, description="模块过滤"),
    hours: int = Query(24, ge=1, le=168, description="时间范围（小时）"),
    limit: int = Query(100, ge=1, le=1000, description="返回条数限制"),
    coordinator: ModuleCoordinator = Depends(get_module_coordinator)
):
    """
    获取系统日志
    
    Args:
        level: 日志级别过滤
        module: 模块过滤
        hours: 时间范围（小时）
        limit: 返回条数限制
        coordinator: 模块协调器
    
    Returns:
        系统日志列表
    """
    try:
        # 计算时间范围
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        # 获取日志
        logs = await coordinator.get_logs(
            level=level,
            module=module,
            start_time=start_time,
            limit=limit
        )
        
        return SuccessResponse(
            data=logs,
            message=f"Retrieved {len(logs)} log entries"
        )
        
    except Exception as e:
        logger.error(f"Error getting system logs: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get system logs")

@router.get("/metrics", response_model=SuccessResponse[Dict[str, Any]])
async def get_system_metrics(
    include_history: bool = Query(False, description="是否包含历史数据"),
    hours: int = Query(24, ge=1, le=168, description="历史数据时间范围（小时）"),
    coordinator: ModuleCoordinator = Depends(get_module_coordinator)
):
    """
    获取系统指标
    
    Args:
        include_history: 是否包含历史数据
        hours: 历史数据时间范围
        coordinator: 模块协调器
    
    Returns:
        系统指标数据
    """
    try:
        # 获取当前指标
        current_metrics = await coordinator.get_current_metrics()
        
        result = {
            'current': current_metrics,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # 如果需要历史数据
        if include_history:
            start_time = datetime.utcnow() - timedelta(hours=hours)
            history_metrics = await coordinator.get_metrics_history(start_time)
            result['history'] = history_metrics
        
        return SuccessResponse(
            data=result,
            message="System metrics retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Error getting system metrics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get system metrics")