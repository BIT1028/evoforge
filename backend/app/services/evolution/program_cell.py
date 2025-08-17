"""程序化数字细胞 - 将生物学概念抽象为程序功能概念

这个模块实现了数字细胞的程序化抽象改造，将传统的生物学概念
转换为现代程序设计中的功能概念，提高计算效率和可维护性。
"""

import uuid
import time
import asyncio
import threading
from typing import Dict, List, Any, Optional, Callable, Set, Tuple
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
from queue import PriorityQueue
from functools import reduce
import numpy as np
import json
from abc import ABC, abstractmethod


@dataclass
class ExecutionContext:
    """执行上下文 - 替代细胞记忆"""
    successful_patterns: List[Dict[str, Any]] = field(default_factory=list)
    failed_patterns: List[Dict[str, Any]] = field(default_factory=list)
    performance_history: List[float] = field(default_factory=list)
    generation_count: int = 0
    optimization_history: List[Dict[str, Any]] = field(default_factory=list)
    learning_rate: float = 0.1


class SecurityPolicy:
    """安全策略 - 替代细胞膜的选择性通透"""
    
    def __init__(self, permission_level: int = 3, rate_limit: float = 1000.0):
        self.permission_level = permission_level
        self.rate_limit = rate_limit  # 请求/秒
        self.input_filters: List[Callable] = []
        self.output_policies: List[Callable] = []
        self.blocked_sources: Set[str] = set()
        self.request_history: List[float] = []
        
    def validate_code(self, code: str) -> bool:
        """验证代码安全性
        
        Args:
            code: 要验证的代码
            
        Returns:
            是否通过验证
        """
        # 基础安全检查
        dangerous_patterns = [
            'import os', 'import sys', 'import subprocess',
            'exec(', 'eval(', '__import__',
            'open(', 'file(', 'input(',
            'raw_input(', 'compile(', 'globals(',
            'locals(', 'vars(', 'dir(',
            'getattr(', 'setattr(', 'delattr(',
            'hasattr(', '__builtins__'
        ]
        
        for pattern in dangerous_patterns:
            if pattern in code:
                return False
        
        # 检查代码长度
        if len(code) > 10000:  # 限制代码长度
            return False
        
        # 检查是否包含基本的Python语法
        try:
            compile(code, '<string>', 'exec')
            return True
        except SyntaxError:
            return False
    
    def validate_all_modules(self, modules: List[Dict]) -> bool:
        """验证所有模块的安全性
        
        Args:
            modules: 模块列表
            
        Returns:
            是否全部通过验证
        """
        for module in modules:
            if not self.validate_code(module.get('code', '')):
                return False
        return True
    
    def get_overall_quality_score(self) -> float:
        """获取整体质量分数
        
        Returns:
            质量分数 (0-1)
        """
        # 简单的质量评估
        return 0.8  # 默认质量分数
        
    def add_input_filter(self, filter_func: Callable[[Any], bool]):
        """添加输入过滤器"""
        self.input_filters.append(filter_func)
        
    def add_output_policy(self, policy_func: Callable[[Any], Any]):
        """添加输出策略"""
        self.output_policies.append(policy_func)
        
    def check_input_permission(self, data_packet: Dict[str, Any]) -> bool:
        """检查输入权限 - 替代can_enter"""
        source = data_packet.get('source', 'unknown')
        
        # 检查黑名单
        if source in self.blocked_sources:
            return False
            
        # 检查速率限制
        current_time = time.time()
        self.request_history = [t for t in self.request_history 
                               if current_time - t < 1.0]
        if len(self.request_history) >= self.rate_limit:
            return False
            
        # 应用输入过滤器
        if not all(f(data_packet) for f in self.input_filters):
            return False
            
        self.request_history.append(current_time)
        return True
        
    def format_output(self, result: Any) -> Any:
        """格式化输出 - 替代can_exit"""
        return reduce(lambda data, policy: policy(data), 
                     self.output_policies, result)


class CodeModule:
    """代码模块 - 替代基因"""
    
    def __init__(self, name: str, code: str, dependencies: List[str] = None):
        self.name = name
        self.code = code
        self.dependencies = dependencies or []
        self.compiled_code = None
        self.execution_count = 0
        self.average_execution_time = 0.0
        self.success_rate = 1.0
        self.last_modified = time.time()
        
    def compile(self) -> bool:
        """编译代码模块"""
        try:
            self.compiled_code = compile(self.code, f'<module_{self.name}>', 'exec')
            return True
        except SyntaxError as e:
            print(f"编译错误 in {self.name}: {e}")
            return False
            
    def execute(self, context: Dict[str, Any]) -> Tuple[bool, Any]:
        """执行代码模块"""
        if not self.compiled_code:
            if not self.compile():
                return False, None
                
        start_time = time.time()
        try:
            exec_globals = context.copy()
            exec(self.compiled_code, exec_globals)
            
            execution_time = time.time() - start_time
            self._update_performance_metrics(execution_time, True)
            
            return True, exec_globals.get('result')
        except Exception as e:
            execution_time = time.time() - start_time
            self._update_performance_metrics(execution_time, False)
            print(f"执行错误 in {self.name}: {e}")
            return False, None
            
    def _update_performance_metrics(self, execution_time: float, success: bool):
        """更新性能指标"""
        self.execution_count += 1
        
        # 更新平均执行时间
        alpha = 0.1  # 指数移动平均的权重
        self.average_execution_time = (alpha * execution_time + 
                                     (1 - alpha) * self.average_execution_time)
        
        # 更新成功率
        self.success_rate = (alpha * (1.0 if success else 0.0) + 
                           (1 - alpha) * self.success_rate)


class ResourceManager:
    """资源管理器 - 替代细胞质"""
    
    def __init__(self, max_memory: int = 1024, max_threads: int = 8):
        self.max_memory = max_memory
        self.max_threads = max_threads
        self.allocated_memory = 0
        self.thread_pool = ThreadPoolExecutor(max_workers=max_threads)
        self.memory_blocks: Dict[str, int] = {}
        self.active_tasks: Dict[str, Any] = {}
        
    def allocate_memory(self, size: int, block_id: str) -> bool:
        """分配内存资源"""
        if self.allocated_memory + size > self.max_memory:
            return False
            
        self.memory_blocks[block_id] = size
        self.allocated_memory += size
        return True
        
    def deallocate_memory(self, block_id: str) -> bool:
        """释放内存资源"""
        if block_id in self.memory_blocks:
            size = self.memory_blocks.pop(block_id)
            self.allocated_memory -= size
            return True
        return False
        
    def submit_task(self, task_id: str, func: Callable, *args, **kwargs):
        """提交异步任务"""
        future = self.thread_pool.submit(func, *args, **kwargs)
        self.active_tasks[task_id] = future
        return future
        
    def get_task_result(self, task_id: str, timeout: float = None):
        """获取任务结果"""
        if task_id in self.active_tasks:
            future = self.active_tasks[task_id]
            try:
                result = future.result(timeout=timeout)
                del self.active_tasks[task_id]
                return result
            except Exception as e:
                print(f"任务 {task_id} 执行失败: {e}")
                return None
        return None
        
    def get_resource_usage(self) -> Dict[str, Any]:
        """获取资源使用情况"""
        return {
            'memory_usage': self.allocated_memory / self.max_memory,
            'thread_usage': len(self.active_tasks) / self.max_threads,
            'active_tasks': len(self.active_tasks),
            'memory_blocks': len(self.memory_blocks)
        }
        
    def cleanup_resources(self):
        """清理资源"""
        # 清理过期的内存块
        expired_blocks = []
        for block_id in self.memory_blocks:
            # 简单的清理逻辑
            expired_blocks.append(block_id)
            
        for block_id in expired_blocks[:len(expired_blocks)//2]:  # 清理一半
            self.deallocate_memory(block_id)
            
    def get_memory_efficiency(self) -> float:
        """获取内存效率"""
        if self.max_memory == 0:
            return 1.0
        return 1.0 - (self.allocated_memory / self.max_memory)


class CoreEngine:
    """核心引擎 - 替代细胞核"""
    
    def __init__(self):
        self.modules: Dict[str, CodeModule] = {}
        self.dependency_graph: Dict[str, List[str]] = {}
        self.execution_order: List[str] = []
        self.global_context: Dict[str, Any] = {}
        self.optimization_enabled = True
        
    def add_module(self, module: CodeModule):
        """添加代码模块"""
        self.modules[module.name] = module
        self.dependency_graph[module.name] = module.dependencies
        self._update_execution_order()
        
    def remove_module(self, module_name: str):
        """移除代码模块"""
        if module_name in self.modules:
            del self.modules[module_name]
            del self.dependency_graph[module_name]
            self._update_execution_order()
            
    def _update_execution_order(self):
        """更新执行顺序 - 拓扑排序"""
        visited = set()
        temp_visited = set()
        order = []
        
        def dfs(node):
            if node in temp_visited:
                raise ValueError(f"循环依赖检测到: {node}")
            if node in visited:
                return
                
            temp_visited.add(node)
            for dep in self.dependency_graph.get(node, []):
                if dep in self.modules:
                    dfs(dep)
                    
            temp_visited.remove(node)
            visited.add(node)
            order.append(node)
            
        for module_name in self.modules:
            if module_name not in visited:
                dfs(module_name)
                
        self.execution_order = order
        
    def execute_module(self, module_name: str, inputs: Dict[str, Any] = None) -> Tuple[bool, Any]:
        """执行单个模块"""
        if module_name not in self.modules:
            return False, f"模块 {module_name} 不存在"
            
        module = self.modules[module_name]
        
        # 检查依赖
        for dep in module.dependencies:
            if dep not in self.modules:
                return False, f"依赖模块 {dep} 不存在"
                
        # 准备执行上下文
        context = self.global_context.copy()
        if inputs:
            context.update(inputs)
            
        return module.execute(context)
        
    def execute_pipeline(self, inputs: Dict[str, Any] = None) -> Dict[str, Any]:
        """执行完整的模块管道"""
        results = {}
        context = self.global_context.copy()
        if inputs:
            context.update(inputs)
            
        for module_name in self.execution_order:
            success, result = self.execute_module(module_name, context)
            results[module_name] = {
                'success': success,
                'result': result
            }
            
            # 如果模块执行成功，将结果添加到上下文
            if success and result is not None:
                context[f'{module_name}_result'] = result
                
        return results
        
    def optimize_modules(self):
        """优化模块执行"""
        if not self.optimization_enabled:
            return
            
        # 基于性能指标重新排序模块
        performance_scores = {}
        for name, module in self.modules.items():
            # 计算性能分数（执行时间越短，成功率越高，分数越高）
            time_score = 1.0 / (module.average_execution_time + 0.001)
            success_score = module.success_rate
            performance_scores[name] = time_score * success_score
            
        # 在满足依赖关系的前提下，优先执行高性能模块
        # 这里可以实现更复杂的优化算法
        pass
        
    def get_module_dependencies(self, module_name: str) -> List[str]:
        """获取模块依赖
        
        Args:
            module_name: 模块名称
            
        Returns:
            依赖列表
        """
        return self.dependency_graph.get(module_name, [])
        
    def validate_dependencies(self) -> bool:
        """验证依赖关系
        
        Returns:
            依赖关系是否有效
        """
        try:
            self._update_execution_order()
            return True
        except ValueError:
            return False
            
    def execute_code(self, code: str, context: Optional[ExecutionContext] = None) -> Dict[str, Any]:
        """执行代码并返回详细结果
        
        Args:
            code: 要执行的代码
            context: 执行上下文
            
        Returns:
            执行结果字典
        """
        start_time = time.time()
        
        try:
            # 准备执行环境
            local_vars = {}
            if context:
                local_vars.update(getattr(context, 'variables', {}))
            
            # 执行代码
            exec(code, {}, local_vars)
            
            execution_time = time.time() - start_time
            result = local_vars.get('result', None)
            
            return {
                'success': True,
                'output': result,
                'execution_time': execution_time,
                'memory_usage': 0,  # 简化实现
                'error': None
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            return {
                'success': False,
                'output': None,
                'execution_time': execution_time,
                'memory_usage': 0,
                'error': str(e)
            }
    
    def register_module(self, name: str, module: 'CodeModule'):
        """注册模块
        
        Args:
            name: 模块名称
            module: 代码模块
        """
        self.modules[name] = module
        self.dependency_graph[name] = module.dependencies
        self._update_execution_order()
    
    def get_success_rate(self) -> float:
        """获取整体成功率
        
        Returns:
            成功率 (0-1)
        """
        if not self.modules:
            return 1.0
        
        total_success_rate = sum(module.success_rate for module in self.modules.values())
        return total_success_rate / len(self.modules)
        
    def get_execution_statistics(self) -> Dict[str, Any]:
        """获取执行统计信息
        
        Returns:
            统计信息字典
        """
        total_executions = sum(module.execution_count for module in self.modules.values())
        avg_execution_time = sum(module.average_execution_time for module in self.modules.values()) / len(self.modules) if self.modules else 0
        avg_success_rate = sum(module.success_rate for module in self.modules.values()) / len(self.modules) if self.modules else 1.0
        
        return {
            'total_modules': len(self.modules),
            'total_executions': total_executions,
            'average_execution_time': avg_execution_time,
            'average_success_rate': avg_success_rate,
            'optimization_enabled': self.optimization_enabled
        }


class CommunicationProtocol:
    """通信协议 - 替代细胞间信号传导"""
    
    def __init__(self, cell_id: str):
        self.cell_id = cell_id
        self.message_queue = PriorityQueue()
        self.subscribers: Dict[str, List[Callable]] = {}
        self.message_history: List[Dict[str, Any]] = []
        
    def subscribe(self, message_type: str, handler: Callable):
        """订阅消息类型"""
        if message_type not in self.subscribers:
            self.subscribers[message_type] = []
        self.subscribers[message_type].append(handler)
        
    def send_message(self, target_cell: 'ProgramCell', message_type: str, 
                    data: Any, priority: int = 0):
        """发送消息"""
        message = {
            'id': str(uuid.uuid4()),
            'source': self.cell_id,
            'target': target_cell.cell_id,
            'type': message_type,
            'data': data,
            'timestamp': time.time(),
            'priority': priority
        }
        
        target_cell.communication.receive_message(message)
        self.message_history.append(message)
        
    def receive_message(self, message: Dict[str, Any]):
        """接收消息"""
        priority = message.get('priority', 0)
        self.message_queue.put((-priority, time.time(), message))
        
    def process_messages(self, max_messages: int = 10):
        """处理消息队列"""
        processed = 0
        while not self.message_queue.empty() and processed < max_messages:
            _, _, message = self.message_queue.get()
            message_type = message['type']
            
            if message_type in self.subscribers:
                for handler in self.subscribers[message_type]:
                    try:
                        handler(message)
                    except Exception as e:
                        print(f"消息处理错误: {e}")
                        
            processed += 1
    
    def get_efficiency_score(self) -> float:
        """获取通信效率分数
        
        Returns:
            效率分数 (0-1)
        """
        # 基于消息队列大小和处理速度计算效率
        queue_size = self.message_queue.qsize()
        max_queue_size = 100  # 假设最大队列大小
        
        if queue_size == 0:
            return 1.0
        
        efficiency = max(0, 1.0 - (queue_size / max_queue_size))
        return efficiency
    
    def is_active(self) -> bool:
        """检查通信是否活跃
        
        Returns:
            是否活跃
        """
        # 简单的活跃检查：队列中有消息或最近有活动
        return not self.message_queue.empty() or (time.time() - getattr(self, 'last_activity', 0)) < 60


class ProgramCell:
    """程序化数字细胞 - 主类
    
    将传统的生物学细胞概念抽象为程序功能概念，
    提供高效的代码执行和资源管理能力。
    """
    
    def __init__(self, cell_id: str = None, config: Dict[str, Any] = None):
        self.cell_id = cell_id or str(uuid.uuid4())
        self.config = config or {}
        
        # 核心组件
        self.security = SecurityPolicy(
            permission_level=self.config.get('permission_level', 3),
            rate_limit=self.config.get('rate_limit', 1000.0)
        )
        self.engine = CoreEngine()
        self.resources = ResourceManager(
            max_memory=self.config.get('max_memory', 1024),
            max_threads=self.config.get('max_threads', 8)
        )
        self.communication = CommunicationProtocol(self.cell_id)
        self.context = ExecutionContext()
        
        # 状态信息
        self.created_at = time.time()
        self.last_update = time.time()
        self.is_active = True
        self.performance_metrics = {
            'total_executions': 0,
            'successful_executions': 0,
            'average_response_time': 0.0,
            'resource_efficiency': 1.0
        }
        
        # 初始化基础模块
        self._initialize_basic_modules()
        
    def _initialize_basic_modules(self):
        """初始化基础代码模块"""
        # 基础函数模块
        basic_function = CodeModule(
            name='basic_function',
            code='''
def hello_world():
    result = "Hello, World!"
    return result

result = hello_world()
'''
        )
        
        # 变量赋值模块
        variable_assignment = CodeModule(
            name='variable_assignment',
            code='''
x = 42
y = "test"
result = {'x': x, 'y': y}
'''
        )
        
        # 简单表达式模块
        simple_expression = CodeModule(
            name='simple_expression',
            code='''
if 'x' in globals():
    result = x + 1
else:
    result = 1
''',
            dependencies=['variable_assignment']
        )
        
        self.engine.add_module(basic_function)
        self.engine.add_module(variable_assignment)
        self.engine.add_module(simple_expression)
        
    def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """处理外部请求 - 主要接口方法"""
        start_time = time.time()
        
        # 安全检查
        if not self.security.check_input_permission(request):
            return {
                'success': False,
                'error': '权限被拒绝',
                'timestamp': time.time()
            }
            
        try:
            # 执行代码管道
            inputs = request.get('inputs', {})
            results = self.engine.execute_pipeline(inputs)
            
            # 格式化输出
            formatted_results = self.security.format_output(results)
            
            # 更新性能指标
            execution_time = time.time() - start_time
            self._update_performance_metrics(execution_time, True)
            
            response = {
                'success': True,
                'results': formatted_results,
                'execution_time': execution_time,
                'timestamp': time.time(),
                'cell_id': self.cell_id
            }
            
            return response
            
        except Exception as e:
            execution_time = time.time() - start_time
            self._update_performance_metrics(execution_time, False)
            
            return {
                'success': False,
                'error': str(e),
                'execution_time': execution_time,
                'timestamp': time.time(),
                'cell_id': self.cell_id
            }
            
    def add_code_module(self, name: str, code: str, dependencies: List[str] = None):
        """添加新的代码模块"""
        module = CodeModule(name, code, dependencies)
        self.engine.add_module(module)
        
    def update_module(self, name: str, new_code: str):
        """更新现有模块"""
        if name in self.engine.modules:
            module = self.engine.modules[name]
            module.code = new_code
            module.compiled_code = None  # 强制重新编译
            module.last_modified = time.time()
            
    def add_code_module(self, name: str, code: str, module_type: str = 'function', priority: float = 1.0):
        """添加代码模块
        
        Args:
            name: 模块名称
            code: 代码内容
            module_type: 模块类型
            priority: 优先级
        """
        module = CodeModule(
            name=name,
            code=code,
            dependencies=[]
        )
        
        # 添加模块到引擎
        self.engine.add_module(module)
        
    def get_status(self) -> Dict[str, Any]:
        """获取细胞状态
        
        Returns:
            状态字典
        """
        # 根据当前状态确定细胞状态
        current_state = 'active'
        resource_usage = self.resources.get_resource_usage()
        
        if resource_usage['memory_usage'] > 0.9:
            current_state = 'overloaded'
        elif len(self.engine.modules) == 0:
            current_state = 'idle'
        elif not self.is_active:
            current_state = 'inactive'
        
        return {
            'id': self.cell_id,
            'state': current_state,
            'is_active': self.is_active,
            'created_at': self.created_at,
            'last_update': self.last_update,
            'module_count': len(self.engine.modules),
            'memory_usage': resource_usage['memory_usage'],
            'thread_usage': resource_usage['thread_usage'],
            'active_tasks': resource_usage['active_tasks'],
            'performance_metrics': self.performance_metrics,
            'message_queue_size': self.communication.message_queue.qsize(),
            'memory_efficiency': max(0, 1.0 - resource_usage['memory_usage']),
            'execution_success_rate': self.performance_metrics['successful_executions'] / max(1, self.performance_metrics['total_executions']),
            'adaptation_rate': min(1.0, len(self.engine.modules) / 10.0)
        }
        
    def _update_performance_metrics(self, execution_time: float, success: bool):
        """更新性能指标"""
        self.performance_metrics['total_executions'] += 1
        if success:
            self.performance_metrics['successful_executions'] += 1
            
        # 更新平均响应时间
        alpha = 0.1
        current_avg = self.performance_metrics['average_response_time']
        self.performance_metrics['average_response_time'] = (
            alpha * execution_time + (1 - alpha) * current_avg
        )
        
        # 更新资源效率
        resource_usage = self.resources.get_resource_usage()
        efficiency = 1.0 - (resource_usage['memory_usage'] + resource_usage['thread_usage']) / 2
        self.performance_metrics['resource_efficiency'] = (
            alpha * efficiency + (1 - alpha) * self.performance_metrics['resource_efficiency']
        )
        
        self.last_update = time.time()
        
    def clone(self) -> 'ProgramCell':
        """克隆细胞 - 替代细胞分裂"""
        new_cell = ProgramCell(config=self.config.copy())
        
        # 复制模块
        for name, module in self.engine.modules.items():
            if name not in ['basic_function', 'variable_assignment', 'simple_expression']:
                new_module = CodeModule(module.name, module.code, module.dependencies.copy())
                new_cell.engine.add_module(new_module)
                
        # 复制上下文
        new_cell.context.successful_patterns = self.context.successful_patterns.copy()
        new_cell.context.generation_count = self.context.generation_count + 1
        
        return new_cell
        
    def mutate(self, mutation_rate: float = 0.1):
        """变异操作 - 随机修改代码模块"""
        mutation_record = {
            'timestamp': time.time(),
            'mutations': []
        }
        
        for name, module in self.engine.modules.items():
            if np.random.random() < mutation_rate:
                # 简单的代码变异：在代码中添加注释或修改常量
                old_code = module.code
                
                # 添加随机注释
                if '# mutated' not in module.code:
                    module.code += f'\n# mutated at {time.time()}'
                    module.compiled_code = None
                    
                    mutation_record['mutations'].append({
                        'module': name,
                        'type': 'comment_addition',
                        'old_code_length': len(old_code),
                        'new_code_length': len(module.code)
                    })
                    
        self.context.optimization_history.append(mutation_record)
        
    def execute_main_module(self) -> Dict[str, Any]:
        """执行主模块
        
        Returns:
            执行结果字典
        """
        # 查找主逻辑模块
        if 'main_logic' not in self.engine.modules:
            return {
                'success': False,
                'error': 'No main module found',
                'output': None,
                'execution_time': 0,
                'memory_usage': 0
            }
        
        start_time = time.time()
        success, result = self.engine.execute_module('main_logic')
        execution_time = time.time() - start_time
        
        resource_usage = self.resources.get_resource_usage()
        
        return {
            'success': success,
            'error': None if success else 'Execution failed',
            'output': result,
            'execution_time': execution_time,
            'memory_usage': resource_usage['memory_usage']
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标
        
        Returns:
            性能指标字典
        """
        total_executions = sum(module.execution_count for module in self.engine.modules.values())
        avg_execution_time = sum(module.average_execution_time for module in self.engine.modules.values()) / len(self.engine.modules) if self.engine.modules else 0
        avg_success_rate = sum(module.success_rate for module in self.engine.modules.values()) / len(self.engine.modules) if self.engine.modules else 1.0
        
        return {
            'module_count': len(self.engine.modules),
            'total_executions': total_executions,
            'average_execution_time': avg_execution_time,
            'average_success_rate': avg_success_rate,
            'memory_usage': self.resources.get_resource_usage()['memory_usage'],
            'thread_usage': self.resources.get_resource_usage()['thread_usage'],
            'active_tasks': self.resources.get_resource_usage()['active_tasks'],
            'error_rate': 1.0 - avg_success_rate,
            'resource_efficiency': self.performance_metrics['resource_efficiency'],
            'message_queue_size': self.communication.message_queue.qsize()
        }

    def shutdown(self):
        """关闭细胞"""
        self.is_active = False
        self.resources.thread_pool.shutdown(wait=True)


def create_program_cell(cell_id: str = None, config: Dict[str, Any] = None) -> ProgramCell:
    """创建程序化数字细胞的工厂函数
    
    Args:
        cell_id: 细胞ID
        config: 配置参数
        
    Returns:
        ProgramCell: 新创建的程序化数字细胞
    """
    return ProgramCell(cell_id, config)


# 兼容性适配器
class BioToProgramAdapter:
    """生物学细胞到程序化细胞的适配器"""
    
    @staticmethod
    def convert_digital_cell(bio_cell) -> ProgramCell:
        """将传统数字细胞转换为程序化细胞"""
        config = {
            'max_memory': int(getattr(bio_cell, 'energy', 100) * 10),
            'max_threads': 8,
            'permission_level': 3,
            'rate_limit': 1000.0
        }
        
        program_cell = create_program_cell(config=config)
        
        # 转换基因组为代码模块
        if hasattr(bio_cell, 'nucleus') and hasattr(bio_cell.nucleus, 'genome_template'):
            genome = bio_cell.nucleus.genome_template
            for gene_name, gene_data in genome.items():
                if isinstance(gene_data, dict) and 'instructions' in gene_data:
                    code = BioToProgramAdapter._convert_instructions_to_code(gene_data['instructions'])
                    program_cell.add_code_module(gene_name, code)
                    
        return program_cell
        
    @staticmethod
    def _convert_instructions_to_code(instructions: List[Dict[str, Any]]) -> str:
        """将基因指令转换为Python代码"""
        code_lines = []
        
        for instruction in instructions:
            inst_type = instruction.get('type', '')
            
            if inst_type == 'CREATE_FUNCTION':
                func_name = instruction.get('name', 'generated_func')
                args = instruction.get('args', [])
                args_str = ', '.join(args)
                code_lines.append(f'def {func_name}({args_str}):')
                code_lines.append('    pass')
                
            elif inst_type == 'CREATE_ASSIGNMENT':
                target = instruction.get('target', 'x')
                value = instruction.get('value', 0)
                code_lines.append(f'{target} = {repr(value)}')
                
            elif inst_type == 'CREATE_EXPRESSION':
                expr_type = instruction.get('expr_type', 'Constant')
                value = instruction.get('value', 0)
                if expr_type == 'Constant':
                    code_lines.append(f'result = {repr(value)}')
                    
        return '\n'.join(code_lines) if code_lines else 'result = None'