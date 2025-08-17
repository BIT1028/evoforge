"""适应度评估模块 - 实现多目标适应度计算

本模块实现了多种适应度评估指标:
- 正确性: 测试通过率、覆盖率
- 性能: 运行时间、内存使用
- 质量: 代码复杂度、可读性
- 新颖度: 代码差异性、行为多样性
- 资源: CPU使用、内存峰值
"""

import ast
import logging
import math
import statistics
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import copy

# 导入代码复杂度分析工具
try:
    import radon.complexity as radon_complexity
    import radon.metrics as radon_metrics
except ImportError:
    # 如果没有安装radon，使用简化版本
    radon_complexity = None
    radon_metrics = None

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # 输出大量DEBUG信息

class FitnessObjective(Enum):
    """适应度目标枚举"""
    CORRECTNESS = "correctness"  # 正确性
    PERFORMANCE = "performance"  # 性能
    MEMORY = "memory"  # 内存使用
    COMPLEXITY = "complexity"  # 代码复杂度
    READABILITY = "readability"  # 可读性
    NOVELTY = "novelty"  # 新颖度
    COVERAGE = "coverage"  # 测试覆盖率
    STABILITY = "stability"  # 稳定性
    EFFICIENCY = "efficiency"  # 效率
    MAINTAINABILITY = "maintainability"  # 可维护性

@dataclass
class FitnessMetrics:
    """适应度指标数据结构"""
    correctness: float = 0.0  # 正确性分数 [0, 1]
    performance: float = 0.0  # 性能分数 [0, 1]
    memory: float = 0.0  # 内存效率分数 [0, 1]
    complexity: float = 0.0  # 复杂度分数 [0, 1] (越低越好)
    readability: float = 0.0  # 可读性分数 [0, 1]
    novelty: float = 0.0  # 新颖度分数 [0, 1]
    coverage: float = 0.0  # 覆盖率分数 [0, 1]
    stability: float = 0.0  # 稳定性分数 [0, 1]
    efficiency: float = 0.0  # 效率分数 [0, 1]
    maintainability: float = 0.0  # 可维护性分数 [0, 1]
    
    # 原始数据
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """初始化后处理"""
        logger.debug(f"创建适应度指标: 正确性={self.correctness:.3f}, 性能={self.performance:.3f}")
    
    def to_dict(self) -> Dict[str, float]:
        """转换为字典格式"""
        return {
            "correctness": self.correctness,
            "performance": self.performance,
            "memory": self.memory,
            "complexity": self.complexity,
            "readability": self.readability,
            "novelty": self.novelty,
            "coverage": self.coverage,
            "stability": self.stability,
            "efficiency": self.efficiency,
            "maintainability": self.maintainability
        }
    
    def weighted_score(self, weights: Dict[str, float]) -> float:
        """计算加权总分
        
        Args:
            weights: 各指标权重
            
        Returns:
            加权总分
        """
        total_score = 0.0
        total_weight = 0.0
        
        metrics = self.to_dict()
        for metric, value in metrics.items():
            weight = weights.get(metric, 0.0)
            total_score += value * weight
            total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        return total_score / total_weight

@dataclass
class FitnessConfig:
    """适应度评估配置"""
    # 权重配置
    weights: Dict[str, float] = field(default_factory=lambda: {
        "correctness": 1.0,
        "performance": 0.8,
        "memory": 0.6,
        "complexity": -0.4,  # 负权重表示越低越好
        "readability": 0.3,
        "novelty": 0.2,
        "coverage": 0.5,
        "stability": 0.4,
        "efficiency": 0.7,
        "maintainability": 0.3
    })
    
    # 性能基准
    performance_baseline: float = 1.0  # 基准运行时间(秒)
    memory_baseline: int = 1024 * 1024  # 基准内存使用(字节)
    
    # 复杂度阈值
    max_complexity: int = 10
    max_lines: int = 100
    
    # 稳定性测试次数
    stability_runs: int = 3
    
    # 新颖度计算参数
    novelty_population_size: int = 50
    novelty_distance_threshold: float = 0.1

class FitnessEvaluator:
    """适应度评估器 - 计算个体的多目标适应度"""
    
    def __init__(self, config: Optional[FitnessConfig] = None):
        """初始化适应度评估器
        
        Args:
            config: 评估配置
        """
        self.config = config or FitnessConfig()
        self.population_history: List[str] = []  # 用于新颖度计算
        
        logger.debug("初始化适应度评估器")
    
    def evaluate(self, code: str, test_results: Dict[str, Any], 
                 execution_stats: Dict[str, Any]) -> FitnessMetrics:
        """评估个体适应度
        
        Args:
            code: 个体代码
            test_results: 测试结果
            execution_stats: 执行统计信息
            
        Returns:
            适应度指标
        """
        logger.debug(f"开始评估适应度，代码长度: {len(code)}")
        
        metrics = FitnessMetrics()
        
        # 1. 正确性评估
        metrics.correctness = self._evaluate_correctness(test_results)
        logger.debug(f"正确性评估完成: {metrics.correctness:.3f}")
        
        # 2. 性能评估
        metrics.performance = self._evaluate_performance(execution_stats)
        logger.debug(f"性能评估完成: {metrics.performance:.3f}")
        
        # 3. 内存效率评估
        metrics.memory = self._evaluate_memory(execution_stats)
        logger.debug(f"内存评估完成: {metrics.memory:.3f}")
        
        # 4. 代码复杂度评估
        metrics.complexity = self._evaluate_complexity(code)
        logger.debug(f"复杂度评估完成: {metrics.complexity:.3f}")
        
        # 5. 可读性评估
        metrics.readability = self._evaluate_readability(code)
        logger.debug(f"可读性评估完成: {metrics.readability:.3f}")
        
        # 6. 新颖度评估
        metrics.novelty = self._evaluate_novelty(code)
        logger.debug(f"新颖度评估完成: {metrics.novelty:.3f}")
        
        # 7. 测试覆盖率评估
        metrics.coverage = self._evaluate_coverage(test_results)
        logger.debug(f"覆盖率评估完成: {metrics.coverage:.3f}")
        
        # 8. 稳定性评估
        metrics.stability = self._evaluate_stability(execution_stats)
        logger.debug(f"稳定性评估完成: {metrics.stability:.3f}")
        
        # 9. 效率评估
        metrics.efficiency = self._evaluate_efficiency(execution_stats)
        logger.debug(f"效率评估完成: {metrics.efficiency:.3f}")
        
        # 10. 可维护性评估
        metrics.maintainability = self._evaluate_maintainability(code)
        logger.debug(f"可维护性评估完成: {metrics.maintainability:.3f}")
        
        # 保存原始数据
        metrics.raw_data = {
            "test_results": test_results,
            "execution_stats": execution_stats,
            "code_length": len(code)
        }
        
        logger.debug(f"适应度评估完成，总体分数: {metrics.weighted_score(self.config.weights):.3f}")
        return metrics
    
    def _evaluate_correctness(self, test_results: Dict[str, Any]) -> float:
        """评估正确性
        
        Args:
            test_results: 测试结果
            
        Returns:
            正确性分数 [0, 1]
        """
        if not test_results:
            logger.debug("测试结果为空，正确性分数为0")
            return 0.0
        
        passed = test_results.get("passed", 0)
        total = test_results.get("total", 1)
        
        if total == 0:
            logger.debug("总测试数为0，正确性分数为0")
            return 0.0
        
        correctness = passed / total
        logger.debug(f"正确性计算: {passed}/{total} = {correctness:.3f}")
        
        return correctness
    
    def _evaluate_performance(self, execution_stats: Dict[str, Any]) -> float:
        """评估性能
        
        Args:
            execution_stats: 执行统计
            
        Returns:
            性能分数 [0, 1]
        """
        duration = execution_stats.get("duration_sec", float('inf'))
        
        if duration == float('inf') or duration <= 0:
            logger.debug(f"无效的执行时间: {duration}，性能分数为0")
            return 0.0
        
        # 使用指数衰减函数，基准时间内得满分
        baseline = self.config.performance_baseline
        performance = math.exp(-duration / baseline)
        
        logger.debug(f"性能计算: 时间={duration:.3f}s, 基准={baseline}s, 分数={performance:.3f}")
        return min(1.0, performance)
    
    def _evaluate_memory(self, execution_stats: Dict[str, Any]) -> float:
        """评估内存效率
        
        Args:
            execution_stats: 执行统计
            
        Returns:
            内存效率分数 [0, 1]
        """
        memory_bytes = execution_stats.get("max_memory_bytes", float('inf'))
        
        if memory_bytes == float('inf') or memory_bytes <= 0:
            logger.debug(f"无效的内存使用: {memory_bytes}，内存分数为0")
            return 0.0
        
        # 使用指数衰减函数
        baseline = self.config.memory_baseline
        memory_score = math.exp(-memory_bytes / baseline)
        
        logger.debug(f"内存计算: 使用={memory_bytes}字节, 基准={baseline}字节, 分数={memory_score:.3f}")
        return min(1.0, memory_score)
    
    def _evaluate_complexity(self, code: str) -> float:
        """评估代码复杂度
        
        Args:
            code: 代码字符串
            
        Returns:
            复杂度分数 [0, 1] (越低越好)
        """
        try:
            # 尝试使用radon计算圈复杂度
            if radon_complexity:
                complexity_results = radon_complexity.cc_visit(code)
                if complexity_results:
                    avg_complexity = sum(result.complexity for result in complexity_results) / len(complexity_results)
                else:
                    avg_complexity = 1
            else:
                # 简化版复杂度计算
                avg_complexity = self._simple_complexity(code)
            
            # 归一化到[0, 1]，越低越好
            normalized = min(1.0, avg_complexity / self.config.max_complexity)
            complexity_score = 1.0 - normalized  # 反转，使得低复杂度得高分
            
            logger.debug(f"复杂度计算: 平均复杂度={avg_complexity:.2f}, 分数={complexity_score:.3f}")
            return complexity_score
            
        except Exception as e:
            logger.error(f"复杂度计算失败: {e}")
            return 0.5  # 默认中等分数
    
    def _simple_complexity(self, code: str) -> float:
        """简化版复杂度计算
        
        Args:
            code: 代码字符串
            
        Returns:
            复杂度值
        """
        try:
            tree = ast.parse(code)
            complexity = 1  # 基础复杂度
            
            for node in ast.walk(tree):
                # 控制流语句增加复杂度
                if isinstance(node, (ast.If, ast.For, ast.While, ast.Try)):
                    complexity += 1
                elif isinstance(node, ast.BoolOp):
                    complexity += len(node.values) - 1
            
            return complexity
            
        except Exception as e:
            logger.debug(f"简化复杂度计算失败: {e}")
            return 5.0  # 默认中等复杂度
    
    def _evaluate_readability(self, code: str) -> float:
        """评估可读性
        
        Args:
            code: 代码字符串
            
        Returns:
            可读性分数 [0, 1]
        """
        try:
            lines = code.split('\n')
            non_empty_lines = [line for line in lines if line.strip()]
            
            # 基于行数的可读性评估
            line_count = len(non_empty_lines)
            line_score = 1.0 - min(1.0, line_count / self.config.max_lines)
            
            # 基于平均行长度的评估
            avg_line_length = sum(len(line) for line in non_empty_lines) / max(1, len(non_empty_lines))
            length_score = 1.0 - min(1.0, avg_line_length / 100)  # 100字符为基准
            
            # 基于注释比例的评估
            comment_lines = sum(1 for line in lines if line.strip().startswith('#'))
            comment_ratio = comment_lines / max(1, len(non_empty_lines))
            comment_score = min(1.0, comment_ratio * 2)  # 注释比例越高越好
            
            # 综合评分
            readability = (line_score + length_score + comment_score) / 3
            
            logger.debug(f"可读性计算: 行数={line_count}, 平均行长={avg_line_length:.1f}, 注释比例={comment_ratio:.2f}, 分数={readability:.3f}")
            return readability
            
        except Exception as e:
            logger.error(f"可读性计算失败: {e}")
            return 0.5
    
    def _evaluate_novelty(self, code: str) -> float:
        """评估新颖度
        
        Args:
            code: 代码字符串
            
        Returns:
            新颖度分数 [0, 1]
        """
        if not self.population_history:
            logger.debug("种群历史为空，新颖度分数为1")
            self.population_history.append(code)
            return 1.0
        
        # 计算与历史个体的平均距离
        distances = []
        for historical_code in self.population_history[-self.config.novelty_population_size:]:
            distance = self._code_distance(code, historical_code)
            distances.append(distance)
        
        avg_distance = statistics.mean(distances) if distances else 0.0
        novelty = min(1.0, avg_distance / self.config.novelty_distance_threshold)
        
        # 添加到历史记录
        self.population_history.append(code)
        if len(self.population_history) > self.config.novelty_population_size * 2:
            self.population_history = self.population_history[-self.config.novelty_population_size:]
        
        logger.debug(f"新颖度计算: 平均距离={avg_distance:.3f}, 分数={novelty:.3f}")
        return novelty
    
    def _code_distance(self, code1: str, code2: str) -> float:
        """计算两段代码的距离
        
        Args:
            code1: 代码1
            code2: 代码2
            
        Returns:
            距离值 [0, 1]
        """
        try:
            # 简化版编辑距离
            lines1 = set(line.strip() for line in code1.split('\n') if line.strip())
            lines2 = set(line.strip() for line in code2.split('\n') if line.strip())
            
            if not lines1 and not lines2:
                return 0.0
            
            intersection = len(lines1 & lines2)
            union = len(lines1 | lines2)
            
            if union == 0:
                return 0.0
            
            jaccard_similarity = intersection / union
            distance = 1.0 - jaccard_similarity
            
            return distance
            
        except Exception as e:
            logger.debug(f"代码距离计算失败: {e}")
            return 0.5
    
    def _evaluate_coverage(self, test_results: Dict[str, Any]) -> float:
        """评估测试覆盖率
        
        Args:
            test_results: 测试结果
            
        Returns:
            覆盖率分数 [0, 1]
        """
        coverage = test_results.get("coverage", 0.0)
        if isinstance(coverage, (int, float)):
            coverage_score = min(1.0, coverage / 100.0)  # 假设覆盖率是百分比
        else:
            coverage_score = 0.0
        
        logger.debug(f"覆盖率计算: 覆盖率={coverage}%, 分数={coverage_score:.3f}")
        return coverage_score
    
    def _evaluate_stability(self, execution_stats: Dict[str, Any]) -> float:
        """评估稳定性
        
        Args:
            execution_stats: 执行统计
            
        Returns:
            稳定性分数 [0, 1]
        """
        # 基于执行是否超时或出错来评估稳定性
        timed_out = execution_stats.get("timed_out", False)
        exit_code = execution_stats.get("exit_code", 0)
        
        if timed_out:
            stability = 0.0
        elif exit_code != 0:
            stability = 0.3  # 部分稳定性
        else:
            stability = 1.0
        
        logger.debug(f"稳定性计算: 超时={timed_out}, 退出码={exit_code}, 分数={stability:.3f}")
        return stability
    
    def _evaluate_efficiency(self, execution_stats: Dict[str, Any]) -> float:
        """评估效率
        
        Args:
            execution_stats: 执行统计
            
        Returns:
            效率分数 [0, 1]
        """
        # 综合时间和内存效率
        duration = execution_stats.get("duration_sec", float('inf'))
        memory = execution_stats.get("max_memory_bytes", float('inf'))
        
        time_efficiency = self._evaluate_performance({"duration_sec": duration})
        memory_efficiency = self._evaluate_memory({"max_memory_bytes": memory})
        
        efficiency = (time_efficiency + memory_efficiency) / 2
        
        logger.debug(f"效率计算: 时间效率={time_efficiency:.3f}, 内存效率={memory_efficiency:.3f}, 综合效率={efficiency:.3f}")
        return efficiency
    
    def _evaluate_maintainability(self, code: str) -> float:
        """评估可维护性
        
        Args:
            code: 代码字符串
            
        Returns:
            可维护性分数 [0, 1]
        """
        # 综合复杂度和可读性
        complexity_score = self._evaluate_complexity(code)
        readability_score = self._evaluate_readability(code)
        
        maintainability = (complexity_score + readability_score) / 2
        
        logger.debug(f"可维护性计算: 复杂度分数={complexity_score:.3f}, 可读性分数={readability_score:.3f}, 可维护性={maintainability:.3f}")
        return maintainability
    
    def compare_individuals(self, metrics1: FitnessMetrics, metrics2: FitnessMetrics) -> int:
        """比较两个个体的适应度
        
        Args:
            metrics1: 个体1的适应度指标
            metrics2: 个体2的适应度指标
            
        Returns:
            1 if metrics1 > metrics2, -1 if metrics1 < metrics2, 0 if equal
        """
        score1 = metrics1.weighted_score(self.config.weights)
        score2 = metrics2.weighted_score(self.config.weights)
        
        if score1 > score2:
            return 1
        elif score1 < score2:
            return -1
        else:
            return 0
    
    def get_pareto_front(self, population_metrics: List[FitnessMetrics]) -> List[int]:
        """获取帕累托前沿
        
        Args:
            population_metrics: 种群适应度指标列表
            
        Returns:
            帕累托前沿个体的索引列表
        """
        logger.debug(f"计算帕累托前沿，种群大小: {len(population_metrics)}")
        
        pareto_front = []
        
        for i, metrics1 in enumerate(population_metrics):
            is_dominated = False
            
            for j, metrics2 in enumerate(population_metrics):
                if i != j and self._dominates(metrics2, metrics1):
                    is_dominated = True
                    break
            
            if not is_dominated:
                pareto_front.append(i)
        
        logger.debug(f"帕累托前沿包含 {len(pareto_front)} 个个体")
        return pareto_front
    
    def _dominates(self, metrics1: FitnessMetrics, metrics2: FitnessMetrics) -> bool:
        """判断metrics1是否支配metrics2
        
        Args:
            metrics1: 适应度指标1
            metrics2: 适应度指标2
            
        Returns:
            是否支配
        """
        objectives = ["correctness", "performance", "memory", "readability", "novelty", 
                     "coverage", "stability", "efficiency", "maintainability"]
        
        at_least_one_better = False
        
        for obj in objectives:
            value1 = getattr(metrics1, obj)
            value2 = getattr(metrics2, obj)
            
            if obj == "complexity":  # 复杂度越低越好
                if value1 > value2:  # metrics1的复杂度更高，更差
                    return False
                elif value1 < value2:  # metrics1的复杂度更低，更好
                    at_least_one_better = True
            else:  # 其他指标越高越好
                if value1 < value2:
                    return False
                elif value1 > value2:
                    at_least_one_better = True
        
        return at_least_one_better

# 工具函数
def create_default_evaluator() -> FitnessEvaluator:
    """创建默认的适应度评估器
    
    Returns:
        配置好的适应度评估器
    """
    logger.debug("创建默认适应度评估器")
    return FitnessEvaluator()

def evaluate_population(evaluator: FitnessEvaluator, 
                       population_data: List[Dict[str, Any]]) -> List[FitnessMetrics]:
    """评估整个种群的适应度
    
    Args:
        evaluator: 适应度评估器
        population_data: 种群数据列表，每个元素包含code, test_results, execution_stats
        
    Returns:
        种群适应度指标列表
    """
    logger.debug(f"开始评估种群适应度，种群大小: {len(population_data)}")
    
    metrics_list = []
    
    for i, individual_data in enumerate(population_data):
        logger.debug(f"评估个体 {i+1}/{len(population_data)}")
        
        code = individual_data.get("code", "")
        test_results = individual_data.get("test_results", {})
        execution_stats = individual_data.get("execution_stats", {})
        
        metrics = evaluator.evaluate(code, test_results, execution_stats)
        metrics_list.append(metrics)
    
    logger.debug(f"种群适应度评估完成，共评估 {len(metrics_list)} 个个体")
    return metrics_list