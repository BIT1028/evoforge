# -*- coding: utf-8 -*-
"""
增强型进化引擎 - EvoForge核心组件

根据comprehensive_implementation_plan.md重新实现的进化引擎，包括：
- NEAT、NSGA-II、QD算法集成
- 多目标优化和帕累托前沿计算
- LLM辅助变异和智能变异策略
- 种群管理和进化循环控制
"""

import uuid
import logging
import random
import math
import time
import copy
import json
import numpy as np
from typing import Dict, List, Optional, Tuple, Any, Set, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
from collections import defaultdict, deque
import threading
import concurrent.futures
from functools import partial

# 导入数字细胞系统
from ..digital_cell.digital_cell import DigitalCell
from ..digital_cell.macro_molecule import MacroMolecule, MoleculeType
from ..digital_cell.gene_expression import GeneExpressionSystem, Gene, GeneType

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class EvolutionAlgorithm(Enum):
    """进化算法类型"""
    NEAT = "neat"
    NSGA_II = "nsga_ii"
    QUALITY_DIVERSITY = "quality_diversity"
    HYBRID = "hybrid"

class MutationType(Enum):
    """变异类型"""
    RANDOM = "random"
    GUIDED = "guided"
    LLM_ASSISTED = "llm_assisted"
    ADAPTIVE = "adaptive"

class SelectionMethod(Enum):
    """选择方法"""
    TOURNAMENT = "tournament"
    ROULETTE = "roulette"
    RANK_BASED = "rank_based"
    PARETO_FRONT = "pareto_front"

@dataclass
class Individual:
    """个体"""
    individual_id: str
    genome: Dict[str, Any]  # 基因组
    phenotype: Optional[DigitalCell] = None  # 表型（数字细胞）
    fitness_scores: Dict[str, float] = field(default_factory=dict)
    objectives: Dict[str, float] = field(default_factory=dict)
    
    # NEAT特定属性
    species_id: Optional[str] = None
    innovation_number: int = 0
    
    # QD特定属性
    behavior_descriptor: Optional[Tuple[float, ...]] = None
    novelty_score: float = 0.0
    
    # 进化历史
    generation: int = 0
    parent_ids: List[str] = field(default_factory=list)
    mutation_history: List[str] = field(default_factory=list)
    
    # 性能指标
    evaluation_time: float = 0.0
    complexity_score: float = 0.0
    
    def __post_init__(self):
        if not self.individual_id:
            self.individual_id = str(uuid.uuid4())
    
    def get_total_fitness(self) -> float:
        """获取总适应度"""
        if not self.fitness_scores:
            return 0.0
        return sum(self.fitness_scores.values()) / len(self.fitness_scores)
    
    def dominates(self, other: 'Individual') -> bool:
        """检查是否支配另一个个体（用于NSGA-II）"""
        if not self.objectives or not other.objectives:
            return False
        
        better_in_any = False
        for obj_name in self.objectives:
            if obj_name not in other.objectives:
                continue
            
            if self.objectives[obj_name] < other.objectives[obj_name]:
                return False
            elif self.objectives[obj_name] > other.objectives[obj_name]:
                better_in_any = True
        
        return better_in_any
    
    def calculate_crowding_distance(self, population: List['Individual'], 
                                  objective_names: List[str]) -> float:
        """计算拥挤距离"""
        if len(population) <= 2:
            return float('inf')
        
        distance = 0.0
        
        for obj_name in objective_names:
            # 按目标值排序
            sorted_pop = sorted(population, key=lambda x: x.objectives.get(obj_name, 0))
            
            if sorted_pop[0].individual_id == self.individual_id or \
               sorted_pop[-1].individual_id == self.individual_id:
                return float('inf')  # 边界个体
            
            # 找到当前个体在排序中的位置
            current_index = next(i for i, ind in enumerate(sorted_pop) 
                               if ind.individual_id == self.individual_id)
            
            if current_index > 0 and current_index < len(sorted_pop) - 1:
                obj_range = sorted_pop[-1].objectives.get(obj_name, 0) - \
                           sorted_pop[0].objectives.get(obj_name, 0)
                
                if obj_range > 0:
                    distance += (sorted_pop[current_index + 1].objectives.get(obj_name, 0) - 
                               sorted_pop[current_index - 1].objectives.get(obj_name, 0)) / obj_range
        
        return distance

@dataclass
class Species:
    """物种（NEAT算法使用）"""
    species_id: str
    representative: Individual
    members: List[Individual] = field(default_factory=list)
    average_fitness: float = 0.0
    stagnation_count: int = 0
    best_fitness: float = 0.0
    
    def add_member(self, individual: Individual) -> None:
        """添加成员"""
        individual.species_id = self.species_id
        self.members.append(individual)
    
    def update_fitness(self) -> None:
        """更新物种适应度"""
        if not self.members:
            self.average_fitness = 0.0
            return
        
        total_fitness = sum(ind.get_total_fitness() for ind in self.members)
        self.average_fitness = total_fitness / len(self.members)
        
        current_best = max(ind.get_total_fitness() for ind in self.members)
        if current_best <= self.best_fitness:
            self.stagnation_count += 1
        else:
            self.best_fitness = current_best
            self.stagnation_count = 0
    
    def select_representative(self) -> None:
        """选择新的代表"""
        if self.members:
            self.representative = max(self.members, key=lambda x: x.get_total_fitness())

@dataclass
class EvolutionConfig:
    """进化配置"""
    # 基本参数
    population_size: int = 100
    max_generations: int = 1000
    mutation_rate: float = 0.1
    crossover_rate: float = 0.8
    
    # 算法选择
    algorithm: EvolutionAlgorithm = EvolutionAlgorithm.HYBRID
    selection_method: SelectionMethod = SelectionMethod.TOURNAMENT
    
    # NEAT参数
    compatibility_threshold: float = 3.0
    species_target: int = 10
    stagnation_threshold: int = 15
    
    # NSGA-II参数
    objective_names: List[str] = field(default_factory=lambda: [
        'fitness', 'complexity', 'novelty', 'efficiency', 'robustness', 'adaptability'
    ])
    
    # QD参数
    behavior_dimensions: int = 2
    archive_size: int = 1000
    novelty_threshold: float = 0.1
    
    # LLM辅助变异
    llm_mutation_probability: float = 0.05
    llm_guidance_strength: float = 0.3
    
    # 性能参数
    parallel_evaluation: bool = True
    max_workers: int = 4
    evaluation_timeout: float = 30.0

class NEATEngine:
    """NEAT算法引擎"""
    
    def __init__(self, config: EvolutionConfig):
        self.config = config
        self.species: Dict[str, Species] = {}
        self.innovation_counter = 0
        
    def speciate_population(self, population: List[Individual]) -> None:
        """物种分化"""
        # 清空现有物种成员
        for species in self.species.values():
            species.members.clear()
        
        # 为每个个体分配物种
        for individual in population:
            assigned = False
            
            for species in self.species.values():
                if self._calculate_compatibility(individual, species.representative) < self.config.compatibility_threshold:
                    species.add_member(individual)
                    assigned = True
                    break
            
            if not assigned:
                # 创建新物种
                species_id = f"species_{len(self.species)}"
                new_species = Species(species_id, individual)
                new_species.add_member(individual)
                self.species[species_id] = new_species
        
        # 移除空物种
        empty_species = [sid for sid, species in self.species.items() if not species.members]
        for sid in empty_species:
            del self.species[sid]
        
        # 更新物种适应度
        for species in self.species.values():
            species.update_fitness()
            species.select_representative()
    
    def _calculate_compatibility(self, ind1: Individual, ind2: Individual) -> float:
        """计算兼容性距离"""
        # 简化的兼容性计算
        genome1 = ind1.genome
        genome2 = ind2.genome
        
        # 基因差异
        gene_diff = 0
        total_genes = 0
        
        all_genes = set(genome1.keys()) | set(genome2.keys())
        
        for gene in all_genes:
            total_genes += 1
            if gene not in genome1 or gene not in genome2:
                gene_diff += 1  # 不匹配基因
            else:
                # 权重差异
                if isinstance(genome1[gene], (int, float)) and isinstance(genome2[gene], (int, float)):
                    gene_diff += abs(genome1[gene] - genome2[gene])
        
        if total_genes == 0:
            return 0.0
        
        return gene_diff / total_genes
    
    def evolve_species(self, species: Species) -> List[Individual]:
        """进化物种"""
        if not species.members:
            return []
        
        # 计算物种应该产生的后代数量
        offspring_count = max(1, int(len(species.members) * species.average_fitness))
        
        offspring = []
        
        for _ in range(offspring_count):
            if random.random() < self.config.crossover_rate and len(species.members) > 1:
                # 交叉
                parent1 = self._tournament_selection(species.members)
                parent2 = self._tournament_selection(species.members)
                child = self._crossover(parent1, parent2)
            else:
                # 复制
                parent = self._tournament_selection(species.members)
                child = self._copy_individual(parent)
            
            # 变异
            if random.random() < self.config.mutation_rate:
                child = self._mutate(child)
            
            offspring.append(child)
        
        return offspring
    
    def _tournament_selection(self, individuals: List[Individual], tournament_size: int = 3) -> Individual:
        """锦标赛选择"""
        tournament = random.sample(individuals, min(tournament_size, len(individuals)))
        return max(tournament, key=lambda x: x.get_total_fitness())
    
    def _crossover(self, parent1: Individual, parent2: Individual) -> Individual:
        """交叉操作"""
        child_genome = {}
        
        # 合并基因组
        all_genes = set(parent1.genome.keys()) | set(parent2.genome.keys())
        
        for gene in all_genes:
            if gene in parent1.genome and gene in parent2.genome:
                # 随机选择父母的基因
                if random.random() < 0.5:
                    child_genome[gene] = parent1.genome[gene]
                else:
                    child_genome[gene] = parent2.genome[gene]
            elif gene in parent1.genome:
                child_genome[gene] = parent1.genome[gene]
            else:
                child_genome[gene] = parent2.genome[gene]
        
        child = Individual(
            individual_id=str(uuid.uuid4()),
            genome=child_genome,
            generation=max(parent1.generation, parent2.generation) + 1,
            parent_ids=[parent1.individual_id, parent2.individual_id]
        )
        
        return child
    
    def _copy_individual(self, parent: Individual) -> Individual:
        """复制个体"""
        child = Individual(
            individual_id=str(uuid.uuid4()),
            genome=copy.deepcopy(parent.genome),
            generation=parent.generation + 1,
            parent_ids=[parent.individual_id]
        )
        
        return child
    
    def _mutate(self, individual: Individual) -> Individual:
        """变异操作"""
        # 基因权重变异
        for gene_name, gene_value in individual.genome.items():
            if isinstance(gene_value, (int, float)):
                if random.random() < 0.1:  # 10%概率变异
                    mutation_strength = random.gauss(0, 0.1)
                    individual.genome[gene_name] = gene_value + mutation_strength
        
        # 结构变异（添加/删除基因）
        if random.random() < 0.05:  # 5%概率结构变异
            if random.random() < 0.5 and len(individual.genome) > 1:
                # 删除基因
                gene_to_remove = random.choice(list(individual.genome.keys()))
                del individual.genome[gene_to_remove]
            else:
                # 添加基因
                new_gene_name = f"gene_{self.innovation_counter}"
                individual.genome[new_gene_name] = random.gauss(0, 1)
                self.innovation_counter += 1
        
        individual.mutation_history.append(f"mutation_gen_{individual.generation}")
        return individual

class NSGAIIEngine:
    """NSGA-II算法引擎"""
    
    def __init__(self, config: EvolutionConfig):
        self.config = config
    
    def evolve_population(self, population: List[Individual]) -> List[Individual]:
        """进化种群"""
        # 生成后代
        offspring = self._generate_offspring(population)
        
        # 合并父代和子代
        combined_population = population + offspring
        
        # 非支配排序
        fronts = self._non_dominated_sort(combined_population)
        
        # 选择下一代
        next_population = []
        front_index = 0
        
        while len(next_population) + len(fronts[front_index]) <= self.config.population_size:
            next_population.extend(fronts[front_index])
            front_index += 1
            
            if front_index >= len(fronts):
                break
        
        # 如果需要从最后一个前沿选择部分个体
        if len(next_population) < self.config.population_size and front_index < len(fronts):
            remaining_slots = self.config.population_size - len(next_population)
            last_front = fronts[front_index]
            
            # 计算拥挤距离
            for individual in last_front:
                individual.crowding_distance = individual.calculate_crowding_distance(
                    last_front, self.config.objective_names
                )
            
            # 按拥挤距离排序并选择
            last_front.sort(key=lambda x: getattr(x, 'crowding_distance', 0), reverse=True)
            next_population.extend(last_front[:remaining_slots])
        
        return next_population
    
    def _generate_offspring(self, population: List[Individual]) -> List[Individual]:
        """生成后代"""
        offspring = []
        
        for _ in range(self.config.population_size):
            if random.random() < self.config.crossover_rate:
                # 交叉
                parent1 = self._tournament_selection(population)
                parent2 = self._tournament_selection(population)
                child = self._crossover(parent1, parent2)
            else:
                # 复制
                parent = self._tournament_selection(population)
                child = self._copy_individual(parent)
            
            # 变异
            if random.random() < self.config.mutation_rate:
                child = self._mutate(child)
            
            offspring.append(child)
        
        return offspring
    
    def _non_dominated_sort(self, population: List[Individual]) -> List[List[Individual]]:
        """非支配排序"""
        fronts = [[]]
        domination_count = {}
        dominated_solutions = {}
        
        # 初始化
        for individual in population:
            domination_count[individual.individual_id] = 0
            dominated_solutions[individual.individual_id] = []
        
        # 计算支配关系
        for i, ind1 in enumerate(population):
            for j, ind2 in enumerate(population):
                if i != j:
                    if ind1.dominates(ind2):
                        dominated_solutions[ind1.individual_id].append(ind2)
                    elif ind2.dominates(ind1):
                        domination_count[ind1.individual_id] += 1
            
            # 第一前沿
            if domination_count[ind1.individual_id] == 0:
                fronts[0].append(ind1)
        
        # 构建其他前沿
        front_index = 0
        while fronts[front_index]:
            next_front = []
            
            for individual in fronts[front_index]:
                for dominated_ind in dominated_solutions[individual.individual_id]:
                    domination_count[dominated_ind.individual_id] -= 1
                    
                    if domination_count[dominated_ind.individual_id] == 0:
                        next_front.append(dominated_ind)
            
            if next_front:
                fronts.append(next_front)
            
            front_index += 1
        
        return fronts
    
    def _tournament_selection(self, population: List[Individual], tournament_size: int = 2) -> Individual:
        """锦标赛选择（基于支配关系）"""
        tournament = random.sample(population, min(tournament_size, len(population)))
        
        # 选择非支配的个体
        for individual in tournament:
            is_dominated = False
            for other in tournament:
                if other.individual_id != individual.individual_id and other.dominates(individual):
                    is_dominated = True
                    break
            
            if not is_dominated:
                return individual
        
        # 如果都被支配，随机选择
        return random.choice(tournament)
    
    def _crossover(self, parent1: Individual, parent2: Individual) -> Individual:
        """交叉操作"""
        child_genome = {}
        
        # 模拟二进制交叉（SBX）
        for gene_name in set(parent1.genome.keys()) | set(parent2.genome.keys()):
            if gene_name in parent1.genome and gene_name in parent2.genome:
                p1_val = parent1.genome[gene_name]
                p2_val = parent2.genome[gene_name]
                
                if isinstance(p1_val, (int, float)) and isinstance(p2_val, (int, float)):
                    # SBX交叉
                    eta = 20  # 分布指数
                    u = random.random()
                    
                    if u <= 0.5:
                        beta = (2 * u) ** (1 / (eta + 1))
                    else:
                        beta = (1 / (2 * (1 - u))) ** (1 / (eta + 1))
                    
                    child_val = 0.5 * ((1 + beta) * p1_val + (1 - beta) * p2_val)
                    child_genome[gene_name] = child_val
                else:
                    child_genome[gene_name] = random.choice([p1_val, p2_val])
            elif gene_name in parent1.genome:
                child_genome[gene_name] = parent1.genome[gene_name]
            else:
                child_genome[gene_name] = parent2.genome[gene_name]
        
        child = Individual(
            individual_id=str(uuid.uuid4()),
            genome=child_genome,
            generation=max(parent1.generation, parent2.generation) + 1,
            parent_ids=[parent1.individual_id, parent2.individual_id]
        )
        
        return child
    
    def _copy_individual(self, parent: Individual) -> Individual:
        """复制个体"""
        child = Individual(
            individual_id=str(uuid.uuid4()),
            genome=copy.deepcopy(parent.genome),
            generation=parent.generation + 1,
            parent_ids=[parent.individual_id]
        )
        
        return child
    
    def _mutate(self, individual: Individual) -> Individual:
        """多项式变异"""
        eta = 20  # 分布指数
        
        for gene_name, gene_value in individual.genome.items():
            if isinstance(gene_value, (int, float)):
                if random.random() < 0.1:  # 变异概率
                    u = random.random()
                    
                    if u < 0.5:
                        delta = (2 * u) ** (1 / (eta + 1)) - 1
                    else:
                        delta = 1 - (2 * (1 - u)) ** (1 / (eta + 1))
                    
                    individual.genome[gene_name] = gene_value + delta
        
        individual.mutation_history.append(f"polynomial_mutation_gen_{individual.generation}")
        return individual

class QualityDiversityEngine:
    """质量多样性算法引擎"""
    
    def __init__(self, config: EvolutionConfig):
        self.config = config
        self.archive: Dict[Tuple, Individual] = {}  # 行为描述符 -> 个体
        self.behavior_space = self._initialize_behavior_space()
    
    def _initialize_behavior_space(self) -> Dict[Tuple, Optional[Individual]]:
        """初始化行为空间"""
        behavior_space = {}
        
        # 创建网格化的行为空间
        grid_size = int(self.config.archive_size ** (1 / self.config.behavior_dimensions))
        
        def generate_grid_points(dimensions, current_point=None):
            if current_point is None:
                current_point = []
            
            if len(current_point) == dimensions:
                yield tuple(current_point)
                return
            
            for i in range(grid_size):
                yield from generate_grid_points(dimensions, current_point + [i])
        
        for point in generate_grid_points(self.config.behavior_dimensions):
            behavior_space[point] = None
        
        return behavior_space
    
    def evolve_population(self, population: List[Individual]) -> List[Individual]:
        """进化种群"""
        # 更新档案
        for individual in population:
            self._update_archive(individual)
        
        # 生成新个体
        new_population = []
        
        for _ in range(self.config.population_size):
            if random.random() < 0.5 and self.archive:
                # 从档案中选择
                parent = random.choice(list(self.archive.values()))
            else:
                # 从当前种群中选择
                parent = self._novelty_selection(population)
            
            # 变异
            child = self._copy_individual(parent)
            if random.random() < self.config.mutation_rate:
                child = self._mutate(child)
            
            new_population.append(child)
        
        return new_population
    
    def _update_archive(self, individual: Individual) -> None:
        """更新档案"""
        if individual.behavior_descriptor is None:
            return
        
        # 将行为描述符映射到网格
        grid_point = self._map_to_grid(individual.behavior_descriptor)
        
        if grid_point in self.behavior_space:
            current_occupant = self.behavior_space[grid_point]
            
            if current_occupant is None or individual.get_total_fitness() > current_occupant.get_total_fitness():
                self.behavior_space[grid_point] = individual
                self.archive[grid_point] = individual
    
    def _map_to_grid(self, behavior_descriptor: Tuple[float, ...]) -> Tuple[int, ...]:
        """将行为描述符映射到网格"""
        grid_size = int(self.config.archive_size ** (1 / self.config.behavior_dimensions))
        
        grid_point = []
        for value in behavior_descriptor:
            # 假设行为值在[0, 1]范围内
            grid_index = int(value * (grid_size - 1))
            grid_index = max(0, min(grid_size - 1, grid_index))
            grid_point.append(grid_index)
        
        return tuple(grid_point)
    
    def _novelty_selection(self, population: List[Individual]) -> Individual:
        """新颖性选择"""
        # 计算新颖性分数
        for individual in population:
            individual.novelty_score = self._calculate_novelty(individual, population)
        
        # 选择新颖性最高的个体
        return max(population, key=lambda x: x.novelty_score)
    
    def _calculate_novelty(self, individual: Individual, population: List[Individual]) -> float:
        """计算新颖性分数"""
        if individual.behavior_descriptor is None:
            return 0.0
        
        distances = []
        
        # 与种群中其他个体的距离
        for other in population:
            if other.individual_id != individual.individual_id and other.behavior_descriptor is not None:
                distance = self._behavior_distance(individual.behavior_descriptor, other.behavior_descriptor)
                distances.append(distance)
        
        # 与档案中个体的距离
        for archived_individual in self.archive.values():
            if archived_individual.behavior_descriptor is not None:
                distance = self._behavior_distance(individual.behavior_descriptor, archived_individual.behavior_descriptor)
                distances.append(distance)
        
        if not distances:
            return 1.0
        
        # 使用k近邻的平均距离作为新颖性分数
        k = min(15, len(distances))
        distances.sort()
        return sum(distances[:k]) / k
    
    def _behavior_distance(self, desc1: Tuple[float, ...], desc2: Tuple[float, ...]) -> float:
        """计算行为描述符之间的距离"""
        if len(desc1) != len(desc2):
            return float('inf')
        
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(desc1, desc2)))
    
    def _copy_individual(self, parent: Individual) -> Individual:
        """复制个体"""
        child = Individual(
            individual_id=str(uuid.uuid4()),
            genome=copy.deepcopy(parent.genome),
            generation=parent.generation + 1,
            parent_ids=[parent.individual_id]
        )
        
        return child
    
    def _mutate(self, individual: Individual) -> Individual:
        """变异操作"""
        # 基因变异
        for gene_name, gene_value in individual.genome.items():
            if isinstance(gene_value, (int, float)):
                if random.random() < 0.1:
                    mutation_strength = random.gauss(0, 0.2)
                    individual.genome[gene_name] = gene_value + mutation_strength
        
        individual.mutation_history.append(f"qd_mutation_gen_{individual.generation}")
        return individual

class LLMAssistedMutator:
    """LLM辅助变异器"""
    
    def __init__(self, config: EvolutionConfig):
        self.config = config
        self.mutation_cache = {}  # 缓存LLM建议
    
    def llm_guided_mutation(self, individual: Individual, 
                          fitness_feedback: Dict[str, float]) -> Individual:
        """LLM指导的变异"""
        # 简化的LLM辅助变异（实际实现需要调用LLM API）
        
        # 分析适应度反馈
        weak_areas = [obj for obj, score in fitness_feedback.items() if score < 0.5]
        strong_areas = [obj for obj, score in fitness_feedback.items() if score > 0.8]
        
        # 生成变异策略
        mutation_strategy = self._generate_mutation_strategy(weak_areas, strong_areas)
        
        # 应用变异
        mutated_individual = self._apply_guided_mutation(individual, mutation_strategy)
        
        return mutated_individual
    
    def _generate_mutation_strategy(self, weak_areas: List[str], 
                                  strong_areas: List[str]) -> Dict[str, Any]:
        """生成变异策略"""
        strategy = {
            'focus_areas': weak_areas,
            'preserve_areas': strong_areas,
            'mutation_strength': 0.1,
            'structural_changes': len(weak_areas) > 2
        }
        
        # 根据弱点调整策略
        if 'complexity' in weak_areas:
            strategy['add_genes'] = True
            strategy['mutation_strength'] = 0.15
        
        if 'efficiency' in weak_areas:
            strategy['optimize_weights'] = True
            strategy['remove_redundant'] = True
        
        if 'novelty' in weak_areas:
            strategy['structural_changes'] = True
            strategy['mutation_strength'] = 0.2
        
        return strategy
    
    def _apply_guided_mutation(self, individual: Individual, 
                             strategy: Dict[str, Any]) -> Individual:
        """应用指导变异"""
        mutated = self._copy_individual(individual)
        
        # 权重优化
        if strategy.get('optimize_weights', False):
            for gene_name, gene_value in mutated.genome.items():
                if isinstance(gene_value, (int, float)):
                    if random.random() < 0.3:
                        # 更精细的调整
                        adjustment = random.gauss(0, strategy['mutation_strength'] * 0.5)
                        mutated.genome[gene_name] = gene_value + adjustment
        
        # 结构变化
        if strategy.get('structural_changes', False):
            if strategy.get('add_genes', False) and random.random() < 0.3:
                # 添加新基因
                new_gene_name = f"llm_gene_{len(mutated.genome)}"
                mutated.genome[new_gene_name] = random.gauss(0, 0.5)
            
            if strategy.get('remove_redundant', False) and len(mutated.genome) > 3:
                # 移除冗余基因
                genes_to_remove = random.sample(
                    list(mutated.genome.keys()), 
                    min(2, len(mutated.genome) - 3)
                )
                for gene in genes_to_remove:
                    del mutated.genome[gene]
        
        mutated.mutation_history.append(f"llm_guided_gen_{individual.generation}")
        return mutated
    
    def _copy_individual(self, parent: Individual) -> Individual:
        """复制个体"""
        return Individual(
            individual_id=str(uuid.uuid4()),
            genome=copy.deepcopy(parent.genome),
            generation=parent.generation + 1,
            parent_ids=[parent.individual_id]
        )

class EnhancedEvolutionEngine:
    """增强型进化引擎"""
    
    def __init__(self, config: EvolutionConfig = None):
        self.config = config or EvolutionConfig()
        
        # 初始化算法引擎
        self.neat_engine = NEATEngine(self.config)
        self.nsga_engine = NSGAIIEngine(self.config)
        self.qd_engine = QualityDiversityEngine(self.config)
        self.llm_mutator = LLMAssistedMutator(self.config)
        
        # 种群管理
        self.population: List[Individual] = []
        self.generation = 0
        self.best_individuals: List[Individual] = []
        
        # 统计信息
        self.stats = {
            'total_evaluations': 0,
            'successful_evaluations': 0,
            'failed_evaluations': 0,
            'best_fitness_history': [],
            'diversity_history': [],
            'algorithm_usage': defaultdict(int)
        }
        
        # 性能监控
        self.evaluation_times = deque(maxlen=100)
        self.is_running = False
        
        logger.info(f"增强型进化引擎初始化完成，算法: {self.config.algorithm.value}")
    
    def initialize_population(self, genome_template: Dict[str, Any] = None) -> None:
        """初始化种群"""
        self.population.clear()
        
        if genome_template is None:
            genome_template = self._create_default_genome_template()
        
        for i in range(self.config.population_size):
            # 创建随机基因组
            genome = self._create_random_genome(genome_template)
            
            individual = Individual(
                individual_id=f"ind_{i}_{uuid.uuid4().hex[:8]}",
                genome=genome,
                generation=0
            )
            
            self.population.append(individual)
        
        logger.info(f"初始化种群完成，大小: {len(self.population)}")
    
    def _create_default_genome_template(self) -> Dict[str, Any]:
        """创建默认基因组模板"""
        return {
            'gene_count': 10,
            'connection_density': 0.3,
            'activation_functions': ['sigmoid', 'tanh', 'relu'],
            'layer_sizes': [5, 10, 5],
            'learning_rate': 0.01,
            'mutation_rate': 0.1
        }
    
    def _create_random_genome(self, template: Dict[str, Any]) -> Dict[str, Any]:
        """创建随机基因组"""
        genome = {}
        
        # 基因数量
        gene_count = template.get('gene_count', 10)
        for i in range(gene_count):
            genome[f"gene_{i}"] = random.gauss(0, 1)
        
        # 连接权重
        connection_count = int(gene_count * template.get('connection_density', 0.3))
        for i in range(connection_count):
            genome[f"connection_{i}"] = random.gauss(0, 0.5)
        
        # 超参数
        genome['learning_rate'] = random.uniform(0.001, 0.1)
        genome['mutation_rate'] = random.uniform(0.01, 0.3)
        
        return genome
    
    def evaluate_individual(self, individual: Individual, 
                          evaluation_function: Callable[[Individual], Dict[str, float]]) -> None:
        """评估个体"""
        start_time = time.time()
        
        try:
            # 创建数字细胞表型
            individual.phenotype = self._create_phenotype(individual)
            
            # 评估适应度
            fitness_scores = evaluation_function(individual)
            individual.fitness_scores = fitness_scores
            
            # 计算目标值（用于多目标优化）
            individual.objectives = self._calculate_objectives(individual, fitness_scores)
            
            # 计算行为描述符（用于QD算法）
            individual.behavior_descriptor = self._calculate_behavior_descriptor(individual)
            
            # 计算复杂度
            individual.complexity_score = self._calculate_complexity(individual)
            
            individual.evaluation_time = time.time() - start_time
            self.evaluation_times.append(individual.evaluation_time)
            
            self.stats['total_evaluations'] += 1
            self.stats['successful_evaluations'] += 1
            
            logger.debug(f"个体 {individual.individual_id} 评估完成，适应度: {individual.get_total_fitness():.3f}")
        
        except Exception as e:
            individual.fitness_scores = {'error': 0.0}
            individual.objectives = {'error': 0.0}
            individual.evaluation_time = time.time() - start_time
            
            self.stats['total_evaluations'] += 1
            self.stats['failed_evaluations'] += 1
            
            logger.error(f"个体 {individual.individual_id} 评估失败: {e}")
    
    def _create_phenotype(self, individual: Individual) -> DigitalCell:
        """根据基因组创建数字细胞表型"""
        # 简化的表型创建
        cell = DigitalCell(cell_id=f"cell_{individual.individual_id}")
        
        # 根据基因组配置细胞
        for gene_name, gene_value in individual.genome.items():
            if gene_name.startswith('gene_') and isinstance(gene_value, (int, float)):
                # 将基因值转换为细胞参数
                if gene_value > 0.5:
                    # 添加分子
                    pass  # 实际实现中会添加相应的分子
        
        return cell
    
    def _calculate_objectives(self, individual: Individual, 
                            fitness_scores: Dict[str, float]) -> Dict[str, float]:
        """计算多目标优化的目标值"""
        objectives = {}
        
        # 基本适应度目标
        objectives['fitness'] = individual.get_total_fitness()
        
        # 复杂度目标（最小化）
        objectives['complexity'] = -individual.complexity_score
        
        # 效率目标
        objectives['efficiency'] = fitness_scores.get('efficiency', 0.0)
        
        # 鲁棒性目标
        objectives['robustness'] = fitness_scores.get('robustness', 0.0)
        
        # 适应性目标
        objectives['adaptability'] = fitness_scores.get('adaptability', 0.0)
        
        # 新颖性目标
        objectives['novelty'] = getattr(individual, 'novelty_score', 0.0)
        
        return objectives
    
    def _calculate_behavior_descriptor(self, individual: Individual) -> Tuple[float, ...]:
        """计算行为描述符"""
        # 简化的行为描述符计算
        descriptors = []
        
        # 基因组特征
        gene_values = [v for v in individual.genome.values() if isinstance(v, (int, float))]
        if gene_values:
            descriptors.append(sum(gene_values) / len(gene_values))  # 平均基因值
            descriptors.append(max(gene_values) - min(gene_values))  # 基因值范围
        else:
            descriptors.extend([0.0, 0.0])
        
        # 确保描述符在[0, 1]范围内
        normalized_descriptors = []
        for desc in descriptors:
            normalized = (desc + 1) / 2  # 假设原始值在[-1, 1]范围
            normalized = max(0.0, min(1.0, normalized))
            normalized_descriptors.append(normalized)
        
        return tuple(normalized_descriptors)
    
    def _calculate_complexity(self, individual: Individual) -> float:
        """计算个体复杂度"""
        complexity = 0.0
        
        # 基因组大小
        complexity += len(individual.genome) * 0.1
        
        # 连接数量
        connections = [k for k in individual.genome.keys() if k.startswith('connection_')]
        complexity += len(connections) * 0.05
        
        # 参数变异程度
        gene_values = [v for v in individual.genome.values() if isinstance(v, (int, float))]
        if gene_values:
            complexity += np.std(gene_values) * 0.1
        
        return complexity
    
    def evolve_generation(self, evaluation_function: Callable[[Individual], Dict[str, float]]) -> None:
        """进化一代"""
        logger.info(f"开始进化第 {self.generation + 1} 代")
        
        # 并行评估种群
        if self.config.parallel_evaluation:
            self._parallel_evaluate_population(evaluation_function)
        else:
            self._sequential_evaluate_population(evaluation_function)
        
        # 记录最佳个体
        best_individual = max(self.population, key=lambda x: x.get_total_fitness())
        self.best_individuals.append(copy.deepcopy(best_individual))
        
        # 更新统计信息
        self._update_statistics()
        
        # 根据算法类型进化
        if self.config.algorithm == EvolutionAlgorithm.NEAT:
            self.population = self._evolve_with_neat()
        elif self.config.algorithm == EvolutionAlgorithm.NSGA_II:
            self.population = self._evolve_with_nsga_ii()
        elif self.config.algorithm == EvolutionAlgorithm.QUALITY_DIVERSITY:
            self.population = self._evolve_with_qd()
        elif self.config.algorithm == EvolutionAlgorithm.HYBRID:
            self.population = self._evolve_with_hybrid()
        
        self.generation += 1
        
        logger.info(f"第 {self.generation} 代进化完成，最佳适应度: {best_individual.get_total_fitness():.3f}")
    
    def _parallel_evaluate_population(self, evaluation_function: Callable[[Individual], Dict[str, float]]) -> None:
        """并行评估种群"""
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            futures = []
            
            for individual in self.population:
                future = executor.submit(self.evaluate_individual, individual, evaluation_function)
                futures.append(future)
            
            # 等待所有评估完成
            for future in concurrent.futures.as_completed(futures, timeout=self.config.evaluation_timeout):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"并行评估出错: {e}")
    
    def _sequential_evaluate_population(self, evaluation_function: Callable[[Individual], Dict[str, float]]) -> None:
        """顺序评估种群"""
        for individual in self.population:
            self.evaluate_individual(individual, evaluation_function)
    
    def _evolve_with_neat(self) -> List[Individual]:
        """使用NEAT算法进化"""
        self.stats['algorithm_usage']['neat'] += 1
        
        # 物种分化
        self.neat_engine.speciate_population(self.population)
        
        # 进化各物种
        new_population = []
        for species in self.neat_engine.species.values():
            offspring = self.neat_engine.evolve_species(species)
            new_population.extend(offspring)
        
        # 确保种群大小
        if len(new_population) > self.config.population_size:
            new_population = new_population[:self.config.population_size]
        elif len(new_population) < self.config.population_size:
            # 补充个体
            while len(new_population) < self.config.population_size:
                parent = random.choice(self.population)
                child = self.neat_engine._copy_individual(parent)
                new_population.append(child)
        
        return new_population
    
    def _evolve_with_nsga_ii(self) -> List[Individual]:
        """使用NSGA-II算法进化"""
        self.stats['algorithm_usage']['nsga_ii'] += 1
        return self.nsga_engine.evolve_population(self.population)
    
    def _evolve_with_qd(self) -> List[Individual]:
        """使用质量多样性算法进化"""
        self.stats['algorithm_usage']['quality_diversity'] += 1
        return self.qd_engine.evolve_population(self.population)
    
    def _evolve_with_hybrid(self) -> List[Individual]:
        """使用混合算法进化"""
        self.stats['algorithm_usage']['hybrid'] += 1
        
        # 动态选择算法
        if self.generation % 10 == 0:
            # 每10代使用NSGA-II进行多目标优化
            return self._evolve_with_nsga_ii()
        elif self.generation % 5 == 0:
            # 每5代使用QD算法增加多样性
            return self._evolve_with_qd()
        else:
            # 其他时候使用NEAT算法
            return self._evolve_with_neat()
    
    def _update_statistics(self) -> None:
        """更新统计信息"""
        if not self.population:
            return
        
        # 最佳适应度
        best_fitness = max(ind.get_total_fitness() for ind in self.population)
        self.stats['best_fitness_history'].append(best_fitness)
        
        # 多样性计算
        diversity = self._calculate_population_diversity()
        self.stats['diversity_history'].append(diversity)
    
    def _calculate_population_diversity(self) -> float:
        """计算种群多样性"""
        if len(self.population) < 2:
            return 0.0
        
        total_distance = 0.0
        comparisons = 0
        
        for i, ind1 in enumerate(self.population):
            for j, ind2 in enumerate(self.population[i+1:], i+1):
                # 计算基因组距离
                distance = self._calculate_genome_distance(ind1.genome, ind2.genome)
                total_distance += distance
                comparisons += 1
        
        return total_distance / comparisons if comparisons > 0 else 0.0
    
    def _calculate_genome_distance(self, genome1: Dict[str, Any], genome2: Dict[str, Any]) -> float:
        """计算基因组距离"""
        all_genes = set(genome1.keys()) | set(genome2.keys())
        
        if not all_genes:
            return 0.0
        
        total_diff = 0.0
        
        for gene in all_genes:
            if gene in genome1 and gene in genome2:
                val1, val2 = genome1[gene], genome2[gene]
                if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
                    total_diff += abs(val1 - val2)
                else:
                    total_diff += 1.0 if val1 != val2 else 0.0
            else:
                total_diff += 1.0  # 基因缺失
        
        return total_diff / len(all_genes)
    
    def run_evolution(self, evaluation_function: Callable[[Individual], Dict[str, float]], 
                     max_generations: int = None) -> Individual:
        """运行进化过程"""
        if max_generations is None:
            max_generations = self.config.max_generations
        
        self.is_running = True
        
        logger.info(f"开始进化过程，最大代数: {max_generations}")
        
        try:
            for generation in range(max_generations):
                if not self.is_running:
                    logger.info("进化过程被中断")
                    break
                
                self.evolve_generation(evaluation_function)
                
                # 检查收敛条件
                if self._check_convergence():
                    logger.info(f"在第 {generation + 1} 代达到收敛")
                    break
                
                # LLM辅助变异
                if random.random() < self.config.llm_mutation_probability:
                    self._apply_llm_mutations()
        
        except KeyboardInterrupt:
            logger.info("进化过程被用户中断")
        except Exception as e:
            logger.error(f"进化过程出错: {e}")
        finally:
            self.is_running = False
        
        # 返回最佳个体
        if self.best_individuals:
            best_individual = max(self.best_individuals, key=lambda x: x.get_total_fitness())
            logger.info(f"进化完成，最佳适应度: {best_individual.get_total_fitness():.3f}")
            return best_individual
        else:
            logger.warning("没有找到有效的个体")
            return None
    
    def _check_convergence(self) -> bool:
        """检查收敛条件"""
        if len(self.stats['best_fitness_history']) < 50:
            return False
        
        # 检查最近50代的适应度变化
        recent_fitness = self.stats['best_fitness_history'][-50:]
        fitness_std = np.std(recent_fitness)
        
        # 如果标准差很小，认为已收敛
        return fitness_std < 0.001
    
    def _apply_llm_mutations(self) -> None:
        """应用LLM辅助变异"""
        # 选择表现较差的个体进行LLM辅助变异
        sorted_population = sorted(self.population, key=lambda x: x.get_total_fitness())
        bottom_quarter = sorted_population[:len(sorted_population) // 4]
        
        for individual in bottom_quarter:
            if random.random() < 0.5:  # 50%概率进行LLM变异
                fitness_feedback = individual.objectives.copy()
                mutated = self.llm_mutator.llm_guided_mutation(individual, fitness_feedback)
                
                # 替换原个体
                index = self.population.index(individual)
                self.population[index] = mutated
        
        logger.debug(f"应用LLM辅助变异到 {len(bottom_quarter)} 个个体")
    
    def get_evolution_state(self) -> Dict[str, Any]:
        """获取进化状态"""
        return {
            'generation': self.generation,
            'population_size': len(self.population),
            'best_fitness': max(ind.get_total_fitness() for ind in self.population) if self.population else 0.0,
            'average_fitness': sum(ind.get_total_fitness() for ind in self.population) / len(self.population) if self.population else 0.0,
            'diversity': self._calculate_population_diversity(),
            'species_count': len(self.neat_engine.species),
            'archive_size': len(self.qd_engine.archive),
            'stats': self.stats.copy(),
            'config': {
                'algorithm': self.config.algorithm.value,
                'population_size': self.config.population_size,
                'mutation_rate': self.config.mutation_rate,
                'crossover_rate': self.config.crossover_rate
            }
        }
    
    def save_state(self, filepath: str) -> None:
        """保存进化状态"""
        state = {
            'generation': self.generation,
            'population': [{
                'individual_id': ind.individual_id,
                'genome': ind.genome,
                'fitness_scores': ind.fitness_scores,
                'objectives': ind.objectives,
                'generation': ind.generation,
                'parent_ids': ind.parent_ids,
                'mutation_history': ind.mutation_history
            } for ind in self.population],
            'best_individuals': [{
                'individual_id': ind.individual_id,
                'genome': ind.genome,
                'fitness_scores': ind.fitness_scores,
                'generation': ind.generation
            } for ind in self.best_individuals],
            'stats': self.stats,
            'config': {
                'population_size': self.config.population_size,
                'max_generations': self.config.max_generations,
                'mutation_rate': self.config.mutation_rate,
                'crossover_rate': self.config.crossover_rate,
                'algorithm': self.config.algorithm.value
            }
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        
        logger.info(f"进化状态已保存到 {filepath}")
    
    def load_state(self, filepath: str) -> None:
        """加载进化状态"""
        with open(filepath, 'r', encoding='utf-8') as f:
            state = json.load(f)
        
        self.generation = state['generation']
        self.stats = state['stats']
        
        # 重建种群
        self.population = []
        for ind_data in state['population']:
            individual = Individual(
                individual_id=ind_data['individual_id'],
                genome=ind_data['genome'],
                fitness_scores=ind_data['fitness_scores'],
                objectives=ind_data['objectives'],
                generation=ind_data['generation'],
                parent_ids=ind_data['parent_ids'],
                mutation_history=ind_data['mutation_history']
            )
            self.population.append(individual)
        
        # 重建最佳个体历史
        self.best_individuals = []
        for ind_data in state['best_individuals']:
            individual = Individual(
                individual_id=ind_data['individual_id'],
                genome=ind_data['genome'],
                fitness_scores=ind_data['fitness_scores'],
                generation=ind_data['generation']
            )
            self.best_individuals.append(individual)
        
        logger.info(f"进化状态已从 {filepath} 加载")
    
    def stop_evolution(self) -> None:
        """停止进化过程"""
        self.is_running = False
        logger.info("进化过程停止请求已发送")

if __name__ == "__main__":
    # 测试代码
    logger.info("增强型进化引擎测试开始")
    
    # 创建配置
    config = EvolutionConfig(
        population_size=50,
        max_generations=100,
        algorithm=EvolutionAlgorithm.HYBRID,
        mutation_rate=0.1,
        crossover_rate=0.8
    )
    
    # 创建进化引擎
    engine = EnhancedEvolutionEngine(config)
    
    # 定义简单的评估函数
    def simple_evaluation(individual: Individual) -> Dict[str, float]:
        """简单的评估函数示例"""
        fitness = 0.0
        
        # 基于基因组计算适应度
        for gene_name, gene_value in individual.genome.items():
            if isinstance(gene_value, (int, float)):
                # 简单的适应度函数：接近1.0的基因值获得更高分数
                fitness += 1.0 - abs(gene_value - 1.0)
        
        return {
            'fitness': fitness / len(individual.genome) if individual.genome else 0.0,
            'efficiency': random.uniform(0.3, 1.0),
            'robustness': random.uniform(0.2, 0.9),
            'adaptability': random.uniform(0.1, 0.8),
            'novelty': random.uniform(0.0, 1.0)
        }
    
    # 初始化种群
    engine.initialize_population()
    
    # 运行几代进化
    logger.info("开始测试进化过程")
    
    for generation in range(5):
        engine.evolve_generation(simple_evaluation)
        
        state = engine.get_evolution_state()
        logger.info(f"第 {state['generation']} 代: 最佳适应度={state['best_fitness']:.3f}, "
                   f"平均适应度={state['average_fitness']:.3f}, 多样性={state['diversity']:.3f}")
    
    # 获取最终状态
    final_state = engine.get_evolution_state()
    logger.info(f"测试完成，最终状态: {final_state}")
    
    logger.info("增强型进化引擎测试完成")