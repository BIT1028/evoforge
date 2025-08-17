#!/usr/bin/env python3
"""
进化算法核心引擎
"""
import asyncio
import random
import json
from typing import List, Tuple, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
import structlog

from app.core.database import SessionLocal
from app.core.config import settings
from app.models.generation import Generation
from app.models.digital_cell import DigitalCell
from app.models.task import Task
from app.schemas.evolution import EvolutionConfig
from app.services.oracle.manager import oracle_manager
from app.services.execution.sandbox import SandboxExecutor
from app.core.websocket import websocket_manager
from .evolution_strategies import (
    EvolutionStrategy, StrategyConfig, EvolutionStrategyFactory,
    AdaptiveEvolutionManager, Individual
)
from app.services.analysis.shap_analyzer import shap_analyzer, ShapExplanation

logger = structlog.get_logger()

class EvolutionEngine:
    """进化算法核心引擎
    
    增强的进化引擎，支持多种选择策略、智能交叉变异和自适应参数调整。
    采用生物学启发的算法设计，提供更真实的进化模拟。
    """
    
    def __init__(self):
        self.is_running = False
        self.is_paused = False
        self.current_generation = 0
        self.population: List[DigitalCell] = []
        self.config = EvolutionConfig()
        self.oracle_service = oracle_manager
        self.sandbox_executor = SandboxExecutor()
        self.start_time: Optional[datetime] = None
        
        # 进化策略参数
        self.selection_strategy = "tournament"  # tournament, roulette, rank, elitist
        self.crossover_strategy = "uniform"     # single_point, two_point, uniform, semantic
        self.mutation_strategy = "adaptive"     # random, adaptive, guided, semantic
        
        # 自适应参数
        self.adaptive_mutation_rate = 0.1
        self.adaptive_crossover_rate = 0.8
        self.diversity_threshold = 0.3
        self.stagnation_counter = 0
        self.best_fitness_history = []
        
        # 多目标优化支持
        self.objectives = ["fitness", "complexity", "diversity"]
        self.pareto_front = []
        
        # 种群统计
        self.population_stats = {
            "avg_fitness": 0.0,
            "max_fitness": 0.0,
            "min_fitness": 0.0,
            "diversity_index": 0.0,
            "convergence_rate": 0.0
        }
        
        # 进化策略模式支持
        self.strategy_config = StrategyConfig(
            strategy_type=EvolutionStrategy.GENETIC_ALGORITHM,
            population_size=50,
            max_generations=100,
            adaptive_parameters=True
        )
        self.adaptive_manager: Optional[AdaptiveEvolutionManager] = None
        self.use_strategy_pattern = False  # 是否使用新的策略模式
        
        # SHAP分析支持
        self.enable_shap_analysis = True  # 是否启用SHAP分析
        self.shap_analysis_interval = 1   # SHAP分析间隔（每N代分析一次）
        self.latest_shap_results: List[ShapExplanation] = []  # 最新的SHAP分析结果
        
        logger.info("进化引擎初始化完成，支持多种进化策略和SHAP可解释性分析")
        
    async def start_evolution(self, config: Optional[EvolutionConfig] = None, 
                              use_strategy_pattern: bool = False,
                              strategy_type: Optional[EvolutionStrategy] = None) -> bool:
        """开始进化过程
        
        Args:
            config: 进化配置
            use_strategy_pattern: 是否使用新的策略模式
            strategy_type: 指定的进化策略类型
        """
        if self.is_running:
            logger.warning("进化已在运行中")
            return False
            
        if config:
            self.config = config
            
        # 设置策略模式
        self.use_strategy_pattern = use_strategy_pattern
        if use_strategy_pattern:
            if strategy_type:
                self.strategy_config.strategy_type = strategy_type
            
            # 初始化自适应管理器
            self.adaptive_manager = AdaptiveEvolutionManager(self.strategy_config)
            logger.info("启用进化策略模式", strategy=self.strategy_config.strategy_type.value)
            
        self.is_running = True
        self.is_paused = False
        self.start_time = datetime.now()
        
        # 初始化Oracle管理器
        await self.oracle_service.initialize()
        
        logger.info("开始进化过程", config=self.config.dict(), 
                   strategy_pattern=self.use_strategy_pattern)
        
        # 广播进化开始事件
        await websocket_manager.broadcast_to_room("evolution", {
            "event": "evolution_started",
            "data": {
                "config": self.config.dict(),
                "start_time": self.start_time.isoformat(),
                "strategy_pattern": self.use_strategy_pattern,
                "strategy_type": self.strategy_config.strategy_type.value if self.use_strategy_pattern else None
            }
        })
        
        # 启动进化循环
        if self.use_strategy_pattern:
            asyncio.create_task(self._strategy_evolution_loop())
        else:
            asyncio.create_task(self._evolution_loop())
        return True
    
    async def pause_evolution(self) -> bool:
        """暂停进化"""
        if not self.is_running or self.is_paused:
            return False
            
        self.is_paused = True
        logger.info("进化已暂停")
        
        await websocket_manager.broadcast_to_room("evolution", {
            "event": "evolution_paused",
            "data": {"generation": self.current_generation}
        })
        return True
    
    async def resume_evolution(self) -> bool:
        """恢复进化"""
        if not self.is_running or not self.is_paused:
            return False
            
        self.is_paused = False
        logger.info("进化已恢复")
        
        await websocket_manager.broadcast_to_room("evolution", {
            "event": "evolution_resumed",
            "data": {"generation": self.current_generation}
        })
        return True
    
    async def stop_evolution(self) -> bool:
        """停止进化"""
        if not self.is_running:
            return False
            
        self.is_running = False
        self.is_paused = False
        logger.info("进化已停止")
        
        await websocket_manager.broadcast_to_room("evolution", {
            "event": "evolution_stopped",
            "data": {"generation": self.current_generation}
        })
        return True
    
    async def reset_evolution(self) -> bool:
        """重置进化"""
        await self.stop_evolution()
        
        self.current_generation = 0
        self.population = []
        self.start_time = None
        
        logger.info("进化已重置")
        
        await websocket_manager.broadcast_to_room("evolution", {
            "event": "evolution_reset",
            "data": {}
        })
        return True
    
    async def _evolution_loop(self):
        """进化主循环"""
        try:
            # 初始化种群
            await self._initialize_population()
            
            while self.is_running:
                if self.is_paused:
                    await asyncio.sleep(1)
                    continue
                    
                # 检查是否达到最大代数
                if (self.config.max_generations and 
                    self.current_generation >= self.config.max_generations):
                    logger.info("达到最大代数，停止进化")
                    break
                
                # 运行一代进化
                await self._run_generation()
                
                # 短暂休息，避免过度占用资源
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error("进化循环出错", error=str(e))
            await websocket_manager.broadcast_to_room("evolution", {
                "event": "evolution_error",
                "data": {"error": str(e)}
            })
        finally:
            self.is_running = False
            self.is_paused = False
    
    async def _initialize_population(self):
        """初始化种群"""
        logger.info("初始化种群", size=self.config.population_size)
        
        db = SessionLocal()
        try:
            # 创建第0代
            generation = Generation(
                generation_number=0,
                population_size=self.config.population_size
            )
            db.add(generation)
            db.commit()
            db.refresh(generation)
            
            # 生成初始个体
            self.population = []
            for i in range(self.config.population_size):
                genome = self._generate_random_genome()
                cell = DigitalCell(
                    generation_id=generation.id,
                    genome=genome,
                    mutation_rate=self.config.mutation_rate
                )
                db.add(cell)
                self.population.append(cell)
            
            db.commit()
            
            # 评估初始种群
            await self._evaluate_population(db, generation)
            
            logger.info("种群初始化完成")
            
        finally:
            db.close()
    
    async def _run_generation(self):
        """运行一代进化"""
        self.current_generation += 1
        logger.info("开始第{}代进化".format(self.current_generation))
        
        db = SessionLocal()
        try:
            # 创建新代数记录
            generation = Generation(
                generation_number=self.current_generation,
                population_size=self.config.population_size
            )
            db.add(generation)
            db.commit()
            db.refresh(generation)
            
            # 选择、交叉、变异
            new_population = await self._evolve_population(db, generation)
            
            # 评估新种群
            await self._evaluate_population(db, generation)
            
            # 更新种群
            self.population = new_population
            
            # 计算统计信息
            await self._update_generation_stats(db, generation)
            
            # 广播代数完成事件
            await self._broadcast_generation_update(generation)
            
            logger.info("第{}代进化完成".format(self.current_generation))
            
        finally:
            db.close()
    
    async def _evolve_population(self, db: Session, generation: Generation) -> List[DigitalCell]:
        """进化种群"""
        new_population = []
        
        # 精英保留
        elite_count = min(self.config.elite_size, len(self.population))
        sorted_population = sorted(self.population, 
                                 key=lambda x: x.fitness_score or 0, 
                                 reverse=True)
        
        for i in range(elite_count):
            elite = sorted_population[i]
            new_cell = DigitalCell(
                generation_id=generation.id,
                genome=elite.genome,
                parent1_id=elite.id,
                mutation_rate=elite.mutation_rate
            )
            db.add(new_cell)
            new_population.append(new_cell)
        
        # 生成剩余个体
        while len(new_population) < self.config.population_size:
            if random.random() < self.config.crossover_rate:
                # 交叉
                parent1, parent2 = self._selection(2)
                child1, child2 = await self._crossover(parent1, parent2)
                
                for child in [child1, child2]:
                    if len(new_population) < self.config.population_size:
                        child.generation_id = generation.id
                        if random.random() < self.config.mutation_rate:
                            child = await self._mutation(child)
                        db.add(child)
                        new_population.append(child)
            else:
                # 直接选择并变异
                parent = self._selection(1)[0]
                child = DigitalCell(
                    generation_id=generation.id,
                    genome=parent.genome,
                    parent1_id=parent.id,
                    mutation_rate=parent.mutation_rate
                )
                if random.random() < self.config.mutation_rate:
                    child = await self._mutation(child)
                db.add(child)
                new_population.append(child)
        
        db.commit()
        return new_population
    
    def _selection(self, count: int) -> List[DigitalCell]:
        """智能选择操作
        
        根据当前选择策略执行不同的选择算法，支持多种生物学启发的选择机制。
        
        Args:
            count: 需要选择的个体数量
            
        Returns:
            List[DigitalCell]: 选中的个体列表
        """
        if self.selection_strategy == "tournament":
            return self._tournament_selection(count)
        elif self.selection_strategy == "roulette":
            return self._roulette_selection(count)
        elif self.selection_strategy == "rank":
            return self._rank_selection(count)
        elif self.selection_strategy == "elitist":
            return self._elitist_selection(count)
        else:
            return self._tournament_selection(count)  # 默认策略
    
    def _tournament_selection(self, count: int) -> List[DigitalCell]:
        """锦标赛选择
        
        模拟自然界中个体间的竞争，适应度高的个体更容易获胜。
        """
        selected = []
        tournament_size = max(2, min(5, len(self.population) // 10))
        
        for _ in range(count):
            tournament = random.sample(self.population, 
                                     min(tournament_size, len(self.population)))
            # 考虑适应度和多样性的综合评分
            winner = max(tournament, key=lambda x: self._calculate_selection_score(x))
            selected.append(winner)
        
        return selected
    
    def _roulette_selection(self, count: int) -> List[DigitalCell]:
        """轮盘赌选择
        
        基于适应度比例的概率选择，适应度越高被选中概率越大。
        """
        selected = []
        fitness_scores = [max(0.1, cell.fitness_score or 0) for cell in self.population]
        total_fitness = sum(fitness_scores)
        
        if total_fitness == 0:
            return random.sample(self.population, min(count, len(self.population)))
        
        probabilities = [f / total_fitness for f in fitness_scores]
        
        for _ in range(count):
            r = random.random()
            cumulative_prob = 0
            for i, prob in enumerate(probabilities):
                cumulative_prob += prob
                if r <= cumulative_prob:
                    selected.append(self.population[i])
                    break
        
        return selected
    
    def _rank_selection(self, count: int) -> List[DigitalCell]:
        """排名选择
        
        基于个体在种群中的排名进行选择，减少适应度差异过大的影响。
        """
        sorted_population = sorted(self.population, 
                                 key=lambda x: x.fitness_score or 0, 
                                 reverse=True)
        
        # 线性排名概率分配
        n = len(sorted_population)
        rank_probs = [(2 * (n - i)) / (n * (n + 1)) for i in range(n)]
        
        selected = []
        for _ in range(count):
            r = random.random()
            cumulative_prob = 0
            for i, prob in enumerate(rank_probs):
                cumulative_prob += prob
                if r <= cumulative_prob:
                    selected.append(sorted_population[i])
                    break
        
        return selected
    
    def _elitist_selection(self, count: int) -> List[DigitalCell]:
        """精英选择
        
        直接选择适应度最高的个体，保证优秀基因的传承。
        """
        sorted_population = sorted(self.population, 
                                 key=lambda x: x.fitness_score or 0, 
                                 reverse=True)
        return sorted_population[:count]
    
    def _calculate_selection_score(self, cell: DigitalCell) -> float:
        """计算选择评分
        
        综合考虑适应度、多样性和年龄等因素的选择评分。
        
        Args:
            cell: 细胞个体
            
        Returns:
            float: 选择评分
        """
        fitness_score = cell.fitness_score or 0
        
        # 多样性奖励：基因组独特性
        diversity_bonus = self._calculate_diversity_bonus(cell)
        
        # 年龄惩罚：避免过度老化
        age_penalty = max(0, (cell.age or 0) - 10) * 0.01
        
        # 综合评分
        total_score = fitness_score + diversity_bonus - age_penalty
        
        return max(0.01, total_score)
    
    async def _crossover(self, parent1: DigitalCell, parent2: DigitalCell) -> Tuple[DigitalCell, DigitalCell]:
        """智能交叉操作
        
        根据当前交叉策略执行不同的交叉算法，支持多种生物学启发的交叉机制。
        
        Args:
            parent1: 父代个体1
            parent2: 父代个体2
            
        Returns:
            Tuple[DigitalCell, DigitalCell]: 子代个体对
        """
        try:
            from .genome import Genome, create_random_genome
            import json
            
            # 解析父代基因组
            parent1_data = json.loads(parent1.genome)
            parent2_data = json.loads(parent2.genome)
            
            if isinstance(parent1_data, dict) and 'root' in parent1_data:
                # 新格式：使用基因组对象进行智能交叉
                parent1_genome = Genome.from_dict(parent1_data)
                parent2_genome = Genome.from_dict(parent2_data)
                
                # 根据交叉策略选择交叉方法
                if self.crossover_strategy == "uniform":
                    child1_genome, child2_genome = self._uniform_crossover(parent1_genome, parent2_genome)
                elif self.crossover_strategy == "single_point":
                    child1_genome, child2_genome = self._single_point_crossover(parent1_genome, parent2_genome)
                elif self.crossover_strategy == "two_point":
                    child1_genome, child2_genome = self._two_point_crossover(parent1_genome, parent2_genome)
                elif self.crossover_strategy == "semantic":
                    child1_genome, child2_genome = self._semantic_crossover(parent1_genome, parent2_genome)
                else:
                    child1_genome, child2_genome = self._uniform_crossover(parent1_genome, parent2_genome)
                
                new_genome1 = json.dumps(child1_genome.to_dict())
                new_genome2 = json.dumps(child2_genome.to_dict())
            else:
                # 旧格式：使用原有的交叉逻辑
                new_genome1, new_genome2 = self._legacy_crossover(parent1_data, parent2_data)
                
        except Exception as e:
            logger.warning(f"交叉操作失败，使用随机基因组: {e}")
            # 如果解析失败，生成新的随机基因组
            genome1_obj = create_random_genome()
            genome2_obj = create_random_genome()
            new_genome1 = json.dumps(genome1_obj.to_dict())
            new_genome2 = json.dumps(genome2_obj.to_dict())
        
        # 创建子代个体
        child1 = DigitalCell(
            genome=new_genome1,
            parent1_id=parent1.id,
            parent2_id=parent2.id,
            mutation_rate=self._calculate_adaptive_mutation_rate(parent1, parent2)
        )
        
        child2 = DigitalCell(
            genome=new_genome2,
            parent1_id=parent1.id,
            parent2_id=parent2.id,
            mutation_rate=self._calculate_adaptive_mutation_rate(parent1, parent2)
        )
        
        return child1, child2
    
    def _uniform_crossover(self, parent1_genome: 'Genome', parent2_genome: 'Genome') -> Tuple['Genome', 'Genome']:
        """均匀交叉 - 在每个基因位点随机选择来自哪个父代"""
        child1_genome = parent1_genome.copy()
        child2_genome = parent2_genome.copy()
        
        # 递归交叉AST节点
        self._crossover_nodes(child1_genome.root, child2_genome.root, parent1_genome.root, parent2_genome.root)
        return child1_genome, child2_genome
    
    def _single_point_crossover(self, parent1_genome: 'Genome', parent2_genome: 'Genome') -> Tuple['Genome', 'Genome']:
        """单点交叉 - 在AST的某个节点处进行交叉"""
        child1_genome = parent1_genome.copy()
        child2_genome = parent2_genome.copy()
        
        nodes1 = self._get_all_nodes(child1_genome.root)
        nodes2 = self._get_all_nodes(child2_genome.root)
        
        if len(nodes1) > 1 and len(nodes2) > 1:
            crossover_idx = random.randint(1, min(len(nodes1), len(nodes2)) - 1)
            if crossover_idx < len(nodes1) and crossover_idx < len(nodes2):
                nodes1[crossover_idx], nodes2[crossover_idx] = nodes2[crossover_idx], nodes1[crossover_idx]
        
        return child1_genome, child2_genome
    
    def _two_point_crossover(self, parent1_genome: 'Genome', parent2_genome: 'Genome') -> Tuple['Genome', 'Genome']:
        """两点交叉 - 在两个交叉点之间交换基因片段"""
        child1_genome = parent1_genome.copy()
        child2_genome = parent2_genome.copy()
        
        nodes1 = self._get_all_nodes(child1_genome.root)
        nodes2 = self._get_all_nodes(child2_genome.root)
        
        if len(nodes1) > 2 and len(nodes2) > 2:
            point1 = random.randint(1, min(len(nodes1), len(nodes2)) // 2)
            point2 = random.randint(point1 + 1, min(len(nodes1), len(nodes2)) - 1)
            
            for i in range(point1, point2):
                if i < len(nodes1) and i < len(nodes2):
                    nodes1[i], nodes2[i] = nodes2[i], nodes1[i]
        
        return child1_genome, child2_genome
    
    def _semantic_crossover(self, parent1_genome: 'Genome', parent2_genome: 'Genome') -> Tuple['Genome', 'Genome']:
        """语义交叉 - 基于代码语义进行交叉"""
        child1_genome = parent1_genome.copy()
        child2_genome = parent2_genome.copy()
        
        similar_pairs = self._find_semantic_similar_nodes(parent1_genome.root, parent2_genome.root)
        
        for node1, node2 in similar_pairs:
            if random.random() < 0.3:
                if hasattr(node1, 'value') and hasattr(node2, 'value'):
                    node1.value, node2.value = node2.value, node1.value
        
        return child1_genome, child2_genome
    
    def _crossover_nodes(self, child1_node, child2_node, parent1_node, parent2_node, crossover_prob: float = 0.5):
        """递归交叉AST节点"""
        if random.random() < crossover_prob:
            if hasattr(child1_node, 'value') and hasattr(child2_node, 'value'):
                child1_node.value, child2_node.value = parent2_node.value, parent1_node.value
        
        min_children = min(len(child1_node.children), len(child2_node.children))
        for i in range(min_children):
            self._crossover_nodes(
                child1_node.children[i], child2_node.children[i],
                parent1_node.children[i], parent2_node.children[i],
                crossover_prob
            )
    
    def _get_all_nodes(self, root_node) -> list:
        """获取AST中的所有节点"""
        nodes = [root_node]
        for child in root_node.children:
            nodes.extend(self._get_all_nodes(child))
        return nodes
    
    def _find_semantic_similar_nodes(self, root1, root2) -> list:
        """查找语义相似的节点对"""
        similar_pairs = []
        
        def compare_nodes(node1, node2):
            if (hasattr(node1, 'node_type') and hasattr(node2, 'node_type') and
                node1.node_type == node2.node_type):
                similar_pairs.append((node1, node2))
            
            min_children = min(len(node1.children), len(node2.children))
            for i in range(min_children):
                compare_nodes(node1.children[i], node2.children[i])
        
        compare_nodes(root1, root2)
        return similar_pairs
    
    def _calculate_adaptive_mutation_rate(self, parent1: DigitalCell, parent2: DigitalCell) -> float:
        """计算自适应变异率"""
        base_rate = self.adaptive_mutation_rate
        
        avg_fitness = (parent1.fitness_score or 0 + parent2.fitness_score or 0) / 2
        population_avg = self.population_stats["avg_fitness"]
        
        if population_avg > 0:
            fitness_factor = max(0.5, min(2.0, population_avg / max(0.01, avg_fitness)))
        else:
            fitness_factor = 1.0
        
        diversity_factor = max(0.5, min(2.0, 1.0 / max(0.1, self.population_stats["diversity_index"])))
        stagnation_factor = 1.0 + (self.stagnation_counter * 0.1)
        
        adaptive_rate = base_rate * fitness_factor * diversity_factor * stagnation_factor
        return min(0.5, max(0.01, adaptive_rate))
    
    def _legacy_crossover(self, genome1, genome2):
        """旧格式的交叉操作"""
        # 确保基因长度一致
        min_len = min(len(genome1), len(genome2))
        if min_len > 1:
            crossover_point = random.randint(1, min_len - 1)
            
            new_genome1 = genome1[:crossover_point] + genome2[crossover_point:]
            new_genome2 = genome2[:crossover_point] + genome1[crossover_point:]
        else:
            new_genome1, new_genome2 = genome1, genome2
        
        return json.dumps(new_genome1), json.dumps(new_genome2)
    
    async def _mutation(self, cell: DigitalCell) -> DigitalCell:
        """智能变异操作
        
        根据当前变异策略执行不同的变异算法，支持自适应和引导式变异。
        
        Args:
            cell: 要变异的细胞个体
            
        Returns:
            DigitalCell: 变异后的细胞个体
        """
        try:
            from .genome import Genome, create_random_genome
            import json
            
            genome_data = json.loads(cell.genome)
            
            if isinstance(genome_data, dict) and 'root' in genome_data:
                # 新格式：使用基因组对象进行智能变异
                genome_obj = Genome.from_dict(genome_data)
                
                # 根据变异策略选择变异方法
                if self.mutation_strategy == "adaptive":
                    self._adaptive_mutation(genome_obj, cell.mutation_rate)
                elif self.mutation_strategy == "guided":
                    self._guided_mutation(genome_obj, cell.mutation_rate)
                elif self.mutation_strategy == "semantic":
                    self._semantic_mutation(genome_obj, cell.mutation_rate)
                else:
                    self._random_mutation(genome_obj, cell.mutation_rate)
                
                cell.genome = json.dumps(genome_obj.to_dict())
            else:
                # 旧格式：使用原有的变异逻辑
                cell.genome = self._legacy_mutation(genome_data)
                
        except Exception as e:
            logger.warning(f"变异操作失败，使用随机基因组: {e}")
            # 如果解析失败，生成新的随机基因组
            genome_obj = create_random_genome()
            cell.genome = json.dumps(genome_obj.to_dict())
        
        return cell
    
    def _adaptive_mutation(self, genome_obj, mutation_rate):
        """自适应变异：根据种群多样性和进化停滞情况调整变异强度"""
        # 计算当前种群多样性
        diversity = self._calculate_population_diversity()
        
        # 根据多样性调整变异率
        if diversity < self.diversity_threshold:
            # 多样性低，增加变异强度
            adjusted_rate = min(mutation_rate * 2.0, 0.5)
        else:
            # 多样性高，保持正常变异率
            adjusted_rate = mutation_rate
        
        # 执行变异
        self._mutate_genome_nodes(genome_obj.root, adjusted_rate)
    
    def _guided_mutation(self, genome_obj, mutation_rate):
        """引导式变异：基于历史最优解的结构特征进行变异"""
        if hasattr(self, 'best_genome_structure'):
            # 基于最优结构进行引导变异
            self._guided_mutate_nodes(genome_obj.root, mutation_rate, self.best_genome_structure)
        else:
            # 没有引导信息时使用随机变异
            self._mutate_genome_nodes(genome_obj.root, mutation_rate)
    
    def _semantic_mutation(self, genome_obj, mutation_rate):
        """语义变异：保持代码语义正确性的变异"""
        # 获取所有可变异的节点
        mutable_nodes = self._get_mutable_nodes(genome_obj.root)
        
        # 对每个节点进行语义感知的变异
        for node in mutable_nodes:
            if random.random() < mutation_rate:
                self._semantic_mutate_node(node)
    
    def _random_mutation(self, genome_obj, mutation_rate):
        """随机变异：传统的随机变异策略"""
        self._mutate_genome_nodes(genome_obj.root, mutation_rate)
    
    def _calculate_population_diversity(self):
        """计算种群多样性指数"""
        if len(self.population) < 2:
            return 1.0
        
        # 计算基因组之间的平均距离
        total_distance = 0
        comparisons = 0
        
        for i in range(len(self.population)):
            for j in range(i + 1, len(self.population)):
                distance = self._calculate_genome_distance(
                    self.population[i].genome, 
                    self.population[j].genome
                )
                total_distance += distance
                comparisons += 1
        
        return total_distance / comparisons if comparisons > 0 else 0.0
    
    def _calculate_genome_distance(self, genome1, genome2):
        """计算两个基因组之间的距离"""
        try:
            import json
            from .genome import Genome
            
            g1_data = json.loads(genome1)
            g2_data = json.loads(genome2)
            
            if isinstance(g1_data, dict) and isinstance(g2_data, dict):
                g1_obj = Genome.from_dict(g1_data)
                g2_obj = Genome.from_dict(g2_data)
                return self._ast_distance(g1_obj.root, g2_obj.root)
            else:
                # 旧格式比较
                return self._legacy_genome_distance(g1_data, g2_data)
        except Exception:
            return 1.0  # 默认距离
    
    def _ast_distance(self, node1, node2):
        """计算AST节点之间的距离"""
        if type(node1) != type(node2):
            return 1.0
        
        if hasattr(node1, 'children') and hasattr(node2, 'children'):
            if len(node1.children) != len(node2.children):
                return 0.8
            
            child_distances = []
            for c1, c2 in zip(node1.children, node2.children):
                child_distances.append(self._ast_distance(c1, c2))
            
            return sum(child_distances) / len(child_distances) if child_distances else 0.0
        
        return 0.0 if str(node1) == str(node2) else 0.5
    
    def _guided_mutate_nodes(self, node, mutation_rate, guide_structure):
        """基于引导结构的变异"""
        if random.random() < mutation_rate:
            # 根据引导结构选择变异方向
            if hasattr(guide_structure, 'preferred_patterns'):
                self._apply_guided_pattern(node, guide_structure.preferred_patterns)
            else:
                self._mutate_single_node(node)
        
        # 递归处理子节点
        if hasattr(node, 'children'):
            for child in node.children:
                self._guided_mutate_nodes(child, mutation_rate, guide_structure)
    
    def _get_mutable_nodes(self, node):
        """获取所有可变异的节点"""
        mutable_nodes = []
        
        # 检查当前节点是否可变异
        if self._is_mutable_node(node):
            mutable_nodes.append(node)
        
        # 递归收集子节点
        if hasattr(node, 'children'):
            for child in node.children:
                mutable_nodes.extend(self._get_mutable_nodes(child))
        
        return mutable_nodes
    
    def _is_mutable_node(self, node):
        """判断节点是否可以变异"""
        # 常量、变量名、操作符等可以变异
        mutable_types = ['ConstantNode', 'VariableNode', 'BinaryOpNode', 'CompareNode']
        return type(node).__name__ in mutable_types
    
    def _semantic_mutate_node(self, node):
        """对单个节点进行语义感知的变异"""
        node_type = type(node).__name__
        
        if node_type == 'ConstantNode':
            # 常量节点：在合理范围内变异
            if isinstance(node.value, int):
                node.value += random.randint(-5, 5)
            elif isinstance(node.value, float):
                node.value += random.uniform(-1.0, 1.0)
        
        elif node_type == 'BinaryOpNode':
            # 二元操作符：替换为语义相近的操作符
            similar_ops = {
                '+': ['-', '*'],
                '-': ['+', '/'],
                '*': ['+', '/'],
                '/': ['-', '*'],
                '==': ['!=', '<', '>'],
                '!=': ['==', '<=', '>='],
                '<': ['<=', '>', '!='],
                '>': ['>=', '<', '!=']
            }
            
            if hasattr(node, 'op') and node.op in similar_ops:
                node.op = random.choice(similar_ops[node.op])
    
    def _legacy_genome_distance(self, genome1, genome2):
        """计算旧格式基因组之间的距离"""
        if len(genome1) != len(genome2):
            return 1.0
        
        differences = sum(1 for g1, g2 in zip(genome1, genome2) if g1 != g2)
        return differences / len(genome1) if genome1 else 0.0
    
    def _mutate_genome_nodes(self, node, mutation_rate: float):
        """递归变异基因组节点"""
        if random.random() < mutation_rate:
            # 变异当前节点的值
            if hasattr(node, 'node_type') and hasattr(node.node_type, 'value'):
                if node.node_type.value == 'constant' and isinstance(node.value, (int, float)):
                    node.value = random.randint(1, 100)
                elif node.node_type.value == 'name' and isinstance(node.value, str):
                    variables = ['x', 'y', 'z', 'data', 'result', 'temp', 'numbers']
                    node.value = random.choice(variables)
        
        # 递归处理子节点
        if hasattr(node, 'children'):
            for child in node.children:
                self._mutate_genome_nodes(child, mutation_rate)
    
    def _legacy_mutation(self, genome):
        """旧格式的变异操作"""
        # 随机变异基因中的一个元素
        if genome:
            mutation_index = random.randint(0, len(genome) - 1)
            
            # 根据基因类型进行变异
            if isinstance(genome[mutation_index], str):
                # 字符串变异：随机替换字符
                chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"
                genome[mutation_index] = random.choice(chars)
            elif isinstance(genome[mutation_index], (int, float)):
                # 数值变异：添加随机噪声
                genome[mutation_index] += random.gauss(0, 0.1)
        
        return json.dumps(genome)
    
    def _generate_random_genome(self) -> str:
        """生成随机基因序列"""
        try:
            from .genome import create_random_genome
            import json
            
            # 使用新的基因组系统生成随机基因组
            genome_obj = create_random_genome()
            return json.dumps(genome_obj.to_dict())
            
        except ImportError:
            # 如果新的基因组系统不可用，使用旧的方法
            functions = ["print", "len", "sum", "max", "min", "sorted", "range"]
            variables = ["x", "y", "z", "data", "result", "temp"]
            operators = ["+", "-", "*", "/", "==", "!=", "<", ">"]
            
            genome = []
            genome_length = random.randint(5, 15)
            
            for _ in range(genome_length):
                gene_type = random.choice(["function", "variable", "operator", "value"])
                
                if gene_type == "function":
                    genome.append(random.choice(functions))
                elif gene_type == "variable":
                    genome.append(random.choice(variables))
                elif gene_type == "operator":
                    genome.append(random.choice(operators))
                else:  # value
                    genome.append(random.randint(1, 100))
            
            return json.dumps(genome)
    
    async def _evaluate_population(self, db: Session, generation: Generation):
        """智能适应度评估
        
        实现多目标优化和自适应评估策略，综合考虑代码质量、
        执行效率、创新性和生物学合理性等多个维度。
        
        Args:
            db: 数据库会话
            generation: 当前代数对象
        """
        logger.info("开始智能适应度评估", generation=generation.generation_number)
        
        # 获取活跃任务
        tasks = db.execute(
            select(Task).where(Task.is_active == True)
        ).scalars().all()
        
        if not tasks:
            logger.warning("没有活跃任务，跳过评估")
            return
        
        # 批量评估以提高效率
        evaluation_batch = []
        
        for cell in self.population:
            if cell.generation_id == generation.id:
                try:
                    # 从基因生成代码
                    code = await self._generate_code_from_genome(cell.genome)
                    cell.generated_code = code
                    
                    # 多任务评估
                    multi_objective_scores = await self._multi_objective_evaluation(
                        cell, code, tasks
                    )
                    
                    # 计算综合适应度
                    cell.fitness_score = self._calculate_composite_fitness(
                        multi_objective_scores
                    )
                    
                    # 更新帕累托前沿
                    self._update_pareto_front(cell, multi_objective_scores)
                    
                    evaluation_batch.append({
                        'cell_id': cell.id,
                        'fitness': cell.fitness_score,
                        'objectives': multi_objective_scores
                    })
                    
                except Exception as e:
                    logger.error("细胞评估失败", cell_id=cell.id, error=str(e))
                    cell.fitness_score = 0.0
        
        # 更新种群统计
        self._update_population_statistics(evaluation_batch)
        
        db.commit()
        logger.info("适应度评估完成", evaluated_cells=len(evaluation_batch))
    
    async def _multi_objective_evaluation(self, cell, code: str, tasks):
        """多目标评估：从多个维度评估个体
        
        Args:
            cell: 细胞个体
            code: 生成的代码
            tasks: 任务列表
            
        Returns:
            dict: 多维度评估分数
        """
        objectives = {
            'functionality': 0.0,  # 功能正确性
            'efficiency': 0.0,     # 执行效率
            'complexity': 0.0,     # 代码复杂度
            'innovation': 0.0,     # 创新性
            'biological_realism': 0.0  # 生物学合理性
        }
        
        # 功能正确性评估
        try:
            # 选择多个任务进行评估
            task_scores = []
            for task in random.sample(tasks, min(3, len(tasks))):
                evaluation_result = await self.oracle_service.evaluate_code(
                    code, task.description
                )
                task_scores.append(evaluation_result.overall_score)
            
            objectives['functionality'] = sum(task_scores) / len(task_scores)
        except Exception:
            objectives['functionality'] = 0.0
        
        # 执行效率评估
        objectives['efficiency'] = self._evaluate_code_efficiency(code)
        
        # 代码复杂度评估（越简单越好）
        objectives['complexity'] = 1.0 - self._evaluate_code_complexity(code)
        
        # 创新性评估
        objectives['innovation'] = self._evaluate_innovation(cell, code)
        
        # 生物学合理性评估
        objectives['biological_realism'] = self._evaluate_biological_realism(cell)
        
        return objectives
    
    def _calculate_composite_fitness(self, objectives: dict) -> float:
        """计算综合适应度分数
        
        为了兼容性保留此方法，但在NSGA-III模式下主要用于显示目的。
        实际的多目标选择由NSGA-III算法处理。
        
        Args:
            objectives: 多维度评估分数
            
        Returns:
            float: 综合适应度分数
        """
        # 如果使用NSGA-III，返回功能性分数作为主要指标
        if self.selection_strategy == "nsga3":
            return objectives.get('functionality', 0.0)
        
        # 传统加权求和方法（向后兼容）
        weights = {
            'functionality': 0.4,
            'efficiency': 0.2,
            'complexity': 0.15,
            'innovation': 0.15,
            'biological_realism': 0.1
        }
        
        # 动态调整权重
        if self.current_generation < 10:
            # 早期阶段：重视功能正确性
            weights['functionality'] = 0.6
            weights['efficiency'] = 0.1
        elif self.current_generation > 50:
            # 后期阶段：重视效率和创新
            weights['efficiency'] = 0.3
            weights['innovation'] = 0.25
        
        # 计算加权平均
        composite_score = sum(
            objectives.get(obj, 0.0) * weight 
            for obj, weight in weights.items()
        )
        
        return max(0.0, min(1.0, composite_score))
    
    def _update_pareto_front(self, cell, objectives: dict):
        """更新帕累托前沿
        
        Args:
            cell: 细胞个体
            objectives: 多维度评估分数
        """
        if not hasattr(self, 'pareto_front'):
            self.pareto_front = []
        
        # 检查是否被现有解支配
        is_dominated = False
        dominated_solutions = []
        
        for existing_cell, existing_objectives in self.pareto_front:
            if self._dominates(existing_objectives, objectives):
                is_dominated = True
                break
            elif self._dominates(objectives, existing_objectives):
                dominated_solutions.append((existing_cell, existing_objectives))
        
        # 移除被新解支配的解
        for dominated in dominated_solutions:
            self.pareto_front.remove(dominated)
        
        # 如果新解不被支配，加入帕累托前沿
        if not is_dominated:
            self.pareto_front.append((cell, objectives))
    
    def _dominates(self, obj1: dict, obj2: dict) -> bool:
        """判断obj1是否支配obj2（帕累托支配关系）
        
        Args:
            obj1: 第一个目标向量
            obj2: 第二个目标向量
            
        Returns:
            bool: obj1是否支配obj2
        """
        better_in_all = True
        better_in_at_least_one = False
        
        for key in obj1.keys():
            if obj1[key] < obj2.get(key, 0.0):
                better_in_all = False
            elif obj1[key] > obj2.get(key, 0.0):
                better_in_at_least_one = True
        
        return better_in_all and better_in_at_least_one
    
    def _evaluate_code_efficiency(self, code: str) -> float:
        """评估代码执行效率
        
        Args:
            code: 代码字符串
            
        Returns:
            float: 效率分数 (0-1)
        """
        try:
            # 简单的效率评估：基于代码长度和复杂度
            lines = code.split('\n')
            line_count = len([line for line in lines if line.strip()])
            
            # 检查是否有嵌套循环（效率较低）
            nested_loops = code.count('for') + code.count('while')
            if 'for' in code and code.count('for') > 1:
                nested_penalty = 0.2
            else:
                nested_penalty = 0.0
            
            # 基于行数的效率评估（越少越好）
            line_efficiency = max(0.0, 1.0 - (line_count - 5) / 20.0)
            
            return max(0.0, line_efficiency - nested_penalty)
        except Exception:
            return 0.5  # 默认中等效率
    
    def _evaluate_code_complexity(self, code: str) -> float:
        """评估代码复杂度
        
        Args:
            code: 代码字符串
            
        Returns:
            float: 复杂度分数 (0-1，越高越复杂)
        """
        try:
            # 圈复杂度的简单估算
            complexity_indicators = [
                'if', 'elif', 'else', 'for', 'while', 
                'try', 'except', 'and', 'or'
            ]
            
            complexity_score = 0
            for indicator in complexity_indicators:
                complexity_score += code.count(indicator)
            
            # 归一化到0-1范围
            return min(1.0, complexity_score / 10.0)
        except Exception:
            return 0.5  # 默认中等复杂度
    
    def _evaluate_innovation(self, cell, code: str) -> float:
        """评估创新性
        
        Args:
            cell: 细胞个体
            code: 代码字符串
            
        Returns:
            float: 创新性分数 (0-1)
        """
        try:
            # 基于代码与历史解的差异度
            if hasattr(self, 'code_history'):
                max_similarity = 0.0
                for historical_code in self.code_history[-10:]:  # 检查最近10个解
                    similarity = self._calculate_code_similarity(code, historical_code)
                    max_similarity = max(max_similarity, similarity)
                
                innovation_score = 1.0 - max_similarity
            else:
                innovation_score = 0.5  # 默认中等创新性
            
            # 记录当前代码到历史
            if not hasattr(self, 'code_history'):
                self.code_history = []
            self.code_history.append(code)
            
            # 保持历史记录大小
            if len(self.code_history) > 50:
                self.code_history = self.code_history[-50:]
            
            return innovation_score
        except Exception:
            return 0.5
    
    def _calculate_code_similarity(self, code1: str, code2: str) -> float:
        """计算两段代码的相似度
        
        Args:
            code1: 第一段代码
            code2: 第二段代码
            
        Returns:
            float: 相似度 (0-1)
        """
        try:
            # 简单的基于字符串的相似度计算
            lines1 = set(line.strip() for line in code1.split('\n') if line.strip())
            lines2 = set(line.strip() for line in code2.split('\n') if line.strip())
            
            if not lines1 and not lines2:
                return 1.0
            if not lines1 or not lines2:
                return 0.0
            
            intersection = len(lines1.intersection(lines2))
            union = len(lines1.union(lines2))
            
            return intersection / union if union > 0 else 0.0
        except Exception:
            return 0.0
    
    def _evaluate_biological_realism(self, cell) -> float:
        """评估生物学合理性
        
        Args:
            cell: 细胞个体
            
        Returns:
            float: 生物学合理性分数 (0-1)
        """
        try:
            realism_score = 0.0
            
            # 基因组长度合理性
            genome_length = len(cell.genome)
            if 100 <= genome_length <= 5000:  # 合理的基因组长度范围
                realism_score += 0.3
            
            # 变异率合理性
            if hasattr(cell, 'mutation_rate') and 0.001 <= cell.mutation_rate <= 0.1:
                realism_score += 0.2
            
            # 年龄因素
            if hasattr(cell, 'age') and cell.age > 0:
                age_factor = min(1.0, cell.age / 10.0)  # 年龄越大，经验越丰富
                realism_score += 0.2 * age_factor
            
            # 能量水平
            if hasattr(cell, 'energy') and cell.energy > 0.5:
                realism_score += 0.3
            
            return min(1.0, realism_score)
        except Exception:
            return 0.5
    
    def _update_population_statistics(self, evaluation_batch):
        """更新种群统计信息
        
        Args:
            evaluation_batch: 评估批次数据
        """
        if not evaluation_batch:
            return
        
        # 更新种群统计
        fitness_scores = [item['fitness'] for item in evaluation_batch]
        
        self.population_stats = {
            'mean_fitness': sum(fitness_scores) / len(fitness_scores),
            'max_fitness': max(fitness_scores),
            'min_fitness': min(fitness_scores),
            'fitness_std': self._calculate_std(fitness_scores),
            'diversity_index': self._calculate_population_diversity(),
            'pareto_front_size': len(getattr(self, 'pareto_front', [])),
            'generation': self.current_generation
        }
        
        # 更新最优基因组结构（用于引导变异）
        best_item = max(evaluation_batch, key=lambda x: x['fitness'])
        best_cell = next(
            cell for cell in self.population 
            if cell.id == best_item['cell_id']
        )
        
        try:
            import json
            from .genome import Genome
            genome_data = json.loads(best_cell.genome)
            if isinstance(genome_data, dict) and 'root' in genome_data:
                self.best_genome_structure = Genome.from_dict(genome_data)
        except Exception:
            pass
    
    def _calculate_std(self, values):
        """计算标准差
        
        Args:
            values: 数值列表
            
        Returns:
            float: 标准差
        """
        if len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5
    
    async def _generate_code_from_genome(self, genome: str) -> str:
        """从基因序列生成Python代码"""
        try:
            from .genome import Genome, GenomeGenerator, create_random_genome
            import json
            
            # 尝试解析为新的基因组格式
            try:
                genome_data = json.loads(genome)
                if isinstance(genome_data, dict) and 'root' in genome_data:
                    # 新格式：使用AST基因组
                    genome_obj = Genome.from_dict(genome_data)
                    return genome_obj.to_code()
                else:
                    # 旧格式：转换为新格式
                    generator = GenomeGenerator()
                    genome_obj = generator.generate_random()
                    return genome_obj.to_code()
            except:
                # 如果解析失败，生成新的随机基因组
                genome_obj = create_random_genome()
                return genome_obj.to_code()
            
        except Exception as e:
            logger.error("代码生成失败", error=str(e))
            # 返回简单的默认实现
            return "def sort_numbers(numbers: list[int]) -> list[int]:\n    return sorted(numbers)"
    
    async def _update_generation_stats(self, db: Session, generation: Generation):
        """更新代数统计信息"""
        fitness_scores = [cell.fitness_score for cell in self.population 
                         if cell.fitness_score is not None]
        
        if fitness_scores:
            generation.avg_fitness = sum(fitness_scores) / len(fitness_scores)
            generation.max_fitness = max(fitness_scores)
            generation.min_fitness = min(fitness_scores)
        
        generation.completed_at = datetime.now()
        db.commit()
        
        # 执行SHAP分析（如果启用且满足间隔条件）
        if (self.enable_shap_analysis and 
            self.current_generation % self.shap_analysis_interval == 0):
            await self._perform_shap_analysis()
            logger.info("SHAP分析完成", generation=self.current_generation)
    
    async def _broadcast_generation_update(self, generation: Generation):
        """广播代数更新事件"""
        fitness_scores = [cell.fitness_score for cell in self.population 
                         if cell.fitness_score is not None]
        
        # 准备广播数据
        broadcast_data = {
            "generation_number": generation.generation_number,
            "population_size": generation.population_size,
            "avg_fitness": generation.avg_fitness,
            "max_fitness": generation.max_fitness,
            "min_fitness": generation.min_fitness,
            "fitness_distribution": fitness_scores
        }
        
        # 如果有SHAP分析结果，添加到广播数据中
        if self.latest_shap_results:
            broadcast_data["shap_analysis"] = {
                "enabled": True,
                "results_count": len(self.latest_shap_results),
                "top_explanations": [{
                    "cell_id": result.cell_id,
                    "fitness_score": result.fitness_score,
                    "explanation_text": result.explanation_text,
                    "top_features": sorted(
                        result.feature_importance.items(), 
                        key=lambda x: x[1], 
                        reverse=True
                    )[:5]  # 只发送前5个最重要的特征
                } for result in self.latest_shap_results[:3]]  # 只发送前3个解释
            }
        else:
            broadcast_data["shap_analysis"] = {"enabled": self.enable_shap_analysis}
        
        await websocket_manager.broadcast_to_room("evolution", {
            "event": "generation_completed",
            "data": broadcast_data
        })
    
    def get_status(self) -> dict:
        """获取进化状态"""
        fitness_scores = [cell.fitness_score for cell in self.population 
                         if cell.fitness_score is not None]
        
        elapsed_time = 0.0
        start_time_timestamp = 0.0
        if self.start_time:
            elapsed_time = (datetime.now() - self.start_time).total_seconds()
            start_time_timestamp = self.start_time.timestamp()
        
        return {
            "is_running": self.is_running,
            "current_generation": self.current_generation,
            "population_size": len(self.population),
            "best_fitness": max(fitness_scores) if fitness_scores else 0.0,
            "avg_fitness": sum(fitness_scores) / len(fitness_scores) if fitness_scores else 0.0,
            "total_evaluations": len(fitness_scores),
            "start_time": start_time_timestamp,
            "elapsed_time": elapsed_time
        }
    
    def get_stats(self) -> dict:
        """获取详细的进化统计信息"""
        fitness_scores = [cell.fitness_score for cell in self.population 
                         if cell.fitness_score is not None]
        
        # 计算分子统计（模拟数据）
        total_molecules = len(self.population) * random.randint(50, 200)
        active_reactions = random.randint(10, 50)
        
        # 计算编译统计
        successful_compilations = len([cell for cell in self.population if cell.fitness_score and cell.fitness_score > 0])
        total_compilations = len(self.population)
        compilation_success_rate = successful_compilations / total_compilations if total_compilations > 0 else 0
        
        # 计算多样性指数（简化版）
        diversity_index = len(set(cell.genome for cell in self.population)) / len(self.population) if self.population else 0
        
        elapsed_time = 0
        if self.start_time:
            elapsed_time = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "generation": self.current_generation,
            "population_size": len(self.population),
            "best_fitness": max(fitness_scores) if fitness_scores else 0.0,
            "avg_fitness": sum(fitness_scores) / len(fitness_scores) if fitness_scores else 0.0,
            "min_fitness": min(fitness_scores) if fitness_scores else 0.0,
            "diversity_index": diversity_index,
            "total_molecules": total_molecules,
            "active_reactions": active_reactions,
            "successful_compilations": successful_compilations,
            "total_compilations": total_compilations,
            "compilation_success_rate": compilation_success_rate,
            "total_runtime": elapsed_time,
            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "fitness_distribution": fitness_scores
        }
    
    async def _strategy_evolution_loop(self):
        """基于策略模式的进化主循环
        
        使用新的进化策略框架进行进化，支持多种算法和自适应参数调整。
        """
        try:
            logger.info("启动策略模式进化循环", strategy=self.strategy_config.strategy_type.value)
            
            # 初始化策略
            strategy = EvolutionStrategyFactory.create_strategy(self.strategy_config)
            
            # 转换现有种群为Individual格式
            individuals = await self._convert_population_to_individuals()
            
            # 如果种群为空，初始化新种群
            if not individuals:
                logger.info("种群为空，使用策略初始化新种群")
                individuals = strategy.initialize_population()
                logger.info("策略模式种群初始化完成", size=len(individuals))
            
            generation_count = 0
            
            while self.is_running and generation_count < self.strategy_config.max_generations:
                if self.is_paused:
                    await asyncio.sleep(1)
                    continue
                
                logger.info(f"开始第{generation_count}代进化", 
                           strategy=self.strategy_config.strategy_type.value,
                           population_size=len(individuals))
                
                # 评估种群
                individuals = await self._evaluate_individuals(individuals)
                
                # 设置策略的种群
                strategy.population = individuals
                
                # 执行一代进化
                evolution_stats = strategy.evolve_generation()
                
                # 获取进化后的种群
                individuals = strategy.population
                
                # 自适应参数调整
                if self.adaptive_manager and self.strategy_config.adaptive_parameters:
                    performance_metrics = self._calculate_performance_metrics(individuals)
                    new_strategy = self.adaptive_manager.adapt_strategy(performance_metrics)
                    
                    if new_strategy != strategy:
                        logger.info("切换进化策略", 
                                   old_strategy=strategy.__class__.__name__,
                                   new_strategy=new_strategy.__class__.__name__)
                        strategy = new_strategy
                
                # 更新当前代数
                self.current_generation = generation_count
                
                # 执行SHAP分析（策略模式）
                if (self.enable_shap_analysis and 
                    generation_count % self.shap_analysis_interval == 0):
                    await self._perform_strategy_shap_analysis(individuals)
                
                # 广播策略进化更新
                await self._broadcast_strategy_update(individuals, generation_count)
                
                generation_count += 1
                await asyncio.sleep(0.1)  # 避免过度占用资源
            
            logger.info("策略模式进化循环完成", final_generation=generation_count)
            
        except Exception as e:
            logger.error("策略模式进化循环出错", error=str(e))
            await websocket_manager.broadcast_to_room("evolution", {
                "event": "strategy_evolution_error",
                "data": {"error": str(e)}
            })
        finally:
            self.is_running = False
            self.is_paused = False
    
    async def _convert_population_to_individuals(self) -> List[Individual]:
        """将现有种群转换为Individual格式
        
        Returns:
            List[Individual]: 转换后的个体列表
        """
        individuals = []
        
        for cell in self.population:
            try:
                # 解析基因组
                import json
                genome_data = json.loads(cell.genome) if isinstance(cell.genome, str) else cell.genome
                
                # 创建Individual对象
                individual = Individual(
                    genome=genome_data,
                    fitness=cell.fitness_score or 0.0,
                    objectives=[cell.fitness_score or 0.0],  # 单目标优化
                    constraints=[],
                    age=getattr(cell, 'age', 0),
                    generation=self.current_generation
                )
                
                individuals.append(individual)
                
            except Exception as e:
                logger.warning("转换个体失败", cell_id=cell.id, error=str(e))
                continue
        
        logger.info("种群转换完成", original_size=len(self.population), 
                   converted_size=len(individuals))
        return individuals
    
    async def _evaluate_individuals(self, individuals: List[Individual]) -> List[Individual]:
        """评估个体适应度
        
        Args:
            individuals: 待评估的个体列表
            
        Returns:
            List[Individual]: 评估后的个体列表
        """
        for individual in individuals:
            try:
                # 生成代码
                code = await self._generate_code_from_individual(individual)
                
                # 执行代码评估
                result = self.sandbox_executor.run_code(code)
                
                # 转换结果格式
                execution_result = {
                    'success': result.exit_code == 0,
                    'output': result.stdout,
                    'error': result.stderr,
                    'execution_time': result.duration_sec
                }
                
                # 计算适应度
                fitness = self._calculate_individual_fitness(execution_result, individual)
                individual.fitness = {"fitness": fitness}
                individual.objectives = {"fitness": fitness}  # 单目标优化
                
            except Exception as e:
                logger.warning("个体评估失败", error=str(e))
                individual.fitness = {"fitness": 0.0}
                individual.objectives = {"fitness": 0.0}
        
        return individuals
    
    async def _generate_code_from_individual(self, individual: Individual) -> str:
        """从Individual对象生成代码
        
        Args:
            individual: 个体对象
            
        Returns:
            str: 生成的Python代码
        """
        try:
            from .genome import Genome
            
            # 如果基因组是字典格式，转换为Genome对象
            if isinstance(individual.genome, dict):
                genome_obj = Genome.from_dict(individual.genome)
                return genome_obj.to_code()
            else:
                # 如果是其他格式，使用默认代码生成
                return await self._generate_code_from_genome(str(individual.genome))
                
        except Exception as e:
            logger.error("从Individual生成代码失败", error=str(e))
            return "def sort_numbers(numbers: list[int]) -> list[int]:\n    return sorted(numbers)"
    
    def _calculate_individual_fitness(self, execution_result: dict, individual: Individual) -> float:
        """计算个体适应度
        
        Args:
            execution_result: 代码执行结果
            individual: 个体对象
            
        Returns:
            float: 适应度分数
        """
        try:
            fitness = 0.0
            
            # 基于执行结果计算适应度
            if execution_result.get('success', False):
                fitness += 0.5  # 成功执行基础分
                
                # 基于输出质量评分
                output = execution_result.get('output', '')
                if output and len(output.strip()) > 0:
                    fitness += 0.3
                
                # 基于执行时间评分（越快越好）
                execution_time = execution_result.get('execution_time', 1.0)
                if execution_time < 1.0:
                    fitness += 0.2 * (1.0 - execution_time)
            
            # 添加多样性奖励
            diversity_bonus = self._calculate_diversity_bonus(individual)
            fitness += diversity_bonus * 0.1
            
            return min(1.0, max(0.0, fitness))
            
        except Exception as e:
            logger.error("计算个体适应度失败", error=str(e))
            return 0.0
    
    def _calculate_diversity_bonus(self, individual: Individual) -> float:
        """计算多样性奖励
        
        Args:
            individual: 个体对象
            
        Returns:
            float: 多样性奖励分数
        """
        try:
            # 简化的多样性计算
            genome_str = str(individual.genome)
            genome_hash = hash(genome_str)
            
            # 基于哈希值的简单多样性度量
            diversity_score = (genome_hash % 1000) / 1000.0
            return diversity_score
            
        except Exception:
            return 0.0
    
    def _calculate_performance_metrics(self, individuals: List[Individual]) -> dict:
        """计算性能指标用于自适应调整
        
        Args:
            individuals: 个体列表
            
        Returns:
            dict: 性能指标字典
        """
        try:
            fitness_scores = [ind.get_fitness() for ind in individuals if ind.fitness]
            
            if not fitness_scores:
                return {
                    'avg_fitness': 0.0,
                    'max_fitness': 0.0,
                    'diversity': 0.0,
                    'convergence_rate': 0.0
                }
            
            avg_fitness = sum(fitness_scores) / len(fitness_scores)
            max_fitness = max(fitness_scores)
            
            # 计算多样性
            unique_genomes = len(set(str(ind.genome) for ind in individuals))
            diversity = unique_genomes / len(individuals) if individuals else 0.0
            
            # 计算收敛率（简化版）
            convergence_rate = 1.0 - diversity
            
            return {
                'avg_fitness': avg_fitness,
                'max_fitness': max_fitness,
                'diversity': diversity,
                'convergence_rate': convergence_rate,
                'generation': self.current_generation
            }
            
        except Exception as e:
            logger.error("计算性能指标失败", error=str(e))
            return {
                'avg_fitness': 0.0,
                'max_fitness': 0.0,
                'diversity': 0.0,
                'convergence_rate': 0.0
            }
    
    async def _broadcast_strategy_update(self, individuals: List[Individual], generation: int):
        """广播策略模式进化更新
        
        Args:
            individuals: 当前个体列表
            generation: 当前代数
        """
        try:
            fitness_scores = [ind.get_fitness() for ind in individuals if ind.fitness]
            
            update_data = {
                "event": "strategy_generation_completed",
                "data": {
                    "generation": generation,
                    "strategy_type": self.strategy_config.strategy_type.value,
                    "population_size": len(individuals),
                    "avg_fitness": sum(fitness_scores) / len(fitness_scores) if fitness_scores else 0.0,
                    "max_fitness": max(fitness_scores) if fitness_scores else 0.0,
                    "min_fitness": min(fitness_scores) if fitness_scores else 0.0,
                    "diversity": len(set(str(ind.genome) for ind in individuals)) / len(individuals) if individuals else 0.0,
                    "fitness_distribution": fitness_scores[:10]  # 只发送前10个适应度分数
                }
            }
            
            await websocket_manager.broadcast_to_room("evolution", update_data)
            
        except Exception as e:
            logger.error("广播策略更新失败", error=str(e))
    
    async def _perform_shap_analysis(self):
        """执行SHAP分析
        
        分析当前种群中最优个体的基因贡献度，提供可解释性分析。
        """
        try:
            logger.info("开始执行SHAP分析", generation=self.current_generation)
            
            # 获取当前种群中适应度最高的个体
            top_cells = sorted(
                [cell for cell in self.population if cell.fitness_score is not None],
                key=lambda x: x.fitness_score,
                reverse=True
            )[:5]  # 分析前5个最优个体
            
            if not top_cells:
                logger.warning("没有有效的细胞进行SHAP分析")
                return
            
            # 执行SHAP分析
            shap_results = await shap_analyzer.analyze_population(top_cells)
            
            # 更新最新的SHAP分析结果
            self.latest_shap_results = shap_results
            
            # 获取种群级别的洞察
            population_insights = shap_analyzer.get_population_insights(shap_results)
            
            # 广播SHAP分析完成事件
            await websocket_manager.broadcast_to_room("evolution", {
                "event": "shap_analysis_completed",
                "data": {
                    "generation": self.current_generation,
                    "analyzed_cells": len(shap_results),
                    "population_insights": population_insights,
                    "analysis_summary": population_insights.get('analysis_summary', ''),
                    "top_features_global": population_insights.get('top_features', [])[:5]
                }
            })
            
            logger.info("SHAP分析完成并广播", 
                       generation=self.current_generation,
                       analyzed_cells=len(shap_results))
            
        except Exception as e:
            logger.error("SHAP分析执行失败", error=str(e), generation=self.current_generation)
            
            # 广播SHAP分析错误事件
            await websocket_manager.broadcast_to_room("evolution", {
                "event": "shap_analysis_error",
                "data": {
                    "generation": self.current_generation,
                    "error": str(e)
                }
            })
    
    def get_latest_shap_results(self) -> List[ShapExplanation]:
        """获取最新的SHAP分析结果
        
        Returns:
            List[ShapExplanation]: SHAP分析结果列表
        """
        return self.latest_shap_results.copy()
    
    def set_shap_analysis_config(self, enabled: bool = True, interval: int = 1):
        """设置SHAP分析配置
        
        Args:
            enabled: 是否启用SHAP分析
            interval: 分析间隔（每N代分析一次）
        """
        self.enable_shap_analysis = enabled
        self.shap_analysis_interval = max(1, interval)
        
        logger.info("SHAP分析配置已更新", 
                    enabled=enabled, 
                    interval=self.shap_analysis_interval)
    
    async def _perform_strategy_shap_analysis(self, individuals: List[Individual]):
        """执行策略模式下的SHAP分析
        
        Args:
            individuals: 当前个体列表
        """
        try:
            logger.info("开始执行策略模式SHAP分析", generation=self.current_generation)
            
            # 将Individual对象转换为DigitalCell对象进行SHAP分析
            top_individuals = sorted(
                [ind for ind in individuals if ind.fitness],
                key=lambda x: x.get_fitness(),
                reverse=True
            )[:5]  # 分析前5个最优个体
            
            if not top_individuals:
                logger.warning("没有有效的个体进行SHAP分析")
                return
            
            # 转换为DigitalCell格式
            temp_cells = []
            for i, individual in enumerate(top_individuals):
                try:
                    import json
                    temp_cell = DigitalCell(
                        id=f"temp_{i}",
                        genome=json.dumps(individual.genome) if isinstance(individual.genome, dict) else str(individual.genome),
                        fitness_score=individual.get_fitness(),
                        generation_id=self.current_generation
                    )
                    temp_cells.append(temp_cell)
                except Exception as e:
                    logger.warning("转换个体为细胞失败", error=str(e))
                    continue
            
            if not temp_cells:
                logger.warning("没有成功转换的细胞进行SHAP分析")
                return
            
            # 执行SHAP分析
            shap_results = await shap_analyzer.analyze_population(temp_cells)
            
            # 更新最新的SHAP分析结果
            self.latest_shap_results = shap_results
            
            # 获取种群级别的洞察
            population_insights = shap_analyzer.get_population_insights(shap_results)
            
            # 广播策略模式SHAP分析完成事件
            await websocket_manager.broadcast_to_room("evolution", {
                "event": "strategy_shap_analysis_completed",
                "data": {
                    "generation": self.current_generation,
                    "strategy_type": self.strategy_config.strategy_type.value,
                    "analyzed_individuals": len(shap_results),
                    "population_insights": population_insights,
                    "analysis_summary": population_insights.get('analysis_summary', ''),
                    "top_features_global": population_insights.get('top_features', [])[:5]
                }
            })
            
            logger.info("策略模式SHAP分析完成并广播", 
                       generation=self.current_generation,
                       analyzed_individuals=len(shap_results))
            
        except Exception as e:
            logger.error("策略模式SHAP分析执行失败", error=str(e), generation=self.current_generation)
            
            # 广播策略模式SHAP分析错误事件
            await websocket_manager.broadcast_to_room("evolution", {
                "event": "strategy_shap_analysis_error",
                "data": {
                    "generation": self.current_generation,
                    "strategy_type": self.strategy_config.strategy_type.value,
                    "error": str(e)
                }
            })

# 全局进化引擎实例
evolution_engine = EvolutionEngine()