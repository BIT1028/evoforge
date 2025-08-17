"""evoforge.evolution
-------------------
极简遗传算法（GA）核心，用于驱动代码个体的自进化。

⚠️ 当前版本只实现 MVP：
1. 基础个体、种群、适应度评估（调用 evaluation.evaluate_individual）
2. 随机变异（字符串替换）与精简交叉（取前/后片段拼接）
3. 循环迭代更新种群，输出最佳个体

后续可扩展：
- 复杂 AST 级别重组
- 多目标适应度
- 并行评估
- 分布式种群岛模型
"""
from __future__ import annotations

import logging
import random
import string
from dataclasses import dataclass, field
from typing import Callable, List, Tuple

from .evaluation import evaluate_individual, TestResult

logger = logging.getLogger("evoforge.evolution")
logger.setLevel(logging.DEBUG)

# ----------------------------- 数据结构 -----------------------------

@dataclass
class Individual:
    """种群个体，保存代码文本与适应度。"""

    code: str
    fitness: float | None = None  # 未评估时为 None
    test_result: TestResult | None = None

    def __str__(self) -> str:  # pragma: no cover
        return f"Fitness={self.fitness:.3f if self.fitness is not None else -1}"  # type: ignore

@dataclass
class EvolutionConfig:
    """进化算法配置。"""

    population_size: int = 10
    generations: int = 5
    mutation_rate: float = 0.3
    crossover_rate: float = 0.5
    elitism: int = 1  # 每代保留最优个体数量

# ----------------------------- 进化核心 -----------------------------

class EvolutionEngine:
    """极简 GA 引擎。"""

    def __init__(
        self,
        test_code: str,
        seed_generator: Callable[[int], str],
        fitness_func: Callable[[str, str], float] | None = None,
        config: EvolutionConfig | None = None,
    ) -> None:
        self.test_code = test_code
        self.seed_generator = seed_generator
        self.fitness_func = fitness_func or self._default_fitness
        self.config = config or EvolutionConfig()
        self.population: List[Individual] = []
        logger.debug("EvolutionEngine 初始化: %s", self.config)

    # -----------------------------------------------------------------
    # 公共 API
    # -----------------------------------------------------------------

    def initialize(self) -> None:
        """随机初始化种群。"""
        self.population = [Individual(self.seed_generator(i)) for i in range(self.config.population_size)]
        logger.debug("已初始化 %d 个体", len(self.population))

    def evolve(self) -> Individual:
        """执行进化主循环，返回最终最佳个体。"""
        assert self.population, "请先调用 initialize()"  # noqa: S101
        for gen in range(self.config.generations):
            logger.debug("========== 第 %d 代 ==========" , gen)
            self._evaluate_population()
            self.population.sort(key=lambda ind: ind.fitness or 0, reverse=True)
            logger.debug("本代最佳适应度=%.3f", self.population[0].fitness)
            next_population: List[Individual] = self.population[: self.config.elitism]
            while len(next_population) < self.config.population_size:
                parent1, parent2 = self._select_parents()
                if random.random() < self.config.crossover_rate:
                    child_code = self._crossover(parent1.code, parent2.code)
                else:
                    child_code = parent1.code
                if random.random() < self.config.mutation_rate:
                    child_code = self._mutate(child_code)
                next_population.append(Individual(child_code))
            self.population = next_population
        # 最终评估一次确保 fitness 最新
        self._evaluate_population()
        self.population.sort(key=lambda ind: ind.fitness or 0, reverse=True)
        return self.population[0]

    # -----------------------------------------------------------------
    # 内部方法
    # -----------------------------------------------------------------

    def _evaluate_population(self) -> None:
        for ind in self.population:
            if ind.fitness is not None:
                continue  # 已评估
            ind.fitness = self.fitness_func(ind.code, self.test_code)
            logger.debug("个体评估完成: fitness=%.3f", ind.fitness)

    def _default_fitness(self, code: str, test_code: str) -> float:
        test_result, _ = evaluate_individual(code, test_code)
        return test_result.success_rate()

    def _select_parents(self) -> Tuple[Individual, Individual]:
        """简单轮盘赌（按适应度加权）选父母。"""
        total_fitness = sum((ind.fitness or 0) for ind in self.population)
        if total_fitness == 0:
            # 全部适应度 0，则随机选两个
            return random.sample(self.population, 2)
        def pick_one() -> Individual:
            r = random.random() * total_fitness
            acc = 0.0
            for ind in self.population:
                acc += ind.fitness or 0
                if acc >= r:
                    return ind
            return self.population[-1]
        return pick_one(), pick_one()

    def _crossover(self, code1: str, code2: str) -> str:
        """将两个代码字符串在随机位置切分后拼接。"""
        pos1 = random.randint(0, len(code1))
        pos2 = random.randint(0, len(code2))
        child = code1[:pos1] + code2[pos2:]
        logger.debug("交叉生成新个体，长度 %d -> %d", len(code1) + len(code2), len(child))
        return child

    def _mutate(self, code: str) -> str:
        """随机替换一个字符实现简单变异。"""
        if not code:
            return code
        pos = random.randint(0, len(code) - 1)
        new_char = random.choice(string.ascii_letters + string.digits + "_\n    ")
        mutated = code[:pos] + new_char + code[pos + 1 :]
        logger.debug("变异位置 %d 字符 -> '%s'", pos, new_char)
        return mutated