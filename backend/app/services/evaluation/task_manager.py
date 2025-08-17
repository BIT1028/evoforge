"""EvoForge任务管理器

实现完整的演进任务管理功能:
- 任务调度和生命周期管理
- 进化循环控制
- 资源管理和监控
- 并发执行支持
- 错误处理和恢复
"""

import asyncio
import json
import logging
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
import json
import traceback

# 导入EvoForge组件 - 修正导入路径
from gae.engine.engine import EvolutionEngine, EvolutionConfig
from backend.app.services.evolution.genome import Genome
from backend.app.services.evolution.selection import NSGA2Selector, TournamentSelector
from backend.app.services.evolution.distance import DistanceManager
from evaluation import evaluate_individual
from sandbox import Sandbox, SandboxResult
from storage.database import DatabaseManager, get_database_manager
from storage.models import Task, Generation, Individual, Fitness

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"

class ExecutionMode(Enum):
    """执行模式枚举"""
    SEQUENTIAL = "sequential"  # 顺序执行
    PARALLEL_THREAD = "parallel_thread"  # 线程并行
    PARALLEL_PROCESS = "parallel_process"  # 进程并行
    DISTRIBUTED = "distributed"  # 分布式执行

@dataclass
class TaskConfig:
    """任务配置"""
    # 基本信息
    name: str
    description: str = ""
    function_signature: str = ""
    test_cases: List[Dict] = field(default_factory=list)
    
    # 进化参数
    population_size: int = 50
    max_generations: int = 100
    mutation_rate: float = 0.1
    crossover_rate: float = 0.8
    
    # 目标和权重
    objectives: List[str] = field(default_factory=lambda: ["correctness", "performance"])
    objective_weights: Dict[str, float] = field(default_factory=dict)
    
    # 资源限制
    timeout_seconds: int = 300
    memory_limit_mb: int = 128
    cpu_quota: int = 100000
    max_parallel_evaluations: int = 4
    
    # 执行配置
    execution_mode: ExecutionMode = ExecutionMode.PARALLEL_THREAD
    checkpoint_interval: int = 10  # 每N代保存检查点
    
    # 停止条件
    target_fitness: Optional[Dict[str, float]] = None
    convergence_threshold: float = 1e-6
    stagnation_generations: int = 20
    
    # 其他配置
    seed: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TaskProgress:
    """任务进度信息"""
    task_id: str
    current_generation: int = 0
    total_generations: int = 0
    current_individual: int = 0
    total_individuals: int = 0
    best_fitness: Dict[str, float] = field(default_factory=dict)
    average_fitness: Dict[str, float] = field(default_factory=dict)
    diversity_score: float = 0.0
    elapsed_time: float = 0.0
    estimated_remaining_time: float = 0.0
    
class TaskManager:
    """任务管理器"""
    
    def __init__(self, 
                 database_manager: Optional[DatabaseManager] = None,
                 max_concurrent_tasks: int = 4,
                 checkpoint_dir: str = "./checkpoints"):
        """初始化任务管理器
        
        Args:
            database_manager: 数据库管理器
            max_concurrent_tasks: 最大并发任务数
            checkpoint_dir: 检查点目录
        """
        self.db = database_manager or get_database_manager()
        self.max_concurrent_tasks = max_concurrent_tasks
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(exist_ok=True)
        
        # 运行时状态
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.task_progress: Dict[str, TaskProgress] = {}
        self.task_configs: Dict[str, TaskConfig] = {}
        self.stop_flags: Dict[str, bool] = {}
        
        # 执行器
        self.thread_executor = ThreadPoolExecutor(max_workers=max_concurrent_tasks * 2)
        self.process_executor = ProcessPoolExecutor(max_workers=max_concurrent_tasks)
        
        # 回调函数
        self.progress_callbacks: List[Callable[[str, TaskProgress], None]] = []
        self.completion_callbacks: List[Callable[[str, TaskStatus, Any], None]] = []
        
        logger.info(f"任务管理器初始化完成，最大并发任务数: {max_concurrent_tasks}")
    
    async def create_task(self, config: TaskConfig) -> str:
        """创建新任务
        
        Args:
            config: 任务配置
            
        Returns:
            任务ID
        """
        task_id = str(uuid.uuid4())
        
        # 保存到数据库
        task_data = {
            'id': task_id,
            'name': config.name,
            'description': config.description,
            'function_signature': config.function_signature,
            'test_cases': config.test_cases,
            'objectives': config.objectives,
            'population_size': config.population_size,
            'max_generations': config.max_generations,
            'mutation_rate': config.mutation_rate,
            'crossover_rate': config.crossover_rate,
            'timeout_seconds': config.timeout_seconds,
            'memory_limit_mb': config.memory_limit_mb,
            'cpu_quota': config.cpu_quota,
            'config': config.__dict__,
            'metadata': config.metadata
        }
        
        self.db.create_task(task_data)
        
        # 保存配置和进度
        self.task_configs[task_id] = config
        self.task_progress[task_id] = TaskProgress(
            task_id=task_id,
            total_generations=config.max_generations,
            total_individuals=config.population_size
        )
        
        logger.info(f"创建任务 {task_id}: {config.name}")
        return task_id
    
    async def start_task(self, task_id: str) -> bool:
        """启动任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否启动成功
        """
        if task_id in self.running_tasks:
            logger.warning(f"任务 {task_id} 已在运行中")
            return False
        
        if len(self.running_tasks) >= self.max_concurrent_tasks:
            logger.warning(f"已达到最大并发任务数 {self.max_concurrent_tasks}")
            return False
        
        if task_id not in self.task_configs:
            logger.error(f"任务 {task_id} 配置未找到")
            return False
        
        # 更新数据库状态
        self.db.update_task_status(task_id, TaskStatus.RUNNING.value)
        
        # 启动异步任务
        task = asyncio.create_task(self._run_evolution_task(task_id))
        self.running_tasks[task_id] = task
        self.stop_flags[task_id] = False
        
        logger.info(f"启动任务 {task_id}")
        return True
    
    async def stop_task(self, task_id: str) -> bool:
        """停止任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否停止成功
        """
        if task_id not in self.running_tasks:
            logger.warning(f"任务 {task_id} 未在运行中")
            return False
        
        # 设置停止标志
        self.stop_flags[task_id] = True
        
        # 取消异步任务
        task = self.running_tasks[task_id]
        task.cancel()
        
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        # 清理
        del self.running_tasks[task_id]
        del self.stop_flags[task_id]
        
        # 更新数据库状态
        self.db.update_task_status(task_id, TaskStatus.STOPPED.value)
        
        logger.info(f"停止任务 {task_id}")
        return True
    
    async def pause_task(self, task_id: str) -> bool:
        """暂停任务"""
        if task_id not in self.running_tasks:
            return False
        
        # 这里可以实现暂停逻辑
        self.db.update_task_status(task_id, TaskStatus.PAUSED.value)
        logger.info(f"暂停任务 {task_id}")
        return True
    
    async def resume_task(self, task_id: str) -> bool:
        """恢复任务"""
        # 这里可以实现恢复逻辑
        self.db.update_task_status(task_id, TaskStatus.RUNNING.value)
        logger.info(f"恢复任务 {task_id}")
        return True
    
    def get_task_progress(self, task_id: str) -> Optional[TaskProgress]:
        """获取任务进度"""
        return self.task_progress.get(task_id)
    
    def get_running_tasks(self) -> List[str]:
        """获取运行中的任务列表"""
        return list(self.running_tasks.keys())
    
    def add_progress_callback(self, callback: Callable[[str, TaskProgress], None]):
        """添加进度回调函数"""
        self.progress_callbacks.append(callback)
    
    def add_completion_callback(self, callback: Callable[[str, TaskStatus, Any], None]):
        """添加完成回调函数"""
        self.completion_callbacks.append(callback)
    
    async def _run_evolution_task(self, task_id: str):
        """运行进化任务"""
        try:
            config = self.task_configs[task_id]
            progress = self.task_progress[task_id]
            
            logger.info(f"开始执行进化任务 {task_id}")
            start_time = time.time()
            
            # 创建进化引擎
            evo_config = EvolutionConfig(
                population_size=config.population_size,
                max_generations=config.max_generations,
                mutation_rate=config.mutation_rate,
                crossover_rate=config.crossover_rate
            )
            
            engine = EvolutionEngine(evo_config)
            
            # 初始化种群
            population = await self._initialize_population(task_id, config)
            
            # 进化循环
            for generation in range(config.max_generations):
                if self.stop_flags.get(task_id, False):
                    logger.info(f"任务 {task_id} 被停止")
                    break
                
                # 更新进度
                progress.current_generation = generation
                progress.elapsed_time = time.time() - start_time
                
                # 评估种群
                await self._evaluate_population(task_id, population, config)
                
                # 计算统计信息
                stats = self._calculate_generation_stats(population, config.objectives)
                progress.best_fitness = stats['best_fitness']
                progress.average_fitness = stats['average_fitness']
                progress.diversity_score = stats['diversity_score']
                
                # 保存代信息到数据库
                generation_data = {
                    'task_id': task_id,
                    'generation_number': generation,
                    'population_size': len(population),
                    'best_fitness': stats['best_fitness'],
                    'average_fitness': stats['average_fitness'],
                    'diversity_score': stats['diversity_score']
                }
                db_generation = self.db.create_generation(generation_data)
                
                # 保存个体到数据库
                for i, individual in enumerate(population):
                    individual_data = {
                        'task_id': task_id,
                        'generation_id': db_generation.id,
                        'generation_number': generation,
                        'individual_number': i,
                        'source_code': individual.get('code', ''),
                        'genome_data': individual.get('genome'),
                        'metadata': individual.get('metadata', {})
                    }
                    db_individual = self.db.create_individual(individual_data)
                    
                    # 保存适应度
                    for obj_name, fitness_value in individual.get('fitness', {}).items():
                        fitness_data = {
                            'individual_id': db_individual.id,
                            'objective_name': obj_name,
                            'value': fitness_value
                        }
                        self.db.create_fitness(fitness_data)
                
                # 调用进度回调
                for callback in self.progress_callbacks:
                    try:
                        callback(task_id, progress)
                    except Exception as e:
                        logger.error(f"进度回调失败: {e}")
                
                # 检查停止条件
                if self._check_stopping_conditions(task_id, config, stats, generation):
                    logger.info(f"任务 {task_id} 满足停止条件")
                    break
                
                # 保存检查点
                if generation % config.checkpoint_interval == 0:
                    await self._save_checkpoint(task_id, generation, population)
                
                # 选择和繁殖下一代
                if generation < config.max_generations - 1:
                    population = await self._evolve_population(population, config)
                
                # 添加延迟以避免过度占用资源
                await asyncio.sleep(0.01)
            
            # 任务完成
            self.db.update_task_status(task_id, TaskStatus.COMPLETED.value)
            
            # 调用完成回调
            for callback in self.completion_callbacks:
                try:
                    callback(task_id, TaskStatus.COMPLETED, population)
                except Exception as e:
                    logger.error(f"完成回调失败: {e}")
            
            logger.info(f"任务 {task_id} 完成")
            
        except Exception as e:
            logger.error(f"任务 {task_id} 执行失败: {e}")
            logger.error(traceback.format_exc())
            
            # 更新失败状态
            self.db.update_task_status(task_id, TaskStatus.FAILED.value, error_message=str(e))
            
            # 调用完成回调
            for callback in self.completion_callbacks:
                try:
                    callback(task_id, TaskStatus.FAILED, str(e))
                except Exception as e:
                    logger.error(f"完成回调失败: {e}")
        
        finally:
            # 清理
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
            if task_id in self.stop_flags:
                del self.stop_flags[task_id]
    
    async def _initialize_population(self, task_id: str, config: TaskConfig) -> List[Dict]:
        """初始化种群"""
        population = []
        
        for i in range(config.population_size):
            # 创建随机个体
            genome = Genome.random()
            code = genome.to_code()
            
            individual = {
                'id': f"{task_id}_gen0_ind{i}",
                'genome': genome.to_dict() if hasattr(genome, 'to_dict') else {},
                'code': code,
                'fitness': {},
                'metadata': {'created_at': datetime.now().isoformat()}
            }
            
            population.append(individual)
        
        return population
    
    async def _evaluate_population(self, task_id: str, population: List[Dict], config: TaskConfig):
        """评估种群"""
        if config.execution_mode == ExecutionMode.SEQUENTIAL:
            for individual in population:
                await self._evaluate_individual(individual, config)
        
        elif config.execution_mode == ExecutionMode.PARALLEL_THREAD:
            tasks = []
            for individual in population:
                task = asyncio.create_task(self._evaluate_individual(individual, config))
                tasks.append(task)
            
            await asyncio.gather(*tasks)
        
        else:
            # 其他执行模式的实现
            for individual in population:
                await self._evaluate_individual(individual, config)
    
    async def _evaluate_individual(self, individual: Dict, config: TaskConfig):
        """评估单个个体"""
        logger.debug(f"[DEBUG] 开始评估个体: {individual.get('id', 'unknown')}")
        
        try:
            # 创建基因组对象
            genome_data = individual.get('genome', {})
            if not genome_data:
                logger.warning(f"[DEBUG] 个体缺少基因组数据，使用随机基因组")
                genome = Genome.random()
            else:
                genome = Genome.from_dict(genome_data)
            
            logger.debug(f"[DEBUG] 基因组创建完成，代码长度: {len(genome.to_code())}")
            
            # 使用evaluation模块进行真实评估
            evaluation_result = await asyncio.get_event_loop().run_in_executor(
                self.thread_executor,
                evaluate_individual,
                genome,
                config.test_cases,
                {
                    'timeout_seconds': config.timeout_seconds,
                    'memory_limit_mb': config.memory_limit_mb,
                    'cpu_quota': config.cpu_quota,
                    'objectives': config.objectives,
                    'objective_weights': config.objective_weights
                }
            )
            
            logger.debug(f"[DEBUG] 评估完成，结果: {evaluation_result}")
            
            # 提取适应度分数
            fitness = evaluation_result.get('fitness', {})
            
            # 确保所有目标都有分数
            for objective in config.objectives:
                if objective not in fitness:
                    fitness[objective] = 0.0
                    logger.warning(f"[DEBUG] 目标 {objective} 缺少适应度分数，设为0.0")
            
            individual['fitness'] = fitness
            individual['evaluation_result'] = evaluation_result
            
            # 添加评估时间和元数据
            individual['metadata']['evaluated_at'] = datetime.now().isoformat()
            individual['metadata']['evaluation_time'] = evaluation_result.get('execution_time', 0.0)
            individual['metadata']['memory_usage'] = evaluation_result.get('memory_usage', 0)
            
            logger.debug(f"[DEBUG] 个体评估成功，适应度: {fitness}")
            
        except Exception as e:
            logger.error(f"[DEBUG] 个体评估失败: {str(e)}")
            logger.error(f"[DEBUG] 异常堆栈: {traceback.format_exc()}")
            
            # 设置默认适应度
            individual['fitness'] = {obj: 0.0 for obj in config.objectives}
            individual['evaluation_result'] = {
                'error': str(e),
                'fitness': {obj: 0.0 for obj in config.objectives}
            }
            individual['metadata']['evaluated_at'] = datetime.now().isoformat()
            individual['metadata']['evaluation_error'] = str(e)
    
    def _calculate_generation_stats(self, population: List[Dict], objectives: List[str]) -> Dict:
        """计算代统计信息"""
        if not population:
            return {
                'best_fitness': {},
                'average_fitness': {},
                'diversity_score': 0.0
            }
        
        best_fitness = {}
        average_fitness = {}
        
        for objective in objectives:
            values = [ind['fitness'].get(objective, 0.0) for ind in population]
            best_fitness[objective] = max(values)
            average_fitness[objective] = sum(values) / len(values)
        
        # 计算多样性分数（简化版本）
        diversity_score = len(set(ind['code'] for ind in population)) / len(population)
        
        return {
            'best_fitness': best_fitness,
            'average_fitness': average_fitness,
            'diversity_score': diversity_score
        }
    
    def _check_stopping_conditions(self, task_id: str, config: TaskConfig, 
                                 stats: Dict, generation: int) -> bool:
        """检查停止条件"""
        # 检查目标适应度
        if config.target_fitness:
            for obj, target in config.target_fitness.items():
                if stats['best_fitness'].get(obj, 0.0) >= target:
                    return True
        
        # 检查收敛性和停滞
        # 这里可以实现更复杂的停止条件
        
        return False
    
    async def _evolve_population(self, population: List[Dict], config: TaskConfig) -> List[Dict]:
        """进化种群"""
        # 简化的进化过程
        import random
        
        # 选择
        selected = self._selection(population, config)
        
        # 交叉和变异
        new_population = []
        for i in range(0, len(selected), 2):
            parent1 = selected[i]
            parent2 = selected[i + 1] if i + 1 < len(selected) else selected[0]
            
            # 交叉
            if random.random() < config.crossover_rate:
                child1, child2 = self._crossover(parent1, parent2)
            else:
                child1, child2 = parent1.copy(), parent2.copy()
            
            # 变异
            if random.random() < config.mutation_rate:
                child1 = self._mutate(child1)
            if random.random() < config.mutation_rate:
                child2 = self._mutate(child2)
            
            new_population.extend([child1, child2])
        
        return new_population[:config.population_size]
    
    def _selection(self, population: List[Dict], config: TaskConfig) -> List[Dict]:
        """选择操作"""
        # 简化的锦标赛选择
        import random
        
        selected = []
        tournament_size = 3
        
        for _ in range(config.population_size):
            tournament = random.sample(population, min(tournament_size, len(population)))
            winner = max(tournament, key=lambda x: sum(x['fitness'].values()))
            selected.append(winner.copy())
        
        return selected
    
    def _crossover(self, parent1: Dict, parent2: Dict) -> Tuple[Dict, Dict]:
        """交叉操作"""
        # 简化的交叉
        child1 = parent1.copy()
        child2 = parent2.copy()
        
        # 这里应该实现真正的基因交叉
        child1['metadata']['parents'] = [parent1['id'], parent2['id']]
        child2['metadata']['parents'] = [parent1['id'], parent2['id']]
        
        return child1, child2
    
    def _mutate(self, individual: Dict) -> Dict:
        """变异操作"""
        # 简化的变异
        mutated = individual.copy()
        mutated['metadata']['mutated'] = True
        
        # 这里应该实现真正的基因变异
        
        return mutated
    
    async def _save_checkpoint(self, task_id: str, generation: int, population: List[Dict]):
        """保存检查点"""
        checkpoint_file = self.checkpoint_dir / f"{task_id}_gen{generation}.json"
        
        checkpoint_data = {
            'task_id': task_id,
            'generation': generation,
            'population': population,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            with open(checkpoint_file, 'w') as f:
                json.dump(checkpoint_data, f, indent=2)
            
            logger.info(f"保存检查点: {checkpoint_file}")
        except Exception as e:
            logger.error(f"保存检查点失败: {e}")
    
    async def load_checkpoint(self, task_id: str, generation: int) -> Optional[List[Dict]]:
        """加载检查点"""
        checkpoint_file = self.checkpoint_dir / f"{task_id}_gen{generation}.json"
        
        try:
            if checkpoint_file.exists():
                with open(checkpoint_file, 'r') as f:
                    checkpoint_data = json.load(f)
                
                logger.info(f"加载检查点: {checkpoint_file}")
                return checkpoint_data['population']
        except Exception as e:
            logger.error(f"加载检查点失败: {e}")
        
        return None
    
    async def cleanup(self):
        """清理资源"""
        # 停止所有运行中的任务
        for task_id in list(self.running_tasks.keys()):
            await self.stop_task(task_id)
        
        # 关闭执行器
        self.thread_executor.shutdown(wait=True)
        self.process_executor.shutdown(wait=True)
        
        logger.info("任务管理器清理完成")

# 全局任务管理器实例
_task_manager: Optional[TaskManager] = None

def get_task_manager(**kwargs) -> TaskManager:
    """获取全局任务管理器实例"""
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager(**kwargs)
    return _task_manager