#!/usr/bin/env python3
"""
Multi-Provider Oracle管理器
实现负载均衡、故障转移和成本优化
"""
import asyncio
import random
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import structlog

from .base import BaseOracle, ProviderType, ProviderStatus, OracleConfig
from .openai_oracle import OpenAIOracle
from .siliconflow import OracleService as SiliconFlowOracle
from app.schemas.evaluation import OracleEvaluationResult
from app.core.config import settings

logger = structlog.get_logger()

class OracleManager:
    """Multi-Provider Oracle管理器"""
    
    def __init__(self):
        self.config = OracleConfig()
        self.oracles: Dict[ProviderType, BaseOracle] = {}
        self.current_provider_index = 0
        self.cost_tracker = CostTracker()
        self.health_check_interval = 300  # 5分钟
        self.last_health_check = datetime.now()
        
        # 初始化配置
        self._load_config()
        
    def _load_config(self):
        """加载Oracle配置"""
        # OpenAI配置
        if hasattr(settings, 'OPENAI_API_KEY') and settings.OPENAI_API_KEY:
            self.config.add_provider(ProviderType.OPENAI, {
                "api_key": settings.OPENAI_API_KEY,
                "model": getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini'),
                "base_url": getattr(settings, 'OPENAI_BASE_URL', 'https://api.openai.com/v1')
            })
        
        # SiliconFlow配置
        if hasattr(settings, 'SILICONFLOW_API_KEY') and settings.SILICONFLOW_API_KEY:
            self.config.add_provider(ProviderType.SILICONFLOW, {
                "api_key": settings.SILICONFLOW_API_KEY,
                "model": getattr(settings, 'SILICONFLOW_MODEL', 'deepseek-ai/deepseek-coder'),
                "base_url": getattr(settings, 'SILICONFLOW_BASE_URL', 'https://api.siliconflow.cn/v1')
            })
        
        # 设置负载均衡策略
        self.config.load_balancing_strategy = getattr(settings, 'ORACLE_LOAD_BALANCING', 'cost_optimized')
        self.config.cost_limit_per_hour = getattr(settings, 'ORACLE_COST_LIMIT_PER_HOUR', 10.0)
        
        logger.info("Oracle配置加载完成", 
                   providers=list(self.config.providers.keys()),
                   strategy=self.config.load_balancing_strategy)
    
    async def initialize(self):
        """初始化所有Oracle提供商"""
        logger.info("初始化Oracle提供商")
        
        for provider_type, config in self.config.providers.items():
            try:
                oracle = await self._create_oracle(provider_type, config)
                if oracle:
                    self.oracles[provider_type] = oracle
                    # 执行健康检查
                    await oracle.health_check()
                    logger.info(f"{provider_type.value} Oracle初始化完成", 
                               status=oracle.status.value)
                
            except Exception as e:
                logger.error(f"{provider_type.value} Oracle初始化失败", error=str(e))
        
        if not self.oracles:
            logger.warning("没有可用的Oracle提供商")
        else:
            logger.info("Oracle管理器初始化完成", 
                       available_providers=len(self.oracles))
    
    async def _create_oracle(self, provider_type: ProviderType, config: Dict[str, Any]) -> Optional[BaseOracle]:
        """创建Oracle实例"""
        try:
            if provider_type == ProviderType.OPENAI:
                return OpenAIOracle(config)
            elif provider_type == ProviderType.SILICONFLOW:
                # 适配现有的SiliconFlow实现
                oracle = SiliconFlowOracle()
                oracle.provider_type = provider_type
                oracle.config = config
                oracle.status = ProviderStatus.UNAVAILABLE
                return oracle
            else:
                logger.warning(f"不支持的Oracle提供商: {provider_type.value}")
                return None
                
        except Exception as e:
            logger.error(f"创建{provider_type.value} Oracle失败", error=str(e))
            return None
    
    async def evaluate_code(self, code: str, task_description: str) -> OracleEvaluationResult:
        """评估代码质量（使用最佳可用提供商）"""
        # 检查成本限制
        if self.cost_tracker.is_cost_limit_exceeded():
            logger.warning("Oracle成本限制已超出")
            return self._create_cost_limit_result()
        
        # 执行定期健康检查
        await self._periodic_health_check()
        
        # 选择最佳提供商
        oracle = await self._select_best_oracle()
        if not oracle:
            logger.error("没有可用的Oracle提供商")
            return self._create_no_provider_result()
        
        try:
            logger.info(f"使用{oracle.provider_type.value}评估代码")
            result = await oracle.evaluate_code(code, task_description)
            
            # 记录成本
            self.cost_tracker.record_cost(oracle.provider_type, result.cost)
            
            return result
            
        except Exception as e:
            logger.error(f"{oracle.provider_type.value}评估失败", error=str(e))
            
            # 尝试故障转移
            if self.config.fallback_enabled:
                return await self._fallback_evaluate(code, task_description, oracle.provider_type)
            else:
                return self._create_error_result(f"评估失败: {str(e)}")
    
    async def generate_code(self, task_description: str, context: Optional[str] = None) -> str:
        """生成代码（使用最佳可用提供商）"""
        # 检查成本限制
        if self.cost_tracker.is_cost_limit_exceeded():
            raise Exception("Oracle成本限制已超出")
        
        # 执行定期健康检查
        await self._periodic_health_check()
        
        # 选择最佳提供商
        oracle = await self._select_best_oracle()
        if not oracle:
            raise Exception("没有可用的Oracle提供商")
        
        try:
            logger.info(f"使用{oracle.provider_type.value}生成代码")
            code = await oracle.generate_code(task_description, context)
            return code
            
        except Exception as e:
            logger.error(f"{oracle.provider_type.value}代码生成失败", error=str(e))
            
            # 尝试故障转移
            if self.config.fallback_enabled:
                return await self._fallback_generate(task_description, context, oracle.provider_type)
            else:
                raise
    
    async def _select_best_oracle(self) -> Optional[BaseOracle]:
        """根据策略选择最佳Oracle"""
        available_oracles = [oracle for oracle in self.oracles.values() 
                           if oracle.is_available()]
        
        if not available_oracles:
            return None
        
        if self.config.load_balancing_strategy == "round_robin":
            return self._round_robin_selection(available_oracles)
        elif self.config.load_balancing_strategy == "cost_optimized":
            return self._cost_optimized_selection(available_oracles)
        elif self.config.load_balancing_strategy == "performance_optimized":
            return self._performance_optimized_selection(available_oracles)
        else:
            return random.choice(available_oracles)
    
    def _round_robin_selection(self, oracles: List[BaseOracle]) -> BaseOracle:
        """轮询选择"""
        oracle = oracles[self.current_provider_index % len(oracles)]
        self.current_provider_index += 1
        return oracle
    
    def _cost_optimized_selection(self, oracles: List[BaseOracle]) -> BaseOracle:
        """成本优化选择"""
        # 根据历史成本选择最便宜的提供商
        cost_scores = []
        for oracle in oracles:
            avg_cost = oracle.total_cost / max(oracle.successful_requests, 1)
            cost_scores.append((oracle, avg_cost))
        
        # 选择平均成本最低的
        cost_scores.sort(key=lambda x: x[1])
        return cost_scores[0][0]
    
    def _performance_optimized_selection(self, oracles: List[BaseOracle]) -> BaseOracle:
        """性能优化选择"""
        # 根据成功率选择最可靠的提供商
        performance_scores = []
        for oracle in oracles:
            success_rate = oracle.successful_requests / max(oracle.total_requests, 1)
            performance_scores.append((oracle, success_rate))
        
        # 选择成功率最高的
        performance_scores.sort(key=lambda x: x[1], reverse=True)
        return performance_scores[0][0]
    
    async def _fallback_evaluate(self, code: str, task_description: str, 
                                failed_provider: ProviderType) -> OracleEvaluationResult:
        """故障转移评估"""
        available_oracles = [oracle for oracle in self.oracles.values() 
                           if oracle.is_available() and oracle.provider_type != failed_provider]
        
        for oracle in available_oracles:
            try:
                logger.info(f"故障转移到{oracle.provider_type.value}")
                result = await oracle.evaluate_code(code, task_description)
                self.cost_tracker.record_cost(oracle.provider_type, result.cost)
                return result
                
            except Exception as e:
                logger.error(f"故障转移到{oracle.provider_type.value}失败", error=str(e))
                continue
        
        return self._create_error_result("所有Oracle提供商都不可用")
    
    async def _fallback_generate(self, task_description: str, context: Optional[str], 
                               failed_provider: ProviderType) -> str:
        """故障转移代码生成"""
        available_oracles = [oracle for oracle in self.oracles.values() 
                           if oracle.is_available() and oracle.provider_type != failed_provider]
        
        for oracle in available_oracles:
            try:
                logger.info(f"故障转移到{oracle.provider_type.value}")
                return await oracle.generate_code(task_description, context)
                
            except Exception as e:
                logger.error(f"故障转移到{oracle.provider_type.value}失败", error=str(e))
                continue
        
        raise Exception("所有Oracle提供商都不可用")
    
    async def _periodic_health_check(self):
        """定期健康检查"""
        now = datetime.now()
        if (now - self.last_health_check).total_seconds() > self.health_check_interval:
            logger.info("执行定期健康检查")
            
            for oracle in self.oracles.values():
                try:
                    await oracle.health_check()
                except Exception as e:
                    logger.error(f"{oracle.provider_type.value}健康检查失败", error=str(e))
            
            self.last_health_check = now
    
    def _create_cost_limit_result(self) -> OracleEvaluationResult:
        """创建成本限制结果"""
        return OracleEvaluationResult(
            scores={"correctness": 0, "quality": 0, "efficiency": 0, "innovation": 0},
            overall_score=0.0,
            feedback="Oracle成本限制已超出，请稍后再试",
            cost=0.0,
            input_tokens=0,
            output_tokens=0
        )
    
    def _create_no_provider_result(self) -> OracleEvaluationResult:
        """创建无提供商结果"""
        return OracleEvaluationResult(
            scores={"correctness": 0, "quality": 0, "efficiency": 0, "innovation": 0},
            overall_score=0.0,
            feedback="没有可用的Oracle提供商",
            cost=0.0,
            input_tokens=0,
            output_tokens=0
        )
    
    def _create_error_result(self, error_message: str) -> OracleEvaluationResult:
        """创建错误结果"""
        return OracleEvaluationResult(
            scores={"correctness": 0, "quality": 0, "efficiency": 0, "innovation": 0},
            overall_score=0.0,
            feedback=error_message,
            cost=0.0,
            input_tokens=0,
            output_tokens=0
        )
    
    def get_status(self) -> Dict[str, Any]:
        """获取Oracle管理器状态"""
        provider_stats = {}
        for provider_type, oracle in self.oracles.items():
            provider_stats[provider_type.value] = oracle.get_stats()
        
        return {
            "total_providers": len(self.oracles),
            "available_providers": len([o for o in self.oracles.values() if o.is_available()]),
            "load_balancing_strategy": self.config.load_balancing_strategy,
            "cost_limit_per_hour": self.config.cost_limit_per_hour,
            "current_hour_cost": self.cost_tracker.get_current_hour_cost(),
            "provider_stats": provider_stats,
            "cost_tracker": self.cost_tracker.get_stats()
        }
    
    async def close(self):
        """关闭所有Oracle连接"""
        logger.info("关闭Oracle管理器")
        for oracle in self.oracles.values():
            try:
                await oracle.close()
            except Exception as e:
                logger.error(f"关闭{oracle.provider_type.value} Oracle失败", error=str(e))

class CostTracker:
    """成本跟踪器"""
    
    def __init__(self):
        self.hourly_costs: Dict[datetime, Dict[ProviderType, float]] = {}
        self.total_cost = 0.0
        self.cost_limit_per_hour = 10.0
    
    def record_cost(self, provider: ProviderType, cost: float):
        """记录成本"""
        current_hour = datetime.now().replace(minute=0, second=0, microsecond=0)
        
        if current_hour not in self.hourly_costs:
            self.hourly_costs[current_hour] = {}
        
        if provider not in self.hourly_costs[current_hour]:
            self.hourly_costs[current_hour][provider] = 0.0
        
        self.hourly_costs[current_hour][provider] += cost
        self.total_cost += cost
        
        logger.debug("记录Oracle成本", 
                    provider=provider.value, 
                    cost=cost, 
                    hour_total=self.get_current_hour_cost())
    
    def get_current_hour_cost(self) -> float:
        """获取当前小时成本"""
        current_hour = datetime.now().replace(minute=0, second=0, microsecond=0)
        return sum(self.hourly_costs.get(current_hour, {}).values())
    
    def is_cost_limit_exceeded(self) -> bool:
        """检查是否超出成本限制"""
        return self.get_current_hour_cost() >= self.cost_limit_per_hour
    
    def get_stats(self) -> Dict[str, Any]:
        """获取成本统计"""
        return {
            "total_cost": self.total_cost,
            "current_hour_cost": self.get_current_hour_cost(),
            "cost_limit_per_hour": self.cost_limit_per_hour,
            "cost_limit_exceeded": self.is_cost_limit_exceeded()
        }

# 全局Oracle管理器实例
oracle_manager = OracleManager()