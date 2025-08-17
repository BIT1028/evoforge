#!/usr/bin/env python3
"""
进化策略模式实现

本模块实现了多种进化算法的策略模式，包括：
- 遗传算法 (Genetic Algorithm)
- 进化策略 (Evolution Strategy)
- 差分进化 (Differential Evolution)
- 粒子群优化 (Particle Swarm Optimization)
- 多目标优化算法 (Multi-Objective Optimization)

支持自适应参数调整和动态策略切换。
"""

import random
import math
import logging
import numpy as np
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import copy
import json

logger = logging.getLogger(__name__)

class EvolutionStrategy(Enum):
    """进化策略枚举"""
    GENETIC_ALGORITHM = "genetic_algorithm"
    EVOLUTION_STRATEGY = "evolution_strategy"
    DIFFERENTIAL_EVOLUTION = "differential_evolution"
    PARTICLE_SWARM = "particle_swarm"
    MULTI_OBJECTIVE = "multi_objective"
    HYBRID = "hybrid"

@dataclass
class StrategyConfig:
    """策略配置"""
    strategy_type: EvolutionStrategy = EvolutionStrategy.GENETIC_ALGORITHM
    population_size: int = 50
    max_generations: int = 100
    
    # 遗传算法参数
    crossover_rate: float = 0.8
    mutation_rate: float = 0.1
    elite_ratio: float = 0.1
    
    # 进化策略参数
    mu: int = 15  # 父代个体数
    lambda_: int = 100  # 子代个体数
    sigma: float = 0.1  # 变异步长
    tau: float = 0.1  # 步长自适应参数
    
    # 差分进化参数
    differential_weight: float = 0.5
    crossover_probability: float = 0.9
    
    # 粒子群优化参数
    inertia_weight: float = 0.9
    cognitive_weight: float = 2.0
    social_weight: float = 2.0
    
    # 多目标优化参数
    objectives: List[str] = field(default_factory=lambda: ["fitness", "complexity", "novelty"])
    objective_weights: Dict[str, float] = field(default_factory=dict)
    
    # 自适应参数
    adaptive_parameters: bool = True
    adaptation_interval: int = 10
    performance_threshold: float = 0.01
    stagnation_limit: int = 20

class Individual:
    """个体类 - 统一的个体表示"""
    
    def __init__(self, genome: Any = None, **kwargs):
        """初始化个体
        
        Args:
            genome: 基因组数据
            **kwargs: 其他属性
        """
        self.genome = genome
        self.fitness: Dict[str, float] = {}
        self.objectives: Dict[str, float] = {}
        self.constraints: Dict[str, float] = {}
        
        # 进化策略特有属性
        self.strategy_parameters: Dict[str, float] = {}
        
        # 粒子群优化特有属性
        self.velocity: Optional[np.ndarray] = None
        self.best_position: Optional[np.ndarray] = None
        self.best_fitness: float = float('-inf')
        
        # 其他属性
        self.age: int = 0
        self.generation: int = 0
        self.rank: int = 0
        self.crowding_distance: float = 0.0
        
        # 设置额外属性
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def copy(self) -> 'Individual':
        """深拷贝个体"""
        return copy.deepcopy(self)
    
    def get_fitness(self, objective: str = "fitness") -> float:
        """获取指定目标的适应度"""
        return self.objectives.get(objective, self.fitness.get(objective, 0.0))
    
    def set_fitness(self, objective: str, value: float):
        """设置指定目标的适应度"""
        self.objectives[objective] = value
        if objective == "fitness":
            self.fitness[objective] = value

class EvolutionStrategyBase(ABC):
    """进化策略基类"""
    
    def __init__(self, config: StrategyConfig):
        """初始化进化策略
        
        Args:
            config: 策略配置
        """
        self.config = config
        self.population: List[Individual] = []
        self.generation = 0
        self.best_individual: Optional[Individual] = None
        self.stagnation_counter = 0
        self.performance_history: List[float] = []
        
        logger.info(f"初始化进化策略: {config.strategy_type.value}")
    
    @abstractmethod
    def initialize_population(self) -> List[Individual]:
        """初始化种群"""
        pass
    
    @abstractmethod
    def selection(self, population: List[Individual]) -> List[Individual]:
        """选择操作"""
        pass
    
    @abstractmethod
    def reproduction(self, parents: List[Individual]) -> List[Individual]:
        """繁殖操作（交叉和变异）"""
        pass
    
    @abstractmethod
    def evaluate_fitness(self, individual: Individual) -> Dict[str, float]:
        """评估个体适应度"""
        pass
    
    def evolve_generation(self) -> Dict[str, Any]:
        """进化一代
        
        Returns:
            进化统计信息
        """
        logger.debug(f"开始第 {self.generation} 代进化")
        
        # 评估当前种群
        self._evaluate_population()
        
        # 选择父代
        parents = self.selection(self.population)
        
        # 生成子代
        offspring = self.reproduction(parents)
        
        # 评估子代
        for individual in offspring:
            individual.objectives = self.evaluate_fitness(individual)
        
        # 环境选择
        self.population = self._environmental_selection(self.population + offspring)
        
        # 更新最优个体
        self._update_best_individual()
        
        # 自适应参数调整
        if self.config.adaptive_parameters:
            self._adapt_parameters()
        
        # 更新统计信息
        stats = self._calculate_statistics()
        
        self.generation += 1
        logger.debug(f"第 {self.generation - 1} 代进化完成")
        
        return stats
    
    def _evaluate_population(self):
        """评估整个种群的适应度"""
        for individual in self.population:
            if not individual.objectives:
                individual.objectives = self.evaluate_fitness(individual)
    
    def _environmental_selection(self, combined_population: List[Individual]) -> List[Individual]:
        """环境选择 - 从父代和子代中选择下一代
        
        Args:
            combined_population: 父代和子代的合并种群
            
        Returns:
            下一代种群
        """
        # 按适应度排序
        combined_population.sort(key=lambda x: x.get_fitness(), reverse=True)
        
        # 选择前N个个体
        return combined_population[:self.config.population_size]
    
    def _update_best_individual(self):
        """更新最优个体"""
        if not self.population:
            return
        
        current_best = max(self.population, key=lambda x: x.get_fitness())
        
        if self.best_individual is None or current_best.get_fitness() > self.best_individual.get_fitness():
            self.best_individual = current_best.copy()
            self.stagnation_counter = 0
        else:
            self.stagnation_counter += 1
    
    def _adapt_parameters(self):
        """自适应参数调整"""
        if self.generation % self.config.adaptation_interval == 0:
            current_performance = self.best_individual.get_fitness() if self.best_individual else 0.0
            
            # 检查性能改进
            if len(self.performance_history) > 0:
                improvement = current_performance - self.performance_history[-1]
                
                if improvement < self.config.performance_threshold:
                    # 性能停滞，调整参数
                    self._adjust_parameters_for_stagnation()
                else:
                    # 性能改进，保持当前参数
                    self._adjust_parameters_for_improvement()
            
            self.performance_history.append(current_performance)
            
            # 保持历史记录大小
            if len(self.performance_history) > 50:
                self.performance_history = self.performance_history[-50:]
    
    def _adjust_parameters_for_stagnation(self):
        """为停滞情况调整参数"""
        # 增加变异率以增加多样性
        if hasattr(self.config, 'mutation_rate'):
            self.config.mutation_rate = min(0.5, self.config.mutation_rate * 1.1)
        
        logger.debug(f"检测到停滞，调整参数: mutation_rate={getattr(self.config, 'mutation_rate', 'N/A')}")
    
    def _adjust_parameters_for_improvement(self):
        """为改进情况调整参数"""
        # 略微降低变异率以保持收敛
        if hasattr(self.config, 'mutation_rate'):
            self.config.mutation_rate = max(0.01, self.config.mutation_rate * 0.95)
        
        logger.debug(f"检测到改进，调整参数: mutation_rate={getattr(self.config, 'mutation_rate', 'N/A')}")
    
    def _calculate_statistics(self) -> Dict[str, Any]:
        """计算进化统计信息"""
        if not self.population:
            return {}
        
        fitness_values = [ind.get_fitness() for ind in self.population]
        
        return {
            "generation": self.generation,
            "population_size": len(self.population),
            "best_fitness": max(fitness_values),
            "avg_fitness": sum(fitness_values) / len(fitness_values),
            "min_fitness": min(fitness_values),
            "fitness_std": np.std(fitness_values),
            "stagnation_counter": self.stagnation_counter,
            "diversity": self._calculate_diversity()
        }
    
    def _calculate_diversity(self) -> float:
        """计算种群多样性"""
        if len(self.population) < 2:
            return 0.0
        
        # 简化的多样性计算：基于适应度方差
        fitness_values = [ind.get_fitness() for ind in self.population]
        return float(np.std(fitness_values))

class GeneticAlgorithmStrategy(EvolutionStrategyBase):
    """遗传算法策略"""
    
    def initialize_population(self) -> List[Individual]:
        """初始化种群"""
        population = []
        
        for i in range(self.config.population_size):
            # 生成随机基因组
            genome = self._generate_random_genome()
            individual = Individual(genome=genome, generation=0)
            population.append(individual)
        
        self.population = population
        logger.info(f"初始化遗传算法种群，大小: {len(population)}")
        return population
    
    def _generate_random_genome(self) -> str:
        """生成随机基因组"""
        try:
            from .genome import create_random_genome
            genome_obj = create_random_genome()
            return json.dumps(genome_obj.to_dict())
        except ImportError:
            # 简单的随机基因组
            genome_length = random.randint(10, 50)
            genome = [random.randint(0, 100) for _ in range(genome_length)]
            return json.dumps(genome)
    
    def selection(self, population: List[Individual]) -> List[Individual]:
        """锦标赛选择"""
        parents = []
        tournament_size = 3
        
        for _ in range(len(population)):
            tournament = random.sample(population, min(tournament_size, len(population)))
            winner = max(tournament, key=lambda x: x.get_fitness())
            parents.append(winner)
        
        return parents
    
    def reproduction(self, parents: List[Individual]) -> List[Individual]:
        """繁殖操作：交叉和变异"""
        offspring = []
        
        for i in range(0, len(parents) - 1, 2):
            parent1 = parents[i]
            parent2 = parents[i + 1] if i + 1 < len(parents) else parents[0]
            
            # 交叉
            if random.random() < self.config.crossover_rate:
                child1, child2 = self._crossover(parent1, parent2)
            else:
                child1, child2 = parent1.copy(), parent2.copy()
            
            # 变异
            if random.random() < self.config.mutation_rate:
                child1 = self._mutate(child1)
            if random.random() < self.config.mutation_rate:
                child2 = self._mutate(child2)
            
            child1.generation = self.generation + 1
            child2.generation = self.generation + 1
            
            offspring.extend([child1, child2])
        
        return offspring
    
    def _crossover(self, parent1: Individual, parent2: Individual) -> Tuple[Individual, Individual]:
        """单点交叉"""
        try:
            genome1 = json.loads(parent1.genome)
            genome2 = json.loads(parent2.genome)
            
            if isinstance(genome1, list) and isinstance(genome2, list):
                # 简单列表交叉
                min_len = min(len(genome1), len(genome2))
                if min_len > 1:
                    crossover_point = random.randint(1, min_len - 1)
                    
                    new_genome1 = genome1[:crossover_point] + genome2[crossover_point:]
                    new_genome2 = genome2[:crossover_point] + genome1[crossover_point:]
                else:
                    # 长度太小，直接交换
                    new_genome1, new_genome2 = genome2.copy(), genome1.copy()
            else:
                # 复杂结构交叉（简化处理）
                new_genome1, new_genome2 = genome1, genome2
            
            child1 = Individual(genome=json.dumps(new_genome1))
            child2 = Individual(genome=json.dumps(new_genome2))
            
            return child1, child2
            
        except Exception as e:
            logger.warning(f"交叉操作失败: {e}")
            return parent1.copy(), parent2.copy()
    
    def _mutate(self, individual: Individual) -> Individual:
        """变异操作"""
        try:
            genome = json.loads(individual.genome)
            
            if isinstance(genome, list):
                # 简单列表变异
                if genome:
                    mutation_index = random.randint(0, len(genome) - 1)
                    if isinstance(genome[mutation_index], (int, float)):
                        genome[mutation_index] += random.gauss(0, 10)
                    else:
                        genome[mutation_index] = random.randint(0, 100)
            
            individual.genome = json.dumps(genome)
            
        except Exception as e:
            logger.warning(f"变异操作失败: {e}")
        
        return individual
    
    def evaluate_fitness(self, individual: Individual) -> Dict[str, float]:
        """评估个体适应度"""
        try:
            # 简化的适应度评估
            genome = json.loads(individual.genome)
            
            if isinstance(genome, list):
                # 基于基因组特征的适应度
                fitness = sum(genome) / len(genome) if genome else 0.0
                complexity = len(genome) / 100.0  # 归一化复杂度
                novelty = random.random()  # 简化的新颖性
            else:
                fitness = random.random()
                complexity = random.random()
                novelty = random.random()
            
            return {
                "fitness": max(0.0, fitness),
                "complexity": complexity,
                "novelty": novelty
            }
            
        except Exception as e:
            logger.warning(f"适应度评估失败: {e}")
            return {"fitness": 0.0, "complexity": 0.0, "novelty": 0.0}

class EvolutionStrategyES(EvolutionStrategyBase):
    """进化策略 (μ+λ)-ES"""
    
    def initialize_population(self) -> List[Individual]:
        """初始化种群"""
        population = []
        
        for i in range(self.config.mu):
            # 生成随机个体
            genome = np.random.randn(20)  # 20维实数向量
            individual = Individual(genome=genome.tolist())
            
            # 初始化策略参数（变异步长）
            individual.strategy_parameters = {
                "sigma": self.config.sigma
            }
            
            population.append(individual)
        
        self.population = population
        logger.info(f"初始化进化策略种群，大小: {len(population)}")
        return population
    
    def selection(self, population: List[Individual]) -> List[Individual]:
        """选择父代（所有个体都参与繁殖）"""
        return population
    
    def reproduction(self, parents: List[Individual]) -> List[Individual]:
        """生成λ个子代"""
        offspring = []
        
        for _ in range(self.config.lambda_):
            # 随机选择父代
            parent = random.choice(parents)
            
            # 创建子代
            child = self._create_offspring(parent)
            child.generation = self.generation + 1
            
            offspring.append(child)
        
        return offspring
    
    def _create_offspring(self, parent: Individual) -> Individual:
        """创建子代个体"""
        child = parent.copy()
        
        # 变异策略参数
        tau = self.config.tau
        tau_prime = tau / math.sqrt(2 * len(parent.genome))
        
        # 全局变异
        global_mutation = random.gauss(0, 1)
        
        # 更新策略参数
        old_sigma = child.strategy_parameters["sigma"]
        new_sigma = old_sigma * math.exp(tau_prime * global_mutation + tau * random.gauss(0, 1))
        child.strategy_parameters["sigma"] = max(0.001, new_sigma)  # 防止步长过小
        
        # 变异基因组
        genome = np.array(child.genome)
        mutations = np.random.normal(0, new_sigma, len(genome))
        child.genome = (genome + mutations).tolist()
        
        return child
    
    def evaluate_fitness(self, individual: Individual) -> Dict[str, float]:
        """评估个体适应度（球面函数）"""
        genome = np.array(individual.genome)
        
        # 球面函数：最小化 sum(x_i^2)
        sphere_value = np.sum(genome ** 2)
        fitness = 1.0 / (1.0 + sphere_value)  # 转换为最大化问题
        
        return {
            "fitness": fitness,
            "complexity": len(genome) / 100.0,
            "novelty": random.random()
        }
    
    def _environmental_selection(self, combined_population: List[Individual]) -> List[Individual]:
        """(μ+λ)选择策略"""
        # 按适应度排序
        combined_population.sort(key=lambda x: x.get_fitness(), reverse=True)
        
        # 选择前μ个个体作为下一代父代
        return combined_population[:self.config.mu]

class DifferentialEvolutionStrategy(EvolutionStrategyBase):
    """差分进化策略"""
    
    def initialize_population(self) -> List[Individual]:
        """初始化种群"""
        population = []
        dimension = 20  # 问题维度
        
        for i in range(self.config.population_size):
            # 在[-5, 5]范围内随机初始化
            genome = np.random.uniform(-5, 5, dimension)
            individual = Individual(genome=genome.tolist())
            population.append(individual)
        
        self.population = population
        logger.info(f"初始化差分进化种群，大小: {len(population)}")
        return population
    
    def selection(self, population: List[Individual]) -> List[Individual]:
        """差分进化不需要显式选择"""
        return population
    
    def reproduction(self, parents: List[Individual]) -> List[Individual]:
        """差分进化的变异和交叉"""
        offspring = []
        
        for i, target in enumerate(parents):
            # 选择三个不同的个体
            candidates = [j for j in range(len(parents)) if j != i]
            if len(candidates) < 3:
                offspring.append(target.copy())
                continue
            
            a, b, c = random.sample(candidates, 3)
            
            # 差分变异
            mutant = self._differential_mutation(parents[a], parents[b], parents[c])
            
            # 交叉
            trial = self._binomial_crossover(target, mutant)
            trial.generation = self.generation + 1
            
            offspring.append(trial)
        
        return offspring
    
    def _differential_mutation(self, a: Individual, b: Individual, c: Individual) -> Individual:
        """差分变异：V = A + F * (B - C)"""
        genome_a = np.array(a.genome)
        genome_b = np.array(b.genome)
        genome_c = np.array(c.genome)
        
        mutant_genome = genome_a + self.config.differential_weight * (genome_b - genome_c)
        
        return Individual(genome=mutant_genome.tolist())
    
    def _binomial_crossover(self, target: Individual, mutant: Individual) -> Individual:
        """二项式交叉"""
        target_genome = np.array(target.genome)
        mutant_genome = np.array(mutant.genome)
        
        # 确保至少有一个基因来自变异向量
        j_rand = random.randint(0, len(target_genome) - 1)
        
        trial_genome = target_genome.copy()
        for j in range(len(target_genome)):
            if random.random() < self.config.crossover_probability or j == j_rand:
                trial_genome[j] = mutant_genome[j]
        
        return Individual(genome=trial_genome.tolist())
    
    def evaluate_fitness(self, individual: Individual) -> Dict[str, float]:
        """评估个体适应度（Rastrigin函数）"""
        genome = np.array(individual.genome)
        n = len(genome)
        
        # Rastrigin函数：最小化
        rastrigin_value = 10 * n + np.sum(genome**2 - 10 * np.cos(2 * np.pi * genome))
        fitness = 1.0 / (1.0 + rastrigin_value)  # 转换为最大化问题
        
        return {
            "fitness": fitness,
            "complexity": len(genome) / 100.0,
            "novelty": random.random()
        }
    
    def _environmental_selection(self, combined_population: List[Individual]) -> List[Individual]:
        """贪婪选择：每个位置选择更好的个体"""
        selected = []
        
        # 假设combined_population的前半部分是父代，后半部分是子代
        mid = len(combined_population) // 2
        parents = combined_population[:mid]
        offspring = combined_population[mid:]
        
        for i in range(min(len(parents), len(offspring))):
            if offspring[i].get_fitness() >= parents[i].get_fitness():
                selected.append(offspring[i])
            else:
                selected.append(parents[i])
        
        # 如果数量不匹配，添加剩余的个体
        if len(parents) > len(offspring):
            selected.extend(parents[len(offspring):])
        elif len(offspring) > len(parents):
            selected.extend(offspring[len(parents):])
        
        return selected[:self.config.population_size]

class EvolutionStrategyFactory:
    """进化策略工厂类"""
    
    @staticmethod
    def create_strategy(config: StrategyConfig) -> EvolutionStrategyBase:
        """创建进化策略实例
        
        Args:
            config: 策略配置
            
        Returns:
            进化策略实例
        """
        strategy_map = {
            EvolutionStrategy.GENETIC_ALGORITHM: GeneticAlgorithmStrategy,
            EvolutionStrategy.EVOLUTION_STRATEGY: EvolutionStrategyES,
            EvolutionStrategy.DIFFERENTIAL_EVOLUTION: DifferentialEvolutionStrategy,
        }
        
        strategy_class = strategy_map.get(config.strategy_type)
        if strategy_class is None:
            raise ValueError(f"不支持的进化策略: {config.strategy_type}")
        
        logger.info(f"创建进化策略: {config.strategy_type.value}")
        return strategy_class(config)

class AdaptiveEvolutionManager:
    """自适应进化管理器
    
    根据进化过程的表现动态切换进化策略和调整参数。
    """
    
    def __init__(self, initial_config: StrategyConfig):
        """初始化自适应进化管理器
        
        Args:
            initial_config: 初始策略配置
        """
        self.current_config = initial_config
        self.current_strategy = EvolutionStrategyFactory.create_strategy(initial_config)
        self.strategy_history: List[Tuple[EvolutionStrategy, float]] = []
        self.performance_window = 10  # 性能评估窗口
        
        logger.info("初始化自适应进化管理器")
    
    def evolve(self, num_generations: int) -> List[Dict[str, Any]]:
        """执行自适应进化
        
        Args:
            num_generations: 进化代数
            
        Returns:
            进化统计信息列表
        """
        stats_history = []
        
        # 初始化种群
        self.current_strategy.initialize_population()
        
        for generation in range(num_generations):
            # 执行一代进化
            stats = self.current_strategy.evolve_generation()
            stats_history.append(stats)
            
            # 记录策略性能
            self.strategy_history.append((
                self.current_config.strategy_type,
                stats.get("best_fitness", 0.0)
            ))
            
            # 检查是否需要切换策略
            if generation > 0 and generation % 20 == 0:
                self._consider_strategy_switch(stats_history[-self.performance_window:])
            
            logger.debug(f"第 {generation} 代完成，最佳适应度: {stats.get('best_fitness', 0.0)}")
        
        return stats_history
    
    def _consider_strategy_switch(self, recent_stats: List[Dict[str, Any]]):
        """考虑是否切换策略
        
        Args:
            recent_stats: 最近的统计信息
        """
        if len(recent_stats) < self.performance_window:
            return
        
        # 计算最近的性能改进
        recent_fitness = [stats.get("best_fitness", 0.0) for stats in recent_stats]
        improvement = recent_fitness[-1] - recent_fitness[0]
        
        # 如果改进很小，考虑切换策略
        if improvement < 0.01:
            new_strategy_type = self._select_alternative_strategy()
            if new_strategy_type != self.current_config.strategy_type:
                self._switch_strategy(new_strategy_type)
    
    def _select_alternative_strategy(self) -> EvolutionStrategy:
        """选择替代策略
        
        Returns:
            新的策略类型
        """
        # 简单的策略轮换
        strategies = [
            EvolutionStrategy.GENETIC_ALGORITHM,
            EvolutionStrategy.EVOLUTION_STRATEGY,
            EvolutionStrategy.DIFFERENTIAL_EVOLUTION
        ]
        
        current_index = strategies.index(self.current_config.strategy_type)
        next_index = (current_index + 1) % len(strategies)
        
        return strategies[next_index]
    
    def _switch_strategy(self, new_strategy_type: EvolutionStrategy):
        """切换到新策略
        
        Args:
            new_strategy_type: 新的策略类型
        """
        logger.info(f"切换策略: {self.current_config.strategy_type.value} -> {new_strategy_type.value}")
        
        # 保存当前种群
        current_population = self.current_strategy.population
        
        # 创建新配置和策略
        new_config = copy.deepcopy(self.current_config)
        new_config.strategy_type = new_strategy_type
        
        new_strategy = EvolutionStrategyFactory.create_strategy(new_config)
        
        # 迁移种群（如果可能）
        try:
            new_strategy.population = self._migrate_population(current_population, new_strategy)
        except Exception as e:
            logger.warning(f"种群迁移失败，重新初始化: {e}")
            new_strategy.initialize_population()
        
        # 更新当前策略
        self.current_config = new_config
        self.current_strategy = new_strategy
    
    def _migrate_population(self, old_population: List[Individual], new_strategy: EvolutionStrategyBase) -> List[Individual]:
        """迁移种群到新策略
        
        Args:
            old_population: 旧种群
            new_strategy: 新策略
            
        Returns:
            迁移后的种群
        """
        # 简单的迁移：保持最优个体，其余重新初始化
        migrated_population = []
        
        if old_population:
            # 保留最优个体
            best_individual = max(old_population, key=lambda x: x.get_fitness())
            migrated_population.append(best_individual)
        
        # 重新初始化其余个体
        remaining_size = new_strategy.config.population_size - len(migrated_population)
        new_individuals = new_strategy.initialize_population()
        
        if len(new_individuals) > remaining_size:
            migrated_population.extend(new_individuals[:remaining_size])
        else:
            migrated_population.extend(new_individuals)
        
        return migrated_population
    
    def get_best_individual(self) -> Optional[Individual]:
        """获取当前最优个体"""
        return self.current_strategy.best_individual
    
    def get_current_stats(self) -> Dict[str, Any]:
        """获取当前统计信息"""
        stats = self.current_strategy._calculate_statistics()
        stats["current_strategy"] = self.current_config.strategy_type.value
        return stats
    
    def adapt_strategy(self, performance_metrics: Dict[str, Any]) -> EvolutionStrategyBase:
        """根据性能指标自适应调整策略
        
        Args:
            performance_metrics: 性能指标字典
            
        Returns:
            调整后的策略实例
        """
        try:
            # 检查是否需要切换策略
            convergence_rate = performance_metrics.get('convergence_rate', 0.0)
            diversity = performance_metrics.get('diversity', 1.0)
            
            # 如果收敛率过高且多样性过低，考虑切换策略
            if convergence_rate > 0.8 and diversity < 0.2:
                new_strategy_type = self._select_alternative_strategy()
                if new_strategy_type != self.current_config.strategy_type:
                    self._switch_strategy(new_strategy_type)
                    logger.info(f"基于性能指标切换策略到: {new_strategy_type.value}")
            
            return self.current_strategy
            
        except Exception as e:
            logger.error(f"自适应策略调整失败: {e}")
            return self.current_strategy