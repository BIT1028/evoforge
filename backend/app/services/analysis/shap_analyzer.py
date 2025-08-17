#!/usr/bin/env python3
"""
SHAP值分析模块 - 解释基因对适应度的贡献

本模块实现了基于SHAP（SHapley Additive exPlanations）的可解释性分析，
用于理解基因组中不同基因片段对最终适应度分数的贡献程度。
"""

import numpy as np
import json
import logging
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from itertools import combinations
import asyncio
from concurrent.futures import ThreadPoolExecutor

# from app.models.digital_cell import DigitalCell  # 使用类型提示避免导入错误
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.models.digital_cell import DigitalCell
from app.services.evolution.genome import Genome, GeneNode, NodeType

logger = logging.getLogger(__name__)

@dataclass
class ShapValue:
    """SHAP值数据结构"""
    feature_name: str
    shap_value: float
    feature_value: Any
    base_value: float
    contribution_percentage: float

@dataclass
class ShapExplanation:
    """SHAP解释结果"""
    cell_id: str
    fitness_score: float
    base_value: float  # 基准值（所有特征的平均贡献）
    shap_values: List[ShapValue]
    feature_importance: Dict[str, float]
    explanation_text: str

class GenomeFeatureExtractor:
    """基因组特征提取器
    
    从基因组中提取可用于SHAP分析的特征
    """
    
    def __init__(self):
        """初始化特征提取器"""
        self.feature_names = [
            'ast_depth',           # AST深度
            'node_count',          # 节点总数
            'cyclomatic_complexity', # 圈复杂度
            'assignment_count',    # 赋值语句数量
            'if_stmt_count',       # 条件语句数量
            'loop_count',          # 循环语句数量
            'function_call_count', # 函数调用数量
            'binary_op_count',     # 二元运算数量
            'compare_count',       # 比较运算数量
            'constant_count',      # 常量数量
            'variable_count',      # 变量数量
            'return_stmt_count',   # 返回语句数量
            'list_usage_count',    # 列表使用数量
            'subscript_count',     # 下标访问数量
        ]
        logger.debug(f"初始化特征提取器，共 {len(self.feature_names)} 个特征")
        
    def extract_features(self, genome: Genome) -> Dict[str, float]:
        """从基因组中提取特征
        
        Args:
            genome: 基因组对象
            
        Returns:
            Dict[str, float]: 特征字典
        """
        logger.debug(f"开始提取基因组特征: {genome.function_name}")
        
        features = {name: 0.0 for name in self.feature_names}
        
        try:
            # 计算复杂度指标
            complexity = genome.get_complexity()
            features['ast_depth'] = float(complexity.get('depth', 0))
            features['node_count'] = float(complexity.get('nodes', 0))
            features['cyclomatic_complexity'] = float(complexity.get('cyclomatic', 0))
            
            logger.debug(f"复杂度指标: depth={features['ast_depth']}, nodes={features['node_count']}, cyclomatic={features['cyclomatic_complexity']}")
            
            # 递归统计节点类型
            node_counts = self._count_node_types(genome.root)
            logger.debug(f"节点类型统计: {node_counts}")
            
            features['assignment_count'] = float(node_counts.get(NodeType.ASSIGNMENT, 0))
            features['if_stmt_count'] = float(node_counts.get(NodeType.IF_STMT, 0))
            features['loop_count'] = float(
                node_counts.get(NodeType.FOR_LOOP, 0) + 
                node_counts.get(NodeType.WHILE_LOOP, 0)
            )
            features['function_call_count'] = float(node_counts.get(NodeType.CALL, 0))
            features['binary_op_count'] = float(node_counts.get(NodeType.BINARY_OP, 0))
            features['compare_count'] = float(node_counts.get(NodeType.COMPARE, 0))
            features['constant_count'] = float(node_counts.get(NodeType.CONSTANT, 0))
            features['variable_count'] = float(node_counts.get(NodeType.NAME, 0))
            features['return_stmt_count'] = float(node_counts.get(NodeType.RETURN_STMT, 0))
            features['list_usage_count'] = float(node_counts.get(NodeType.LIST, 0))
            features['subscript_count'] = float(node_counts.get(NodeType.SUBSCRIPT, 0))
            
            logger.debug(f"提取的特征: {features}")
            return features
            
        except Exception as e:
            logger.error(f"特征提取失败: {e}")
            logger.debug(f"返回默认特征值: {features}")
            return features
    
    def _count_node_types(self, node: GeneNode) -> Dict[NodeType, int]:
        """递归统计节点类型数量
        
        Args:
            node: 基因节点
            
        Returns:
            Dict[NodeType, int]: 节点类型计数
        """
        logger.debug(f"统计节点类型: {node.node_type}")
        counts = {node.node_type: 1}
        
        for child in node.children:
            child_counts = self._count_node_types(child)
            for node_type, count in child_counts.items():
                counts[node_type] = counts.get(node_type, 0) + count
        
        logger.debug(f"节点 {node.node_type} 的子树统计: {counts}")
        return counts

class ShapAnalyzer:
    """SHAP值分析器
    
    实现基于Shapley值的特征重要性分析
    """
    
    def __init__(self, max_workers: int = 4):
        """初始化SHAP分析器
        
        Args:
            max_workers: 最大工作线程数
        """
        self.feature_extractor = GenomeFeatureExtractor()
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        logger.info(f"初始化SHAP分析器，最大工作线程数: {max_workers}")
        
    async def analyze_cell(self, cell: Any, 
                          reference_cells: List[Any] = None) -> ShapExplanation:
        """分析单个细胞的SHAP值
        
        Args:
            cell: 要分析的细胞
            reference_cells: 参考细胞集合（用于计算基准值）
            
        Returns:
            ShapExplanation: SHAP解释结果
        """
        logger.info(f"开始SHAP分析: 细胞ID {cell.id}")
        
        try:
            # 解析基因组
            logger.debug(f"解析细胞基因组: {type(cell.genome)}")
            if isinstance(cell.genome, str):
                genome_data = json.loads(cell.genome)
                genome = Genome.from_dict(genome_data)
            else:
                genome = cell.genome
            
            logger.debug(f"基因组解析成功: {genome.function_name}")
            
            # 提取特征
            features = self.feature_extractor.extract_features(genome)
            logger.debug(f"特征提取完成: {len(features)} 个特征")
            
            # 计算基准值
            base_value = await self._calculate_base_value(reference_cells)
            logger.debug(f"基准值计算完成: {base_value}")
            
            # 计算SHAP值
            shap_values = await self._calculate_shap_values(features, genome)
            logger.debug(f"SHAP值计算完成: {len(shap_values)} 个值")
            
            # 计算特征重要性
            feature_importance = self._calculate_feature_importance(shap_values)
            logger.debug(f"特征重要性计算完成: {len(feature_importance)} 个特征")
            
            # 生成解释文本
            explanation_text = self._generate_explanation(shap_values, cell.fitness_score or 0.0)
            logger.debug(f"解释文本生成完成: {len(explanation_text)} 字符")
            
            explanation = ShapExplanation(
                cell_id=str(cell.id),
                fitness_score=cell.fitness_score or 0.0,
                base_value=base_value,
                shap_values=shap_values,
                feature_importance=feature_importance,
                explanation_text=explanation_text
            )
            
            logger.info(f"SHAP分析完成: 细胞ID {cell.id}，适应度 {cell.fitness_score}")
            return explanation
            
        except Exception as e:
            logger.error(f"SHAP分析失败: {e}")
            logger.debug(f"异常详情: {type(e).__name__}: {str(e)}")
            # 返回默认解释
            return ShapExplanation(
                cell_id=str(cell.id),
                fitness_score=cell.fitness_score or 0.0,
                base_value=0.0,
                shap_values=[],
                feature_importance={},
                explanation_text=f"分析失败: {e}"
            )
    
    async def _calculate_base_value(self, reference_cells: List[Any] = None) -> float:
        """计算基准值（平均适应度）
        
        Args:
            reference_cells: 参考细胞集合
            
        Returns:
            float: 基准值
        """
        if not reference_cells:
            logger.debug("没有参考细胞，基准值设为0.0")
            return 0.0
        
        fitness_scores = [cell.fitness_score or 0.0 for cell in reference_cells]
        base_value = np.mean(fitness_scores)
        
        logger.debug(f"计算基准值: {len(fitness_scores)} 个细胞，平均适应度 {base_value}")
        return base_value
    
    async def _calculate_shap_values(self, features: Dict[str, float], 
                                   genome: Genome) -> List[ShapValue]:
        """计算SHAP值
        
        使用近似算法计算每个特征的Shapley值
        
        Args:
            features: 特征字典
            genome: 基因组对象
            
        Returns:
            List[ShapValue]: SHAP值列表
        """
        logger.debug("开始计算SHAP值")
        
        shap_values = []
        feature_names = list(features.keys())
        n_features = len(feature_names)
        
        logger.debug(f"特征数量: {n_features}")
        
        # 获取完整模型的预测值
        full_prediction = await self._predict_fitness(features, genome)
        logger.debug(f"完整模型预测值: {full_prediction}")
        
        # 计算每个特征的边际贡献
        for i, feature_name in enumerate(feature_names):
            logger.debug(f"计算特征 {feature_name} 的SHAP值 ({i+1}/{n_features})")
            
            marginal_contributions = []
            
            # 对所有可能的特征子集计算边际贡献
            for subset_size in range(min(n_features, 5)):  # 限制子集大小以提高性能
                # 限制计算复杂度，只采样部分子集
                max_subsets = min(5, len(list(combinations(range(n_features), subset_size))))
                sampled_subsets = list(combinations(range(n_features), subset_size))[:max_subsets]
                
                logger.debug(f"子集大小 {subset_size}，采样 {len(sampled_subsets)} 个子集")
                
                for subset_indices in sampled_subsets:
                    if i in subset_indices:
                        continue
                    
                    # 不包含当前特征的子集
                    subset_without = {feature_names[j]: features[feature_names[j]] 
                                    for j in subset_indices}
                    
                    # 包含当前特征的子集
                    subset_with = subset_without.copy()
                    subset_with[feature_name] = features[feature_name]
                    
                    # 计算边际贡献
                    pred_without = await self._predict_fitness(subset_without, genome)
                    pred_with = await self._predict_fitness(subset_with, genome)
                    
                    marginal_contribution = pred_with - pred_without
                    marginal_contributions.append(marginal_contribution)
                    
                    logger.debug(f"边际贡献: {marginal_contribution} (without: {pred_without}, with: {pred_with})")
            
            # 计算平均边际贡献作为SHAP值
            shap_value = np.mean(marginal_contributions) if marginal_contributions else 0.0
            
            # 计算贡献百分比
            total_contribution = abs(full_prediction)
            contribution_percentage = (abs(shap_value) / total_contribution * 100) if total_contribution > 0 else 0.0
            
            logger.debug(f"特征 {feature_name} SHAP值: {shap_value}, 贡献百分比: {contribution_percentage}%")
            
            shap_values.append(ShapValue(
                feature_name=feature_name,
                shap_value=shap_value,
                feature_value=features[feature_name],
                base_value=0.0,  # 简化处理
                contribution_percentage=contribution_percentage
            ))
        
        logger.debug(f"SHAP值计算完成，共 {len(shap_values)} 个特征")
        return shap_values
    
    async def _predict_fitness(self, features: Dict[str, float], 
                             genome: Genome) -> float:
        """基于特征预测适应度
        
        这是一个简化的预测模型，实际应用中可以使用更复杂的机器学习模型
        
        Args:
            features: 特征字典
            genome: 基因组对象
            
        Returns:
            float: 预测的适应度分数
        """
        try:
            logger.debug(f"预测适应度，特征数量: {len(features)}")
            
            # 简化的线性模型权重（基于经验设定）
            weights = {
                'ast_depth': -0.1,           # 深度过大降低适应度
                'node_count': 0.05,          # 适量节点提高适应度
                'cyclomatic_complexity': -0.2, # 复杂度过高降低适应度
                'assignment_count': 0.1,     # 赋值语句有助于功能实现
                'if_stmt_count': 0.15,       # 条件语句增加逻辑复杂性
                'loop_count': 0.2,           # 循环对排序算法重要
                'function_call_count': 0.1,  # 函数调用增加功能性
                'binary_op_count': 0.05,     # 运算操作基础重要
                'compare_count': 0.25,       # 比较操作对排序关键
                'constant_count': 0.02,      # 常量使用适度有益
                'variable_count': 0.03,      # 变量使用适度有益
                'return_stmt_count': 0.3,    # 返回语句对函数完整性重要
                'list_usage_count': 0.2,     # 列表操作对排序重要
                'subscript_count': 0.15,     # 下标访问对数组操作重要
            }
            
            # 计算加权分数
            score = 0.0
            for feature_name, value in features.items():
                weight = weights.get(feature_name, 0.0)
                contribution = weight * value
                score += contribution
                logger.debug(f"特征 {feature_name}: 值={value}, 权重={weight}, 贡献={contribution}")
            
            logger.debug(f"基础加权分数: {score}")
            
            # 添加非线性调整
            # 惩罚过度复杂的代码
            if features.get('cyclomatic_complexity', 0) > 10:
                score *= 0.5
                logger.debug(f"复杂度惩罚后分数: {score}")
            
            # 奖励平衡的代码结构
            if (features.get('loop_count', 0) > 0 and 
                features.get('compare_count', 0) > 0 and 
                features.get('return_stmt_count', 0) > 0):
                score *= 1.2
                logger.debug(f"平衡结构奖励后分数: {score}")
            
            # 确保分数在合理范围内
            score = max(0.0, min(100.0, score))
            
            logger.debug(f"最终预测适应度: {score}")
            return score
            
        except Exception as e:
            logger.error(f"适应度预测失败: {e}")
            return 0.0
    
    def _calculate_feature_importance(self, shap_values: List[ShapValue]) -> Dict[str, float]:
        """计算特征重要性
        
        Args:
            shap_values: SHAP值列表
            
        Returns:
            Dict[str, float]: 特征重要性字典
        """
        logger.debug("计算特征重要性")
        
        importance = {}
        total_abs_shap = sum(abs(sv.shap_value) for sv in shap_values)
        
        logger.debug(f"总SHAP值绝对值: {total_abs_shap}")
        
        for shap_value in shap_values:
            if total_abs_shap > 0:
                importance[shap_value.feature_name] = abs(shap_value.shap_value) / total_abs_shap
            else:
                importance[shap_value.feature_name] = 0.0
            
            logger.debug(f"特征 {shap_value.feature_name} 重要性: {importance[shap_value.feature_name]}")
        
        return importance
    
    def _generate_explanation(self, shap_values: List[ShapValue], 
                            fitness_score: float) -> str:
        """生成人类可读的解释文本
        
        Args:
            shap_values: SHAP值列表
            fitness_score: 适应度分数
            
        Returns:
            str: 解释文本
        """
        logger.debug("生成解释文本")
        
        # 按贡献度排序
        sorted_shaps = sorted(shap_values, key=lambda x: abs(x.shap_value), reverse=True)
        
        explanation_parts = [
            f"该基因组的适应度分数为 {fitness_score:.2f}。",
            "\n主要贡献因素："
        ]
        
        # 显示前5个最重要的特征
        for i, shap_value in enumerate(sorted_shaps[:5]):
            if abs(shap_value.shap_value) < 0.01:
                continue
                
            direction = "正向" if shap_value.shap_value > 0 else "负向"
            feature_desc = self._get_feature_description(shap_value.feature_name)
            
            explanation_parts.append(
                f"{i+1}. {feature_desc}（值: {shap_value.feature_value:.1f}）"
                f"对适应度有{direction}贡献 {abs(shap_value.shap_value):.3f} "
                f"({shap_value.contribution_percentage:.1f}%）"
            )
        
        explanation_text = "\n".join(explanation_parts)
        logger.debug(f"解释文本生成完成: {len(explanation_text)} 字符")
        return explanation_text
    
    def _get_feature_description(self, feature_name: str) -> str:
        """获取特征的中文描述
        
        Args:
            feature_name: 特征名称
            
        Returns:
            str: 中文描述
        """
        descriptions = {
            'ast_depth': 'AST深度',
            'node_count': '节点总数',
            'cyclomatic_complexity': '圈复杂度',
            'assignment_count': '赋值语句数量',
            'if_stmt_count': '条件语句数量',
            'loop_count': '循环语句数量',
            'function_call_count': '函数调用数量',
            'binary_op_count': '二元运算数量',
            'compare_count': '比较运算数量',
            'constant_count': '常量数量',
            'variable_count': '变量数量',
            'return_stmt_count': '返回语句数量',
            'list_usage_count': '列表使用数量',
            'subscript_count': '下标访问数量',
        }
        return descriptions.get(feature_name, feature_name)
    
    async def analyze_population(self, cells: List[Any]) -> List[ShapExplanation]:
        """分析整个种群的SHAP值
        
        Args:
            cells: 细胞列表
            
        Returns:
            List[ShapExplanation]: SHAP解释结果列表
        """
        logger.info(f"开始种群SHAP分析，共 {len(cells)} 个细胞")
        
        explanations = []
        
        # 并行分析所有细胞
        tasks = []
        for cell in cells:
            task = self.analyze_cell(cell, cells)  # 使用整个种群作为参考
            tasks.append(task)
        
        logger.debug(f"创建 {len(tasks)} 个分析任务")
        
        explanations = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 过滤异常结果
        valid_explanations = []
        for explanation in explanations:
            if isinstance(explanation, ShapExplanation):
                valid_explanations.append(explanation)
            else:
                logger.error(f"SHAP分析异常: {explanation}")
        
        logger.info(f"种群SHAP分析完成，成功分析 {len(valid_explanations)} 个细胞")
        return valid_explanations
    
    def get_population_insights(self, explanations: List[ShapExplanation]) -> Dict[str, Any]:
        """获取种群级别的洞察
        
        Args:
            explanations: SHAP解释结果列表
            
        Returns:
            Dict[str, Any]: 种群洞察
        """
        logger.debug(f"生成种群洞察，共 {len(explanations)} 个解释")
        
        if not explanations:
            logger.warning("没有有效的解释结果")
            return {}
        
        # 计算平均特征重要性
        all_features = set()
        for explanation in explanations:
            all_features.update(explanation.feature_importance.keys())
        
        logger.debug(f"发现 {len(all_features)} 个特征")
        
        avg_importance = {}
        for feature in all_features:
            importances = [exp.feature_importance.get(feature, 0.0) for exp in explanations]
            avg_importance[feature] = np.mean(importances)
            logger.debug(f"特征 {feature} 平均重要性: {avg_importance[feature]}")
        
        # 找出最重要的特征
        top_features = sorted(avg_importance.items(), key=lambda x: x[1], reverse=True)[:5]
        logger.debug(f"前5个重要特征: {top_features}")
        
        # 计算适应度分布
        fitness_scores = [exp.fitness_score for exp in explanations]
        
        insights = {
            'population_size': len(explanations),
            'avg_fitness': np.mean(fitness_scores),
            'fitness_std': np.std(fitness_scores),
            'max_fitness': np.max(fitness_scores),
            'min_fitness': np.min(fitness_scores),
            'top_features': top_features,
            'avg_feature_importance': avg_importance,
            'analysis_summary': self._generate_population_summary(top_features, fitness_scores)
        }
        
        logger.debug(f"种群洞察生成完成: {len(insights)} 个指标")
        return insights
    
    def _generate_population_summary(self, top_features: List[Tuple[str, float]], 
                                   fitness_scores: List[float]) -> str:
        """生成种群分析摘要
        
        Args:
            top_features: 最重要特征列表
            fitness_scores: 适应度分数列表
            
        Returns:
            str: 分析摘要
        """
        logger.debug("生成种群分析摘要")
        
        summary_parts = [
            f"种群分析摘要：",
            f"- 平均适应度: {np.mean(fitness_scores):.2f}",
            f"- 适应度标准差: {np.std(fitness_scores):.2f}",
            f"- 最高适应度: {np.max(fitness_scores):.2f}",
            "\n最重要的特征（影响适应度）："
        ]
        
        for i, (feature, importance) in enumerate(top_features):
            feature_desc = self._get_feature_description(feature)
            summary_parts.append(
                f"{i+1}. {feature_desc}: {importance:.3f} ({importance*100:.1f}%)"
            )
        
        summary = "\n".join(summary_parts)
        logger.debug(f"种群分析摘要生成完成: {len(summary)} 字符")
        return summary

# 全局SHAP分析器实例
shap_analyzer = ShapAnalyzer()
logger.info("SHAP分析器模块初始化完成")

# 导出主要类和函数
__all__ = [
    'ShapValue',
    'ShapExplanation', 
    'GenomeFeatureExtractor',
    'ShapAnalyzer',
    'shap_analyzer'
]