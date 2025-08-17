#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志调试系统 - 核心实现文件

根据 comprehensive_implementation_plan.md 文档重新实现

功能包括：
- 统一日志管理
- 性能监控
- 错误处理和异常恢复
- 调试信息收集
- 日志分析和报告
"""

import logging
import logging.handlers
import sys
import os
import time
import threading
import traceback
import json
import gzip
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from pathlib import Path
import psutil
import functools
from collections import defaultdict, deque
import asyncio
import inspect
import uuid
from contextlib import contextmanager
import weakref

class LogLevel(Enum):
    """日志级别"""
    TRACE = 5
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50

class LogFormat(Enum):
    """日志格式"""
    SIMPLE = "simple"
    DETAILED = "detailed"
    JSON = "json"
    STRUCTURED = "structured"

class MetricType(Enum):
    """指标类型"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"

@dataclass
class LogConfig:
    """日志配置"""
    level: LogLevel = LogLevel.INFO
    format_type: LogFormat = LogFormat.DETAILED
    console_output: bool = True
    file_output: bool = True
    file_path: str = "logs/evoforge.log"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    compress_backups: bool = True
    json_output: bool = False
    include_caller_info: bool = True
    include_thread_info: bool = True
    include_process_info: bool = True
    buffer_size: int = 1024
    flush_interval: float = 1.0
    
    def __post_init__(self):
        # 确保日志目录存在
        log_dir = Path(self.file_path).parent
        log_dir.mkdir(parents=True, exist_ok=True)

@dataclass
class PerformanceMetric:
    """性能指标"""
    name: str
    metric_type: MetricType
    value: float
    timestamp: datetime = field(default_factory=datetime.now)
    tags: Dict[str, str] = field(default_factory=dict)
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.metric_type.value,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags,
            "description": self.description
        }

@dataclass
class ErrorInfo:
    """错误信息"""
    error_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    error_type: str = ""
    message: str = ""
    traceback_info: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    module: str = ""
    function: str = ""
    line_number: int = 0
    context: Dict[str, Any] = field(default_factory=dict)
    severity: LogLevel = LogLevel.ERROR
    resolved: bool = False
    resolution_notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_id": self.error_id,
            "error_type": self.error_type,
            "message": self.message,
            "traceback": self.traceback_info,
            "timestamp": self.timestamp.isoformat(),
            "module": self.module,
            "function": self.function,
            "line_number": self.line_number,
            "context": self.context,
            "severity": self.severity.name,
            "resolved": self.resolved,
            "resolution_notes": self.resolution_notes
        }

class CustomFormatter(logging.Formatter):
    """自定义日志格式化器"""
    
    def __init__(self, config: LogConfig):
        self.config = config
        self.start_time = time.time()
        
        # 定义格式模板
        if config.format_type == LogFormat.SIMPLE:
            fmt = "%(asctime)s [%(levelname)s] %(message)s"
        elif config.format_type == LogFormat.DETAILED:
            fmt = "%(asctime)s [%(levelname)8s] %(name)s:%(lineno)d - %(message)s"
        elif config.format_type == LogFormat.STRUCTURED:
            fmt = "%(asctime)s [%(levelname)8s] [%(process)d:%(thread)d] %(name)s:%(funcName)s:%(lineno)d - %(message)s"
        else:
            fmt = "%(asctime)s [%(levelname)s] %(message)s"
        
        super().__init__(fmt, datefmt="%Y-%m-%d %H:%M:%S")
    
    def format(self, record):
        # 添加自定义字段
        record.relative_time = time.time() - self.start_time
        
        if self.config.include_caller_info:
            frame = inspect.currentframe()
            try:
                # 查找调用者信息
                caller_frame = frame
                for _ in range(10):  # 最多查找10层
                    caller_frame = caller_frame.f_back
                    if caller_frame is None:
                        break
                    
                    filename = caller_frame.f_code.co_filename
                    if not filename.endswith('logging.py') and not filename.endswith('logging_system.py'):
                        record.caller_file = os.path.basename(filename)
                        record.caller_line = caller_frame.f_lineno
                        record.caller_func = caller_frame.f_code.co_name
                        break
            finally:
                del frame
        
        if self.config.format_type == LogFormat.JSON:
            return self._format_json(record)
        else:
            return super().format(record)
    
    def _format_json(self, record) -> str:
        """JSON格式化"""
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        if self.config.include_thread_info:
            log_data["thread_id"] = record.thread
            log_data["thread_name"] = record.threadName
        
        if self.config.include_process_info:
            log_data["process_id"] = record.process
        
        if hasattr(record, 'caller_file'):
            log_data["caller"] = {
                "file": record.caller_file,
                "line": record.caller_line,
                "function": record.caller_func
            }
        
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False)

class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self._metrics: Dict[str, List[PerformanceMetric]] = defaultdict(list)
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._timers: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.RLock()
        self._start_time = time.time()
        
        # 系统资源监控
        self._system_monitor_active = False
        self._system_monitor_thread = None
        
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def start_system_monitoring(self, interval: float = 5.0):
        """启动系统资源监控"""
        if self._system_monitor_active:
            return
        
        self._system_monitor_active = True
        self._system_monitor_thread = threading.Thread(
            target=self._system_monitor_loop,
            args=(interval,),
            daemon=True
        )
        self._system_monitor_thread.start()
        self.logger.info(f"系统监控已启动，监控间隔: {interval}秒")
    
    def stop_system_monitoring(self):
        """停止系统资源监控"""
        self._system_monitor_active = False
        if self._system_monitor_thread:
            self._system_monitor_thread.join(timeout=1.0)
        self.logger.info("系统监控已停止")
    
    def _system_monitor_loop(self, interval: float):
        """系统监控循环"""
        while self._system_monitor_active:
            try:
                # CPU使用率
                cpu_percent = psutil.cpu_percent(interval=0.1)
                self.record_gauge("system.cpu.usage_percent", cpu_percent)
                
                # 内存使用情况
                memory = psutil.virtual_memory()
                self.record_gauge("system.memory.usage_percent", memory.percent)
                self.record_gauge("system.memory.available_mb", memory.available / 1024 / 1024)
                self.record_gauge("system.memory.used_mb", memory.used / 1024 / 1024)
                
                # 磁盘使用情况
                try:
                    # Windows使用C:，Unix使用/
                    disk_path = 'C:\\' if os.name == 'nt' else '/'
                    disk = psutil.disk_usage(disk_path)
                    self.record_gauge("system.disk.usage_percent", (disk.used / disk.total) * 100)
                    self.record_gauge("system.disk.free_gb", disk.free / 1024 / 1024 / 1024)
                except Exception as disk_error:
                    self.logger.warning(f"磁盘监控失败: {disk_error}")
                
                # 进程信息
                process = psutil.Process()
                self.record_gauge("process.memory.rss_mb", process.memory_info().rss / 1024 / 1024)
                self.record_gauge("process.memory.vms_mb", process.memory_info().vms / 1024 / 1024)
                self.record_gauge("process.cpu.percent", process.cpu_percent())
                self.record_gauge("process.threads.count", process.num_threads())
                
                # 运行时间
                uptime = time.time() - self._start_time
                self.record_gauge("system.uptime_seconds", uptime)
                
            except Exception as e:
                self.logger.error(f"系统监控错误: {e}")
            
            time.sleep(interval)
    
    def record_counter(self, name: str, value: float = 1.0, tags: Dict[str, str] = None):
        """记录计数器指标"""
        with self._lock:
            self._counters[name] += value
            metric = PerformanceMetric(
                name=name,
                metric_type=MetricType.COUNTER,
                value=self._counters[name],
                tags=tags or {}
            )
            self._metrics[name].append(metric)
            self._cleanup_old_metrics(name)
    
    def record_gauge(self, name: str, value: float, tags: Dict[str, str] = None):
        """记录仪表指标"""
        with self._lock:
            self._gauges[name] = value
            metric = PerformanceMetric(
                name=name,
                metric_type=MetricType.GAUGE,
                value=value,
                tags=tags or {}
            )
            self._metrics[name].append(metric)
            self._cleanup_old_metrics(name)
    
    def record_timer(self, name: str, duration: float, tags: Dict[str, str] = None):
        """记录计时器指标"""
        with self._lock:
            self._timers[name].append(duration)
            metric = PerformanceMetric(
                name=name,
                metric_type=MetricType.TIMER,
                value=duration,
                tags=tags or {}
            )
            self._metrics[name].append(metric)
            self._cleanup_old_metrics(name)
    
    def _cleanup_old_metrics(self, name: str, max_count: int = 1000):
        """清理旧的指标数据"""
        if len(self._metrics[name]) > max_count:
            self._metrics[name] = self._metrics[name][-max_count:]
    
    @contextmanager
    def timer(self, name: str, tags: Dict[str, str] = None):
        """计时器上下文管理器"""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.record_timer(name, duration, tags)
    
    def get_metrics(self, name: str = None, since: datetime = None) -> List[PerformanceMetric]:
        """获取指标数据"""
        with self._lock:
            if name:
                metrics = self._metrics.get(name, [])
            else:
                metrics = []
                for metric_list in self._metrics.values():
                    metrics.extend(metric_list)
            
            if since:
                metrics = [m for m in metrics if m.timestamp >= since]
            
            return metrics.copy()
    
    def get_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        with self._lock:
            summary = {
                "counters": self._counters.copy(),
                "gauges": self._gauges.copy(),
                "timers": {}
            }
            
            # 计算计时器统计
            for name, times in self._timers.items():
                if times:
                    summary["timers"][name] = {
                        "count": len(times),
                        "min": min(times),
                        "max": max(times),
                        "avg": sum(times) / len(times),
                        "total": sum(times)
                    }
            
            return summary

class ErrorTracker:
    """错误跟踪器"""
    
    def __init__(self, max_errors: int = 1000):
        self._errors: deque = deque(maxlen=max_errors)
        self._error_counts: Dict[str, int] = defaultdict(int)
        self._lock = threading.RLock()
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def track_error(self, error: Exception, context: Dict[str, Any] = None) -> ErrorInfo:
        """跟踪错误"""
        # 获取调用栈信息
        tb = traceback.extract_tb(error.__traceback__) if error.__traceback__ else []
        
        # 创建错误信息
        error_info = ErrorInfo(
            error_type=type(error).__name__,
            message=str(error),
            traceback_info=traceback.format_exc(),
            context=context or {},
            severity=self._determine_severity(error)
        )
        
        # 如果有调用栈，获取最后一个有效帧的信息
        if tb:
            last_frame = tb[-1]
            error_info.module = os.path.basename(last_frame.filename)
            error_info.function = last_frame.name
            error_info.line_number = last_frame.lineno
        
        with self._lock:
            self._errors.append(error_info)
            self._error_counts[error_info.error_type] += 1
        
        self.logger.error(f"错误已跟踪: {error_info.error_id} - {error_info.error_type}: {error_info.message}")
        return error_info
    
    def _determine_severity(self, error: Exception) -> LogLevel:
        """确定错误严重程度"""
        if isinstance(error, (SystemExit, KeyboardInterrupt)):
            return LogLevel.CRITICAL
        elif isinstance(error, (MemoryError, OSError)):
            return LogLevel.CRITICAL
        elif isinstance(error, (ValueError, TypeError, AttributeError)):
            return LogLevel.ERROR
        elif isinstance(error, (Warning, UserWarning)):
            return LogLevel.WARNING
        else:
            return LogLevel.ERROR
    
    def resolve_error(self, error_id: str, resolution_notes: str = ""):
        """标记错误为已解决"""
        with self._lock:
            for error in self._errors:
                if error.error_id == error_id:
                    error.resolved = True
                    error.resolution_notes = resolution_notes
                    self.logger.info(f"错误已解决: {error_id}")
                    return
        
        self.logger.warning(f"未找到错误: {error_id}")
    
    def get_errors(self, resolved: bool = None, since: datetime = None) -> List[ErrorInfo]:
        """获取错误列表"""
        with self._lock:
            errors = list(self._errors)
        
        if resolved is not None:
            errors = [e for e in errors if e.resolved == resolved]
        
        if since:
            errors = [e for e in errors if e.timestamp >= since]
        
        return errors
    
    def get_error_stats(self) -> Dict[str, Any]:
        """获取错误统计"""
        with self._lock:
            total_errors = len(self._errors)
            resolved_errors = sum(1 for e in self._errors if e.resolved)
            
            return {
                "total_errors": total_errors,
                "resolved_errors": resolved_errors,
                "unresolved_errors": total_errors - resolved_errors,
                "error_types": dict(self._error_counts),
                "recent_errors": [
                    e.to_dict() for e in list(self._errors)[-10:]
                ]
            }

class LoggingSystem:
    """日志系统"""
    
    def __init__(self, config: LogConfig = None):
        self.config = config or LogConfig()
        self._loggers: Dict[str, logging.Logger] = {}
        self._handlers: List[logging.Handler] = []
        self._performance_monitor = PerformanceMonitor()
        self._error_tracker = ErrorTracker()
        self._lock = threading.RLock()
        self._initialized = False
        
        # 初始化日志系统
        self._initialize_logging()
        
        self.logger = self.get_logger(self.__class__.__name__)
        self.logger.info("日志系统初始化完成")
    
    def _initialize_logging(self):
        """初始化日志系统"""
        if self._initialized:
            return
        
        # 设置根日志级别
        root_logger = logging.getLogger()
        root_logger.setLevel(self.config.level.value)
        
        # 创建格式化器
        formatter = CustomFormatter(self.config)
        
        # 控制台处理器
        if self.config.console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self.config.level.value)
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
            self._handlers.append(console_handler)
        
        # 文件处理器
        if self.config.file_output:
            file_handler = logging.handlers.RotatingFileHandler(
                filename=self.config.file_path,
                maxBytes=self.config.max_file_size,
                backupCount=self.config.backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(self.config.level.value)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
            self._handlers.append(file_handler)
        
        # 启动性能监控
        self._performance_monitor.start_system_monitoring()
        
        self._initialized = True
    
    def get_logger(self, name: str) -> logging.Logger:
        """获取日志记录器"""
        with self._lock:
            if name not in self._loggers:
                logger = logging.getLogger(name)
                self._loggers[name] = logger
            return self._loggers[name]
    
    def log_performance(self, name: str, metric_type: MetricType, value: float, tags: Dict[str, str] = None):
        """记录性能指标"""
        if metric_type == MetricType.COUNTER:
            self._performance_monitor.record_counter(name, value, tags)
        elif metric_type == MetricType.GAUGE:
            self._performance_monitor.record_gauge(name, value, tags)
        elif metric_type == MetricType.TIMER:
            self._performance_monitor.record_timer(name, value, tags)
    
    def track_error(self, error: Exception, context: Dict[str, Any] = None) -> ErrorInfo:
        """跟踪错误"""
        return self._error_tracker.track_error(error, context)
    
    def performance_timer(self, name: str, tags: Dict[str, str] = None):
        """性能计时器上下文管理器"""
        return self._performance_monitor.timer(name, tags)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        return self._performance_monitor.get_summary()
    
    def get_error_stats(self) -> Dict[str, Any]:
        """获取错误统计"""
        return self._error_tracker.get_error_stats()
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            "logging_config": {
                "level": self.config.level.name,
                "format": self.config.format_type.value,
                "console_output": self.config.console_output,
                "file_output": self.config.file_output,
                "file_path": self.config.file_path
            },
            "performance": self.get_performance_summary(),
            "errors": self.get_error_stats(),
            "loggers": list(self._loggers.keys()),
            "handlers": len(self._handlers)
        }
    
    def shutdown(self):
        """关闭日志系统"""
        self.logger.info("正在关闭日志系统")
        
        # 停止性能监控
        self._performance_monitor.stop_system_monitoring()
        
        # 关闭所有处理器
        for handler in self._handlers:
            handler.close()
        
        self._handlers.clear()
        self._loggers.clear()
        
        self.logger.info("日志系统已关闭")

# 装饰器函数
def log_performance(metric_name: str, metric_type: MetricType = MetricType.TIMER, tags: Dict[str, str] = None):
    """性能监控装饰器"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logging_system = get_logging_system()
            
            if metric_type == MetricType.TIMER:
                with logging_system.performance_timer(metric_name, tags):
                    return func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
                if metric_type == MetricType.COUNTER:
                    logging_system.log_performance(metric_name, MetricType.COUNTER, 1.0, tags)
                return result
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            logging_system = get_logging_system()
            
            if metric_type == MetricType.TIMER:
                with logging_system.performance_timer(metric_name, tags):
                    return await func(*args, **kwargs)
            else:
                result = await func(*args, **kwargs)
                if metric_type == MetricType.COUNTER:
                    logging_system.log_performance(metric_name, MetricType.COUNTER, 1.0, tags)
                return result
        
        return async_wrapper if inspect.iscoroutinefunction(func) else wrapper
    return decorator

def log_errors(logger_name: str = None, reraise: bool = True):
    """错误跟踪装饰器"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logging_system = get_logging_system()
                logger = logging_system.get_logger(logger_name or func.__module__)
                
                context = {
                    "function": func.__name__,
                    "args": str(args)[:200],  # 限制长度
                    "kwargs": str(kwargs)[:200]
                }
                
                error_info = logging_system.track_error(e, context)
                logger.error(f"函数执行失败: {func.__name__}, 错误ID: {error_info.error_id}")
                
                if reraise:
                    raise
                return None
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logging_system = get_logging_system()
                logger = logging_system.get_logger(logger_name or func.__module__)
                
                context = {
                    "function": func.__name__,
                    "args": str(args)[:200],
                    "kwargs": str(kwargs)[:200]
                }
                
                error_info = logging_system.track_error(e, context)
                logger.error(f"异步函数执行失败: {func.__name__}, 错误ID: {error_info.error_id}")
                
                if reraise:
                    raise
                return None
        
        return async_wrapper if inspect.iscoroutinefunction(func) else wrapper
    return decorator

# 全局日志系统实例
_logging_system: Optional[LoggingSystem] = None
_logging_system_lock = threading.Lock()

def get_logging_system(config: LogConfig = None) -> LoggingSystem:
    """获取全局日志系统实例"""
    global _logging_system
    
    with _logging_system_lock:
        if _logging_system is None:
            _logging_system = LoggingSystem(config)
        return _logging_system

def get_logger(name: str) -> logging.Logger:
    """获取日志记录器的便捷函数"""
    return get_logging_system().get_logger(name)

# 测试代码
if __name__ == "__main__":
    import asyncio
    
    @log_performance("test_function_timer")
    @log_errors("test_module")
    def test_function():
        """测试函数"""
        logger = get_logger("test_module")
        logger.info("测试函数开始执行")
        
        # 模拟一些工作
        time.sleep(0.1)
        
        # 记录一些指标
        logging_system = get_logging_system()
        logging_system.log_performance("test_counter", MetricType.COUNTER, 1.0)
        logging_system.log_performance("test_gauge", MetricType.GAUGE, 42.0)
        
        logger.info("测试函数执行完成")
        return "success"
    
    @log_performance("test_async_function_timer")
    @log_errors("test_async_module")
    async def test_async_function():
        """测试异步函数"""
        logger = get_logger("test_async_module")
        logger.info("异步测试函数开始执行")
        
        await asyncio.sleep(0.1)
        
        logger.info("异步测试函数执行完成")
        return "async_success"
    
    def test_error_function():
        """测试错误处理"""
        logger = get_logger("error_test")
        logger.info("错误测试开始")
        
        try:
            raise ValueError("这是一个测试错误")
        except Exception as e:
            logging_system = get_logging_system()
            error_info = logging_system.track_error(e, {"test_context": "error_handling"})
            logger.error(f"捕获到错误: {error_info.error_id}")
    
    async def main():
        """主测试函数"""
        # 配置日志系统
        config = LogConfig(
            level=LogLevel.DEBUG,
            format_type=LogFormat.DETAILED,
            console_output=True,
            file_output=True,
            file_path="logs/test.log"
        )
        
        logging_system = get_logging_system(config)
        logger = get_logger("main")
        
        logger.info("日志系统测试开始")
        
        # 测试同步函数
        result1 = test_function()
        logger.info(f"同步函数结果: {result1}")
        
        # 测试异步函数
        result2 = await test_async_function()
        logger.info(f"异步函数结果: {result2}")
        
        # 测试错误处理
        test_error_function()
        
        # 等待一段时间让系统监控收集数据
        await asyncio.sleep(2)
        
        # 获取系统状态
        status = logging_system.get_system_status()
        logger.info(f"系统状态: {json.dumps(status, indent=2, ensure_ascii=False)}")
        
        # 关闭日志系统
        logging_system.shutdown()
        
        print("日志系统测试完成")
    
    # 运行测试
    asyncio.run(main())