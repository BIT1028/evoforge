"""元进化模块 - 实现进化算法的自我改进

本模块实现了元进化机制，让进化算法能够:
- MetaEvolutionEngine: 元进化引擎，优化进化策略本身
- StrategyEvolution: 策略进化，改进选择、变异、交叉等算子
- ParameterOptimization: 参数优化，自动调整进化参数
- AlgorithmDiscovery: 算法发现，探索新的进化方法
- PerformanceAnalyzer: 性能分析器，评估不同策略的效果
"""

import logging
import random
import time
import json
import copy
import math
from typing import Dict, List, Any, Optional, Tuple, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import uuid
import numpy as np
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

class EvolutionStrategy(Enum):
    """进化策略类型"""
    GENETIC_ALGORITHM = "genetic_algorithm"
    EVOLUTION_STRATEGY = "evolution_strategy"
    DIFFERENTIAL_EVOLUTION = "differential_evolution"
    PARTICLE_SWARM = "particle_swarm"
    SIMULATED_ANNEALING = "simulated_annealing"
    HYBRID = "hybrid"
    CUSTOM = "custom"

class OptimizationObjective(Enum):
    """优化目标类型"""
    CONVERGENCE_SPEED = "convergence_speed"  # 收敛速度
    SOLUTION_QUALITY = "solution_quality"    # 解质量
    DIVERSITY_MAINTENANCE = "diversity_maintenance"  # 多样性维持
    ROBUSTNESS = "robustness"  # 鲁棒性
    ADAPTABILITY = "adaptability"  # 适应性
    EFFICIENCY = "efficiency"  # 效率

@dataclass
class EvolutionParameters:
    """进化参数配置
    
    包含所有可调整的进化算法参数。
    """
    population_size: int = 100
    mutation_rate: float = 0.1
    crossover_rate: float = 0.8
    selection_pressure: float = 2.0
    elitism_ratio: float = 0.1
    diversity_threshold: float = 0.1
    max_generations: int = 1000
    convergence_threshold: float = 1e-6
    
    # 高级参数
    adaptive_mutation: bool = True
    dynamic_population: bool = False
    multi_objective: bool = True
    niching_enabled: bool = False
    
    # 策略特定参数
    strategy_params: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'population_size': self.population_size,
            'mutation_rate': self.mutation_rate,
            'crossover_rate': self.crossover_rate,
            'selection_pressure': self.selection_pressure,
            'elitism_ratio': self.elitism_ratio,
            'diversity_threshold': self.diversity_threshold,
            'max_generations': self.max_generations,
            'convergence_threshold': self.convergence_threshold,
            'adaptive_mutation': self.adaptive_mutation,
            'dynamic_population': self.dynamic_population,
            'multi_objective': self.multi_objective,
            'niching_enabled': self.niching_enabled,
            'strategy_params': self.strategy_params
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EvolutionParameters':
        """从字典创建"""
        return cls(**data)
    
    def mutate(self, mutation_strength: float = 0.1) -> 'EvolutionParameters':
        """变异参数"""
        new_params = copy.deepcopy(self)
        
        # 变异数值参数
        if random.random() < 0.3:
            new_params.population_size = max(10, int(self.population_size * (1 + random.gauss(0, mutation_strength))))
        
        if random.random() < 0.5:
            new_params.mutation_rate = max(0.001, min(0.5, self.mutation_rate * (1 + random.gauss(0, mutation_strength))))
        
        if random.random() < 0.5:
            new_params.crossover_rate = max(0.1, min(1.0, self.crossover_rate * (1 + random.gauss(0, mutation_strength))))
        
        if random.random() < 0.3:
            new_params.selection_pressure = max(1.0, min(5.0, self.selection_pressure * (1 + random.gauss(0, mutation_strength))))
        
        if random.random() < 0.3:
            new_params.elitism_ratio = max(0.0, min(0.3, self.elitism_ratio * (1 + random.gauss(0, mutation_strength))))
        
        # 变异布尔参数
        if random.random() < 0.2:
            new_params.adaptive_mutation = not self.adaptive_mutation
        
        if random.random() < 0.1:
            new_params.dynamic_population = not self.dynamic_population
        
        if random.random() < 0.1:
            new_params.niching_enabled = not self.niching_enabled
        
        logger.debug(f"[META_EVOLUTION_DEBUG] 参数变异完成")
        return new_params

@dataclass
class StrategyConfiguration:
    """策略配置
    
    定义完整的进化策略配置。
    """
    id: str
    strategy_type: EvolutionStrategy
    parameters: EvolutionParameters
    operators: Dict[str, str]  # 算子配置
    fitness_function: str  # 适应度函数类型
    performance_history: List[Dict[str, float]] = field(default_factory=list)
    creation_time: datetime = field(default_factory=datetime.now)
    usage_count: int = 0
    success_rate: float = 0.0
    
    def evaluate_performance(self) -> float:
        """评估策略性能"""
        if not self.performance_history:
            return 0.0
        
        # 计算最近性能的加权平均
        recent_performances = self.performance_history[-10:]  # 最近10次
        weights = [math.exp(-i * 0.1) for i in range(len(recent_performances))]  # 指数衰减权重
        
        weighted_sum = sum(perf.get('overall_score', 0) * weight 
                          for perf, weight in zip(recent_performances, weights))
        weight_sum = sum(weights)
        
        return weighted_sum / weight_sum if weight_sum > 0 else 0.0
    
    def add_performance_record(self, performance: Dict[str, float]):
        """添加性能记录"""
        self.performance_history.append({
            **performance,
            'timestamp': datetime.now().isoformat()
        })
        
        # 保持最近100条记录
        if len(self.performance_history) > 100:
            self.performance_history = self.performance_history[-100:]
        
        # 更新使用统计
        self.usage_count += 1
        
        # 更新成功率
        recent_successes = sum(1 for p in self.performance_history[-20:] 
                             if p.get('overall_score', 0) > 0.6)
        self.success_rate = recent_successes / min(20, len(self.performance_history))
        
        logger.debug(f"[META_EVOLUTION_DEBUG] 策略 {self.id} 性能记录已更新")

class PerformanceAnalyzer:
    """性能分析器
    
    分析不同进化策略的性能表现。
    """
    
    def __init__(self):
        """初始化性能分析器"""
        self.analysis_history: List[Dict[str, Any]] = []
        
        logger.debug(f"[PERFORMANCE_ANALYZER_DEBUG] 初始化性能分析器")
    
    def analyze_strategy_performance(self, strategies: List[StrategyConfiguration], 
                                   current_environment: Dict[str, Any]) -> Dict[str, Any]:
        """分析策略性能"""
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'environment': current_environment,
            'strategy_rankings': [],
            'performance_insights': [],
            'recommendations': []
        }
        
        # 计算每个策略的综合评分
        strategy_scores = []
        for strategy in strategies:
            score = self._calculate_comprehensive_score(strategy, current_environment)
            strategy_scores.append({
                'strategy_id': strategy.id,
                'strategy_type': strategy.strategy_type.value,
                'score': score,
                'usage_count': strategy.usage_count,
                'success_rate': strategy.success_rate,
                'recent_performance': strategy.evaluate_performance()
            })
        
        # 按分数排序
        strategy_scores.sort(key=lambda x: x['score'], reverse=True)
        analysis['strategy_rankings'] = strategy_scores
        
        # 生成洞察
        insights = self._generate_performance_insights(strategy_scores, current_environment)
        analysis['performance_insights'] = insights
        
        # 生成建议
        recommendations = self._generate_optimization_recommendations(strategy_scores, current_environment)
        analysis['recommendations'] = recommendations
        
        self.analysis_history.append(analysis)
        
        logger.debug(f"[PERFORMANCE_ANALYZER_DEBUG] 完成策略性能分析，分析了 {len(strategies)} 个策略")
        return analysis
    
    def _calculate_comprehensive_score(self, strategy: StrategyConfiguration, 
                                     environment: Dict[str, Any]) -> float:
        """计算综合评分"""
        base_performance = strategy.evaluate_performance()
        
        # 环境适应性加权
        environment_complexity = environment.get('complexity', 0.5)
        if strategy.strategy_type == EvolutionStrategy.HYBRID and environment_complexity > 0.7:
            base_performance *= 1.2  # 复杂环境下混合策略加分
        elif strategy.strategy_type == EvolutionStrategy.GENETIC_ALGORITHM and environment_complexity < 0.3:
            base_performance *= 1.1  # 简单环境下遗传算法加分
        
        # 使用频率调整
        usage_factor = min(1.0, strategy.usage_count / 100.0)  # 使用经验加分
        
        # 成功率权重
        success_weight = strategy.success_rate
        
        # 综合评分
        comprehensive_score = (base_performance * 0.5 + 
                             usage_factor * 0.2 + 
                             success_weight * 0.3)
        
        return comprehensive_score
    
    def _generate_performance_insights(self, strategy_scores: List[Dict[str, Any]], 
                                     environment: Dict[str, Any]) -> List[str]:
        """生成性能洞察"""
        insights = []
        
        if not strategy_scores:
            return insights
        
        # 最佳策略分析
        best_strategy = strategy_scores[0]
        insights.append(f"当前最佳策略: {best_strategy['strategy_type']} (评分: {best_strategy['score']:.3f})")
        
        # 性能差异分析
        if len(strategy_scores) > 1:
            score_gap = best_strategy['score'] - strategy_scores[1]['score']
            if score_gap > 0.2:
                insights.append("存在明显的性能差异，最佳策略显著优于其他策略")
            elif score_gap < 0.05:
                insights.append("策略性能相近，可能需要更细致的调优")
        
        # 使用模式分析
        high_usage_strategies = [s for s in strategy_scores if s['usage_count'] > 50]
        if high_usage_strategies:
            avg_performance = sum(s['score'] for s in high_usage_strategies) / len(high_usage_strategies)
            insights.append(f"高使用频率策略平均性能: {avg_performance:.3f}")
        
        # 环境适应性分析
        environment_complexity = environment.get('complexity', 0.5)
        if environment_complexity > 0.8:
            insights.append("当前环境复杂度很高，建议使用自适应策略")
        elif environment_complexity < 0.3:
            insights.append("当前环境相对简单，可以使用更直接的优化方法")
        
        return insights
    
    def _generate_optimization_recommendations(self, strategy_scores: List[Dict[str, Any]], 
                                             environment: Dict[str, Any]) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        if not strategy_scores:
            return recommendations
        
        # 基于性能的建议
        low_performance_strategies = [s for s in strategy_scores if s['score'] < 0.4]
        if low_performance_strategies:
            recommendations.append(f"建议优化或替换 {len(low_performance_strategies)} 个低性能策略")
        
        # 基于多样性的建议
        strategy_types = set(s['strategy_type'] for s in strategy_scores)
        if len(strategy_types) < 3:
            recommendations.append("建议增加策略多样性，探索更多算法类型")
        
        # 基于环境的建议
        environment_complexity = environment.get('complexity', 0.5)
        change_rate = environment.get('change_rate', 0.0)
        
        if change_rate > 0.5:
            recommendations.append("环境变化较快，建议增强策略的适应性")
        
        if environment_complexity > 0.7:
            recommendations.append("环境复杂度高，建议使用混合策略或元启发式算法")
        
        # 参数调优建议
        best_strategy = strategy_scores[0]
        if best_strategy['score'] < 0.7:
            recommendations.append("最佳策略性能仍有提升空间，建议进行参数微调")
        
        return recommendations

class StrategyEvolution:
    """策略进化器
    
    负责进化和改进进化策略本身。
    """
    
    def __init__(self, performance_analyzer: PerformanceAnalyzer):
        """初始化策略进化器"""
        self.performance_analyzer = performance_analyzer
        self.strategy_population: List[StrategyConfiguration] = []
        self.generation_count = 0
        
        # 初始化基础策略
        self._initialize_base_strategies()
        
        logger.debug(f"[STRATEGY_EVOLUTION_DEBUG] 初始化策略进化器，初始策略数: {len(self.strategy_population)}")
    
    def _initialize_base_strategies(self):
        """初始化基础策略集合"""
        base_strategies = [
            {
                'type': EvolutionStrategy.GENETIC_ALGORITHM,
                'params': EvolutionParameters(population_size=100, mutation_rate=0.1, crossover_rate=0.8)
            },
            {
                'type': EvolutionStrategy.EVOLUTION_STRATEGY,
                'params': EvolutionParameters(population_size=50, mutation_rate=0.2, selection_pressure=3.0)
            },
            {
                'type': EvolutionStrategy.DIFFERENTIAL_EVOLUTION,
                'params': EvolutionParameters(population_size=80, mutation_rate=0.15, crossover_rate=0.9)
            },
            {
                'type': EvolutionStrategy.HYBRID,
                'params': EvolutionParameters(population_size=120, mutation_rate=0.12, crossover_rate=0.85, adaptive_mutation=True)
            }
        ]
        
        for i, strategy_def in enumerate(base_strategies):
            strategy = StrategyConfiguration(
                id=f"base_strategy_{i}",
                strategy_type=strategy_def['type'],
                parameters=strategy_def['params'],
                operators=self._get_default_operators(strategy_def['type']),
                fitness_function="multi_objective"
            )
            self.strategy_population.append(strategy)
    
    def _get_default_operators(self, strategy_type: EvolutionStrategy) -> Dict[str, str]:
        """获取默认算子配置"""
        if strategy_type == EvolutionStrategy.GENETIC_ALGORITHM:
            return {
                'selection': 'tournament',
                'crossover': 'uniform',
                'mutation': 'gaussian',
                'replacement': 'generational'
            }
        elif strategy_type == EvolutionStrategy.EVOLUTION_STRATEGY:
            return {
                'selection': 'plus',
                'mutation': 'self_adaptive',
                'recombination': 'intermediate',
                'replacement': 'mu_plus_lambda'
            }
        elif strategy_type == EvolutionStrategy.DIFFERENTIAL_EVOLUTION:
            return {
                'mutation': 'de_rand_1',
                'crossover': 'binomial',
                'selection': 'greedy'
            }
        else:  # HYBRID
            return {
                'selection': 'adaptive',
                'crossover': 'adaptive',
                'mutation': 'adaptive',
                'replacement': 'elitist'
            }
    
    def evolve_strategies(self, current_environment: Dict[str, Any], 
                         performance_feedback: List[Dict[str, Any]]) -> List[StrategyConfiguration]:
        """进化策略集合"""
        self.generation_count += 1
        
        logger.debug(f"[STRATEGY_EVOLUTION_DEBUG] 开始策略进化第 {self.generation_count} 代")
        
        # 更新策略性能记录
        self._update_strategy_performance(performance_feedback)
        
        # 分析当前策略性能
        analysis = self.performance_analyzer.analyze_strategy_performance(
            self.strategy_population, current_environment
        )
        
        # 选择优秀策略
        elite_strategies = self._select_elite_strategies(analysis)
        
        # 生成新策略
        new_strategies = self._generate_new_strategies(elite_strategies, current_environment)
        
        # 更新策略种群
        self._update_strategy_population(elite_strategies, new_strategies)
        
        logger.debug(f"[STRATEGY_EVOLUTION_DEBUG] 策略进化完成，当前策略数: {len(self.strategy_population)}")
        return self.strategy_population
    
    def _update_strategy_performance(self, performance_feedback: List[Dict[str, Any]]):
        """更新策略性能记录"""
        strategy_dict = {s.id: s for s in self.strategy_population}
        
        for feedback in performance_feedback:
            strategy_id = feedback.get('strategy_id')
            if strategy_id in strategy_dict:
                strategy_dict[strategy_id].add_performance_record(feedback)
    
    def _select_elite_strategies(self, analysis: Dict[str, Any]) -> List[StrategyConfiguration]:
        """选择精英策略"""
        rankings = analysis['strategy_rankings']
        
        # 选择前50%的策略
        elite_count = max(2, len(rankings) // 2)
        elite_ids = [r['strategy_id'] for r in rankings[:elite_count]]
        
        elite_strategies = [s for s in self.strategy_population if s.id in elite_ids]
        
        logger.debug(f"[STRATEGY_EVOLUTION_DEBUG] 选择了 {len(elite_strategies)} 个精英策略")
        return elite_strategies
    
    def _generate_new_strategies(self, elite_strategies: List[StrategyConfiguration], 
                               environment: Dict[str, Any]) -> List[StrategyConfiguration]:
        """生成新策略"""
        new_strategies = []
        
        # 参数变异生成新策略
        for elite in elite_strategies[:3]:  # 对前3个精英策略进行变异
            mutated_params = elite.parameters.mutate(mutation_strength=0.1)
            
            new_strategy = StrategyConfiguration(
                id=f"mutated_{elite.id}_{self.generation_count}",
                strategy_type=elite.strategy_type,
                parameters=mutated_params,
                operators=copy.deepcopy(elite.operators),
                fitness_function=elite.fitness_function
            )
            new_strategies.append(new_strategy)
        
        # 策略杂交生成新策略
        if len(elite_strategies) >= 2:
            for i in range(min(2, len(elite_strategies) - 1)):
                parent1 = elite_strategies[i]
                parent2 = elite_strategies[i + 1]
                
                crossover_strategy = self._crossover_strategies(parent1, parent2)
                new_strategies.append(crossover_strategy)
        
        # 基于环境生成适应性策略
        if environment.get('complexity', 0.5) > 0.8:
            adaptive_strategy = self._create_adaptive_strategy(environment)
            new_strategies.append(adaptive_strategy)
        
        # 随机探索新策略
        if random.random() < 0.2:  # 20%概率生成随机策略
            random_strategy = self._create_random_strategy()
            new_strategies.append(random_strategy)
        
        logger.debug(f"[STRATEGY_EVOLUTION_DEBUG] 生成了 {len(new_strategies)} 个新策略")
        return new_strategies
    
    def _crossover_strategies(self, parent1: StrategyConfiguration, 
                            parent2: StrategyConfiguration) -> StrategyConfiguration:
        """策略杂交"""
        # 参数杂交
        child_params = EvolutionParameters()
        
        # 数值参数取平均或随机选择
        child_params.population_size = random.choice([parent1.parameters.population_size, parent2.parameters.population_size])
        child_params.mutation_rate = (parent1.parameters.mutation_rate + parent2.parameters.mutation_rate) / 2
        child_params.crossover_rate = (parent1.parameters.crossover_rate + parent2.parameters.crossover_rate) / 2
        child_params.selection_pressure = (parent1.parameters.selection_pressure + parent2.parameters.selection_pressure) / 2
        child_params.elitism_ratio = (parent1.parameters.elitism_ratio + parent2.parameters.elitism_ratio) / 2
        
        # 布尔参数随机选择
        child_params.adaptive_mutation = random.choice([parent1.parameters.adaptive_mutation, parent2.parameters.adaptive_mutation])
        child_params.dynamic_population = random.choice([parent1.parameters.dynamic_population, parent2.parameters.dynamic_population])
        child_params.multi_objective = random.choice([parent1.parameters.multi_objective, parent2.parameters.multi_objective])
        
        # 策略类型选择
        strategy_type = random.choice([parent1.strategy_type, parent2.strategy_type])
        if random.random() < 0.1:  # 10%概率生成混合策略
            strategy_type = EvolutionStrategy.HYBRID
        
        # 算子配置杂交
        child_operators = {}
        all_operator_keys = set(parent1.operators.keys()) | set(parent2.operators.keys())
        for key in all_operator_keys:
            if key in parent1.operators and key in parent2.operators:
                child_operators[key] = random.choice([parent1.operators[key], parent2.operators[key]])
            elif key in parent1.operators:
                child_operators[key] = parent1.operators[key]
            else:
                child_operators[key] = parent2.operators[key]
        
        child_strategy = StrategyConfiguration(
            id=f"crossover_{parent1.id}_{parent2.id}_{self.generation_count}",
            strategy_type=strategy_type,
            parameters=child_params,
            operators=child_operators,
            fitness_function=random.choice([parent1.fitness_function, parent2.fitness_function])
        )
        
        return child_strategy
    
    def _create_adaptive_strategy(self, environment: Dict[str, Any]) -> StrategyConfiguration:
        """创建适应性策略"""
        complexity = environment.get('complexity', 0.5)
        change_rate = environment.get('change_rate', 0.0)
        
        # 根据环境特征调整参数
        params = EvolutionParameters()
        
        if complexity > 0.8:
            params.population_size = 150  # 复杂环境需要更大种群
            params.mutation_rate = 0.15   # 更高变异率
            params.adaptive_mutation = True
            params.multi_objective = True
        
        if change_rate > 0.5:
            params.dynamic_population = True  # 动态种群适应变化
            params.diversity_threshold = 0.15  # 更高多样性要求
        
        strategy = StrategyConfiguration(
            id=f"adaptive_{self.generation_count}_{int(time.time())}",
            strategy_type=EvolutionStrategy.HYBRID,
            parameters=params,
            operators={
                'selection': 'adaptive',
                'crossover': 'adaptive',
                'mutation': 'adaptive',
                'replacement': 'diversity_preserving'
            },
            fitness_function="adaptive_multi_objective"
        )
        
        return strategy
    
    def _create_random_strategy(self) -> StrategyConfiguration:
        """创建随机策略"""
        strategy_types = list(EvolutionStrategy)
        strategy_type = random.choice(strategy_types)
        
        params = EvolutionParameters(
            population_size=random.randint(50, 200),
            mutation_rate=random.uniform(0.05, 0.3),
            crossover_rate=random.uniform(0.6, 0.95),
            selection_pressure=random.uniform(1.5, 4.0),
            elitism_ratio=random.uniform(0.05, 0.25),
            adaptive_mutation=random.choice([True, False]),
            dynamic_population=random.choice([True, False]),
            multi_objective=random.choice([True, False])
        )
        
        strategy = StrategyConfiguration(
            id=f"random_{self.generation_count}_{int(time.time())}",
            strategy_type=strategy_type,
            parameters=params,
            operators=self._get_default_operators(strategy_type),
            fitness_function=random.choice(["single_objective", "multi_objective", "adaptive_multi_objective"])
        )
        
        return strategy
    
    def _update_strategy_population(self, elite_strategies: List[StrategyConfiguration], 
                                  new_strategies: List[StrategyConfiguration]):
        """更新策略种群"""
        # 保留精英策略和新策略
        self.strategy_population = elite_strategies + new_strategies
        
        # 限制种群大小
        max_population = 20
        if len(self.strategy_population) > max_population:
            # 按性能排序，保留最好的
            self.strategy_population.sort(key=lambda s: s.evaluate_performance(), reverse=True)
            self.strategy_population = self.strategy_population[:max_population]
        
        logger.debug(f"[STRATEGY_EVOLUTION_DEBUG] 策略种群已更新，当前大小: {len(self.strategy_population)}")

class MetaEvolutionEngine:
    """元进化引擎 - 整合所有元进化功能
    
    这是元进化的核心引擎，负责协调策略进化、性能分析等功能。
    """
    
    def __init__(self):
        """初始化元进化引擎"""
        self.performance_analyzer = PerformanceAnalyzer()
        self.strategy_evolution = StrategyEvolution(self.performance_analyzer)
        
        self.evolution_history: List[Dict[str, Any]] = []
        self.current_best_strategy: Optional[StrategyConfiguration] = None
        self.meta_generation_count = 0
        
        logger.debug(f"[META_EVOLUTION_DEBUG] 初始化元进化引擎")
    
    def evolve_evolution(self, current_environment: Dict[str, Any], 
                        performance_feedback: List[Dict[str, Any]]) -> Dict[str, Any]:
        """执行元进化 - 进化进化算法本身
        
        这是元进化的主要接口，返回优化后的进化策略。
        """
        self.meta_generation_count += 1
        
        logger.debug(f"[META_EVOLUTION_DEBUG] 开始元进化第 {self.meta_generation_count} 代")
        
        # 进化策略集合
        evolved_strategies = self.strategy_evolution.evolve_strategies(
            current_environment, performance_feedback
        )
        
        # 分析策略性能
        performance_analysis = self.performance_analyzer.analyze_strategy_performance(
            evolved_strategies, current_environment
        )
        
        # 选择当前最佳策略
        if performance_analysis['strategy_rankings']:
            best_strategy_id = performance_analysis['strategy_rankings'][0]['strategy_id']
            self.current_best_strategy = next(
                (s for s in evolved_strategies if s.id == best_strategy_id), None
            )
        
        # 记录进化历史
        evolution_record = {
            'generation': self.meta_generation_count,
            'timestamp': datetime.now().isoformat(),
            'environment': current_environment,
            'strategy_count': len(evolved_strategies),
            'best_strategy': {
                'id': self.current_best_strategy.id if self.current_best_strategy else None,
                'type': self.current_best_strategy.strategy_type.value if self.current_best_strategy else None,
                'performance': self.current_best_strategy.evaluate_performance() if self.current_best_strategy else 0.0
            },
            'performance_analysis': performance_analysis
        }
        
        self.evolution_history.append(evolution_record)
        
        # 构建返回结果
        result = {
            'best_strategy': self._strategy_to_dict(self.current_best_strategy) if self.current_best_strategy else None,
            'all_strategies': [self._strategy_to_dict(s) for s in evolved_strategies],
            'performance_analysis': performance_analysis,
            'evolution_insights': self._generate_evolution_insights(),
            'meta_generation': self.meta_generation_count
        }
        
        logger.debug(f"[META_EVOLUTION_DEBUG] 元进化第 {self.meta_generation_count} 代完成")
        return result
    
    def _strategy_to_dict(self, strategy: StrategyConfiguration) -> Dict[str, Any]:
        """将策略配置转换为字典"""
        return {
            'id': strategy.id,
            'strategy_type': strategy.strategy_type.value,
            'parameters': strategy.parameters.to_dict(),
            'operators': strategy.operators,
            'fitness_function': strategy.fitness_function,
            'performance': strategy.evaluate_performance(),
            'usage_count': strategy.usage_count,
            'success_rate': strategy.success_rate,
            'creation_time': strategy.creation_time.isoformat()
        }
    
    def _generate_evolution_insights(self) -> List[str]:
        """生成元进化洞察"""
        insights = []
        
        if len(self.evolution_history) < 2:
            return insights
        
        # 分析进化趋势
        recent_records = self.evolution_history[-5:]  # 最近5代
        
        # 性能趋势分析
        performance_trend = []
        for record in recent_records:
            if record['best_strategy']['performance']:
                performance_trend.append(record['best_strategy']['performance'])
        
        if len(performance_trend) >= 2:
            if performance_trend[-1] > performance_trend[0]:
                insights.append("元进化正在改善策略性能")
            elif performance_trend[-1] < performance_trend[0] * 0.9:
                insights.append("策略性能出现下降，可能需要调整元进化参数")
        
        # 策略多样性分析
        current_strategies = self.strategy_evolution.strategy_population
        strategy_types = set(s.strategy_type for s in current_strategies)
        if len(strategy_types) >= 4:
            insights.append("策略多样性良好，有利于探索不同的优化方向")
        elif len(strategy_types) <= 2:
            insights.append("策略多样性不足，建议增加探索性")
        
        # 收敛性分析
        if len(self.evolution_history) >= 10:
            recent_best_performances = [r['best_strategy']['performance'] 
                                      for r in self.evolution_history[-10:]
                                      if r['best_strategy']['performance']]
            if recent_best_performances:
                performance_variance = np.var(recent_best_performances)
                if performance_variance < 0.01:
                    insights.append("策略性能趋于稳定，可能已接近最优")
                elif performance_variance > 0.1:
                    insights.append("策略性能波动较大，仍在探索阶段")
        
        return insights
    
    def get_best_strategy(self) -> Optional[Dict[str, Any]]:
        """获取当前最佳策略"""
        if self.current_best_strategy:
            return self._strategy_to_dict(self.current_best_strategy)
        return None
    
    def get_evolution_summary(self) -> Dict[str, Any]:
        """获取元进化摘要"""
        current_strategies = self.strategy_evolution.strategy_population
        
        return {
            'meta_generation_count': self.meta_generation_count,
            'total_strategies': len(current_strategies),
            'strategy_types': list(set(s.strategy_type.value for s in current_strategies)),
            'best_strategy_performance': self.current_best_strategy.evaluate_performance() if self.current_best_strategy else 0.0,
            'average_strategy_performance': sum(s.evaluate_performance() for s in current_strategies) / max(len(current_strategies), 1),
            'evolution_insights': self._generate_evolution_insights(),
            'last_evolution_time': self.evolution_history[-1]['timestamp'] if self.evolution_history else None
        }