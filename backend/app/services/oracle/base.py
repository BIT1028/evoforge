#!/usr/bin/env python3
"""
Oracle服务基类和接口定义
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from enum import Enum
import structlog

from app.schemas.evaluation import OracleEvaluationResult

logger = structlog.get_logger()

class ProviderType(Enum):
    """LLM提供商类型"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    SILICONFLOW = "siliconflow"
    LOCAL = "local"

class ProviderStatus(Enum):
    """提供商状态"""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    ERROR = "error"
    RATE_LIMITED = "rate_limited"
    QUOTA_EXCEEDED = "quota_exceeded"

class BaseOracle(ABC):
    """Oracle服务基类"""
    
    def __init__(self, provider_type: ProviderType, config: Dict[str, Any]):
        self.provider_type = provider_type
        self.config = config
        self.status = ProviderStatus.UNAVAILABLE
        self.error_count = 0
        self.last_error: Optional[str] = None
        self.total_requests = 0
        self.successful_requests = 0
        self.total_cost = 0.0
        
    @abstractmethod
    async def evaluate_code(self, code: str, task_description: str) -> OracleEvaluationResult:
        """评估代码质量"""
        pass
    
    @abstractmethod
    async def generate_code(self, task_description: str, context: Optional[str] = None) -> str:
        """生成代码"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """健康检查"""
        pass
    
    @abstractmethod
    async def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        pass
    
    def update_status(self, status: ProviderStatus, error: Optional[str] = None):
        """更新提供商状态"""
        self.status = status
        if error:
            self.last_error = error
            self.error_count += 1
            logger.warning(f"{self.provider_type.value} Oracle状态更新", 
                         status=status.value, error=error)
        else:
            logger.info(f"{self.provider_type.value} Oracle状态更新", status=status.value)
    
    def record_request(self, success: bool, cost: float = 0.0):
        """记录请求统计"""
        self.total_requests += 1
        if success:
            self.successful_requests += 1
        self.total_cost += cost
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        success_rate = (self.successful_requests / self.total_requests 
                       if self.total_requests > 0 else 0)
        
        return {
            "provider_type": self.provider_type.value,
            "status": self.status.value,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "success_rate": success_rate,
            "error_count": self.error_count,
            "last_error": self.last_error,
            "total_cost": self.total_cost
        }
    
    def is_available(self) -> bool:
        """检查是否可用"""
        return self.status == ProviderStatus.AVAILABLE
    
    async def close(self):
        """关闭连接"""
        pass

class OracleConfig:
    """Oracle配置类"""
    
    def __init__(self):
        self.providers: Dict[ProviderType, Dict[str, Any]] = {}
        self.load_balancing_strategy = "round_robin"  # round_robin, cost_optimized, performance_optimized
        self.fallback_enabled = True
        self.max_retries = 3
        self.timeout = 30
        self.cost_limit_per_hour = 10.0  # USD
        
    def add_provider(self, provider_type: ProviderType, config: Dict[str, Any]):
        """添加提供商配置"""
        self.providers[provider_type] = config
        logger.info(f"添加Oracle提供商配置", provider=provider_type.value)
    
    def get_provider_config(self, provider_type: ProviderType) -> Optional[Dict[str, Any]]:
        """获取提供商配置"""
        return self.providers.get(provider_type)
    
    def get_enabled_providers(self) -> list[ProviderType]:
        """获取启用的提供商列表"""
        return list(self.providers.keys())