"""距离度量模块 - 实现各种距离计算算法

本模块实现了多种距离度量方法:
- AST树编辑距离
- 代码编辑距离(Levenshtein)
- 行为距离(输出差异)
- 语义距离(执行轨迹)
- 结构距离(语法特征)
"""

import ast
import logging
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum
import difflib
import hashlib
import re

from .genome import Genome, GeneNode, NodeType

logger = logging.getLogger(__name__)

class DistanceType(Enum):
    """距离类型枚举"""
    AST_EDIT = "ast_edit"  # AST编辑距离
    CODE_EDIT = "code_edit"  # 代码编辑距离
    BEHAVIORAL = "behavioral"  # 行为距离
    SEMANTIC = "semantic"  # 语义距离
    STRUCTURAL = "structural"  # 结构距离
    HAMMING = "hamming"  # 汉明距离
    JACCARD = "jaccard"  # Jaccard距离

@dataclass
class DistanceConfig:
    """距离计算配置"""
    # 权重配置
    ast_weight: float = 0.4
    code_weight: float = 0.3
    behavioral_weight: float = 0.2
    structural_weight: float = 0.1
    
    # AST距离参数
    node_insert_cost: float = 1.0
    node_delete_cost: float = 1.0
    node_replace_cost: float = 1.0
    
    # 行为距离参数
    output_diff_weight: float = 0.6
    execution_time_weight: float = 0.2
    memory_usage_weight: float = 0.2
    
    # 结构距离参数
    complexity_weight: float = 0.3
    depth_weight: float = 0.3
    node_count_weight: float = 0.2
    operator_weight: float = 0.2
    
    # 缓存配置
    enable_cache: bool = True
    cache_size: int = 1000

class ASTDistanceCalculator:
    """AST距离计算器 - 计算抽象语法树之间的编辑距离"""
    
    def __init__(self, config: DistanceConfig):
        """初始化AST距离计算器
        
        Args:
            config: 距离配置
        """
        self.config = config
        self.cache = {} if config.enable_cache else None
        logger.debug("初始化AST距离计算器")
    
    def calculate(self, genome1: Genome, genome2: Genome) -> float:
        """计算两个基因组的AST编辑距离
        
        Args:
            genome1: 基因组1
            genome2: 基因组2
            
        Returns:
            AST编辑距离
        """
        logger.debug("计算AST编辑距离")
        
        # 检查缓存
        if self.cache is not None:
            cache_key = self._get_cache_key(genome1, genome2)
            if cache_key in self.cache:
                logger.debug("使用缓存的AST距离")
                return self.cache[cache_key]
        
        # 计算树编辑距离
        distance = self._tree_edit_distance(genome1.root, genome2.root)
        
        # 归一化
        max_nodes = max(genome1.root.count_nodes(), genome2.root.count_nodes())
        normalized_distance = distance / max_nodes if max_nodes > 0 else 0.0
        
        # 缓存结果
        if self.cache is not None and len(self.cache) < self.config.cache_size:
            self.cache[cache_key] = normalized_distance
        
        logger.debug(f"AST编辑距离: {normalized_distance}")
        return normalized_distance
    
    def _tree_edit_distance(self, tree1: GeneNode, tree2: GeneNode) -> float:
        """计算树编辑距离
        
        Args:
            tree1: 树1的根节点
            tree2: 树2的根节点
            
        Returns:
            编辑距离
        """
        # 使用动态规划计算树编辑距离
        # 这是一个简化版本，实际的树编辑距离算法更复杂
        
        if tree1 is None and tree2 is None:
            return 0.0
        if tree1 is None:
            return self._tree_size(tree2) * self.config.node_insert_cost
        if tree2 is None:
            return self._tree_size(tree1) * self.config.node_delete_cost
        
        # 节点替换成本
        replace_cost = 0.0 if self._nodes_equal(tree1, tree2) else self.config.node_replace_cost
        
        # 递归计算子树距离
        children_distance = self._calculate_children_distance(tree1.children, tree2.children)
        
        return replace_cost + children_distance
    
    def _calculate_children_distance(self, children1: List[GeneNode], 
                                   children2: List[GeneNode]) -> float:
        """计算子节点列表的距离
        
        Args:
            children1: 子节点列表1
            children2: 子节点列表2
            
        Returns:
            子节点距离
        """
        len1, len2 = len(children1), len(children2)
        
        # 动态规划矩阵
        dp = [[0.0] * (len2 + 1) for _ in range(len1 + 1)]
        
        # 初始化边界
        for i in range(len1 + 1):
            dp[i][0] = i * self.config.node_delete_cost
        for j in range(len2 + 1):
            dp[0][j] = j * self.config.node_insert_cost
        
        # 填充DP表
        for i in range(1, len1 + 1):
            for j in range(1, len2 + 1):
                # 替换
                replace_cost = self._tree_edit_distance(children1[i-1], children2[j-1])
                
                # 插入
                insert_cost = dp[i][j-1] + self.config.node_insert_cost
                
                # 删除
                delete_cost = dp[i-1][j] + self.config.node_delete_cost
                
                dp[i][j] = min(dp[i-1][j-1] + replace_cost, insert_cost, delete_cost)
        
        return dp[len1][len2]
    
    def _tree_size(self, tree: GeneNode) -> int:
        """计算树的大小
        
        Args:
            tree: 树根节点
            
        Returns:
            节点数量
        """
        if tree is None:
            return 0
        return tree.count_nodes()
    
    def _nodes_equal(self, node1: GeneNode, node2: GeneNode) -> bool:
        """判断两个节点是否相等
        
        Args:
            node1: 节点1
            node2: 节点2
            
        Returns:
            是否相等
        """
        return (node1.node_type == node2.node_type and 
                node1.value == node2.value)
    
    def _get_cache_key(self, genome1: Genome, genome2: Genome) -> str:
        """生成缓存键
        
        Args:
            genome1: 基因组1
            genome2: 基因组2
            
        Returns:
            缓存键
        """
        code1 = genome1.to_code()
        code2 = genome2.to_code()
        
        # 使用哈希确保键的唯一性
        hash1 = hashlib.md5(code1.encode()).hexdigest()[:8]
        hash2 = hashlib.md5(code2.encode()).hexdigest()[:8]
        
        return f"{hash1}_{hash2}" if hash1 <= hash2 else f"{hash2}_{hash1}"

class CodeDistanceCalculator:
    """代码距离计算器 - 计算源代码之间的编辑距离"""
    
    def __init__(self, config: DistanceConfig):
        """初始化代码距离计算器
        
        Args:
            config: 距离配置
        """
        self.config = config
        logger.debug("初始化代码距离计算器")
    
    def calculate(self, genome1: Genome, genome2: Genome) -> float:
        """计算两个基因组的代码编辑距离
        
        Args:
            genome1: 基因组1
            genome2: 基因组2
            
        Returns:
            代码编辑距离
        """
        logger.debug("计算代码编辑距离")
        
        code1 = genome1.to_code()
        code2 = genome2.to_code()
        
        # 计算Levenshtein距离
        distance = self._levenshtein_distance(code1, code2)
        
        # 归一化
        max_length = max(len(code1), len(code2))
        normalized_distance = distance / max_length if max_length > 0 else 0.0
        
        logger.debug(f"代码编辑距离: {normalized_distance}")
        return normalized_distance
    
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """计算Levenshtein编辑距离
        
        Args:
            s1: 字符串1
            s2: 字符串2
            
        Returns:
            编辑距离
        """
        len1, len2 = len(s1), len(s2)
        
        # 动态规划矩阵
        dp = [[0] * (len2 + 1) for _ in range(len1 + 1)]
        
        # 初始化
        for i in range(len1 + 1):
            dp[i][0] = i
        for j in range(len2 + 1):
            dp[0][j] = j
        
        # 填充DP表
        for i in range(1, len1 + 1):
            for j in range(1, len2 + 1):
                if s1[i-1] == s2[j-1]:
                    dp[i][j] = dp[i-1][j-1]
                else:
                    dp[i][j] = min(
                        dp[i-1][j] + 1,    # 删除
                        dp[i][j-1] + 1,    # 插入
                        dp[i-1][j-1] + 1   # 替换
                    )
        
        return dp[len1][len2]

class BehavioralDistanceCalculator:
    """行为距离计算器 - 基于程序执行行为计算距离"""
    
    def __init__(self, config: DistanceConfig):
        """初始化行为距离计算器
        
        Args:
            config: 距离配置
        """
        self.config = config
        logger.debug("初始化行为距离计算器")
    
    def calculate(self, genome1: Genome, genome2: Genome, 
                 test_cases: Optional[List[Dict[str, Any]]] = None) -> float:
        """计算两个基因组的行为距离
        
        Args:
            genome1: 基因组1
            genome2: 基因组2
            test_cases: 测试用例列表
            
        Returns:
            行为距离
        """
        logger.debug("计算行为距离")
        
        if test_cases is None:
            test_cases = self._generate_default_test_cases()
        
        total_distance = 0.0
        valid_cases = 0
        
        for test_case in test_cases:
            try:
                # 执行两个程序
                output1 = self._execute_code(genome1, test_case)
                output2 = self._execute_code(genome2, test_case)
                
                # 计算输出差异
                output_diff = self._calculate_output_difference(output1, output2)
                total_distance += output_diff
                valid_cases += 1
                
            except Exception as e:
                logger.warning(f"测试用例执行失败: {e}")
                # 执行失败的情况下给予最大距离
                total_distance += 1.0
                valid_cases += 1
        
        # 平均距离
        average_distance = total_distance / valid_cases if valid_cases > 0 else 1.0
        
        logger.debug(f"行为距离: {average_distance}")
        return average_distance
    
    def _execute_code(self, genome: Genome, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """执行代码并获取结果
        
        Args:
            genome: 基因组
            test_case: 测试用例
            
        Returns:
            执行结果
        """
        from ..sandbox import Sandbox, SandboxResult
        import json
        import traceback
        
        logger.debug(f"[DEBUG] 开始执行代码，测试用例: {test_case}")
        
        try:
            # 获取代码和输入数据
            code = genome.to_code()
            input_data = test_case.get("input", [])
            
            logger.debug(f"[DEBUG] 生成的代码长度: {len(code)} 字符")
            logger.debug(f"[DEBUG] 输入数据: {input_data}")
            
            # 构造完整的测试代码
            test_code = f"""
import json
import sys

# 用户生成的代码
{code}

# 测试执行
try:
    input_data = {repr(input_data)}
    
    # 假设用户代码定义了一个main函数或者直接可执行
    # 这里需要根据具体的基因组结构调整
    if 'def main(' in locals() or 'def main(' in globals():
        result = main(input_data)
    else:
        # 如果没有main函数，尝试直接执行并获取结果
        result = input_data  # 默认返回输入
        
    # 输出结果为JSON格式
    output = {{
        "success": True,
        "result": result,
        "error": None
    }}
    print(json.dumps(output))
    
except Exception as e:
    error_output = {{
        "success": False,
        "result": None,
        "error": str(e)
    }}
    print(json.dumps(error_output))
    sys.exit(1)
"""
            
            logger.debug(f"[DEBUG] 完整测试代码长度: {len(test_code)} 字符")
            
            # 创建沙盒并执行
            sandbox = Sandbox(
                cpu_quota=50_000,  # 0.05 CPU
                mem_limit="256m",   # 256MB内存限制
                network_disabled=True
            )
            
            logger.debug("[DEBUG] 沙盒已创建，开始执行代码")
            
            # 执行代码，设置5秒超时
            sandbox_result: SandboxResult = sandbox.run_code(
                code=test_code,
                timeout_sec=5.0
            )
            
            logger.debug(f"[DEBUG] 沙盒执行完成: {sandbox_result.summary()}")
            logger.debug(f"[DEBUG] stdout: {sandbox_result.stdout[:200]}...")
            logger.debug(f"[DEBUG] stderr: {sandbox_result.stderr[:200]}...")
            
            # 解析执行结果
            execution_result = {
                "output": None,
                "execution_time": sandbox_result.duration_sec,
                "memory_usage": sandbox_result.max_memory_bytes or 0,
                "error": None
            }
            
            if sandbox_result.timed_out:
                execution_result["error"] = "执行超时"
                logger.debug("[DEBUG] 代码执行超时")
            elif sandbox_result.exit_code != 0:
                execution_result["error"] = f"执行失败，退出码: {sandbox_result.exit_code}"
                if sandbox_result.stderr:
                    execution_result["error"] += f", 错误信息: {sandbox_result.stderr}"
                logger.debug(f"[DEBUG] 代码执行失败: {execution_result['error']}")
            else:
                # 尝试解析JSON输出
                try:
                    output_data = json.loads(sandbox_result.stdout.strip())
                    if output_data.get("success"):
                        execution_result["output"] = output_data.get("result")
                        logger.debug(f"[DEBUG] 代码执行成功，结果: {execution_result['output']}")
                    else:
                        execution_result["error"] = output_data.get("error", "未知错误")
                        logger.debug(f"[DEBUG] 代码执行逻辑错误: {execution_result['error']}")
                except json.JSONDecodeError as e:
                    execution_result["error"] = f"输出解析失败: {str(e)}"
                    execution_result["output"] = sandbox_result.stdout  # 保留原始输出
                    logger.debug(f"[DEBUG] JSON解析失败: {str(e)}")
            
            logger.debug(f"[DEBUG] 最终执行结果: {execution_result}")
            return execution_result
            
        except Exception as e:
            logger.error(f"[DEBUG] 代码执行过程中发生异常: {str(e)}")
            logger.error(f"[DEBUG] 异常堆栈: {traceback.format_exc()}")
            
            # 返回错误结果
            return {
                "output": None,
                "execution_time": 0.0,
                "memory_usage": 0,
                "error": f"执行异常: {str(e)}"
            }
    
    def _calculate_output_difference(self, output1: Dict[str, Any], 
                                   output2: Dict[str, Any]) -> float:
        """计算输出差异
        
        Args:
            output1: 输出1
            output2: 输出2
            
        Returns:
            输出差异
        """
        # 输出值差异
        out1 = output1.get("output", [])
        out2 = output2.get("output", [])
        
        if out1 == out2:
            output_diff = 0.0
        else:
            # 计算序列差异
            if isinstance(out1, list) and isinstance(out2, list):
                output_diff = self._sequence_difference(out1, out2)
            else:
                output_diff = 1.0
        
        # 执行时间差异
        time1 = output1.get("execution_time", 0.0)
        time2 = output2.get("execution_time", 0.0)
        time_diff = abs(time1 - time2) / max(time1, time2, 0.001)
        
        # 内存使用差异
        mem1 = output1.get("memory_usage", 0.0)
        mem2 = output2.get("memory_usage", 0.0)
        mem_diff = abs(mem1 - mem2) / max(mem1, mem2, 1.0)
        
        # 加权组合
        total_diff = (self.config.output_diff_weight * output_diff +
                     self.config.execution_time_weight * time_diff +
                     self.config.memory_usage_weight * mem_diff)
        
        return min(1.0, total_diff)
    
    def _sequence_difference(self, seq1: List[Any], seq2: List[Any]) -> float:
        """计算序列差异
        
        Args:
            seq1: 序列1
            seq2: 序列2
            
        Returns:
            序列差异
        """
        if not seq1 and not seq2:
            return 0.0
        
        # 使用difflib计算相似度
        matcher = difflib.SequenceMatcher(None, seq1, seq2)
        similarity = matcher.ratio()
        
        return 1.0 - similarity
    
    def _generate_default_test_cases(self) -> List[Dict[str, Any]]:
        """生成默认测试用例
        
        Returns:
            测试用例列表
        """
        return [
            {"input": []},
            {"input": [1]},
            {"input": [3, 1, 4, 1, 5]},
            {"input": [5, 4, 3, 2, 1]},
            {"input": list(range(10))}
        ]

class StructuralDistanceCalculator:
    """结构距离计算器 - 基于代码结构特征计算距离"""
    
    def __init__(self, config: DistanceConfig):
        """初始化结构距离计算器
        
        Args:
            config: 距离配置
        """
        self.config = config
        logger.debug("初始化结构距离计算器")
    
    def calculate(self, genome1: Genome, genome2: Genome) -> float:
        """计算两个基因组的结构距离
        
        Args:
            genome1: 基因组1
            genome2: 基因组2
            
        Returns:
            结构距离
        """
        logger.debug("计算结构距离")
        
        # 提取结构特征
        features1 = self._extract_structural_features(genome1)
        features2 = self._extract_structural_features(genome2)
        
        # 计算特征差异
        distance = self._calculate_feature_distance(features1, features2)
        
        logger.debug(f"结构距离: {distance}")
        return distance
    
    def _extract_structural_features(self, genome: Genome) -> Dict[str, float]:
        """提取结构特征
        
        Args:
            genome: 基因组
            
        Returns:
            结构特征字典
        """
        complexity = genome.get_complexity()
        code = genome.to_code()
        
        # 统计各种语法元素
        node_counts = self._count_node_types(genome.root)
        operator_counts = self._count_operators(code)
        
        features = {
            "cyclomatic_complexity": complexity.get("cyclomatic", 0),
            "depth": complexity.get("depth", 0),
            "nodes": complexity.get("nodes", 0),
            "lines": complexity.get("lines", 0),
            
            # 节点类型分布
            "if_statements": node_counts.get(NodeType.IF_STMT, 0),
            "for_loops": node_counts.get(NodeType.FOR_LOOP, 0),
            "while_loops": node_counts.get(NodeType.WHILE_LOOP, 0),
            "assignments": node_counts.get(NodeType.ASSIGNMENT, 0),
            "function_calls": node_counts.get(NodeType.CALL, 0),
            "binary_ops": node_counts.get(NodeType.BINARY_OP, 0),
            "comparisons": node_counts.get(NodeType.COMPARE, 0),
            
            # 运算符分布
            "arithmetic_ops": operator_counts.get("arithmetic", 0),
            "comparison_ops": operator_counts.get("comparison", 0),
            "logical_ops": operator_counts.get("logical", 0),
        }
        
        return features
    
    def _count_node_types(self, root: GeneNode) -> Dict[NodeType, int]:
        """统计节点类型
        
        Args:
            root: 根节点
            
        Returns:
            节点类型计数
        """
        counts = {}
        
        def count_recursive(node: GeneNode):
            counts[node.node_type] = counts.get(node.node_type, 0) + 1
            for child in node.children:
                count_recursive(child)
        
        count_recursive(root)
        return counts
    
    def _count_operators(self, code: str) -> Dict[str, int]:
        """统计运算符
        
        Args:
            code: 源代码
            
        Returns:
            运算符计数
        """
        arithmetic_ops = ['+', '-', '*', '/', '//', '%', '**']
        comparison_ops = ['==', '!=', '<', '>', '<=', '>=']
        logical_ops = ['and', 'or', 'not']
        
        counts = {
            "arithmetic": sum(code.count(op) for op in arithmetic_ops),
            "comparison": sum(code.count(op) for op in comparison_ops),
            "logical": sum(code.count(op) for op in logical_ops),
        }
        
        return counts
    
    def _calculate_feature_distance(self, features1: Dict[str, float], 
                                  features2: Dict[str, float]) -> float:
        """计算特征距离
        
        Args:
            features1: 特征1
            features2: 特征2
            
        Returns:
            特征距离
        """
        total_distance = 0.0
        feature_count = 0
        
        all_features = set(features1.keys()) | set(features2.keys())
        
        for feature in all_features:
            val1 = features1.get(feature, 0.0)
            val2 = features2.get(feature, 0.0)
            
            # 归一化差异
            max_val = max(val1, val2, 1.0)
            diff = abs(val1 - val2) / max_val
            
            total_distance += diff
            feature_count += 1
        
        return total_distance / feature_count if feature_count > 0 else 0.0

class DistanceManager:
    """距离管理器 - 统一的距离计算接口"""
    
    def __init__(self, config: Optional[DistanceConfig] = None):
        """初始化距离管理器
        
        Args:
            config: 距离配置
        """
        self.config = config or DistanceConfig()
        
        # 初始化各种距离计算器
        self.ast_calculator = ASTDistanceCalculator(self.config)
        self.code_calculator = CodeDistanceCalculator(self.config)
        self.behavioral_calculator = BehavioralDistanceCalculator(self.config)
        self.structural_calculator = StructuralDistanceCalculator(self.config)
        
        logger.debug("初始化距离管理器")
    
    def calculate_distance(self, genome1: Genome, genome2: Genome, 
                         distance_type: DistanceType = DistanceType.AST_EDIT) -> float:
        """计算两个基因组之间的距离
        
        Args:
            genome1: 基因组1
            genome2: 基因组2
            distance_type: 距离类型
            
        Returns:
            距离值
        """
        logger.debug(f"计算距离，类型: {distance_type}")
        
        if distance_type == DistanceType.AST_EDIT:
            return self.ast_calculator.calculate(genome1, genome2)
        elif distance_type == DistanceType.CODE_EDIT:
            return self.code_calculator.calculate(genome1, genome2)
        elif distance_type == DistanceType.BEHAVIORAL:
            return self.behavioral_calculator.calculate(genome1, genome2)
        elif distance_type == DistanceType.STRUCTURAL:
            return self.structural_calculator.calculate(genome1, genome2)
        else:
            logger.warning(f"未知距离类型: {distance_type}，使用AST编辑距离")
            return self.ast_calculator.calculate(genome1, genome2)
    
    def calculate_combined_distance(self, genome1: Genome, genome2: Genome) -> float:
        """计算组合距离
        
        Args:
            genome1: 基因组1
            genome2: 基因组2
            
        Returns:
            组合距离值
        """
        logger.debug("计算组合距离")
        
        # 计算各种距离
        ast_dist = self.ast_calculator.calculate(genome1, genome2)
        code_dist = self.code_calculator.calculate(genome1, genome2)
        behavioral_dist = self.behavioral_calculator.calculate(genome1, genome2)
        structural_dist = self.structural_calculator.calculate(genome1, genome2)
        
        # 加权组合
        combined_distance = (
            self.config.ast_weight * ast_dist +
            self.config.code_weight * code_dist +
            self.config.behavioral_weight * behavioral_dist +
            self.config.structural_weight * structural_dist
        )
        
        logger.debug(f"组合距离: {combined_distance}")
        return combined_distance
    
    def calculate_diversity_score(self, genome: Genome, 
                                population: List[Genome]) -> float:
        """计算个体在种群中的多样性分数
        
        Args:
            genome: 目标基因组
            population: 种群
            
        Returns:
            多样性分数
        """
        logger.debug("计算多样性分数")
        
        if not population:
            return 1.0
        
        total_distance = 0.0
        for other_genome in population:
            if other_genome is not genome:
                distance = self.calculate_combined_distance(genome, other_genome)
                total_distance += distance
        
        # 平均距离作为多样性分数
        diversity_score = total_distance / len(population) if population else 0.0
        
        logger.debug(f"多样性分数: {diversity_score}")
        return diversity_score

# 便利函数
def calculate_genome_distance(genome1: Genome, genome2: Genome, 
                            distance_type: DistanceType = DistanceType.AST_EDIT,
                            config: Optional[DistanceConfig] = None) -> float:
    """计算基因组距离
    
    Args:
        genome1: 基因组1
        genome2: 基因组2
        distance_type: 距离类型
        config: 距离配置
        
    Returns:
        距离值
    """
    manager = DistanceManager(config)
    return manager.calculate_distance(genome1, genome2, distance_type)

def calculate_population_diversity(population: List[Genome],
                                 config: Optional[DistanceConfig] = None) -> float:
    """计算种群多样性
    
    Args:
        population: 种群
        config: 距离配置
        
    Returns:
        种群多样性分数
    """
    if len(population) < 2:
        return 0.0
    
    manager = DistanceManager(config)
    total_diversity = 0.0
    
    for i, genome in enumerate(population):
        others = population[:i] + population[i+1:]
        diversity = manager.calculate_diversity_score(genome, others)
        total_diversity += diversity
    
    return total_diversity / len(population)