#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
错误处理和异常恢复系统 - 核心实现文件

根据 comprehensive_implementation_plan.md 文档重新实现

功能包括：
- 统一异常管理
- 自动恢复机制
- 故障诊断
- 错误分类和处理策略
- 系统健康检查
"""

import sys
import os
import time
import threading
import traceback
import json
import pickle
import signal
import weakref
from typing import Dict, List, Optional, Any, Callable, Union, Type, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from pathlib import Path
import logging
import functools
from collections import defaultdict, deque
import asyncio
import inspect
import uuid
from contextlib import contextmanager
import psutil
import gc
import resource
from concurrent.futures import ThreadPoolExecutor, Future
import queue

class ErrorSeverity(Enum):
    """错误严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    FATAL = "fatal"

class RecoveryStrategy(Enum):
    """恢复策略"""
    IGNORE = "ignore"  # 忽略错误
    RETRY = "retry"  # 重试操作
    FALLBACK = "fallback"  # 使用备用方案
    RESTART = "restart"  # 重启组件
    SHUTDOWN = "shutdown"  # 安全关闭
    ESCALATE = "escalate"  # 上报处理

class SystemState(Enum):
    """系统状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNSTABLE = "unstable"
    CRITICAL = "critical"
    FAILED = "failed"

class HealthCheckStatus(Enum):
    """健康检查状态"""
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    UNKNOWN = "unknown"

@dataclass
class ErrorPattern:
    """错误模式"""
    error_type: str
    message_pattern: str = ""
    module_pattern: str = ""
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    recovery_strategy: RecoveryStrategy = RecoveryStrategy.RETRY
    max_retries: int = 3
    retry_delay: float = 1.0
    escalation_threshold: int = 5
    description: str = ""
    
    def matches(self, error: Exception, module: str = "") -> bool:
        """检查错误是否匹配此模式"""
        # 检查错误类型
        if self.error_type != "*" and not isinstance(error, eval(self.error_type)):
            return False
        
        # 检查消息模式
        if self.message_pattern and self.message_pattern not in str(error):
            return False
        
        # 检查模块模式
        if self.module_pattern and self.module_pattern not in module:
            return False
        
        return True

@dataclass
class RecoveryAction:
    """恢复动作"""
    action_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    strategy: RecoveryStrategy = RecoveryStrategy.RETRY
    target_function: Optional[Callable] = None
    fallback_function: Optional[Callable] = None
    restart_component: Optional[str] = None
    max_attempts: int = 3
    delay_between_attempts: float = 1.0
    timeout: float = 30.0
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def execute(self, *args, **kwargs) -> Any:
        """执行恢复动作"""
        if self.strategy == RecoveryStrategy.RETRY and self.target_function:
            return self._retry_execution(*args, **kwargs)
        elif self.strategy == RecoveryStrategy.FALLBACK and self.fallback_function:
            return self.fallback_function(*args, **kwargs)
        elif self.strategy == RecoveryStrategy.RESTART:
            return self._restart_component()
        else:
            raise NotImplementedError(f"恢复策略 {self.strategy} 未实现")
    
    def _retry_execution(self, *args, **kwargs) -> Any:
        """重试执行"""
        last_exception = None
        
        for attempt in range(self.max_attempts):
            try:
                if attempt > 0:
                    time.sleep(self.delay_between_attempts)
                return self.target_function(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt == self.max_attempts - 1:
                    break
        
        if last_exception:
            raise last_exception
    
    def _restart_component(self) -> bool:
        """重启组件"""
        # 这里应该实现具体的组件重启逻辑
        # 目前只是一个占位符
        return True

@dataclass
class HealthCheck:
    """健康检查"""
    name: str
    check_function: Callable[[], bool]
    description: str = ""
    interval: float = 60.0  # 检查间隔（秒）
    timeout: float = 10.0  # 超时时间
    critical: bool = False  # 是否为关键检查
    enabled: bool = True
    last_check: Optional[datetime] = None
    last_status: HealthCheckStatus = HealthCheckStatus.UNKNOWN
    last_error: Optional[str] = None
    consecutive_failures: int = 0
    max_failures: int = 3
    
    def run_check(self) -> HealthCheckStatus:
        """运行健康检查"""
        if not self.enabled:
            return HealthCheckStatus.UNKNOWN
        
        try:
            start_time = time.time()
            result = self.check_function()
            duration = time.time() - start_time
            
            if duration > self.timeout:
                self.last_status = HealthCheckStatus.WARN
                self.last_error = f"检查超时: {duration:.2f}s > {self.timeout}s"
            elif result:
                self.last_status = HealthCheckStatus.PASS
                self.last_error = None
                self.consecutive_failures = 0
            else:
                self.last_status = HealthCheckStatus.FAIL
                self.last_error = "检查返回False"
                self.consecutive_failures += 1
            
        except Exception as e:
            self.last_status = HealthCheckStatus.FAIL
            self.last_error = str(e)
            self.consecutive_failures += 1
        
        self.last_check = datetime.now()
        return self.last_status
    
    def is_healthy(self) -> bool:
        """检查是否健康"""
        return self.last_status == HealthCheckStatus.PASS
    
    def is_critical_failure(self) -> bool:
        """检查是否为关键故障"""
        return (self.critical and 
                self.last_status == HealthCheckStatus.FAIL and 
                self.consecutive_failures >= self.max_failures)

@dataclass
class SystemDiagnostics:
    """系统诊断信息"""
    timestamp: datetime = field(default_factory=datetime.now)
    system_state: SystemState = SystemState.HEALTHY
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    disk_usage: float = 0.0
    active_threads: int = 0
    open_files: int = 0
    network_connections: int = 0
    error_rate: float = 0.0
    recovery_rate: float = 0.0
    health_checks: Dict[str, HealthCheckStatus] = field(default_factory=dict)
    recent_errors: List[str] = field(default_factory=list)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "system_state": self.system_state.value,
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
            "disk_usage": self.disk_usage,
            "active_threads": self.active_threads,
            "open_files": self.open_files,
            "network_connections": self.network_connections,
            "error_rate": self.error_rate,
            "recovery_rate": self.recovery_rate,
            "health_checks": {k: v.value for k, v in self.health_checks.items()},
            "recent_errors": self.recent_errors,
            "performance_metrics": self.performance_metrics
        }

class CircuitBreaker:
    """断路器模式实现"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0, expected_exception: Type[Exception] = Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self._failure_count = 0
        self._last_failure_time = None
        self._state = "closed"  # closed, open, half_open
        self._lock = threading.RLock()
        
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def __call__(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with self._lock:
                if self._state == "open":
                    if self._should_attempt_reset():
                        self._state = "half_open"
                        self.logger.info(f"断路器进入半开状态: {func.__name__}")
                    else:
                        raise Exception(f"断路器开启，拒绝调用: {func.__name__}")
                
                try:
                    result = func(*args, **kwargs)
                    self._on_success()
                    return result
                except self.expected_exception as e:
                    self._on_failure()
                    raise
        
        return wrapper
    
    def _should_attempt_reset(self) -> bool:
        """检查是否应该尝试重置"""
        return (self._last_failure_time and 
                time.time() - self._last_failure_time >= self.recovery_timeout)
    
    def _on_success(self):
        """成功时的处理"""
        self._failure_count = 0
        self._state = "closed"
        self.logger.debug("断路器重置为关闭状态")
    
    def _on_failure(self):
        """失败时的处理"""
        self._failure_count += 1
        self._last_failure_time = time.time()
        
        if self._failure_count >= self.failure_threshold:
            self._state = "open"
            self.logger.warning(f"断路器开启，失败次数: {self._failure_count}")

class ErrorHandler:
    """错误处理器"""
    
    def __init__(self):
        self._error_patterns: List[ErrorPattern] = []
        self._recovery_actions: Dict[str, RecoveryAction] = {}
        self._error_history: deque = deque(maxlen=1000)
        self._recovery_history: deque = deque(maxlen=1000)
        self._health_checks: Dict[str, HealthCheck] = {}
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        
        self._lock = threading.RLock()
        self._health_check_thread = None
        self._health_check_active = False
        self._diagnostics_history: deque = deque(maxlen=100)
        
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 注册默认错误模式
        self._register_default_patterns()
        
        # 注册默认健康检查
        self._register_default_health_checks()
        
        # 启动健康检查
        self.start_health_monitoring()
    
    def _register_default_patterns(self):
        """注册默认错误模式"""
        default_patterns = [
            ErrorPattern(
                error_type="ConnectionError",
                severity=ErrorSeverity.HIGH,
                recovery_strategy=RecoveryStrategy.RETRY,
                max_retries=3,
                retry_delay=2.0,
                description="网络连接错误"
            ),
            ErrorPattern(
                error_type="TimeoutError",
                severity=ErrorSeverity.MEDIUM,
                recovery_strategy=RecoveryStrategy.RETRY,
                max_retries=2,
                retry_delay=1.0,
                description="超时错误"
            ),
            ErrorPattern(
                error_type="MemoryError",
                severity=ErrorSeverity.CRITICAL,
                recovery_strategy=RecoveryStrategy.RESTART,
                description="内存不足错误"
            ),
            ErrorPattern(
                error_type="KeyboardInterrupt",
                severity=ErrorSeverity.FATAL,
                recovery_strategy=RecoveryStrategy.SHUTDOWN,
                description="用户中断"
            ),
            ErrorPattern(
                error_type="SystemExit",
                severity=ErrorSeverity.FATAL,
                recovery_strategy=RecoveryStrategy.SHUTDOWN,
                description="系统退出"
            )
        ]
        
        for pattern in default_patterns:
            self.register_error_pattern(pattern)
    
    def _register_default_health_checks(self):
        """注册默认健康检查"""
        # CPU使用率检查
        self.register_health_check(HealthCheck(
            name="cpu_usage",
            check_function=lambda: psutil.cpu_percent(interval=0.1) < 90.0,
            description="CPU使用率检查",
            interval=30.0,
            critical=True
        ))
        
        # 内存使用率检查
        self.register_health_check(HealthCheck(
            name="memory_usage",
            check_function=lambda: psutil.virtual_memory().percent < 90.0,
            description="内存使用率检查",
            interval=30.0,
            critical=True
        ))
        
        # 磁盘使用率检查
        self.register_health_check(HealthCheck(
            name="disk_usage",
            check_function=lambda: psutil.disk_usage('/').percent < 95.0,
            description="磁盘使用率检查",
            interval=60.0,
            critical=False
        ))
        
        # 线程数检查
        self.register_health_check(HealthCheck(
            name="thread_count",
            check_function=lambda: threading.active_count() < 100,
            description="活跃线程数检查",
            interval=30.0,
            critical=False
        ))
    
    def register_error_pattern(self, pattern: ErrorPattern):
        """注册错误模式"""
        with self._lock:
            self._error_patterns.append(pattern)
            self.logger.debug(f"注册错误模式: {pattern.error_type}")
    
    def register_recovery_action(self, action: RecoveryAction):
        """注册恢复动作"""
        with self._lock:
            self._recovery_actions[action.action_id] = action
            self.logger.debug(f"注册恢复动作: {action.action_id}")
    
    def register_health_check(self, health_check: HealthCheck):
        """注册健康检查"""
        with self._lock:
            self._health_checks[health_check.name] = health_check
            self.logger.debug(f"注册健康检查: {health_check.name}")
    
    def handle_error(self, error: Exception, context: Dict[str, Any] = None) -> Any:
        """处理错误"""
        context = context or {}
        module = context.get("module", "")
        
        # 记录错误
        error_record = {
            "timestamp": datetime.now(),
            "error_type": type(error).__name__,
            "message": str(error),
            "module": module,
            "context": context,
            "traceback": traceback.format_exc()
        }
        
        with self._lock:
            self._error_history.append(error_record)
        
        self.logger.error(f"处理错误: {type(error).__name__}: {error}")
        
        # 查找匹配的错误模式
        matching_pattern = self._find_matching_pattern(error, module)
        
        if matching_pattern:
            self.logger.info(f"找到匹配的错误模式: {matching_pattern.error_type}")
            return self._execute_recovery_strategy(error, matching_pattern, context)
        else:
            self.logger.warning(f"未找到匹配的错误模式，使用默认处理: {type(error).__name__}")
            return self._default_error_handling(error, context)
    
    def _find_matching_pattern(self, error: Exception, module: str) -> Optional[ErrorPattern]:
        """查找匹配的错误模式"""
        for pattern in self._error_patterns:
            if pattern.matches(error, module):
                return pattern
        return None
    
    def _execute_recovery_strategy(self, error: Exception, pattern: ErrorPattern, context: Dict[str, Any]) -> Any:
        """执行恢复策略"""
        strategy = pattern.recovery_strategy
        
        recovery_record = {
            "timestamp": datetime.now(),
            "error_type": type(error).__name__,
            "strategy": strategy.value,
            "pattern": pattern.error_type,
            "success": False,
            "attempts": 0
        }
        
        try:
            if strategy == RecoveryStrategy.IGNORE:
                recovery_record["success"] = True
                self.logger.info("忽略错误")
                return None
            
            elif strategy == RecoveryStrategy.RETRY:
                return self._retry_operation(error, pattern, context, recovery_record)
            
            elif strategy == RecoveryStrategy.FALLBACK:
                return self._execute_fallback(error, pattern, context, recovery_record)
            
            elif strategy == RecoveryStrategy.RESTART:
                return self._restart_component(error, pattern, context, recovery_record)
            
            elif strategy == RecoveryStrategy.SHUTDOWN:
                return self._safe_shutdown(error, pattern, context, recovery_record)
            
            elif strategy == RecoveryStrategy.ESCALATE:
                return self._escalate_error(error, pattern, context, recovery_record)
            
            else:
                raise NotImplementedError(f"恢复策略 {strategy} 未实现")
        
        finally:
            with self._lock:
                self._recovery_history.append(recovery_record)
    
    def _retry_operation(self, error: Exception, pattern: ErrorPattern, context: Dict[str, Any], recovery_record: Dict) -> Any:
        """重试操作"""
        target_function = context.get("target_function")
        args = context.get("args", ())
        kwargs = context.get("kwargs", {})
        
        if not target_function:
            self.logger.warning("重试策略需要target_function，但未提供")
            return None
        
        last_exception = error
        
        for attempt in range(pattern.max_retries):
            recovery_record["attempts"] = attempt + 1
            
            try:
                if attempt > 0:
                    time.sleep(pattern.retry_delay)
                    self.logger.info(f"重试操作，第 {attempt + 1} 次尝试")
                
                result = target_function(*args, **kwargs)
                recovery_record["success"] = True
                self.logger.info(f"重试成功，尝试次数: {attempt + 1}")
                return result
            
            except Exception as e:
                last_exception = e
                self.logger.warning(f"重试失败，第 {attempt + 1} 次尝试: {e}")
        
        self.logger.error(f"重试失败，已达到最大重试次数: {pattern.max_retries}")
        raise last_exception
    
    def _execute_fallback(self, error: Exception, pattern: ErrorPattern, context: Dict[str, Any], recovery_record: Dict) -> Any:
        """执行备用方案"""
        fallback_function = context.get("fallback_function")
        args = context.get("args", ())
        kwargs = context.get("kwargs", {})
        
        if not fallback_function:
            self.logger.warning("备用策略需要fallback_function，但未提供")
            return None
        
        try:
            self.logger.info("执行备用方案")
            result = fallback_function(*args, **kwargs)
            recovery_record["success"] = True
            recovery_record["attempts"] = 1
            return result
        except Exception as e:
            self.logger.error(f"备用方案执行失败: {e}")
            raise
    
    def _restart_component(self, error: Exception, pattern: ErrorPattern, context: Dict[str, Any], recovery_record: Dict) -> Any:
        """重启组件"""
        component_name = context.get("component_name", "unknown")
        
        try:
            self.logger.warning(f"重启组件: {component_name}")
            # 这里应该实现具体的组件重启逻辑
            # 目前只是一个占位符
            recovery_record["success"] = True
            recovery_record["attempts"] = 1
            return True
        except Exception as e:
            self.logger.error(f"组件重启失败: {e}")
            raise
    
    def _safe_shutdown(self, error: Exception, pattern: ErrorPattern, context: Dict[str, Any], recovery_record: Dict) -> Any:
        """安全关闭"""
        try:
            self.logger.critical("执行安全关闭")
            # 这里应该实现安全关闭逻辑
            recovery_record["success"] = True
            recovery_record["attempts"] = 1
            
            # 发送关闭信号
            os.kill(os.getpid(), signal.SIGTERM)
            return True
        except Exception as e:
            self.logger.error(f"安全关闭失败: {e}")
            raise
    
    def _escalate_error(self, error: Exception, pattern: ErrorPattern, context: Dict[str, Any], recovery_record: Dict) -> Any:
        """上报错误"""
        try:
            self.logger.critical(f"上报错误: {type(error).__name__}: {error}")
            # 这里应该实现错误上报逻辑
            recovery_record["success"] = True
            recovery_record["attempts"] = 1
            return True
        except Exception as e:
            self.logger.error(f"错误上报失败: {e}")
            raise
    
    def _default_error_handling(self, error: Exception, context: Dict[str, Any]) -> Any:
        """默认错误处理"""
        self.logger.warning(f"使用默认错误处理: {type(error).__name__}")
        
        # 对于一些常见错误类型，提供基本的处理
        if isinstance(error, (ConnectionError, TimeoutError)):
            # 简单重试一次
            target_function = context.get("target_function")
            if target_function:
                try:
                    time.sleep(1.0)
                    return target_function(*context.get("args", ()), **context.get("kwargs", {}))
                except Exception:
                    pass
        
        # 如果无法处理，重新抛出异常
        raise error
    
    def start_health_monitoring(self, interval: float = 30.0):
        """启动健康监控"""
        if self._health_check_active:
            return
        
        self._health_check_active = True
        self._health_check_thread = threading.Thread(
            target=self._health_check_loop,
            args=(interval,),
            daemon=True
        )
        self._health_check_thread.start()
        self.logger.info(f"健康监控已启动，检查间隔: {interval}秒")
    
    def stop_health_monitoring(self):
        """停止健康监控"""
        self._health_check_active = False
        if self._health_check_thread:
            self._health_check_thread.join(timeout=5.0)
        self.logger.info("健康监控已停止")
    
    def _health_check_loop(self, interval: float):
        """健康检查循环"""
        while self._health_check_active:
            try:
                self._run_health_checks()
                self._collect_diagnostics()
            except Exception as e:
                self.logger.error(f"健康检查循环错误: {e}")
            
            time.sleep(interval)
    
    def _run_health_checks(self):
        """运行所有健康检查"""
        with self._lock:
            health_checks = list(self._health_checks.values())
        
        for health_check in health_checks:
            try:
                # 检查是否需要运行
                if (health_check.last_check is None or 
                    (datetime.now() - health_check.last_check).total_seconds() >= health_check.interval):
                    
                    status = health_check.run_check()
                    
                    if status == HealthCheckStatus.FAIL:
                        self.logger.warning(f"健康检查失败: {health_check.name} - {health_check.last_error}")
                        
                        if health_check.is_critical_failure():
                            self.logger.critical(f"关键健康检查失败: {health_check.name}")
                            # 这里可以触发紧急恢复措施
                    
                    elif status == HealthCheckStatus.WARN:
                        self.logger.warning(f"健康检查警告: {health_check.name} - {health_check.last_error}")
            
            except Exception as e:
                self.logger.error(f"健康检查执行错误 {health_check.name}: {e}")
    
    def _collect_diagnostics(self):
        """收集系统诊断信息"""
        try:
            # 收集系统资源信息
            cpu_usage = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # 收集进程信息
            process = psutil.Process()
            
            # 计算错误率和恢复率
            recent_errors = [e for e in self._error_history 
                           if (datetime.now() - e["timestamp"]).total_seconds() < 300]  # 5分钟内
            recent_recoveries = [r for r in self._recovery_history 
                               if (datetime.now() - r["timestamp"]).total_seconds() < 300]
            
            error_rate = len(recent_errors) / 5.0  # 每分钟错误数
            recovery_rate = sum(1 for r in recent_recoveries if r["success"]) / max(len(recent_recoveries), 1)
            
            # 确定系统状态
            system_state = self._determine_system_state(cpu_usage, memory.percent, error_rate)
            
            # 创建诊断信息
            diagnostics = SystemDiagnostics(
                system_state=system_state,
                cpu_usage=cpu_usage,
                memory_usage=memory.percent,
                disk_usage=disk.percent,
                active_threads=threading.active_count(),
                open_files=len(process.open_files()),
                network_connections=len(process.connections()),
                error_rate=error_rate,
                recovery_rate=recovery_rate,
                health_checks={name: hc.last_status for name, hc in self._health_checks.items()},
                recent_errors=[e["error_type"] + ": " + e["message"] for e in recent_errors[-5:]],
                performance_metrics={
                    "process_memory_mb": process.memory_info().rss / 1024 / 1024,
                    "process_cpu_percent": process.cpu_percent()
                }
            )
            
            with self._lock:
                self._diagnostics_history.append(diagnostics)
        
        except Exception as e:
            self.logger.error(f"收集诊断信息失败: {e}")
    
    def _determine_system_state(self, cpu_usage: float, memory_usage: float, error_rate: float) -> SystemState:
        """确定系统状态"""
        # 检查关键健康检查
        critical_failures = sum(1 for hc in self._health_checks.values() 
                              if hc.critical and hc.is_critical_failure())
        
        if critical_failures > 0:
            return SystemState.CRITICAL
        
        if cpu_usage > 90 or memory_usage > 90 or error_rate > 10:
            return SystemState.CRITICAL
        elif cpu_usage > 80 or memory_usage > 80 or error_rate > 5:
            return SystemState.UNSTABLE
        elif cpu_usage > 70 or memory_usage > 70 or error_rate > 2:
            return SystemState.DEGRADED
        else:
            return SystemState.HEALTHY
    
    def get_circuit_breaker(self, name: str, **kwargs) -> CircuitBreaker:
        """获取断路器"""
        with self._lock:
            if name not in self._circuit_breakers:
                self._circuit_breakers[name] = CircuitBreaker(**kwargs)
            return self._circuit_breakers[name]
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """获取错误统计"""
        with self._lock:
            total_errors = len(self._error_history)
            total_recoveries = len(self._recovery_history)
            successful_recoveries = sum(1 for r in self._recovery_history if r["success"])
            
            # 错误类型统计
            error_types = defaultdict(int)
            for error in self._error_history:
                error_types[error["error_type"]] += 1
            
            # 恢复策略统计
            recovery_strategies = defaultdict(int)
            for recovery in self._recovery_history:
                recovery_strategies[recovery["strategy"]] += 1
            
            return {
                "total_errors": total_errors,
                "total_recoveries": total_recoveries,
                "successful_recoveries": successful_recoveries,
                "recovery_success_rate": successful_recoveries / max(total_recoveries, 1),
                "error_types": dict(error_types),
                "recovery_strategies": dict(recovery_strategies),
                "registered_patterns": len(self._error_patterns),
                "registered_actions": len(self._recovery_actions),
                "health_checks": len(self._health_checks),
                "circuit_breakers": len(self._circuit_breakers)
            }
    
    def get_current_diagnostics(self) -> Optional[SystemDiagnostics]:
        """获取当前诊断信息"""
        with self._lock:
            return self._diagnostics_history[-1] if self._diagnostics_history else None
    
    def get_health_status(self) -> Dict[str, Any]:
        """获取健康状态"""
        with self._lock:
            health_status = {}
            for name, health_check in self._health_checks.items():
                health_status[name] = {
                    "status": health_check.last_status.value,
                    "last_check": health_check.last_check.isoformat() if health_check.last_check else None,
                    "last_error": health_check.last_error,
                    "consecutive_failures": health_check.consecutive_failures,
                    "critical": health_check.critical,
                    "enabled": health_check.enabled
                }
            
            return health_status
    
    def shutdown(self):
        """关闭错误处理器"""
        self.logger.info("正在关闭错误处理器")
        self.stop_health_monitoring()
        self.logger.info("错误处理器已关闭")

# 装饰器函数
def with_error_handling(error_handler: ErrorHandler = None, 
                       recovery_strategy: RecoveryStrategy = RecoveryStrategy.RETRY,
                       max_retries: int = 3,
                       fallback_function: Callable = None):
    """错误处理装饰器"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            handler = error_handler or get_error_handler()
            
            context = {
                "target_function": func,
                "args": args,
                "kwargs": kwargs,
                "module": func.__module__,
                "fallback_function": fallback_function
            }
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                return handler.handle_error(e, context)
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            handler = error_handler or get_error_handler()
            
            context = {
                "target_function": func,
                "args": args,
                "kwargs": kwargs,
                "module": func.__module__,
                "fallback_function": fallback_function
            }
            
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                return handler.handle_error(e, context)
        
        return async_wrapper if inspect.iscoroutinefunction(func) else wrapper
    return decorator

def circuit_breaker(failure_threshold: int = 5, recovery_timeout: float = 60.0, expected_exception: Type[Exception] = Exception):
    """断路器装饰器"""
    def decorator(func):
        breaker = CircuitBreaker(failure_threshold, recovery_timeout, expected_exception)
        return breaker(func)
    return decorator

# 全局错误处理器实例
_error_handler: Optional[ErrorHandler] = None
_error_handler_lock = threading.Lock()

def get_error_handler() -> ErrorHandler:
    """获取全局错误处理器实例"""
    global _error_handler
    
    with _error_handler_lock:
        if _error_handler is None:
            _error_handler = ErrorHandler()
        return _error_handler

# 测试代码
if __name__ == "__main__":
    import asyncio
    
    @with_error_handling(recovery_strategy=RecoveryStrategy.RETRY, max_retries=2)
    def test_function_with_retry():
        """测试重试功能"""
        import random
        if random.random() < 0.7:  # 70%概率失败
            raise ConnectionError("模拟连接错误")
        return "成功"
    
    @circuit_breaker(failure_threshold=3, recovery_timeout=5.0)
    def test_function_with_circuit_breaker():
        """测试断路器功能"""
        import random
        if random.random() < 0.8:  # 80%概率失败
            raise ValueError("模拟错误")
        return "成功"
    
    def test_fallback():
        """备用函数"""
        return "备用结果"
    
    @with_error_handling(recovery_strategy=RecoveryStrategy.FALLBACK, fallback_function=test_fallback)
    def test_function_with_fallback():
        """测试备用方案"""
        raise RuntimeError("总是失败")
    
    def main():
        """主测试函数"""
        error_handler = get_error_handler()
        
        print("错误处理系统测试开始")
        
        # 测试重试功能
        print("\n测试重试功能:")
        for i in range(5):
            try:
                result = test_function_with_retry()
                print(f"第{i+1}次调用成功: {result}")
            except Exception as e:
                print(f"第{i+1}次调用失败: {e}")
        
        # 测试断路器功能
        print("\n测试断路器功能:")
        for i in range(10):
            try:
                result = test_function_with_circuit_breaker()
                print(f"第{i+1}次调用成功: {result}")
            except Exception as e:
                print(f"第{i+1}次调用失败: {e}")
        
        # 测试备用方案
        print("\n测试备用方案:")
        try:
            result = test_function_with_fallback()
            print(f"备用方案结果: {result}")
        except Exception as e:
            print(f"备用方案失败: {e}")
        
        # 等待健康检查运行
        time.sleep(5)
        
        # 获取统计信息
        print("\n错误统计:")
        stats = error_handler.get_error_statistics()
        print(json.dumps(stats, indent=2, ensure_ascii=False))
        
        print("\n健康状态:")
        health = error_handler.get_health_status()
        print(json.dumps(health, indent=2, ensure_ascii=False))
        
        print("\n当前诊断:")
        diagnostics = error_handler.get_current_diagnostics()
        if diagnostics:
            print(json.dumps(diagnostics.to_dict(), indent=2, ensure_ascii=False))
        
        # 关闭错误处理器
        error_handler.shutdown()
        
        print("\n错误处理系统测试完成")
    
    # 运行测试
    main()