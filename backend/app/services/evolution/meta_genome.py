import numpy as np
from typing import List, Dict, Optional, Any, Tuple, Callable
from .digital_cell import DigitalCell, create_digital_cell
from .physics_engine import PhysicsEngine
import random
import json
import time
from dataclasses import dataclass, asdict
from collections import defaultdict
import copy

@dataclass
class EvolutionStats:
    """进化统计信息"""
    generation: int
    population_size: int
    average_fitness: float
    best_fitness: float
    worst_fitness: float
    diversity_score: float
    mutation_rate: float
    selection_pressure: float
    compilation_success_rate: float
    energy_efficiency: float

@dataclass
class GenomePattern:
    """基因组模式"""
    pattern_id: str
    genes: Dict[str, Any]
    fitness_history: List[float]
    usage_count: int
    success_rate: float
    last_used: float

class FitnessEvaluator:
    """适应度评估器
    
    负责评估细胞和基因组的适应度，支持多种评估策略。
    """
    
    def __init__(self, evaluation_strategy: str = 'comprehensive'):
        """
        初始化适应度评估器
        
        Args:
            evaluation_strategy: 评估策略 ('energy', 'compilation', 'comprehensive')
        """
        self.evaluation_strategy = evaluation_strategy
        self.fitness_history: Dict[str, List[float]] = defaultdict(list)
        self.evaluation_count = 0
    
    def evaluate_cell(self, cell: DigitalCell) -> float:
        """评估单个细胞的适应度
        
        Args:
            cell: 要评估的细胞
            
        Returns:
            float: 适应度值 (0-1)
        """
        self.evaluation_count += 1
        
        if self.evaluation_strategy == 'energy':
            fitness = self._evaluate_energy_fitness(cell)
        elif self.evaluation_strategy == 'compilation':
            fitness = self._evaluate_compilation_fitness(cell)
        else:  # comprehensive
            fitness = self._evaluate_comprehensive_fitness(cell)
        
        # 记录适应度历史
        self.fitness_history[cell.id].append(fitness)
        
        return fitness
    
    def _evaluate_energy_fitness(self, cell: DigitalCell) -> float:
        """基于能量的适应度评估
        
        Args:
            cell: 细胞
            
        Returns:
            float: 能量适应度
        """
        energy_ratio = cell.energy / cell.max_energy
        health_factor = cell.health
        age_factor = 1.0 / (1.0 + cell.age * 0.01)  # 年龄惩罚
        
        return energy_ratio * health_factor * age_factor
    
    def _evaluate_compilation_fitness(self, cell: DigitalCell) -> float:
        """基于编译成功率的适应度评估
        
        Args:
            cell: 细胞
            
        Returns:
            float: 编译适应度
        """
        mitochondria = cell.cytoplasm.organelles.get('mitochondria')
        if not mitochondria:
            return 0.1
        
        from .organelles import CompilerRunner
        if isinstance(mitochondria, CompilerRunner):
            stats = mitochondria.get_compilation_stats()
            success_rate = stats.get('success_rate', 0.0)
            compilation_count = stats.get('compilation_count', 0)
            
            # 奖励编译次数
            activity_bonus = min(0.3, compilation_count * 0.01)
            
            return success_rate + activity_bonus
        
        return 0.1
    
    def _evaluate_comprehensive_fitness(self, cell: DigitalCell) -> float:
        """综合适应度评估
        
        Args:
            cell: 细胞
            
        Returns:
            float: 综合适应度
        """
        # 能量适应度 (30%)
        energy_fitness = self._evaluate_energy_fitness(cell) * 0.3
        
        # 编译适应度 (40%)
        compilation_fitness = self._evaluate_compilation_fitness(cell) * 0.4
        
        # 生存适应度 (20%)
        survival_fitness = (1.0 if not cell.is_dead() else 0.0) * 0.2
        
        # 繁殖适应度 (10%)
        reproduction_fitness = (1.0 if cell.can_divide() else 0.0) * 0.1
        
        return energy_fitness + compilation_fitness + survival_fitness + reproduction_fitness
    
    def get_fitness_trend(self, cell_id: str, window_size: int = 10) -> float:
        """获取适应度趋势
        
        Args:
            cell_id: 细胞ID
            window_size: 窗口大小
            
        Returns:
            float: 适应度趋势 (-1到1，负值表示下降趋势)
        """
        history = self.fitness_history.get(cell_id, [])
        if len(history) < 2:
            return 0.0
        
        recent_history = history[-window_size:]
        if len(recent_history) < 2:
            return 0.0
        
        # 计算线性趋势
        x = np.arange(len(recent_history))
        y = np.array(recent_history)
        
        # 简单线性回归
        slope = np.corrcoef(x, y)[0, 1] if len(x) > 1 else 0.0
        return np.clip(slope, -1.0, 1.0)

class SelectionOperator:
    """选择算子
    
    实现各种选择策略，用于进化算法中的个体选择。
    """
    
    def __init__(self, selection_method: str = 'tournament'):
        """
        初始化选择算子
        
        Args:
            selection_method: 选择方法 ('tournament', 'roulette', 'rank')
        """
        self.selection_method = selection_method
        self.selection_pressure = 2.0
    
    def select_parents(self, 
                      population: List[DigitalCell], 
                      fitness_scores: List[float], 
                      num_parents: int) -> List[DigitalCell]:
        """选择父代个体
        
        Args:
            population: 种群
            fitness_scores: 适应度分数
            num_parents: 父代数量
            
        Returns:
            List[DigitalCell]: 选中的父代
        """
        if self.selection_method == 'tournament':
            return self._tournament_selection(population, fitness_scores, num_parents)
        elif self.selection_method == 'roulette':
            return self._roulette_selection(population, fitness_scores, num_parents)
        elif self.selection_method == 'rank':
            return self._rank_selection(population, fitness_scores, num_parents)
        else:
            return self._tournament_selection(population, fitness_scores, num_parents)
    
    def _tournament_selection(self, 
                             population: List[DigitalCell], 
                             fitness_scores: List[float], 
                             num_parents: int) -> List[DigitalCell]:
        """锦标赛选择
        
        Args:
            population: 种群
            fitness_scores: 适应度分数
            num_parents: 父代数量
            
        Returns:
            List[DigitalCell]: 选中的父代
        """
        parents = []
        tournament_size = max(2, int(len(population) * 0.1))
        
        for _ in range(num_parents):
            # 随机选择锦标赛参与者
            tournament_indices = random.sample(range(len(population)), 
                                             min(tournament_size, len(population)))
            
            # 选择适应度最高的个体
            best_idx = max(tournament_indices, key=lambda i: fitness_scores[i])
            parents.append(population[best_idx])
        
        return parents
    
    def _roulette_selection(self, 
                           population: List[DigitalCell], 
                           fitness_scores: List[float], 
                           num_parents: int) -> List[DigitalCell]:
        """轮盘赌选择
        
        Args:
            population: 种群
            fitness_scores: 适应度分数
            num_parents: 父代数量
            
        Returns:
            List[DigitalCell]: 选中的父代
        """
        parents = []
        total_fitness = sum(fitness_scores)
        
        if total_fitness == 0:
            # 如果总适应度为0，随机选择
            return random.sample(population, min(num_parents, len(population)))
        
        for _ in range(num_parents):
            pick = random.uniform(0, total_fitness)
            current = 0
            
            for i, fitness in enumerate(fitness_scores):
                current += fitness
                if current >= pick:
                    parents.append(population[i])
                    break
        
        return parents
    
    def _rank_selection(self, 
                       population: List[DigitalCell], 
                       fitness_scores: List[float], 
                       num_parents: int) -> List[DigitalCell]:
        """排名选择
        
        Args:
            population: 种群
            fitness_scores: 适应度分数
            num_parents: 父代数量
            
        Returns:
            List[DigitalCell]: 选中的父代
        """
        # 按适应度排序
        sorted_indices = sorted(range(len(population)), 
                              key=lambda i: fitness_scores[i], 
                              reverse=True)
        
        # 基于排名的概率分布
        ranks = list(range(len(population), 0, -1))
        total_rank = sum(ranks)
        
        parents = []
        for _ in range(num_parents):
            pick = random.uniform(0, total_rank)
            current = 0
            
            for i, rank in enumerate(ranks):
                current += rank
                if current >= pick:
                    parents.append(population[sorted_indices[i]])
                    break
        
        return parents

class MutationOperator:
    """突变算子
    
    实现基因组的突变操作，包括点突变、插入、删除等。
    """
    
    def __init__(self, mutation_rate: float = 0.1):
        """
        初始化突变算子
        
        Args:
            mutation_rate: 突变率
        """
        self.mutation_rate = mutation_rate
        self.mutation_strength = 0.1
        self.mutation_types = ['point', 'insertion', 'deletion', 'duplication']
    
    def mutate_genome(self, genome: Dict[str, Any]) -> Dict[str, Any]:
        """突变基因组
        
        Args:
            genome: 原始基因组
            
        Returns:
            Dict[str, Any]: 突变后的基因组
        """
        mutated_genome = copy.deepcopy(genome)
        
        for gene_name, gene_data in mutated_genome.items():
            if random.random() < self.mutation_rate:
                self._mutate_gene(gene_data)
        
        # 有时添加新基因
        if random.random() < self.mutation_rate * 0.1:
            self._add_random_gene(mutated_genome)
        
        # 有时删除基因
        if len(mutated_genome) > 1 and random.random() < self.mutation_rate * 0.05:
            self._remove_random_gene(mutated_genome)
        
        return mutated_genome
    
    def _mutate_gene(self, gene_data: Dict[str, Any]):
        """突变单个基因
        
        Args:
            gene_data: 基因数据
        """
        instructions = gene_data.get('instructions', [])
        if not instructions:
            return
        
        mutation_type = random.choice(self.mutation_types)
        
        if mutation_type == 'point':
            self._point_mutation(instructions)
        elif mutation_type == 'insertion':
            self._insertion_mutation(instructions)
        elif mutation_type == 'deletion' and len(instructions) > 1:
            self._deletion_mutation(instructions)
        elif mutation_type == 'duplication':
            self._duplication_mutation(instructions)
    
    def _point_mutation(self, instructions: List[Dict[str, Any]]):
        """点突变
        
        Args:
            instructions: 指令列表
        """
        if not instructions:
            return
        
        idx = random.randint(0, len(instructions) - 1)
        instruction = instructions[idx]
        
        # 突变指令参数
        if 'value' in instruction and isinstance(instruction['value'], (int, float)):
            instruction['value'] += random.gauss(0, self.mutation_strength)
        elif 'name' in instruction:
            # 随机修改名称
            instruction['name'] = f"mutated_{random.randint(1000, 9999)}"
        elif 'type' in instruction:
            # 随机改变指令类型
            instruction['type'] = random.choice(['CREATE_FUNCTION', 'CREATE_ASSIGNMENT', 'CREATE_EXPRESSION'])
    
    def _insertion_mutation(self, instructions: List[Dict[str, Any]]):
        """插入突变
        
        Args:
            instructions: 指令列表
        """
        new_instruction = self._create_random_instruction()
        insert_pos = random.randint(0, len(instructions))
        instructions.insert(insert_pos, new_instruction)
    
    def _deletion_mutation(self, instructions: List[Dict[str, Any]]):
        """删除突变
        
        Args:
            instructions: 指令列表
        """
        if len(instructions) > 1:
            del_pos = random.randint(0, len(instructions) - 1)
            del instructions[del_pos]
    
    def _duplication_mutation(self, instructions: List[Dict[str, Any]]):
        """重复突变
        
        Args:
            instructions: 指令列表
        """
        if instructions:
            dup_pos = random.randint(0, len(instructions) - 1)
            duplicated = copy.deepcopy(instructions[dup_pos])
            insert_pos = random.randint(0, len(instructions))
            instructions.insert(insert_pos, duplicated)
    
    def _add_random_gene(self, genome: Dict[str, Any]):
        """添加随机基因
        
        Args:
            genome: 基因组
        """
        gene_name = f"random_gene_{random.randint(1000, 9999)}"
        genome[gene_name] = {
            'instructions': [self._create_random_instruction()],
            'stability': random.uniform(0.5, 1.0)
        }
    
    def _remove_random_gene(self, genome: Dict[str, Any]):
        """移除随机基因
        
        Args:
            genome: 基因组
        """
        if len(genome) > 1:
            gene_to_remove = random.choice(list(genome.keys()))
            del genome[gene_to_remove]
    
    def _create_random_instruction(self) -> Dict[str, Any]:
        """创建随机指令
        
        Returns:
            Dict[str, Any]: 随机指令
        """
        instruction_types = ['CREATE_FUNCTION', 'CREATE_ASSIGNMENT', 'CREATE_EXPRESSION']
        instruction_type = random.choice(instruction_types)
        
        if instruction_type == 'CREATE_FUNCTION':
            return {
                'type': 'CREATE_FUNCTION',
                'name': f"func_{random.randint(100, 999)}",
                'args': []
            }
        elif instruction_type == 'CREATE_ASSIGNMENT':
            return {
                'type': 'CREATE_ASSIGNMENT',
                'target': f"var_{random.randint(100, 999)}"
            }
        else:  # CREATE_EXPRESSION
            return {
                'type': 'CREATE_EXPRESSION',
                'expr_type': random.choice(['Constant', 'Name']),
                'value': random.randint(1, 100) if random.random() < 0.5 else f"var_{random.randint(100, 999)}"
            }

class MetaGenome:
    """元基因组 - 种群级别的基因组管理
    
    元基因组管理整个细胞种群的进化过程，包括选择、交叉、突变等操作。
    它维护基因组模式库，跟踪进化统计信息，并协调种群的进化。
    """
    
    def __init__(self, 
                 population_size: int = 50,
                 world_size: Tuple[float, float, float] = (100.0, 100.0, 100.0)):
        """
        初始化元基因组
        
        Args:
            population_size: 种群大小
            world_size: 世界大小 (x, y, z)
        """
        self.population_size = population_size
        self.world_size = world_size
        self.generation = 0
        
        # 种群
        self.population: List[DigitalCell] = []
        
        # 进化组件
        self.fitness_evaluator = FitnessEvaluator()
        self.selection_operator = SelectionOperator()
        self.mutation_operator = MutationOperator()
        
        # 基因组模式库
        self.genome_patterns: Dict[str, GenomePattern] = {}
        
        # 进化统计
        self.evolution_stats: List[EvolutionStats] = []
        
        # 物理引擎
        self.physics_engine = PhysicsEngine(world_size)
        
        # 进化参数
        self.elite_ratio = 0.1  # 精英比例
        self.crossover_rate = 0.7
        self.adaptive_mutation = True
        
        # 初始化种群
        self._initialize_population()
    
    def _initialize_population(self):
        """初始化种群"""
        for i in range(self.population_size):
            # 随机位置
            position = np.array([
                random.uniform(0, self.world_size[0]),
                random.uniform(0, self.world_size[1]),
                random.uniform(0, self.world_size[2])
            ])
            
            # 创建细胞
            cell = create_digital_cell(position)
            self.population.append(cell)
            
            # 记录基因组模式
            self._record_genome_pattern(cell.nucleus.genome_template)
    
    def _record_genome_pattern(self, genome: Dict[str, Any]):
        """记录基因组模式
        
        Args:
            genome: 基因组
        """
        # 创建基因组的哈希标识
        genome_str = json.dumps(genome, sort_keys=True)
        pattern_id = str(hash(genome_str))
        
        if pattern_id in self.genome_patterns:
            pattern = self.genome_patterns[pattern_id]
            pattern.usage_count += 1
            pattern.last_used = time.time()
        else:
            self.genome_patterns[pattern_id] = GenomePattern(
                pattern_id=pattern_id,
                genes=copy.deepcopy(genome),
                fitness_history=[],
                usage_count=1,
                success_rate=0.0,
                last_used=time.time()
            )
    
    def evolve_generation(self) -> EvolutionStats:
        """进化一代
        
        Returns:
            EvolutionStats: 本代进化统计信息
        """
        # 更新所有细胞
        self._update_population()
        
        # 评估适应度
        fitness_scores = self._evaluate_population()
        
        # 移除死亡细胞
        self._remove_dead_cells()
        
        # 处理细胞分裂
        self._handle_cell_division()
        
        # 选择和繁殖
        if len(self.population) < self.population_size:
            self._reproduce_population(fitness_scores)
        
        # 种群大小控制
        self._control_population_size()
        
        # 更新进化参数
        self._update_evolution_parameters(fitness_scores)
        
        # 统计信息
        stats = self._calculate_evolution_stats(fitness_scores)
        self.evolution_stats.append(stats)
        
        self.generation += 1
        return stats
    
    def _update_population(self):
        """更新种群中的所有细胞"""
        dt = 1.0  # 时间步长
        
        # 获取所有分子
        all_molecules = []
        for cell in self.population:
            all_molecules.extend(cell.cytoplasm.molecules)
        
        # 物理引擎更新
        self.physics_engine.update(all_molecules, dt)
        
        # 更新每个细胞
        for cell in self.population:
            # 获取附近的外部分子
            nearby_molecules = self._get_nearby_molecules(cell, all_molecules)
            cell.update(dt, nearby_molecules)
    
    def _get_nearby_molecules(self, cell: DigitalCell, all_molecules: List) -> List:
        """获取细胞附近的分子
        
        Args:
            cell: 细胞
            all_molecules: 所有分子列表
            
        Returns:
            List: 附近的分子
        """
        nearby = []
        search_radius = cell.radius + 5.0
        
        for molecule in all_molecules:
            # 排除细胞自己的分子
            if molecule in cell.cytoplasm.molecules:
                continue
            
            distance = np.linalg.norm(molecule.position - cell.position)
            if distance <= search_radius:
                nearby.append(molecule)
        
        return nearby
    
    def _evaluate_population(self) -> List[float]:
        """评估种群适应度
        
        Returns:
            List[float]: 适应度分数列表
        """
        fitness_scores = []
        
        for cell in self.population:
            fitness = self.fitness_evaluator.evaluate_cell(cell)
            fitness_scores.append(fitness)
            
            # 更新基因组模式的适应度
            genome_str = json.dumps(cell.nucleus.genome_template, sort_keys=True)
            pattern_id = str(hash(genome_str))
            
            if pattern_id in self.genome_patterns:
                pattern = self.genome_patterns[pattern_id]
                pattern.fitness_history.append(fitness)
                
                # 计算成功率
                if len(pattern.fitness_history) > 0:
                    pattern.success_rate = np.mean(pattern.fitness_history)
        
        return fitness_scores
    
    def _remove_dead_cells(self):
        """移除死亡的细胞"""
        self.population = [cell for cell in self.population if not cell.is_dead()]
    
    def _handle_cell_division(self):
        """处理细胞分裂"""
        new_cells = []
        
        for cell in self.population:
            if cell.can_divide():
                child_cell = cell.divide()
                if child_cell:
                    new_cells.append(child_cell)
                    # 记录新的基因组模式
                    self._record_genome_pattern(child_cell.nucleus.genome_template)
        
        self.population.extend(new_cells)
    
    def _reproduce_population(self, fitness_scores: List[float]):
        """繁殖种群
        
        Args:
            fitness_scores: 适应度分数
        """
        target_size = self.population_size
        current_size = len(self.population)
        
        if current_size >= target_size:
            return
        
        needed = target_size - current_size
        
        # 选择精英
        elite_count = max(1, int(current_size * self.elite_ratio))
        elite_indices = sorted(range(len(fitness_scores)), 
                             key=lambda i: fitness_scores[i], 
                             reverse=True)[:elite_count]
        
        # 选择父代
        parent_count = min(needed * 2, current_size)
        parents = self.selection_operator.select_parents(
            self.population, fitness_scores, parent_count
        )
        
        # 生成后代
        offspring = []
        for i in range(needed):
            if len(parents) >= 2:
                parent1 = random.choice(parents)
                parent2 = random.choice(parents)
                child = self._crossover(parent1, parent2)
            else:
                # 如果父代不足，复制现有个体
                parent = random.choice(self.population)
                child = self._clone_cell(parent)
            
            offspring.append(child)
        
        self.population.extend(offspring)
    
    def _crossover(self, parent1: DigitalCell, parent2: DigitalCell) -> DigitalCell:
        """交叉操作
        
        Args:
            parent1: 父代1
            parent2: 父代2
            
        Returns:
            DigitalCell: 子代细胞
        """
        # 基因组交叉
        child_genome = self._crossover_genomes(
            parent1.nucleus.genome_template,
            parent2.nucleus.genome_template
        )
        
        # 突变
        if random.random() < self.mutation_operator.mutation_rate:
            child_genome = self.mutation_operator.mutate_genome(child_genome)
        
        # 创建子代细胞
        position = (parent1.position + parent2.position) / 2
        position += np.random.randn(3) * 2.0  # 添加一些随机偏移
        
        child = create_digital_cell(position, child_genome)
        
        # 继承一些特性
        child.memory.generation_count = max(
            parent1.memory.generation_count,
            parent2.memory.generation_count
        ) + 1
        
        return child
    
    def _crossover_genomes(self, genome1: Dict[str, Any], genome2: Dict[str, Any]) -> Dict[str, Any]:
        """基因组交叉
        
        Args:
            genome1: 基因组1
            genome2: 基因组2
            
        Returns:
            Dict[str, Any]: 交叉后的基因组
        """
        child_genome = {}
        
        all_genes = set(genome1.keys()) | set(genome2.keys())
        
        for gene_name in all_genes:
            if random.random() < self.crossover_rate:
                # 交叉
                if gene_name in genome1 and gene_name in genome2:
                    # 两个父代都有这个基因，随机选择一个
                    child_genome[gene_name] = copy.deepcopy(
                        random.choice([genome1[gene_name], genome2[gene_name]])
                    )
                elif gene_name in genome1:
                    child_genome[gene_name] = copy.deepcopy(genome1[gene_name])
                else:
                    child_genome[gene_name] = copy.deepcopy(genome2[gene_name])
            else:
                # 不交叉，随机选择父代
                source_genome = random.choice([genome1, genome2])
                if gene_name in source_genome:
                    child_genome[gene_name] = copy.deepcopy(source_genome[gene_name])
        
        return child_genome
    
    def _clone_cell(self, parent: DigitalCell) -> DigitalCell:
        """克隆细胞
        
        Args:
            parent: 父代细胞
            
        Returns:
            DigitalCell: 克隆的细胞
        """
        genome = copy.deepcopy(parent.nucleus.genome_template)
        
        # 轻微突变
        if random.random() < 0.1:
            genome = self.mutation_operator.mutate_genome(genome)
        
        position = parent.position + np.random.randn(3) * 3.0
        child = create_digital_cell(position, genome)
        child.memory.generation_count = parent.memory.generation_count + 1
        
        return child
    
    def _control_population_size(self):
        """控制种群大小"""
        if len(self.population) > self.population_size * 1.2:
            # 如果种群过大，移除适应度最低的个体
            fitness_scores = [self.fitness_evaluator.evaluate_cell(cell) 
                            for cell in self.population]
            
            # 按适应度排序
            sorted_indices = sorted(range(len(self.population)), 
                                  key=lambda i: fitness_scores[i], 
                                  reverse=True)
            
            # 保留前population_size个个体
            self.population = [self.population[i] for i in sorted_indices[:self.population_size]]
    
    def _update_evolution_parameters(self, fitness_scores: List[float]):
        """更新进化参数
        
        Args:
            fitness_scores: 适应度分数
        """
        if not self.adaptive_mutation:
            return
        
        # 基于种群多样性调整突变率
        diversity = self._calculate_diversity()
        
        if diversity < 0.3:  # 多样性过低
            self.mutation_operator.mutation_rate = min(0.3, self.mutation_operator.mutation_rate * 1.1)
        elif diversity > 0.8:  # 多样性过高
            self.mutation_operator.mutation_rate = max(0.01, self.mutation_operator.mutation_rate * 0.9)
        
        # 基于适应度进展调整选择压力
        if len(self.evolution_stats) > 5:
            recent_best = [stats.best_fitness for stats in self.evolution_stats[-5:]]
            if max(recent_best) - min(recent_best) < 0.01:  # 适应度停滞
                self.selection_operator.selection_pressure *= 0.95
            else:
                self.selection_operator.selection_pressure = min(3.0, 
                    self.selection_operator.selection_pressure * 1.02)
    
    def _calculate_diversity(self) -> float:
        """计算种群多样性
        
        Returns:
            float: 多样性分数 (0-1)
        """
        if len(self.population) < 2:
            return 0.0
        
        # 基于基因组模式的多样性
        unique_patterns = len(self.genome_patterns)
        max_possible_patterns = len(self.population)
        
        pattern_diversity = unique_patterns / max_possible_patterns
        
        # 基于适应度分布的多样性
        fitness_scores = [self.fitness_evaluator.evaluate_cell(cell) 
                         for cell in self.population]
        
        if len(set(fitness_scores)) == 1:
            fitness_diversity = 0.0
        else:
            fitness_std = np.std(fitness_scores)
            fitness_diversity = min(1.0, fitness_std * 2)
        
        return (pattern_diversity + fitness_diversity) / 2
    
    def _calculate_evolution_stats(self, fitness_scores: List[float]) -> EvolutionStats:
        """计算进化统计信息
        
        Args:
            fitness_scores: 适应度分数
            
        Returns:
            EvolutionStats: 统计信息
        """
        if not fitness_scores:
            fitness_scores = [0.0]
        
        # 编译成功率统计
        compilation_successes = 0
        total_compilations = 0
        total_energy = 0
        
        for cell in self.population:
            mitochondria = cell.cytoplasm.organelles.get('mitochondria')
            if mitochondria:
                from .organelles import CompilerRunner
                if isinstance(mitochondria, CompilerRunner):
                    stats = mitochondria.get_compilation_stats()
                    compilation_successes += stats.get('success_count', 0)
                    total_compilations += stats.get('compilation_count', 0)
            
            total_energy += cell.energy
        
        compilation_success_rate = (compilation_successes / max(1, total_compilations))
        energy_efficiency = total_energy / (len(self.population) * 200.0)  # 假设最大能量为200
        
        return EvolutionStats(
            generation=self.generation,
            population_size=len(self.population),
            average_fitness=np.mean(fitness_scores),
            best_fitness=max(fitness_scores),
            worst_fitness=min(fitness_scores),
            diversity_score=self._calculate_diversity(),
            mutation_rate=self.mutation_operator.mutation_rate,
            selection_pressure=self.selection_operator.selection_pressure,
            compilation_success_rate=compilation_success_rate,
            energy_efficiency=energy_efficiency
        )
    
    def get_population_status(self) -> Dict[str, Any]:
        """获取种群状态
        
        Returns:
            Dict[str, Any]: 种群状态信息
        """
        cell_statuses = [cell.get_status() for cell in self.population]
        
        return {
            'generation': self.generation,
            'population_size': len(self.population),
            'cells': cell_statuses,
            'genome_patterns': len(self.genome_patterns),
            'world_size': self.world_size,
            'evolution_stats': [asdict(stats) for stats in self.evolution_stats[-10:]]  # 最近10代
        }
    
    def get_best_cells(self, count: int = 5) -> List[DigitalCell]:
        """获取最佳细胞
        
        Args:
            count: 返回的细胞数量
            
        Returns:
            List[DigitalCell]: 最佳细胞列表
        """
        fitness_scores = [self.fitness_evaluator.evaluate_cell(cell) 
                         for cell in self.population]
        
        sorted_indices = sorted(range(len(self.population)), 
                              key=lambda i: fitness_scores[i], 
                              reverse=True)
        
        return [self.population[i] for i in sorted_indices[:count]]
    
    def save_genome_library(self, filepath: str):
        """保存基因组库
        
        Args:
            filepath: 文件路径
        """
        library_data = {
            'patterns': {pid: asdict(pattern) for pid, pattern in self.genome_patterns.items()},
            'generation': self.generation,
            'evolution_stats': [asdict(stats) for stats in self.evolution_stats]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(library_data, f, indent=2, ensure_ascii=False)
    
    def load_genome_library(self, filepath: str):
        """加载基因组库
        
        Args:
            filepath: 文件路径
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            library_data = json.load(f)
        
        # 重建基因组模式
        self.genome_patterns = {}
        for pid, pattern_data in library_data.get('patterns', {}).items():
            self.genome_patterns[pid] = GenomePattern(**pattern_data)
        
        self.generation = library_data.get('generation', 0)
        
        # 重建进化统计
        self.evolution_stats = []
        for stats_data in library_data.get('evolution_stats', []):
            self.evolution_stats.append(EvolutionStats(**stats_data))