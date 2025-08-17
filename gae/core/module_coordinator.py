#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模块协调器 - 核心实现文件

根据 comprehensive_implementation_plan.md 文档重新实现

功能包括：
- 模块生命周期管理
- 依赖关系解析
- 模块间通信
- 事件总线系统
- 资源协调
"""

import asyncio
import logging
import threading
import weakref
from typing import Dict, List, Set, Optional, Any, Callable, Type, Union
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import inspect
from datetime import datetime
import traceback
import uuid
from collections import defaultdict, deque
import time

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class ModuleState(Enum):
    """模块状态枚举"""
    UNINITIALIZED = "uninitialized"  # 未初始化
    INITIALIZING = "initializing"    # 初始化中
    INITIALIZED = "initialized"      # 已初始化
    STARTING = "starting"            # 启动中
    RUNNING = "running"              # 运行中
    STOPPING = "stopping"            # 停止中
    STOPPED = "stopped"              # 已停止
    ERROR = "error"                  # 错误状态
    DESTROYED = "destroyed"          # 已销毁

class EventPriority(Enum):
    """事件优先级"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3

class ModuleType(Enum):
    """模块类型"""
    CORE = "core"                    # 核心模块
    SERVICE = "service"              # 服务模块
    PLUGIN = "plugin"                # 插件模块
    EXTENSION = "extension"          # 扩展模块

@dataclass
class ModuleInfo:
    """模块信息"""
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    module_type: ModuleType = ModuleType.SERVICE
    dependencies: List[str] = field(default_factory=list)
    optional_dependencies: List[str] = field(default_factory=list)
    provides: List[str] = field(default_factory=list)
    priority: int = 0
    auto_start: bool = True
    singleton: bool = True
    
    def __post_init__(self):
        if not self.name:
            raise ValueError("模块名称不能为空")

@dataclass
class Event:
    """事件数据结构"""
    event_type: str
    source: str
    data: Any = None
    priority: EventPriority = EventPriority.NORMAL
    timestamp: datetime = field(default_factory=datetime.now)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    target: Optional[str] = None  # 目标模块，None表示广播
    
    def __post_init__(self):
        if not self.event_type:
            raise ValueError("事件类型不能为空")
        if not self.source:
            raise ValueError("事件源不能为空")

class IModule(ABC):
    """模块接口"""
    
    def __init__(self, coordinator: 'ModuleCoordinator'):
        self.coordinator = coordinator
        self.state = ModuleState.UNINITIALIZED
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self._event_handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._lock = threading.RLock()
    
    @property
    @abstractmethod
    def module_info(self) -> ModuleInfo:
        """获取模块信息"""
        pass
    
    @abstractmethod
    async def initialize(self) -> bool:
        """初始化模块"""
        pass
    
    @abstractmethod
    async def start(self) -> bool:
        """启动模块"""
        pass
    
    @abstractmethod
    async def stop(self) -> bool:
        """停止模块"""
        pass
    
    @abstractmethod
    async def destroy(self) -> bool:
        """销毁模块"""
        pass
    
    def get_state(self) -> ModuleState:
        """获取模块状态"""
        with self._lock:
            return self.state
    
    def set_state(self, state: ModuleState):
        """设置模块状态"""
        with self._lock:
            old_state = self.state
            self.state = state
            self.logger.debug(f"模块状态变更: {old_state.value} -> {state.value}")
            
            # 发送状态变更事件
            self.coordinator.emit_event(Event(
                event_type="module.state_changed",
                source=self.module_info.name,
                data={
                    "old_state": old_state.value,
                    "new_state": state.value
                }
            ))
    
    def register_event_handler(self, event_type: str, handler: Callable):
        """注册事件处理器"""
        with self._lock:
            self._event_handlers[event_type].append(handler)
            self.logger.debug(f"注册事件处理器: {event_type}")
    
    def unregister_event_handler(self, event_type: str, handler: Callable):
        """注销事件处理器"""
        with self._lock:
            if event_type in self._event_handlers:
                if handler in self._event_handlers[event_type]:
                    self._event_handlers[event_type].remove(handler)
                    self.logger.debug(f"注销事件处理器: {event_type}")
    
    async def handle_event(self, event: Event):
        """处理事件"""
        with self._lock:
            handlers = self._event_handlers.get(event.event_type, [])
        
        for handler in handlers:
            try:
                if inspect.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                self.logger.error(f"事件处理器执行失败: {e}")
                self.logger.debug(traceback.format_exc())
    
    def emit_event(self, event: Event):
        """发送事件"""
        self.coordinator.emit_event(event)
    
    def get_dependency(self, module_name: str) -> Optional['IModule']:
        """获取依赖模块"""
        return self.coordinator.get_module(module_name)
    
    def is_dependency_available(self, module_name: str) -> bool:
        """检查依赖模块是否可用"""
        module = self.coordinator.get_module(module_name)
        return module is not None and module.get_state() == ModuleState.RUNNING

class EventBus:
    """事件总线"""
    
    def __init__(self):
        self._subscribers: Dict[str, List[weakref.ref]] = defaultdict(list)
        self._event_queue = deque()
        self._processing = False
        self._lock = threading.RLock()
        self._stats = {
            "events_emitted": 0,
            "events_processed": 0,
            "events_failed": 0
        }
        logger.debug("事件总线初始化完成")
    
    def subscribe(self, event_type: str, handler: Callable, module: IModule):
        """订阅事件"""
        with self._lock:
            # 使用弱引用避免循环引用
            module_ref = weakref.ref(module)
            handler_info = (handler, module_ref)
            self._subscribers[event_type].append(weakref.ref(handler_info))
            logger.debug(f"模块 {module.module_info.name} 订阅事件: {event_type}")
    
    def unsubscribe(self, event_type: str, handler: Callable, module: IModule):
        """取消订阅事件"""
        with self._lock:
            if event_type in self._subscribers:
                # 清理失效的弱引用
                self._cleanup_dead_references(event_type)
                
                # 移除指定的处理器
                to_remove = []
                for ref in self._subscribers[event_type]:
                    handler_info = ref()
                    if handler_info:
                        h, m_ref = handler_info
                        m = m_ref()
                        if h == handler and m == module:
                            to_remove.append(ref)
                
                for ref in to_remove:
                    self._subscribers[event_type].remove(ref)
                
                logger.debug(f"模块 {module.module_info.name} 取消订阅事件: {event_type}")
    
    def emit(self, event: Event):
        """发送事件"""
        with self._lock:
            self._event_queue.append(event)
            self._stats["events_emitted"] += 1
            logger.debug(f"事件已加入队列: {event.event_type} from {event.source}")
        
        # 异步处理事件
        asyncio.create_task(self._process_events())
    
    async def _process_events(self):
        """处理事件队列"""
        if self._processing:
            return
        
        self._processing = True
        try:
            while self._event_queue:
                with self._lock:
                    if not self._event_queue:
                        break
                    event = self._event_queue.popleft()
                
                await self._dispatch_event(event)
        finally:
            self._processing = False
    
    async def _dispatch_event(self, event: Event):
        """分发事件"""
        logger.debug(f"分发事件: {event.event_type} to {event.target or 'all'}")
        
        try:
            # 获取订阅者
            with self._lock:
                subscribers = self._subscribers.get(event.event_type, [])
                # 清理失效的弱引用
                self._cleanup_dead_references(event.event_type)
            
            # 按优先级排序
            handlers = []
            for ref in subscribers:
                handler_info = ref()
                if handler_info:
                    handler, module_ref = handler_info
                    module = module_ref()
                    if module:
                        # 检查目标模块
                        if event.target is None or event.target == module.module_info.name:
                            handlers.append((handler, module, event.priority.value))
            
            # 按优先级排序（高优先级先处理）
            handlers.sort(key=lambda x: x[2], reverse=True)
            
            # 分发事件
            for handler, module, _ in handlers:
                try:
                    if inspect.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
                    
                    logger.debug(f"事件处理成功: {event.event_type} by {module.module_info.name}")
                    
                except Exception as e:
                    logger.error(f"事件处理失败: {event.event_type} by {module.module_info.name}, 错误: {e}")
                    self._stats["events_failed"] += 1
            
            self._stats["events_processed"] += 1
            
        except Exception as e:
            logger.error(f"事件分发失败: {event.event_type}, 错误: {e}")
            self._stats["events_failed"] += 1
    
    def _cleanup_dead_references(self, event_type: str):
        """清理失效的弱引用"""
        if event_type in self._subscribers:
            self._subscribers[event_type] = [
                ref for ref in self._subscribers[event_type] 
                if ref() is not None
            ]
    
    def get_stats(self) -> Dict[str, int]:
        """获取统计信息"""
        with self._lock:
            return self._stats.copy()
    
    def clear_stats(self):
        """清空统计信息"""
        with self._lock:
            self._stats = {
                "events_emitted": 0,
                "events_processed": 0,
                "events_failed": 0
            }

class DependencyResolver:
    """依赖解析器"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def resolve_dependencies(self, modules: Dict[str, ModuleInfo]) -> List[str]:
        """解析模块依赖关系，返回启动顺序"""
        self.logger.debug("开始解析模块依赖关系")
        
        # 构建依赖图
        dependency_graph = {}
        for name, info in modules.items():
            dependency_graph[name] = set(info.dependencies)
        
        # 检查循环依赖
        self._check_circular_dependencies(dependency_graph)
        
        # 拓扑排序
        sorted_modules = self._topological_sort(dependency_graph)
        
        # 按优先级排序
        sorted_modules.sort(key=lambda name: modules[name].priority, reverse=True)
        
        self.logger.debug(f"模块启动顺序: {sorted_modules}")
        return sorted_modules
    
    def _check_circular_dependencies(self, graph: Dict[str, Set[str]]):
        """检查循环依赖"""
        visited = set()
        rec_stack = set()
        
        def dfs(node: str, path: List[str]) -> bool:
            if node in rec_stack:
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                raise ValueError(f"检测到循环依赖: {' -> '.join(cycle)}")
            
            if node in visited:
                return False
            
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in graph.get(node, set()):
                if dfs(neighbor, path):
                    return True
            
            rec_stack.remove(node)
            path.pop()
            return False
        
        for node in graph:
            if node not in visited:
                dfs(node, [])
    
    def _topological_sort(self, graph: Dict[str, Set[str]]) -> List[str]:
        """拓扑排序"""
        # 计算入度
        in_degree = {node: 0 for node in graph}
        for node in graph:
            for neighbor in graph[node]:
                if neighbor in in_degree:
                    in_degree[neighbor] += 1
        
        # 找到入度为0的节点
        queue = deque([node for node, degree in in_degree.items() if degree == 0])
        result = []
        
        while queue:
            node = queue.popleft()
            result.append(node)
            
            # 更新邻居节点的入度
            for neighbor in graph.get(node, set()):
                if neighbor in in_degree:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)
        
        # 检查是否所有节点都被处理
        if len(result) != len(graph):
            unprocessed = set(graph.keys()) - set(result)
            raise ValueError(f"无法解析依赖关系，未处理的模块: {unprocessed}")
        
        return result
    
    def validate_dependencies(self, modules: Dict[str, ModuleInfo]) -> List[str]:
        """验证依赖关系"""
        errors = []
        
        for name, info in modules.items():
            # 检查必需依赖
            for dep in info.dependencies:
                if dep not in modules:
                    errors.append(f"模块 {name} 的依赖 {dep} 不存在")
            
            # 检查可选依赖
            for dep in info.optional_dependencies:
                if dep not in modules:
                    self.logger.warning(f"模块 {name} 的可选依赖 {dep} 不存在")
        
        return errors

class ModuleCoordinator:
    """模块协调器"""
    
    def __init__(self):
        self._modules: Dict[str, IModule] = {}
        self._module_infos: Dict[str, ModuleInfo] = {}
        self._module_instances: Dict[str, Any] = {}  # 单例实例缓存
        self._event_bus = EventBus()
        self._dependency_resolver = DependencyResolver()
        self._lock = threading.RLock()
        self._startup_order: List[str] = []
        self._shutdown_order: List[str] = []
        self._stats = {
            "modules_registered": 0,
            "modules_started": 0,
            "modules_stopped": 0,
            "modules_failed": 0
        }
        
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("模块协调器初始化完成")
    
    def register_module(self, module_class: Type[IModule], module_info: Optional[ModuleInfo] = None) -> bool:
        """注册模块"""
        try:
            # 创建临时实例获取模块信息
            temp_instance = module_class(self)
            info = module_info or temp_instance.module_info
            
            with self._lock:
                if info.name in self._module_infos:
                    self.logger.warning(f"模块已存在: {info.name}")
                    return False
                
                self._module_infos[info.name] = info
                
                # 如果是单例模式，缓存实例
                if info.singleton:
                    self._module_instances[info.name] = temp_instance
                
                self._stats["modules_registered"] += 1
                
                self.logger.info(f"模块注册成功: {info.name} v{info.version}")
                
                # 发送模块注册事件
                self._event_bus.emit(Event(
                    event_type="module.registered",
                    source="coordinator",
                    data={"module_name": info.name, "module_info": info}
                ))
                
                return True
                
        except Exception as e:
            self.logger.error(f"模块注册失败: {e}")
            self.logger.debug(traceback.format_exc())
            return False
    
    def unregister_module(self, module_name: str) -> bool:
        """注销模块"""
        try:
            with self._lock:
                if module_name not in self._module_infos:
                    self.logger.warning(f"模块不存在: {module_name}")
                    return False
                
                # 停止模块
                if module_name in self._modules:
                    asyncio.create_task(self._stop_module(module_name))
                
                # 清理缓存
                del self._module_infos[module_name]
                if module_name in self._module_instances:
                    del self._module_instances[module_name]
                if module_name in self._modules:
                    del self._modules[module_name]
                
                self.logger.info(f"模块注销成功: {module_name}")
                
                # 发送模块注销事件
                self._event_bus.emit(Event(
                    event_type="module.unregistered",
                    source="coordinator",
                    data={"module_name": module_name}
                ))
                
                return True
                
        except Exception as e:
            self.logger.error(f"模块注销失败: {e}")
            return False
    
    async def start_all_modules(self) -> bool:
        """启动所有模块"""
        self.logger.info("开始启动所有模块")
        
        try:
            # 验证依赖关系
            errors = self._dependency_resolver.validate_dependencies(self._module_infos)
            if errors:
                self.logger.error(f"依赖关系验证失败: {errors}")
                return False
            
            # 解析启动顺序
            self._startup_order = self._dependency_resolver.resolve_dependencies(self._module_infos)
            self._shutdown_order = list(reversed(self._startup_order))
            
            # 按顺序启动模块
            for module_name in self._startup_order:
                info = self._module_infos[module_name]
                if info.auto_start:
                    success = await self._start_module(module_name)
                    if not success:
                        self.logger.error(f"模块启动失败: {module_name}")
                        return False
            
            self.logger.info("所有模块启动完成")
            return True
            
        except Exception as e:
            self.logger.error(f"启动模块失败: {e}")
            self.logger.debug(traceback.format_exc())
            return False
    
    async def stop_all_modules(self) -> bool:
        """停止所有模块"""
        self.logger.info("开始停止所有模块")
        
        try:
            # 按逆序停止模块
            for module_name in self._shutdown_order:
                if module_name in self._modules:
                    await self._stop_module(module_name)
            
            self.logger.info("所有模块停止完成")
            return True
            
        except Exception as e:
            self.logger.error(f"停止模块失败: {e}")
            return False
    
    async def _start_module(self, module_name: str) -> bool:
        """启动单个模块"""
        try:
            info = self._module_infos[module_name]
            
            # 检查依赖是否满足
            for dep in info.dependencies:
                if not self.is_module_running(dep):
                    self.logger.error(f"模块 {module_name} 的依赖 {dep} 未运行")
                    return False
            
            # 获取或创建模块实例
            if info.singleton and module_name in self._module_instances:
                module = self._module_instances[module_name]
            else:
                # 这里需要模块类的注册机制，暂时跳过
                self.logger.warning(f"无法创建模块实例: {module_name}")
                return False
            
            # 设置状态并初始化
            module.set_state(ModuleState.INITIALIZING)
            if not await module.initialize():
                module.set_state(ModuleState.ERROR)
                self._stats["modules_failed"] += 1
                return False
            
            module.set_state(ModuleState.INITIALIZED)
            
            # 启动模块
            module.set_state(ModuleState.STARTING)
            if not await module.start():
                module.set_state(ModuleState.ERROR)
                self._stats["modules_failed"] += 1
                return False
            
            module.set_state(ModuleState.RUNNING)
            
            with self._lock:
                self._modules[module_name] = module
                self._stats["modules_started"] += 1
            
            self.logger.info(f"模块启动成功: {module_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"启动模块失败: {module_name}, 错误: {e}")
            self._stats["modules_failed"] += 1
            return False
    
    async def _stop_module(self, module_name: str) -> bool:
        """停止单个模块"""
        try:
            with self._lock:
                if module_name not in self._modules:
                    return True
                
                module = self._modules[module_name]
            
            # 停止模块
            module.set_state(ModuleState.STOPPING)
            if not await module.stop():
                module.set_state(ModuleState.ERROR)
                return False
            
            module.set_state(ModuleState.STOPPED)
            
            # 销毁模块
            if not await module.destroy():
                module.set_state(ModuleState.ERROR)
                return False
            
            module.set_state(ModuleState.DESTROYED)
            
            with self._lock:
                del self._modules[module_name]
                self._stats["modules_stopped"] += 1
            
            self.logger.info(f"模块停止成功: {module_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"停止模块失败: {module_name}, 错误: {e}")
            return False
    
    def get_module(self, module_name: str) -> Optional[IModule]:
        """获取模块实例"""
        with self._lock:
            return self._modules.get(module_name)
    
    def is_module_running(self, module_name: str) -> bool:
        """检查模块是否运行中"""
        module = self.get_module(module_name)
        return module is not None and module.get_state() == ModuleState.RUNNING
    
    def get_module_info(self, module_name: str) -> Optional[ModuleInfo]:
        """获取模块信息"""
        with self._lock:
            return self._module_infos.get(module_name)
    
    def list_modules(self) -> Dict[str, ModuleInfo]:
        """列出所有模块"""
        with self._lock:
            return self._module_infos.copy()
    
    def emit_event(self, event: Event):
        """发送事件"""
        self._event_bus.emit(event)
    
    def subscribe_event(self, event_type: str, handler: Callable, module: IModule):
        """订阅事件"""
        self._event_bus.subscribe(event_type, handler, module)
    
    def unsubscribe_event(self, event_type: str, handler: Callable, module: IModule):
        """取消订阅事件"""
        self._event_bus.unsubscribe(event_type, handler, module)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            stats = self._stats.copy()
            stats.update({
                "event_bus_stats": self._event_bus.get_stats(),
                "startup_order": self._startup_order.copy(),
                "shutdown_order": self._shutdown_order.copy(),
                "running_modules": [
                    name for name, module in self._modules.items()
                    if module.get_state() == ModuleState.RUNNING
                ]
            })
            return stats

# 全局协调器实例
_coordinator: Optional[ModuleCoordinator] = None
_coordinator_lock = threading.Lock()

def get_coordinator() -> ModuleCoordinator:
    """获取全局模块协调器实例"""
    global _coordinator
    
    with _coordinator_lock:
        if _coordinator is None:
            _coordinator = ModuleCoordinator()
        return _coordinator

# 测试代码
if __name__ == "__main__":
    class TestModule(IModule):
        """测试模块"""
        
        def __init__(self, coordinator: ModuleCoordinator, name: str, dependencies: List[str] = None):
            super().__init__(coordinator)
            self._name = name
            self._dependencies = dependencies or []
        
        @property
        def module_info(self) -> ModuleInfo:
            return ModuleInfo(
                name=self._name,
                version="1.0.0",
                description=f"测试模块 {self._name}",
                dependencies=self._dependencies,
                module_type=ModuleType.SERVICE
            )
        
        async def initialize(self) -> bool:
            self.logger.info(f"初始化模块: {self._name}")
            await asyncio.sleep(0.1)  # 模拟初始化时间
            return True
        
        async def start(self) -> bool:
            self.logger.info(f"启动模块: {self._name}")
            await asyncio.sleep(0.1)  # 模拟启动时间
            return True
        
        async def stop(self) -> bool:
            self.logger.info(f"停止模块: {self._name}")
            await asyncio.sleep(0.1)  # 模拟停止时间
            return True
        
        async def destroy(self) -> bool:
            self.logger.info(f"销毁模块: {self._name}")
            return True
    
    async def test_module_coordinator():
        """测试模块协调器"""
        logger.info("模块协调器测试开始")
        
        coordinator = ModuleCoordinator()
        
        # 注册测试模块
        coordinator.register_module(TestModule, ModuleInfo(
            name="module_a",
            dependencies=[],
            priority=1
        ))
        
        coordinator.register_module(TestModule, ModuleInfo(
            name="module_b",
            dependencies=["module_a"],
            priority=2
        ))
        
        coordinator.register_module(TestModule, ModuleInfo(
            name="module_c",
            dependencies=["module_a", "module_b"],
            priority=3
        ))
        
        # 启动所有模块
        success = await coordinator.start_all_modules()
        logger.info(f"模块启动结果: {success}")
        
        # 获取统计信息
        stats = coordinator.get_stats()
        logger.info(f"协调器统计: {stats}")
        
        # 停止所有模块
        await coordinator.stop_all_modules()
        
        logger.info("模块协调器测试完成")
    
    # 运行测试
    asyncio.run(test_module_coordinator())