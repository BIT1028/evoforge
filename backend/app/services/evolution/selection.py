"""选择算法模块 - 实现多目标优化选择策略

本模块实现了多种选择算法:
- NSGA-II: 非支配排序遗传算法
- 锦标赛选择: Tournament Selection
- 适应度共享: Fitness Sharing
- 精英保留: Elitism
- 岛屿模型: Island Model
"""

import random
import logging
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import math
import copy

logger = logging.getLogger(__name__)

class SelectionMethod(Enum):
    """选择方法枚举"""
    NSGA2 = "nsga2"
    NSGA3 = "nsga3"
    TOURNAMENT = "tournament"
    FITNESS_SHARING = "fitness_sharing"
    ROULETTE_WHEEL = "roulette_wheel"
    RANK_BASED = "rank_based"

@dataclass
class Individual:
    """个体类 - 包含基因组和适应度信息"""
    genome: Any  # Genome对象
    fitness: Dict[str, float] = field(default_factory=dict)
    objectives: Dict[str, float] = field(default_factory=dict)
    constraints: Dict[str, float] = field(default_factory=dict)
    
    # NSGA-II相关属性
    rank: int = 0
    crowding_distance: float = 0.0
    domination_count: int = 0
    dominated_solutions: Set[int] = field(default_factory=set)
    
    # NSGA-III相关属性
    reference_point_distance: float = float('inf')
    associated_reference_point: Optional[Tuple[float, ...]] = None
    niche_count: int = 0
    
    # 其他属性
    age: int = 0
    novelty_score: float = 0.0
    diversity_score: float = 0.0
    
    def __post_init__(self):
        """初始化后处理"""
        logger.debug(f"创建个体，适应度: {self.fitness}")
    
    def dominates(self, other: 'Individual', objectives: List[str]) -> bool:
        """判断是否支配另一个个体
        
        Args:
            other: 另一个个体
            objectives: 目标函数列表
            
        Returns:
            是否支配
        """
        at_least_one_better = False
        
        for obj in objectives:
            self_value = self.objectives.get(obj, 0.0)
            other_value = other.objectives.get(obj, 0.0)
            
            # 假设所有目标都是最大化(适应度越大越好)
            if self_value < other_value:
                return False
            elif self_value > other_value:
                at_least_one_better = True
        
        return at_least_one_better
    
    def copy(self) -> 'Individual':
        """深拷贝个体"""
        return copy.deepcopy(self)

@dataclass
class SelectionConfig:
    """选择配置"""
    method: SelectionMethod = SelectionMethod.NSGA2
    population_size: int = 50
    elite_size: int = 10
    tournament_size: int = 3
    
    # NSGA-II/III参数
    objectives: List[str] = field(default_factory=lambda: ["correctness", "performance", "memory", "complexity"])
    objective_weights: Dict[str, float] = field(default_factory=lambda: {
        "correctness": 1.0,
        "performance": 0.8,
        "memory": 0.6,
        "complexity": -0.4,  # 负权重表示最小化
        "novelty": 0.3
    })
    
    # NSGA-III特有参数
    num_reference_points: Optional[int] = None  # 自动计算或手动指定
    reference_point_divisions: int = 12  # 参考点分割数
    adaptive_reference_points: bool = True  # 是否使用自适应参考点
    
    # 适应度共享参数
    sharing_radius: float = 0.1
    sharing_alpha: float = 1.0
    
    # 约束处理
    constraint_penalty: float = 1000.0
    constraint_tolerance: float = 0.01
    
    # 多样性维护
    diversity_weight: float = 0.2
    novelty_weight: float = 0.1
    age_penalty: float = 0.01

class NSGA2Selector:
    """NSGA-II选择器 - 实现非支配排序遗传算法"""
    
    def __init__(self, config: SelectionConfig):
        """初始化NSGA-II选择器
        
        Args:
            config: 选择配置
        """
        self.config = config
        logger.debug("初始化NSGA-II选择器")
    
    def select(self, population: List[Individual]) -> List[Individual]:
        """使用NSGA-II算法选择个体
        
        Args:
            population: 输入种群
            
        Returns:
            选择后的种群
        """
        logger.debug(f"NSGA-II选择开始，种群大小: {len(population)}")
        
        if len(population) <= self.config.population_size:
            return population
        
        # 1. 非支配排序
        fronts = self._fast_non_dominated_sort(population)
        logger.debug(f"非支配排序完成，前沿数: {len(fronts)}")
        
        # 2. 计算拥挤距离
        for front in fronts:
            self._calculate_crowding_distance(front)
        
        # 3. 选择个体
        selected = []
        front_index = 0
        
        while len(selected) + len(fronts[front_index]) <= self.config.population_size:
            selected.extend(fronts[front_index])
            front_index += 1
            if front_index >= len(fronts):
                break
        
        # 4. 如果需要从最后一个前沿选择部分个体
        if len(selected) < self.config.population_size and front_index < len(fronts):
            remaining = self.config.population_size - len(selected)
            last_front = fronts[front_index]
            
            # 按拥挤距离排序最后一个前沿
            def get_crowding_distance(x):
                if isinstance(x, dict):
                    return x.get('crowding_distance', 0.0)
                else:
                    return getattr(x, 'crowding_distance', 0.0)
            
            last_front.sort(key=get_crowding_distance, reverse=True)
            selected.extend(last_front[:remaining])
        
        logger.debug(f"NSGA-II选择完成，选择个体数: {len(selected)}")
        return selected
    
    def _fast_non_dominated_sort(self, population: List[Individual]) -> List[List[Individual]]:
        """快速非支配排序
        
        Args:
            population: 种群
            
        Returns:
            按前沿分组的个体列表
        """
        logger.debug("开始快速非支配排序")
        
        # 初始化
        for i, individual in enumerate(population):
            # 处理字典格式的个体
            if isinstance(individual, dict):
                individual['domination_count'] = 0
                individual['dominated_solutions'] = set()
            else:
                individual.domination_count = 0
                individual.dominated_solutions = set()
            
            for j, other in enumerate(population):
                if i != j:
                    if self._dominates(individual, other, self.config.objectives):
                        if isinstance(individual, dict):
                            individual['dominated_solutions'].add(j)
                        else:
                            individual.dominated_solutions.add(j)
                    elif self._dominates(other, individual, self.config.objectives):
                        if isinstance(individual, dict):
                            individual['domination_count'] += 1
                        else:
                            individual.domination_count += 1
        
        # 第一前沿
        fronts = []
        current_front = []
        
        for individual in population:
            domination_count = individual.get('domination_count', 0) if isinstance(individual, dict) else individual.domination_count
            if domination_count == 0:
                if isinstance(individual, dict):
                    individual['rank'] = 0
                else:
                    individual.rank = 0
                current_front.append(individual)
        
        fronts.append(current_front)
        
        # 后续前沿
        front_index = 0
        while len(fronts[front_index]) > 0:
            next_front = []
            
            for individual in fronts[front_index]:
                dominated_solutions = individual.get('dominated_solutions', set()) if isinstance(individual, dict) else individual.dominated_solutions
                for j in dominated_solutions:
                    dominated = population[j]
                    if isinstance(dominated, dict):
                        dominated['domination_count'] -= 1
                        if dominated['domination_count'] == 0:
                            dominated['rank'] = front_index + 1
                            next_front.append(dominated)
                    else:
                        dominated.domination_count -= 1
                        if dominated.domination_count == 0:
                            dominated.rank = front_index + 1
                            next_front.append(dominated)
            
            front_index += 1
            fronts.append(next_front)
        
        # 移除空的最后一个前沿
        if not fronts[-1]:
            fronts.pop()
        
        logger.debug(f"非支配排序完成，前沿分布: {[len(f) for f in fronts]}")
        return fronts
    
    def _dominates(self, individual1, individual2, objectives: List[str]) -> bool:
        """判断个体1是否支配个体2
        
        Args:
            individual1: 个体1（可以是Individual对象或字典）
            individual2: 个体2（可以是Individual对象或字典）
            objectives: 目标函数列表
            
        Returns:
            bool: 是否支配
        """
        # 获取目标函数值
        if isinstance(individual1, dict):
            obj1 = individual1.get('objectives', {})
        else:
            obj1 = getattr(individual1, 'objectives', {})
            
        if isinstance(individual2, dict):
            obj2 = individual2.get('objectives', {})
        else:
            obj2 = getattr(individual2, 'objectives', {})
        
        # 检查支配关系
        at_least_one_better = False
        for objective in objectives:
            val1 = obj1.get(objective, 0.0)
            val2 = obj2.get(objective, 0.0)
            
            if val1 < val2:  # 假设最小化问题
                return False
            elif val1 > val2:
                at_least_one_better = True
        
        return at_least_one_better
    
    def _calculate_crowding_distance(self, front: List[Individual]) -> None:
        """计算拥挤距离
        
        Args:
            front: 同一前沿的个体列表
        """
        if len(front) <= 2:
            for individual in front:
                if isinstance(individual, dict):
                    individual['crowding_distance'] = float('inf')
                else:
                    individual.crowding_distance = float('inf')
            return
        
        # 初始化拥挤距离
        for individual in front:
            if isinstance(individual, dict):
                individual['crowding_distance'] = 0.0
            else:
                individual.crowding_distance = 0.0
        
        # 对每个目标函数计算拥挤距离
        for objective in self.config.objectives:
            # 按目标函数值排序
            def get_objective_value(x):
                if isinstance(x, dict):
                    return x.get('objectives', {}).get(objective, 0.0)
                else:
                    return getattr(x, 'objectives', {}).get(objective, 0.0)
            
            front.sort(key=get_objective_value)
            
            # 边界个体设为无穷大
            if isinstance(front[0], dict):
                front[0]['crowding_distance'] = float('inf')
                front[-1]['crowding_distance'] = float('inf')
            else:
                front[0].crowding_distance = float('inf')
                front[-1].crowding_distance = float('inf')
            
            # 计算目标函数值范围
            obj_min = get_objective_value(front[0])
            obj_max = get_objective_value(front[-1])
            obj_range = obj_max - obj_min
            
            if obj_range == 0:
                continue
            
            # 计算中间个体的拥挤距离
            for i in range(1, len(front) - 1):
                current_crowding = front[i].get('crowding_distance', 0.0) if isinstance(front[i], dict) else front[i].crowding_distance
                if current_crowding != float('inf'):
                    distance = (get_objective_value(front[i + 1]) - 
                              get_objective_value(front[i - 1])) / obj_range
                    if isinstance(front[i], dict):
                        front[i]['crowding_distance'] += distance
                    else:
                        front[i].crowding_distance += distance
        
        logger.debug(f"拥挤距离计算完成，前沿大小: {len(front)}")
    
    def get_pareto_front(self, population: List[Individual]) -> List[Individual]:
        """获取帕累托前沿
        
        Args:
            population: 种群
            
        Returns:
            帕累托前沿个体列表
        """
        fronts = self._fast_non_dominated_sort(population)
        return fronts[0] if fronts else []

class TournamentSelector:
    """锦标赛选择器"""
    
    def __init__(self, config: SelectionConfig):
        """初始化锦标赛选择器
        
        Args:
            config: 选择配置
        """
        self.config = config
        logger.debug(f"初始化锦标赛选择器，锦标赛大小: {config.tournament_size}")
    
    def select(self, population: List[Individual]) -> List[Individual]:
        """使用锦标赛选择
        
        Args:
            population: 输入种群
            
        Returns:
            选择后的种群
        """
        logger.debug(f"锦标赛选择开始，种群大小: {len(population)}")
        
        selected = []
        
        for _ in range(self.config.population_size):
            # 随机选择锦标赛参与者
            tournament = random.sample(population, 
                                     min(self.config.tournament_size, len(population)))
            
            # 选择最优个体
            winner = self._tournament_winner(tournament)
            selected.append(winner.copy())
        
        logger.debug(f"锦标赛选择完成，选择个体数: {len(selected)}")
        return selected
    
    def _tournament_winner(self, tournament: List[Individual]) -> Individual:
        """确定锦标赛获胜者
        
        Args:
            tournament: 锦标赛参与者
            
        Returns:
            获胜者
        """
        # 计算综合适应度
        best_individual = tournament[0]
        best_fitness = self._calculate_weighted_fitness(best_individual)
        
        for individual in tournament[1:]:
            fitness = self._calculate_weighted_fitness(individual)
            if fitness > best_fitness:
                best_fitness = fitness
                best_individual = individual
        
        return best_individual
    
    def _calculate_weighted_fitness(self, individual: Individual) -> float:
        """计算加权适应度
        
        Args:
            individual: 个体
            
        Returns:
            加权适应度值
        """
        weighted_fitness = 0.0
        
        for objective, weight in self.config.objective_weights.items():
            value = individual.objectives.get(objective, 0.0)
            weighted_fitness += weight * value
        
        # 约束惩罚
        constraint_violation = 0.0
        for constraint, value in individual.constraints.items():
            if value > self.config.constraint_tolerance:
                constraint_violation += value
        
        weighted_fitness -= self.config.constraint_penalty * constraint_violation
        
        # 年龄惩罚
        weighted_fitness -= self.config.age_penalty * individual.age
        
        # 多样性奖励
        weighted_fitness += self.config.diversity_weight * individual.diversity_score
        weighted_fitness += self.config.novelty_weight * individual.novelty_score
        
        return weighted_fitness

class FitnessSharingSelector:
    """适应度共享选择器"""
    
    def __init__(self, config: SelectionConfig):
        """初始化适应度共享选择器
        
        Args:
            config: 选择配置
        """
        self.config = config
        logger.debug(f"初始化适应度共享选择器，共享半径: {config.sharing_radius}")
    
    def select(self, population: List[Individual]) -> List[Individual]:
        """使用适应度共享选择
        
        Args:
            population: 输入种群
            
        Returns:
            选择后的种群
        """
        logger.debug(f"适应度共享选择开始，种群大小: {len(population)}")
        
        # 计算共享适应度
        shared_fitness = self._calculate_shared_fitness(population)
        
        # 轮盘赌选择
        selected = []
        total_fitness = sum(shared_fitness)
        
        if total_fitness <= 0:
            # 如果总适应度为0或负数，随机选择
            selected = random.choices(population, k=self.config.population_size)
        else:
            probabilities = [f / total_fitness for f in shared_fitness]
            selected = random.choices(population, weights=probabilities, 
                                    k=self.config.population_size)
        
        logger.debug(f"适应度共享选择完成，选择个体数: {len(selected)}")
        return [ind.copy() for ind in selected]
    
    def _calculate_shared_fitness(self, population: List[Individual]) -> List[float]:
        """计算共享适应度
        
        Args:
            population: 种群
            
        Returns:
            共享适应度列表
        """
        shared_fitness = []
        
        for i, individual in enumerate(population):
            # 计算原始适应度
            raw_fitness = self._calculate_raw_fitness(individual)
            
            # 计算共享函数
            niche_count = 0.0
            for j, other in enumerate(population):
                distance = self._calculate_distance(individual, other)
                if distance < self.config.sharing_radius:
                    sharing_value = 1.0 - (distance / self.config.sharing_radius) ** self.config.sharing_alpha
                    niche_count += sharing_value
            
            # 共享适应度
            if niche_count > 0:
                shared_fitness.append(raw_fitness / niche_count)
            else:
                shared_fitness.append(raw_fitness)
        
        return shared_fitness
    
    def _calculate_raw_fitness(self, individual: Individual) -> float:
        """计算原始适应度
        
        Args:
            individual: 个体
            
        Returns:
            原始适应度
        """
        fitness = 0.0
        
        for objective, weight in self.config.objective_weights.items():
            value = individual.objectives.get(objective, 0.0)
            fitness += weight * value
        
        return max(0.0, fitness)  # 确保非负
    
    def _calculate_distance(self, ind1: Individual, ind2: Individual) -> float:
        """计算两个个体之间的距离
        
        Args:
            ind1: 个体1
            ind2: 个体2
            
        Returns:
            距离值
        """
        # 在目标空间中计算欧几里得距离
        distance = 0.0
        
        for objective in self.config.objectives:
            val1 = ind1.objectives.get(objective, 0.0)
            val2 = ind2.objectives.get(objective, 0.0)
            distance += (val1 - val2) ** 2
        
        return math.sqrt(distance)

class RouletteWheelSelector:
    """轮盘赌选择器"""
    
    def __init__(self, config: SelectionConfig):
        """初始化轮盘赌选择器
        
        Args:
            config: 选择配置
        """
        self.config = config
        logger.debug("初始化轮盘赌选择器")
    
    def select(self, population: List[Individual]) -> List[Individual]:
        """使用轮盘赌选择
        
        Args:
            population: 输入种群
            
        Returns:
            选择后的种群
        """
        logger.debug(f"轮盘赌选择开始，种群大小: {len(population)}")
        
        # 计算适应度
        fitness_values = [self._calculate_fitness(ind) for ind in population]
        total_fitness = sum(fitness_values)
        
        selected = []
        
        if total_fitness <= 0:
            # 如果总适应度为0或负数，随机选择
            selected = random.choices(population, k=self.config.population_size)
        else:
            # 计算选择概率
            probabilities = [f / total_fitness for f in fitness_values]
            selected = random.choices(population, weights=probabilities, 
                                    k=self.config.population_size)
        
        logger.debug(f"轮盘赌选择完成，选择个体数: {len(selected)}")
        return [ind.copy() for ind in selected]
    
    def _calculate_fitness(self, individual: Individual) -> float:
        """计算个体适应度
        
        Args:
            individual: 个体
            
        Returns:
            适应度值
        """
        fitness = 0.0
        
        for objective, weight in self.config.objective_weights.items():
            value = individual.objectives.get(objective, 0.0)
            fitness += weight * value
        
        return max(0.0, fitness)  # 确保非负

class RankBasedSelector:
    """基于排名的选择器"""
    
    def __init__(self, config: SelectionConfig):
        """初始化基于排名的选择器
        
        Args:
            config: 选择配置
        """
        self.config = config
        self.selection_pressure = 2.0  # 选择压力参数
        logger.debug("初始化基于排名的选择器")
    
    def select(self, population: List[Individual]) -> List[Individual]:
        """使用基于排名的选择
        
        Args:
            population: 输入种群
            
        Returns:
            选择后的种群
        """
        logger.debug(f"基于排名选择开始，种群大小: {len(population)}")
        
        # 按适应度排序
        sorted_population = sorted(population, 
                                 key=lambda x: self._calculate_fitness(x), 
                                 reverse=True)
        
        # 计算排名概率
        n = len(population)
        probabilities = []
        
        for i in range(n):
            rank = i + 1  # 排名从1开始
            prob = (2 - self.selection_pressure) / n + \
                   2 * rank * (self.selection_pressure - 1) / (n * (n - 1))
            probabilities.append(prob)
        
        # 选择个体
        selected = random.choices(sorted_population, weights=probabilities, 
                                k=self.config.population_size)
        
        logger.debug(f"基于排名选择完成，选择个体数: {len(selected)}")
        return [ind.copy() for ind in selected]
    
    def _calculate_fitness(self, individual: Individual) -> float:
        """计算个体适应度
        
        Args:
            individual: 个体
            
        Returns:
            适应度值
        """
        fitness = 0.0
        
        for objective, weight in self.config.objective_weights.items():
            value = individual.objectives.get(objective, 0.0)
            fitness += weight * value
        
        return fitness

class SelectionManager:
    """选择管理器 - 统一的选择接口"""
    
    def __init__(self, config: SelectionConfig):
        """初始化选择管理器
        
        Args:
            config: 选择配置
        """
        self.config = config
        
        # 初始化选择器
        if config.method == SelectionMethod.NSGA2:
            self.selector = NSGA2Selector(config)
        elif config.method == SelectionMethod.NSGA3:
            self.selector = NSGA3Selector(config)
        elif config.method == SelectionMethod.TOURNAMENT:
            self.selector = TournamentSelector(config)
        elif config.method == SelectionMethod.FITNESS_SHARING:
            self.selector = FitnessSharingSelector(config)
        elif config.method == SelectionMethod.ROULETTE_WHEEL:
            self.selector = RouletteWheelSelector(config)
        elif config.method == SelectionMethod.RANK_BASED:
            self.selector = RankBasedSelector(config)
        else:
            logger.warning(f"未知选择方法: {config.method}，使用NSGA-III")
            self.selector = NSGA3Selector(config)
        
        logger.debug(f"初始化选择管理器，方法: {config.method}")
    
    def select(self, population: List[Individual]) -> List[Individual]:
        """执行选择
        
        Args:
            population: 输入种群（可以是Individual对象或字典）
            
        Returns:
            选择后的种群
        """
        logger.debug(f"开始选择，种群大小: {len(population)}")
        
        # 处理字典格式的输入（来自_selection方法）
        processed_population = []
        for individual in population:
            if isinstance(individual, dict):
                # 字典格式，需要安全地更新age
                if 'age' not in individual:
                    individual['age'] = 0
                individual['age'] += 1
                processed_population.append(individual)
            else:
                # Individual对象格式
                if hasattr(individual, 'age'):
                    individual.age += 1
                else:
                    individual.age = 1
                processed_population.append(individual)
        
        # 执行选择
        selected = self.selector.select(processed_population)
        
        # 精英保留
        if self.config.elite_size > 0:
            selected = self._apply_elitism(processed_population, selected)
        
        logger.debug(f"选择完成，输出种群大小: {len(selected)}")
        return selected
    
    def _apply_elitism(self, original_population: List[Individual], 
                      selected_population: List[Individual]) -> List[Individual]:
        """应用精英保留策略
        
        Args:
            original_population: 原始种群
            selected_population: 选择后的种群
            
        Returns:
            应用精英保留后的种群
        """
        logger.debug(f"应用精英保留，精英数量: {self.config.elite_size}")
        
        # 按适应度排序原始种群
        sorted_original = sorted(original_population, 
                               key=lambda x: self._calculate_elite_fitness(x), 
                               reverse=True)
        
        # 选择精英
        elites = sorted_original[:self.config.elite_size]
        
        # 替换选择种群中的最差个体
        sorted_selected = sorted(selected_population, 
                               key=lambda x: self._calculate_elite_fitness(x), 
                               reverse=True)
        
        # 保留最好的个体，用精英替换最差的
        final_population = sorted_selected[:-self.config.elite_size] + elites
        
        return final_population
    
    def _calculate_elite_fitness(self, individual) -> float:
        """计算精英适应度
        
        Args:
            individual: 个体（可以是Individual对象或字典）
            
        Returns:
            适应度值
        """
        fitness = 0.0
        
        # 处理字典格式和Individual对象格式
        if isinstance(individual, dict):
            objectives = individual.get('objectives', {})
        else:
            objectives = getattr(individual, 'objectives', {})
        
        for objective, weight in self.config.objective_weights.items():
            value = objectives.get(objective, 0.0)
            fitness += weight * value
        
        return fitness

# 便利函数
def select_population(population: List[Individual], 
                     config: Optional[SelectionConfig] = None) -> List[Individual]:
    """选择种群
    
    Args:
        population: 输入种群
        config: 选择配置
        
    Returns:
        选择后的种群
    """
    if config is None:
        config = SelectionConfig()
    
    manager = SelectionManager(config)
    return manager.select(population)

def multi_objective_select(population: List[Individual], 
                          objectives: List[str],
                          method: SelectionMethod = SelectionMethod.NSGA2,
                          population_size: int = 50) -> List[Individual]:
    """多目标选择
    
    Args:
        population: 输入种群
        objectives: 目标函数列表
        method: 选择方法
        population_size: 目标种群大小
        
    Returns:
        选择后的种群
    """
    config = SelectionConfig(
        method=method,
        objectives=objectives,
        population_size=population_size
    )
    
    manager = SelectionManager(config)
    return manager.select(population)

def tournament_select(population: List[Individual], 
                     tournament_size: int = 3,
                     population_size: int = 50) -> List[Individual]:
    """锦标赛选择
    
    Args:
        population: 输入种群
        tournament_size: 锦标赛大小
        population_size: 目标种群大小
        
    Returns:
        选择后的种群
    """
    config = SelectionConfig(
        method=SelectionMethod.TOURNAMENT,
        tournament_size=tournament_size,
        population_size=population_size
    )
    
    manager = SelectionManager(config)
    return manager.select(population)

def create_individual_from_genome(genome: Any, 
                                objectives: Optional[Dict[str, float]] = None) -> Individual:
    """从基因组创建个体
    
    Args:
        genome: 基因组对象
        objectives: 目标函数值
        
    Returns:
        个体对象
    """
    individual = Individual(genome=genome)
    if objectives:
        individual.objectives = objectives.copy()
        individual.fitness = objectives.copy()
    
    return individual

def evaluate_diversity(population: List[Individual], 
                      objectives: List[str]) -> List[float]:
    """评估种群多样性
    
    Args:
        population: 种群
        objectives: 目标函数列表
        
    Returns:
        每个个体的多样性分数
    """
    diversity_scores = []
    
    for i, individual in enumerate(population):
        # 计算与其他个体的平均距离
        distances = []
        
        for j, other in enumerate(population):
            if i != j:
                distance = 0.0
                for obj in objectives:
                    val1 = individual.objectives.get(obj, 0.0)
                    val2 = other.objectives.get(obj, 0.0)
                    distance += (val1 - val2) ** 2
                distances.append(math.sqrt(distance))
        
        avg_distance = sum(distances) / len(distances) if distances else 0.0
        diversity_scores.append(avg_distance)
    
    return diversity_scores

def calculate_hypervolume(population: List[Individual], 
                         objectives: List[str],
                         reference_point: Optional[Dict[str, float]] = None) -> float:
    """计算超体积指标
    
    Args:
        population: 种群
        objectives: 目标函数列表
        reference_point: 参考点
        
    Returns:
        超体积值
    """
    if not population or not objectives:
        return 0.0
    
    # 简化的超体积计算（仅适用于2D情况）
    if len(objectives) == 2:
        obj1, obj2 = objectives
        
        # 获取所有目标值
        points = []
        for ind in population:
            val1 = ind.objectives.get(obj1, 0.0)
            val2 = ind.objectives.get(obj2, 0.0)
            points.append((val1, val2))
        
        # 按第一个目标排序
        points.sort(key=lambda x: x[0], reverse=True)
        
        # 计算超体积
        hypervolume = 0.0
        prev_x = 0.0
        
        for x, y in points:
            if x > prev_x:
                hypervolume += (x - prev_x) * y
                prev_x = x
        
        return hypervolume
    
    # 对于高维情况，返回近似值
    return len(population)

class NSGA3Selector:
    """NSGA-III选择器 - 实现基于参考点的多目标优化算法
    
    NSGA-III相比NSGA-II的主要改进：
    1. 使用结构化参考点替代拥挤距离
    2. 更好的多样性维护机制
    3. 适用于多目标优化问题（3个以上目标）
    """
    
    def __init__(self, config: SelectionConfig):
        """初始化NSGA-III选择器
        
        Args:
            config: 选择配置
        """
        self.config = config
        self.reference_points = self._generate_reference_points()
        logger.debug(f"初始化NSGA-III选择器，参考点数量: {len(self.reference_points)}")
    
    def select(self, population: List[Individual]) -> List[Individual]:
        """使用NSGA-III算法选择个体
        
        Args:
            population: 输入种群
            
        Returns:
            选择后的种群
        """
        logger.debug(f"NSGA-III选择开始，种群大小: {len(population)}")
        
        if len(population) <= self.config.population_size:
            return population
        
        # 1. 非支配排序（与NSGA-II相同）
        fronts = self._fast_non_dominated_sort(population)
        logger.debug(f"非支配排序完成，前沿数: {len(fronts)}")
        
        # 2. 选择个体直到最后一个前沿
        selected = []
        last_front_index = 0
        
        for i, front in enumerate(fronts):
            if len(selected) + len(front) <= self.config.population_size:
                selected.extend(front)
                last_front_index = i + 1
            else:
                break
        
        # 3. 如果需要从最后一个前沿选择部分个体
        if len(selected) < self.config.population_size and last_front_index < len(fronts):
            remaining = self.config.population_size - len(selected)
            last_front = fronts[last_front_index]
            
            # 使用参考点选择机制
            selected_from_last = self._reference_point_selection(last_front, remaining)
            selected.extend(selected_from_last)
        
        logger.debug(f"NSGA-III选择完成，选择个体数: {len(selected)}")
        return selected
    
    def _generate_reference_points(self) -> List[Tuple[float, ...]]:
        """生成结构化参考点
        
        使用Das and Dennis方法生成均匀分布的参考点
        
        Returns:
            参考点列表
        """
        num_objectives = len(self.config.objectives)
        divisions = self.config.reference_point_divisions
        
        if self.config.num_reference_points:
            # 如果指定了参考点数量，调整分割数
            divisions = int((self.config.num_reference_points * math.factorial(num_objectives)) ** (1/num_objectives))
        
        reference_points = []
        
        def generate_recursive(point, remaining_sum, remaining_dims):
            """递归生成参考点"""
            if remaining_dims == 1:
                point.append(remaining_sum)
                reference_points.append(tuple(point))
                point.pop()
                return
            
            for i in range(remaining_sum + 1):
                point.append(i / divisions)
                generate_recursive(point, remaining_sum - i, remaining_dims - 1)
                point.pop()
        
        generate_recursive([], divisions, num_objectives)
        
        logger.debug(f"生成参考点数量: {len(reference_points)}")
        return reference_points
    
    def _reference_point_selection(self, front: List[Individual], k: int) -> List[Individual]:
        """基于参考点的选择机制
        
        Args:
            front: 最后一个前沿的个体
            k: 需要选择的个体数量
            
        Returns:
            选择的个体列表
        """
        # 1. 归一化目标值
        normalized_front = self._normalize_objectives(front)
        
        # 2. 将个体关联到最近的参考点
        self._associate_to_reference_points(normalized_front)
        
        # 3. 计算每个参考点的小生境计数
        niche_counts = self._calculate_niche_counts(normalized_front)
        
        # 4. 选择个体
        selected = []
        
        for _ in range(k):
            # 找到小生境计数最小的参考点
            min_niche_count = min(niche_counts.values())
            candidate_points = [rp for rp, count in niche_counts.items() if count == min_niche_count]
            
            # 随机选择一个参考点
            selected_point = random.choice(candidate_points)
            
            # 从该参考点关联的个体中选择
            candidates = [ind for ind in normalized_front 
                         if ind.associated_reference_point == selected_point and ind not in selected]
            
            if candidates:
                # 选择距离参考点最近的个体
                best_candidate = min(candidates, key=lambda x: x.reference_point_distance)
                selected.append(best_candidate)
                niche_counts[selected_point] += 1
            else:
                # 如果没有候选个体，随机选择一个
                remaining = [ind for ind in normalized_front if ind not in selected]
                if remaining:
                    selected.append(random.choice(remaining))
        
        return selected
    
    def _normalize_objectives(self, front: List[Individual]) -> List[Individual]:
        """归一化目标值
        
        Args:
            front: 个体列表
            
        Returns:
            归一化后的个体列表
        """
        if not front:
            return front
        
        # 计算每个目标的最小值和最大值
        obj_mins = {}
        obj_maxs = {}
        
        for obj in self.config.objectives:
            values = [ind.objectives.get(obj, 0.0) for ind in front]
            obj_mins[obj] = min(values)
            obj_maxs[obj] = max(values)
        
        # 归一化
        normalized_front = []
        for individual in front:
            normalized_ind = individual.copy()
            normalized_objectives = {}
            
            for obj in self.config.objectives:
                value = individual.objectives.get(obj, 0.0)
                min_val = obj_mins[obj]
                max_val = obj_maxs[obj]
                
                if max_val > min_val:
                    normalized_value = (value - min_val) / (max_val - min_val)
                else:
                    normalized_value = 0.0
                
                normalized_objectives[obj] = normalized_value
            
            normalized_ind.objectives = normalized_objectives
            normalized_front.append(normalized_ind)
        
        return normalized_front
    
    def _associate_to_reference_points(self, front: List[Individual]) -> None:
        """将个体关联到最近的参考点
        
        Args:
            front: 个体列表
        """
        for individual in front:
            min_distance = float('inf')
            closest_point = None
            
            # 获取个体的目标向量
            obj_vector = tuple(individual.objectives.get(obj, 0.0) for obj in self.config.objectives)
            
            # 找到最近的参考点
            for ref_point in self.reference_points:
                distance = self._calculate_perpendicular_distance(obj_vector, ref_point)
                
                if distance < min_distance:
                    min_distance = distance
                    closest_point = ref_point
            
            individual.associated_reference_point = closest_point
            individual.reference_point_distance = min_distance
    
    def _calculate_perpendicular_distance(self, point: Tuple[float, ...], reference_point: Tuple[float, ...]) -> float:
        """计算点到参考点的垂直距离
        
        Args:
            point: 个体的目标向量
            reference_point: 参考点
            
        Returns:
            垂直距离
        """
        # 计算点到参考线的垂直距离
        # 参考线从原点指向参考点
        
        # 向量投影
        dot_product = sum(p * r for p, r in zip(point, reference_point))
        ref_norm_squared = sum(r * r for r in reference_point)
        
        if ref_norm_squared == 0:
            return math.sqrt(sum(p * p for p in point))
        
        projection_length = dot_product / ref_norm_squared
        projection = tuple(projection_length * r for r in reference_point)
        
        # 计算垂直距离
        distance_squared = sum((p - proj) ** 2 for p, proj in zip(point, projection))
        return math.sqrt(distance_squared)
    
    def _calculate_niche_counts(self, front: List[Individual]) -> Dict[Tuple[float, ...], int]:
        """计算每个参考点的小生境计数
        
        Args:
            front: 个体列表
            
        Returns:
            参考点到计数的映射
        """
        niche_counts = {rp: 0 for rp in self.reference_points}
        
        for individual in front:
            if individual.associated_reference_point:
                niche_counts[individual.associated_reference_point] += 1
        
        return niche_counts
    
    def _fast_non_dominated_sort(self, population: List[Individual]) -> List[List[Individual]]:
        """快速非支配排序（与NSGA-II相同）
        
        Args:
            population: 种群
            
        Returns:
            按前沿分组的个体列表
        """
        logger.debug("开始快速非支配排序")
        
        # 初始化
        for i, individual in enumerate(population):
            individual.domination_count = 0
            individual.dominated_solutions = set()
            
            for j, other in enumerate(population):
                if i != j:
                    if individual.dominates(other, self.config.objectives):
                        individual.dominated_solutions.add(j)
                    elif other.dominates(individual, self.config.objectives):
                        individual.domination_count += 1
        
        # 第一前沿
        fronts = []
        current_front = []
        
        for individual in population:
            if individual.domination_count == 0:
                individual.rank = 0
                current_front.append(individual)
        
        fronts.append(current_front)
        
        # 后续前沿
        front_index = 0
        while len(fronts[front_index]) > 0:
            next_front = []
            
            for individual in fronts[front_index]:
                for j in individual.dominated_solutions:
                    dominated = population[j]
                    dominated.domination_count -= 1
                    
                    if dominated.domination_count == 0:
                        dominated.rank = front_index + 1
                        next_front.append(dominated)
            
            front_index += 1
            fronts.append(next_front)
        
        # 移除空的最后一个前沿
        if not fronts[-1]:
            fronts.pop()
        
        logger.debug(f"非支配排序完成，前沿分布: {[len(f) for f in fronts]}")
        return fronts