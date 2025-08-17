"""基因表示模块 - 实现AST基因编码与代码生成

本模块实现了基于抽象语法树(AST)的基因表示，支持:
- 基因序列到AST的转换
- AST到Python代码的生成
- 语法约束和类型检查
- 代码复杂度分析
"""

import ast
import random
import logging
import time
from typing import List, Dict, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
import copy

logger = logging.getLogger(__name__)

class NodeType(Enum):
    """AST节点类型枚举"""
    FUNCTION_DEF = "function_def"
    ASSIGNMENT = "assignment"
    IF_STMT = "if_stmt"
    FOR_LOOP = "for_loop"
    WHILE_LOOP = "while_loop"
    RETURN_STMT = "return_stmt"
    EXPRESSION = "expression"
    BINARY_OP = "binary_op"
    COMPARE = "compare"
    CALL = "call"
    CONSTANT = "constant"
    NAME = "name"
    LIST = "list"
    SUBSCRIPT = "subscript"

class OperatorType(Enum):
    """运算符类型枚举"""
    # 算术运算符
    ADD = "+"
    SUB = "-"
    MULT = "*"
    DIV = "/"
    FLOOR_DIV = "//"
    MOD = "%"
    POW = "**"
    
    # 比较运算符
    EQ = "=="
    NOT_EQ = "!="
    LT = "<"
    LTE = "<="
    GT = ">"
    GTE = ">="
    IN = "in"
    NOT_IN = "not in"
    
    # 逻辑运算符
    AND = "and"
    OR = "or"
    NOT = "not"

@dataclass
class GeneNode:
    """增强的基因节点 - 表示AST中的一个节点，支持基因表达调控"""
    node_type: NodeType
    value: Any = None
    children: List['GeneNode'] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 基因表达调控属性
    expression_level: float = field(default=1.0)  # 表达水平 (0-1)
    is_active: bool = field(default=True)  # 是否激活
    regulation_factors: Dict[str, float] = field(default_factory=dict)  # 调控因子
    epigenetic_marks: List[str] = field(default_factory=list)  # 表观遗传标记
    
    # 进化属性
    mutation_rate: float = field(default=0.01)  # 变异率
    conservation_score: float = field(default=0.5)  # 保守性评分
    fitness_contribution: float = field(default=0.0)  # 适应度贡献
    
    def __post_init__(self):
        """初始化后处理"""
        logger.debug(f"创建增强基因节点: {self.node_type}, 值: {self.value}, 表达水平: {self.expression_level}")
        
        # 根据节点类型设置默认属性
        self._initialize_node_properties()
    
    def _initialize_node_properties(self):
        """根据节点类型初始化属性"""
        # 控制结构节点通常更保守
        if self.node_type in [NodeType.IF_STMT, NodeType.FOR_LOOP, NodeType.WHILE_LOOP]:
            self.conservation_score = 0.8
            self.mutation_rate = 0.005
        
        # 表达式节点更容易变异
        elif self.node_type in [NodeType.CONSTANT, NodeType.BINARY_OP, NodeType.COMPARE]:
            self.conservation_score = 0.3
            self.mutation_rate = 0.02
        
        # 函数调用节点中等保守
        elif self.node_type == NodeType.CALL:
            self.conservation_score = 0.6
            self.mutation_rate = 0.01
    
    def add_child(self, child: 'GeneNode') -> None:
        """添加子节点"""
        self.children.append(child)
        logger.debug(f"添加子节点: {child.node_type} 到 {self.node_type}")
        
        # 更新子节点的调控关系
        self._update_child_regulation(child)
    
    def _update_child_regulation(self, child: 'GeneNode'):
        """更新子节点的调控关系"""
        # 父节点的表达水平影响子节点
        if self.expression_level < 0.5:
            child.expression_level *= 0.8
        
        # 传递表观遗传标记
        if 'silenced' in self.epigenetic_marks:
            child.epigenetic_marks.append('inherited_silencing')
    
    def activate(self, factor: float = 1.0):
        """激活基因节点
        
        Args:
            factor: 激活因子强度
        """
        self.is_active = True
        self.expression_level = min(1.0, self.expression_level * factor)
        
        # 移除抑制性标记
        if 'silenced' in self.epigenetic_marks:
            self.epigenetic_marks.remove('silenced')
        
        logger.debug(f"激活节点 {self.node_type}, 新表达水平: {self.expression_level}")
    
    def silence(self, factor: float = 0.1):
        """沉默基因节点
        
        Args:
            factor: 沉默因子强度
        """
        self.is_active = False
        self.expression_level *= factor
        
        # 添加沉默标记
        if 'silenced' not in self.epigenetic_marks:
            self.epigenetic_marks.append('silenced')
        
        logger.debug(f"沉默节点 {self.node_type}, 新表达水平: {self.expression_level}")
    
    def add_regulation_factor(self, factor_name: str, strength: float):
        """添加调控因子
        
        Args:
            factor_name: 调控因子名称
            strength: 调控强度 (-1到1，负值为抑制，正值为激活)
        """
        self.regulation_factors[factor_name] = strength
        
        # 根据调控因子更新表达水平
        total_regulation = sum(self.regulation_factors.values())
        if total_regulation > 0:
            self.expression_level = min(1.0, self.expression_level * (1 + total_regulation * 0.1))
        else:
            self.expression_level = max(0.0, self.expression_level * (1 + total_regulation * 0.1))
    
    def get_effective_expression(self) -> float:
        """获取有效表达水平
        
        考虑激活状态、调控因子和表观遗传标记的综合影响
        
        Returns:
            float: 有效表达水平 (0-1)
        """
        if not self.is_active:
            return 0.0
        
        effective_level = self.expression_level
        
        # 应用调控因子
        for factor, strength in self.regulation_factors.items():
            if strength > 0:  # 激活因子
                effective_level *= (1 + strength * 0.2)
            else:  # 抑制因子
                effective_level *= (1 + strength * 0.3)
        
        # 应用表观遗传标记
        if 'silenced' in self.epigenetic_marks:
            effective_level *= 0.1
        if 'enhanced' in self.epigenetic_marks:
            effective_level *= 1.5
        
        return max(0.0, min(1.0, effective_level))
    
    def get_depth(self) -> int:
        """获取节点深度"""
        if not self.children:
            return 1
        return 1 + max(child.get_depth() for child in self.children)
    
    def count_nodes(self) -> int:
        """统计节点总数"""
        count = 1
        for child in self.children:
            count += child.count_nodes()
        return count
    
    def count_active_nodes(self) -> int:
        """统计活跃节点数"""
        count = 1 if self.is_active else 0
        for child in self.children:
            count += child.count_active_nodes()
        return count
    
    def find_nodes_by_type(self, node_type: NodeType) -> List['GeneNode']:
        """查找指定类型的所有节点
        
        Args:
            node_type: 要查找的节点类型
            
        Returns:
            List[GeneNode]: 匹配的节点列表
        """
        nodes = []
        if self.node_type == node_type:
            nodes.append(self)
        
        for child in self.children:
            nodes.extend(child.find_nodes_by_type(node_type))
        
        return nodes
    
    def calculate_semantic_similarity(self, other: 'GeneNode') -> float:
        """计算与另一个节点的语义相似度
        
        Args:
            other: 另一个基因节点
            
        Returns:
            float: 相似度分数 (0-1)
        """
        if self.node_type != other.node_type:
            return 0.0
        
        # 基础相似度
        similarity = 0.5
        
        # 值相似度
        if self.value == other.value:
            similarity += 0.3
        elif isinstance(self.value, (int, float)) and isinstance(other.value, (int, float)):
            # 数值相似度
            diff = abs(self.value - other.value)
            max_val = max(abs(self.value), abs(other.value), 1)
            similarity += 0.3 * (1 - min(diff / max_val, 1))
        
        # 结构相似度
        if len(self.children) == len(other.children):
            similarity += 0.2
            if self.children and other.children:
                child_similarities = [
                    c1.calculate_semantic_similarity(c2)
                    for c1, c2 in zip(self.children, other.children)
                ]
                similarity += 0.2 * (sum(child_similarities) / len(child_similarities))
        
        return min(1.0, similarity)
    
    def clone(self) -> 'GeneNode':
        """克隆节点（深拷贝）
        
        Returns:
            GeneNode: 克隆的节点
        """
        return copy.deepcopy(self)

@dataclass
class Genome:
    """增强的基因组 - 表示一个完整的程序基因，支持基因网络和智能代码生成"""
    root: GeneNode
    function_name: str = "sort_numbers"
    parameters: List[Tuple[str, str]] = field(default_factory=lambda: [("numbers", "list[int]")])
    return_type: str = "list[int]"
    
    # 基因网络属性
    gene_network: Dict[str, List[str]] = field(default_factory=dict)  # 基因调控网络
    expression_profile: Dict[str, float] = field(default_factory=dict)  # 表达谱
    regulatory_elements: List[Dict[str, Any]] = field(default_factory=list)  # 调控元件
    
    # 进化历史
    generation: int = field(default=0)  # 代数
    parent_genomes: List[str] = field(default_factory=list)  # 父代基因组ID
    mutation_history: List[Dict[str, Any]] = field(default_factory=list)  # 变异历史
    
    # 性能指标
    fitness_history: List[float] = field(default_factory=list)  # 适应度历史
    complexity_metrics: Dict[str, float] = field(default_factory=dict)  # 复杂度指标
    semantic_features: Dict[str, Any] = field(default_factory=dict)  # 语义特征
    
    def __post_init__(self):
        """初始化后处理"""
        logger.debug(f"创建增强基因组: 函数 {self.function_name}, 代数: {self.generation}")
        
        # 初始化基因网络
        self._build_gene_network()
        
        # 计算初始表达谱
        self._update_expression_profile()
        
        # 分析语义特征
        self._analyze_semantic_features()
    
    def to_code(self) -> str:
        """将基因组转换为Python代码"""
        logger.debug("开始基因组到代码转换")
        try:
            # 构建函数签名
            params = ", ".join([f"{name}: {type_}" for name, type_ in self.parameters])
            signature = f"def {self.function_name}({params}) -> {self.return_type}:"
            
            # 生成函数体
            body_lines = self._node_to_code(self.root, indent=1)
            
            # 确保有返回语句
            if not any(line.strip().startswith("return") for line in body_lines):
                body_lines.append("    return []")
            
            code = signature + "\n" + "\n".join(body_lines)
            logger.debug(f"生成代码:\n{code}")
            return code
            
        except Exception as e:
            logger.error(f"代码生成失败: {e}")
            # 返回默认实现
            return f"def {self.function_name}({', '.join([f'{name}: {type_}' for name, type_ in self.parameters])}) -> {self.return_type}:\n    return []"
    
    def _node_to_code(self, node: GeneNode, indent: int = 0) -> List[str]:
        """将节点转换为代码行"""
        indent_str = "    " * indent
        lines = []
        
        logger.debug(f"转换节点: {node.node_type}, 缩进: {indent}")
        
        try:
            if node.node_type == NodeType.ASSIGNMENT:
                target = node.value.get("target", "temp")
                expr_lines = self._node_to_code(node.children[0], 0) if node.children else ["[]"]
                expr = expr_lines[0] if expr_lines else "[]"
                lines.append(f"{indent_str}{target} = {expr}")
                
            elif node.node_type == NodeType.IF_STMT:
                condition_lines = self._node_to_code(node.children[0], 0) if node.children else ["True"]
                condition = condition_lines[0] if condition_lines else "True"
                lines.append(f"{indent_str}if {condition}:")
                
                # if体
                if len(node.children) > 1:
                    body_lines = self._node_to_code(node.children[1], indent + 1)
                    lines.extend(body_lines)
                else:
                    lines.append(f"{indent_str}    pass")
                
                # else体
                if len(node.children) > 2:
                    lines.append(f"{indent_str}else:")
                    else_lines = self._node_to_code(node.children[2], indent + 1)
                    lines.extend(else_lines)
                    
            elif node.node_type == NodeType.FOR_LOOP:
                target = node.value.get("target", "i")
                iter_lines = self._node_to_code(node.children[0], 0) if node.children else ["range(10)"]
                iter_expr = iter_lines[0] if iter_lines else "range(10)"
                lines.append(f"{indent_str}for {target} in {iter_expr}:")
                
                if len(node.children) > 1:
                    body_lines = self._node_to_code(node.children[1], indent + 1)
                    lines.extend(body_lines)
                else:
                    lines.append(f"{indent_str}    pass")
                    
            elif node.node_type == NodeType.WHILE_LOOP:
                condition_lines = self._node_to_code(node.children[0], 0) if node.children else ["False"]
                condition = condition_lines[0] if condition_lines else "False"
                lines.append(f"{indent_str}while {condition}:")
                
                if len(node.children) > 1:
                    body_lines = self._node_to_code(node.children[1], indent + 1)
                    lines.extend(body_lines)
                else:
                    lines.append(f"{indent_str}    break")
                    
            elif node.node_type == NodeType.RETURN_STMT:
                if node.children:
                    expr_lines = self._node_to_code(node.children[0], 0)
                    expr = expr_lines[0] if expr_lines else "None"
                else:
                    expr = node.value if node.value else "None"
                lines.append(f"{indent_str}return {expr}")
                
            elif node.node_type == NodeType.BINARY_OP:
                left_lines = self._node_to_code(node.children[0], 0) if len(node.children) > 0 else ["0"]
                right_lines = self._node_to_code(node.children[1], 0) if len(node.children) > 1 else ["0"]
                left = left_lines[0] if left_lines else "0"
                right = right_lines[0] if right_lines else "0"
                op = node.value if node.value else "+"
                lines.append(f"({left} {op} {right})")
                
            elif node.node_type == NodeType.COMPARE:
                left_lines = self._node_to_code(node.children[0], 0) if len(node.children) > 0 else ["0"]
                right_lines = self._node_to_code(node.children[1], 0) if len(node.children) > 1 else ["0"]
                left = left_lines[0] if left_lines else "0"
                right = right_lines[0] if right_lines else "0"
                op = node.value if node.value else "<"
                lines.append(f"({left} {op} {right})")
                
            elif node.node_type == NodeType.CALL:
                func_name = node.value if node.value else "len"
                if node.children:
                    arg_lines = []
                    for child in node.children:
                        child_lines = self._node_to_code(child, 0)
                        if child_lines:
                            arg_lines.append(child_lines[0])
                    args = ", ".join(arg_lines)
                    lines.append(f"{func_name}({args})")
                else:
                    lines.append(f"{func_name}()")
                    
            elif node.node_type == NodeType.CONSTANT:
                lines.append(str(node.value) if node.value is not None else "0")
                
            elif node.node_type == NodeType.NAME:
                lines.append(str(node.value) if node.value else "temp")
                
            elif node.node_type == NodeType.LIST:
                if node.children:
                    elem_lines = []
                    for child in node.children:
                        child_lines = self._node_to_code(child, 0)
                        if child_lines:
                            elem_lines.append(child_lines[0])
                    elements = ", ".join(elem_lines)
                    lines.append(f"[{elements}]")
                else:
                    lines.append("[]")
                    
            elif node.node_type == NodeType.SUBSCRIPT:
                obj_lines = self._node_to_code(node.children[0], 0) if len(node.children) > 0 else ["numbers"]
                index_lines = self._node_to_code(node.children[1], 0) if len(node.children) > 1 else ["0"]
                obj = obj_lines[0] if obj_lines else "numbers"
                index = index_lines[0] if index_lines else "0"
                lines.append(f"{obj}[{index}]")
                
            else:
                # 处理复合语句体
                for child in node.children:
                    child_lines = self._node_to_code(child, indent)
                    lines.extend(child_lines)
                    
        except Exception as e:
            logger.error(f"节点转换失败: {node.node_type}, 错误: {e}")
            lines.append(f"{indent_str}pass  # 转换失败: {e}")
        
        return lines
    
    def update_complexity_metrics(self):
        """更新复杂度指标"""
        complexity = self.get_complexity()
        self.complexity_metrics = {
            'cyclomatic_complexity': complexity['cyclomatic'],
            'nesting_depth': complexity['depth'],
            'node_count': complexity['nodes'],
            'estimated_lines': complexity['lines']
        }
    
    def get_complexity(self) -> Dict[str, int]:
        """计算代码复杂度指标"""
        logger.debug("计算代码复杂度")
        
        def count_complexity(node: GeneNode) -> Dict[str, int]:
            """递归计算复杂度"""
            metrics = {
                "cyclomatic": 0,
                "depth": 0,
                "nodes": 1,
                "lines": 1
            }
            
            # 圈复杂度计算
            if node.node_type in [NodeType.IF_STMT, NodeType.FOR_LOOP, NodeType.WHILE_LOOP]:
                metrics["cyclomatic"] += 1
            
            # 递归处理子节点
            max_child_depth = 0
            for child in node.children:
                child_metrics = count_complexity(child)
                metrics["cyclomatic"] += child_metrics["cyclomatic"]
                metrics["nodes"] += child_metrics["nodes"]
                metrics["lines"] += child_metrics["lines"]
                max_child_depth = max(max_child_depth, child_metrics["depth"])
            
            metrics["depth"] = max_child_depth + 1
            return metrics
        
        complexity = count_complexity(self.root)
        complexity["cyclomatic"] += 1  # 基础复杂度
        
        logger.debug(f"复杂度指标: {complexity}")
        return complexity
    
    def validate(self) -> Tuple[bool, List[str]]:
        """验证基因组的有效性"""
        logger.debug("验证基因组有效性")
        errors = []
        
        try:
            # 检查复杂度
            complexity = self.get_complexity()
            if complexity["depth"] > 6:
                errors.append(f"嵌套深度过深: {complexity['depth']} > 6")
            if complexity["cyclomatic"] > 15:
                errors.append(f"圈复杂度过高: {complexity['cyclomatic']} > 15")
            if complexity["lines"] > 50:
                errors.append(f"代码行数过多: {complexity['lines']} > 50")
            
            # 尝试生成代码并解析
            code = self.to_code()
            try:
                ast.parse(code)
            except SyntaxError as e:
                errors.append(f"语法错误: {e}")
            
            is_valid = len(errors) == 0
            logger.debug(f"验证结果: {'有效' if is_valid else '无效'}, 错误: {errors}")
            return is_valid, errors
            
        except Exception as e:
            logger.error(f"验证过程出错: {e}")
            return False, [f"验证异常: {e}"]
    
    def copy(self) -> 'Genome':
        """深拷贝基因组"""
        logger.debug("复制基因组")
        return copy.deepcopy(self)
    
    def _build_gene_network(self):
        """构建基因调控网络"""
        logger.debug("构建基因调控网络")
        
        # 遍历所有节点，建立调控关系
        def build_network_recursive(node: GeneNode, parent_id: str = None):
            node_id = f"{node.node_type.value}_{id(node)}"
            
            # 初始化网络节点
            if node_id not in self.gene_network:
                self.gene_network[node_id] = []
            
            # 建立父子调控关系
            if parent_id:
                if parent_id not in self.gene_network:
                    self.gene_network[parent_id] = []
                self.gene_network[parent_id].append(node_id)
            
            # 递归处理子节点
            for child in node.children:
                build_network_recursive(child, node_id)
        
        build_network_recursive(self.root)
        logger.debug(f"基因网络构建完成，包含 {len(self.gene_network)} 个节点")
    
    def _update_expression_profile(self):
        """更新表达谱"""
        logger.debug("更新表达谱")
        
        def update_profile_recursive(node: GeneNode):
            node_id = f"{node.node_type.value}_{id(node)}"
            
            # 计算有效表达水平
            effective_expression = node.get_effective_expression()
            self.expression_profile[node_id] = effective_expression
            
            # 递归处理子节点
            for child in node.children:
                update_profile_recursive(child)
        
        update_profile_recursive(self.root)
        logger.debug(f"表达谱更新完成，包含 {len(self.expression_profile)} 个基因")
    
    def _analyze_semantic_features(self):
        """分析语义特征"""
        logger.debug("分析语义特征")
        
        # 统计节点类型分布
        node_type_counts = {}
        operator_counts = {}
        variable_names = set()
        function_calls = set()
        
        def analyze_recursive(node: GeneNode):
            # 统计节点类型
            node_type = node.node_type.value
            node_type_counts[node_type] = node_type_counts.get(node_type, 0) + 1
            
            # 统计运算符
            if node.node_type in [NodeType.BINARY_OP, NodeType.COMPARE] and node.value:
                operator_counts[node.value] = operator_counts.get(node.value, 0) + 1
            
            # 收集变量名
            if node.node_type == NodeType.NAME and node.value:
                variable_names.add(node.value)
            
            # 收集函数调用
            if node.node_type == NodeType.CALL and node.value:
                function_calls.add(node.value)
            
            # 递归处理子节点
            for child in node.children:
                analyze_recursive(child)
        
        analyze_recursive(self.root)
        
        # 计算复杂度指标
        complexity = self.get_complexity()
        
        # 存储语义特征
        self.semantic_features = {
            'node_type_distribution': node_type_counts,
            'operator_distribution': operator_counts,
            'variable_names': list(variable_names),
            'function_calls': list(function_calls),
            'complexity_metrics': complexity,
            'total_nodes': sum(node_type_counts.values()),
            'unique_node_types': len(node_type_counts),
            'control_flow_ratio': sum(node_type_counts.get(t, 0) for t in ['if_stmt', 'for_loop', 'while_loop']) / max(sum(node_type_counts.values()), 1),
            'expression_complexity': len(operator_counts) + len(function_calls)
        }
        
        logger.debug(f"语义特征分析完成: {len(self.semantic_features)} 个特征")
     
    def get_gene_expression_level(self, node_id: str) -> float:
        """获取指定基因的表达水平"""
        return self.expression_profile.get(node_id, 0.0)
    
    def regulate_gene_expression(self, node_id: str, factor: float, regulator_type: str = "enhancer"):
        """调控基因表达"""
        if node_id in self.expression_profile:
            current_level = self.expression_profile[node_id]
            
            if regulator_type == "enhancer":
                new_level = min(1.0, current_level * (1 + factor))
            elif regulator_type == "silencer":
                new_level = max(0.0, current_level * (1 - factor))
            else:
                new_level = current_level
            
            self.expression_profile[node_id] = new_level
            
            # 记录调控事件
            self.regulatory_elements.append({
                'target': node_id,
                'factor': factor,
                'type': regulator_type,
                'timestamp': time.time()
            })
    
    def get_network_connectivity(self) -> Dict[str, float]:
        """计算基因网络连接性指标"""
        if not self.gene_network:
            return {}
        
        total_nodes = len(self.gene_network)
        connectivity_metrics = {}
        
        for node_id, connections in self.gene_network.items():
            # 出度（该节点调控的基因数量）
            out_degree = len(connections)
            
            # 入度（调控该节点的基因数量）
            in_degree = sum(1 for other_connections in self.gene_network.values() 
                          if node_id in other_connections)
            
            connectivity_metrics[node_id] = {
                'out_degree': out_degree,
                'in_degree': in_degree,
                'total_degree': out_degree + in_degree,
                'centrality': (out_degree + in_degree) / max(total_nodes - 1, 1)
            }
        
        return connectivity_metrics
    
    def find_regulatory_motifs(self) -> List[Dict[str, Any]]:
        """识别调控模式"""
        motifs = []
        
        # 查找前馈环路
        for node_a, connections_a in self.gene_network.items():
            for node_b in connections_a:
                if node_b in self.gene_network:
                    for node_c in self.gene_network[node_b]:
                        if node_c in connections_a:  # A->B->C 且 A->C
                            motifs.append({
                                'type': 'feedforward_loop',
                                'nodes': [node_a, node_b, node_c],
                                'description': f'前馈环路: {node_a} -> {node_b} -> {node_c}, {node_a} -> {node_c}'
                            })
        
        # 查找反馈环路
        for node_a, connections_a in self.gene_network.items():
            for node_b in connections_a:
                if node_b in self.gene_network and node_a in self.gene_network[node_b]:
                    motifs.append({
                        'type': 'feedback_loop',
                        'nodes': [node_a, node_b],
                        'description': f'反馈环路: {node_a} <-> {node_b}'
                    })
        
        return motifs
    
    def optimize_expression_profile(self):
        """优化表达谱以提高适应度"""
        logger.debug("优化表达谱")
        
        # 基于节点重要性调整表达水平
        connectivity = self.get_network_connectivity()
        
        for node_id, metrics in connectivity.items():
            if node_id in self.expression_profile:
                # 高连接性节点提高表达水平
                centrality = metrics['centrality']
                current_expression = self.expression_profile[node_id]
                
                # 根据中心性调整表达水平
                adjustment_factor = 0.1 * centrality
                new_expression = min(1.0, current_expression + adjustment_factor)
                
                self.expression_profile[node_id] = new_expression
        
        logger.debug("表达谱优化完成")
    
    def generate_intelligent_code(self, optimization_target: str = "efficiency") -> str:
        """基于基因表达谱生成智能优化的代码"""
        logger.debug(f"生成智能代码，优化目标: {optimization_target}")
        
        # 根据优化目标调整表达谱
        if optimization_target == "efficiency":
            self._optimize_for_efficiency()
        elif optimization_target == "readability":
            self._optimize_for_readability()
        elif optimization_target == "robustness":
            self._optimize_for_robustness()
        
        # 生成优化后的代码
        return self.to_code()
    
    def _optimize_for_efficiency(self):
        """为效率优化表达谱"""
        # 提高循环和条件语句的表达水平
        for node_id, expression_level in self.expression_profile.items():
            if any(keyword in node_id.lower() for keyword in ['for', 'while', 'if']):
                self.expression_profile[node_id] = min(1.0, expression_level * 1.2)
    
    def _optimize_for_readability(self):
        """为可读性优化表达谱"""
        # 平衡各节点的表达水平
        avg_expression = sum(self.expression_profile.values()) / len(self.expression_profile)
        for node_id in self.expression_profile:
            current = self.expression_profile[node_id]
            self.expression_profile[node_id] = (current + avg_expression) / 2
    
    def _optimize_for_robustness(self):
        """为鲁棒性优化表达谱"""
        # 提高错误处理和边界检查的表达水平
        for node_id, expression_level in self.expression_profile.items():
            if any(keyword in node_id.lower() for keyword in ['compare', 'call']):
                self.expression_profile[node_id] = min(1.0, expression_level * 1.1)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Genome':
        """从字典数据创建基因组
        
        Args:
            data: 包含基因组数据的字典
            
        Returns:
            Genome: 创建的基因组对象
        """
        logger.debug("从字典创建基因组")
        try:
            # 递归构建基因节点
            def build_node(node_data: Dict[str, Any]) -> GeneNode:
                node_type = NodeType(node_data.get('node_type', 'expression'))
                value = node_data.get('value')
                metadata = node_data.get('metadata', {})
                
                node = GeneNode(node_type, value, [], metadata)
                
                # 恢复基因表达调控属性
                node.expression_level = node_data.get('expression_level', 1.0)
                node.is_active = node_data.get('is_active', True)
                node.regulation_factors = node_data.get('regulation_factors', {})
                node.epigenetic_marks = node_data.get('epigenetic_marks', [])
                node.mutation_rate = node_data.get('mutation_rate', 0.01)
                node.conservation_score = node_data.get('conservation_score', 0.5)
                node.fitness_contribution = node_data.get('fitness_contribution', 0.0)
                
                # 递归构建子节点
                for child_data in node_data.get('children', []):
                    child_node = build_node(child_data)
                    node.add_child(child_node)
                
                return node
            
            root = build_node(data['root'])
            function_name = data.get('function_name', 'generated_function')
            parameters = data.get('parameters', [('numbers', 'list[int]')])
            return_type = data.get('return_type', 'list[int]')
            
            genome = cls(root, function_name, parameters, return_type)
            
            # 恢复基因组级别的属性
            genome.gene_network = data.get('gene_network', {})
            genome.expression_profile = data.get('expression_profile', {})
            genome.regulatory_elements = data.get('regulatory_elements', [])
            genome.generation = data.get('generation', 0)
            genome.parent_genomes = data.get('parent_genomes', [])
            genome.mutation_history = data.get('mutation_history', [])
            genome.fitness_history = data.get('fitness_history', [])
            genome.complexity_metrics = data.get('complexity_metrics', {})
            genome.semantic_features = data.get('semantic_features', {})
            
            return genome
            
        except Exception as e:
            logger.error(f"从字典创建基因组失败: {e}")
            # 返回简单的默认基因组
            generator = GenomeGenerator()
            return generator.generate_simple_genome()
    
    def to_dict(self) -> Dict[str, Any]:
        """将基因组转换为字典
        
        Returns:
            Dict[str, Any]: 基因组的字典表示
        """
        def node_to_dict(node: GeneNode) -> Dict[str, Any]:
            return {
                'node_type': node.node_type.value,
                'value': node.value,
                'metadata': node.metadata,
                'children': [node_to_dict(child) for child in node.children]
            }
        
        return {
            'root': node_to_dict(self.root),
            'function_name': self.function_name,
            'parameters': self.parameters,
            'return_type': self.return_type,
            'gene_network': self.gene_network,
            'expression_profile': self.expression_profile,
            'regulatory_elements': self.regulatory_elements,
            'generation': self.generation,
            'parent_genomes': self.parent_genomes,
            'mutation_history': self.mutation_history,
            'fitness_history': self.fitness_history,
            'complexity_metrics': self.complexity_metrics,
            'semantic_features': self.semantic_features
        }

class GenomeGenerator:
    """基因组生成器 - 用于创建随机基因组"""
    
    def __init__(self, max_depth: int = 4, max_nodes: int = 30):
        """初始化生成器
        
        Args:
            max_depth: 最大嵌套深度
            max_nodes: 最大节点数
        """
        self.max_depth = max_depth
        self.max_nodes = max_nodes
        self.node_count = 0
        
        logger.debug(f"初始化基因组生成器: 最大深度={max_depth}, 最大节点数={max_nodes}")
    
    def generate_random(self) -> Genome:
        """生成随机基因组"""
        logger.debug("生成随机基因组")
        self.node_count = 0
        
        # 创建函数体
        root = self._generate_statement_block(depth=1)
        
        genome = Genome(root=root)
        logger.debug(f"生成完成，节点数: {self.node_count}")
        return genome
    
    def generate_random_genome(self, max_depth: int = None, max_nodes: int = None) -> Genome:
        """生成随机基因组（兼容接口）
        
        Args:
            max_depth: 最大深度
            max_nodes: 最大节点数
            
        Returns:
            随机基因组
        """
        if max_depth is not None:
            self.max_depth = max_depth
        if max_nodes is not None:
            self.max_nodes = max_nodes
        
        return self.generate_random()
    
    def generate_simple_genome(self) -> Genome:
        """生成简单基因组
        
        Returns:
            简单的基因组
        """
        logger.debug("生成简单基因组")
        
        # 创建简单的返回语句
        return_stmt = GeneNode(NodeType.RETURN_STMT)
        return_expr = GeneNode(NodeType.NAME, "numbers")
        return_stmt.add_child(return_expr)
        
        # 创建根节点
        root = GeneNode(NodeType.EXPRESSION)
        root.add_child(return_stmt)
        
        genome = Genome(root=root)
        logger.debug("简单基因组生成完成")
        return genome
    
    def _generate_statement_block(self, depth: int) -> GeneNode:
        """生成语句块"""
        block = GeneNode(NodeType.EXPRESSION)  # 用作容器
        
        # 生成1-3个语句，确保范围有效
        max_statements = max(1, min(3, self.max_nodes - self.node_count))
        num_statements = random.randint(1, max_statements) if max_statements >= 1 else 1
        
        for _ in range(num_statements):
            if self.node_count >= self.max_nodes:
                break
            
            stmt = self._generate_statement(depth)
            if stmt:
                block.add_child(stmt)
        
        # 确保有返回语句
        if not any(child.node_type == NodeType.RETURN_STMT for child in block.children):
            return_stmt = GeneNode(NodeType.RETURN_STMT)
            return_expr = self._generate_expression(depth + 1)
            if return_expr:
                return_stmt.add_child(return_expr)
            block.add_child(return_stmt)
            self.node_count += 1
        
        return block
    
    def _generate_statement(self, depth: int) -> Optional[GeneNode]:
        """生成单个语句"""
        if depth >= self.max_depth or self.node_count >= self.max_nodes:
            return None
        
        self.node_count += 1
        
        # 选择语句类型
        stmt_types = [NodeType.ASSIGNMENT]
        if depth < self.max_depth - 1:
            stmt_types.extend([NodeType.IF_STMT, NodeType.FOR_LOOP])
        
        stmt_type = random.choice(stmt_types)
        
        if stmt_type == NodeType.ASSIGNMENT:
            return self._generate_assignment(depth)
        elif stmt_type == NodeType.IF_STMT:
            return self._generate_if_statement(depth)
        elif stmt_type == NodeType.FOR_LOOP:
            return self._generate_for_loop(depth)
        
        return None
    
    def _generate_assignment(self, depth: int) -> GeneNode:
        """生成赋值语句"""
        var_names = ["result", "temp", "i", "j", "n", "key", "min_idx"]
        target = random.choice(var_names)
        
        node = GeneNode(NodeType.ASSIGNMENT, {"target": target})
        expr = self._generate_expression(depth + 1)
        if expr:
            node.add_child(expr)
        
        return node
    
    def _generate_if_statement(self, depth: int) -> GeneNode:
        """生成if语句"""
        node = GeneNode(NodeType.IF_STMT)
        
        # 条件
        condition = self._generate_expression(depth + 1)
        if condition:
            node.add_child(condition)
        
        # if体
        if_body = self._generate_statement_block(depth + 1)
        node.add_child(if_body)
        
        return node
    
    def _generate_for_loop(self, depth: int) -> GeneNode:
        """生成for循环"""
        targets = ["i", "j", "k", "idx"]
        target = random.choice(targets)
        
        node = GeneNode(NodeType.FOR_LOOP, {"target": target})
        
        # 迭代器
        iterator = self._generate_expression(depth + 1)
        if iterator:
            node.add_child(iterator)
        
        # 循环体
        body = self._generate_statement_block(depth + 1)
        node.add_child(body)
        
        return node
    
    def _generate_expression(self, depth: int) -> Optional[GeneNode]:
        """生成表达式"""
        if depth >= self.max_depth or self.node_count >= self.max_nodes:
            return self._generate_simple_expression()
        
        self.node_count += 1
        
        expr_types = [NodeType.CONSTANT, NodeType.NAME, NodeType.CALL]
        if depth < self.max_depth - 1:
            expr_types.extend([NodeType.BINARY_OP, NodeType.COMPARE, NodeType.LIST, NodeType.SUBSCRIPT])
        
        expr_type = random.choice(expr_types)
        
        if expr_type == NodeType.CONSTANT:
            return GeneNode(NodeType.CONSTANT, random.randint(0, 100))
        elif expr_type == NodeType.NAME:
            names = ["numbers", "result", "temp", "i", "j", "n", "key"]
            return GeneNode(NodeType.NAME, random.choice(names))
        elif expr_type == NodeType.CALL:
            return self._generate_function_call(depth)
        elif expr_type == NodeType.BINARY_OP:
            return self._generate_binary_op(depth)
        elif expr_type == NodeType.COMPARE:
            return self._generate_compare(depth)
        elif expr_type == NodeType.LIST:
            return self._generate_list(depth)
        elif expr_type == NodeType.SUBSCRIPT:
            return self._generate_subscript(depth)
        
        return self._generate_simple_expression()
    
    def _generate_simple_expression(self) -> GeneNode:
        """生成简单表达式"""
        if random.random() < 0.5:
            return GeneNode(NodeType.CONSTANT, random.randint(0, 10))
        else:
            names = ["numbers", "result", "i", "j"]
            return GeneNode(NodeType.NAME, random.choice(names))
    
    def _generate_function_call(self, depth: int) -> GeneNode:
        """生成函数调用"""
        functions = ["len", "range", "min", "max", "sum"]
        func_name = random.choice(functions)
        
        node = GeneNode(NodeType.CALL, func_name)
        
        # 生成参数
        if func_name in ["len", "min", "max", "sum"]:
            arg = self._generate_expression(depth + 1)
            if arg:
                node.add_child(arg)
        elif func_name == "range":
            # range可以有1-3个参数
            num_args = random.randint(1, 2)
            for _ in range(num_args):
                arg = self._generate_expression(depth + 1)
                if arg:
                    node.add_child(arg)
        
        return node
    
    def _generate_binary_op(self, depth: int) -> GeneNode:
        """生成二元运算"""
        ops = ["+", "-", "*", "//", "%"]
        op = random.choice(ops)
        
        node = GeneNode(NodeType.BINARY_OP, op)
        
        left = self._generate_expression(depth + 1)
        right = self._generate_expression(depth + 1)
        
        if left:
            node.add_child(left)
        if right:
            node.add_child(right)
        
        return node
    
    def _generate_compare(self, depth: int) -> GeneNode:
        """生成比较运算"""
        ops = ["<", ">", "<=", ">=", "==", "!="]
        op = random.choice(ops)
        
        node = GeneNode(NodeType.COMPARE, op)
        
        left = self._generate_expression(depth + 1)
        right = self._generate_expression(depth + 1)
        
        if left:
            node.add_child(left)
        if right:
            node.add_child(right)
        
        return node
    
    def _generate_list(self, depth: int) -> GeneNode:
        """生成列表字面量"""
        node = GeneNode(NodeType.LIST)
        
        # 生成0-3个元素
        num_elements = random.randint(0, 3)
        for _ in range(num_elements):
            elem = self._generate_expression(depth + 1)
            if elem:
                node.add_child(elem)
        
        return node
    
    def _generate_subscript(self, depth: int) -> GeneNode:
        """生成下标访问"""
        node = GeneNode(NodeType.SUBSCRIPT)
        
        # 对象
        obj = GeneNode(NodeType.NAME, "numbers")
        node.add_child(obj)
        
        # 索引
        index = self._generate_expression(depth + 1)
        if index:
            node.add_child(index)
        
        return node

# 导出的工厂函数
def create_random_genome() -> Genome:
    """创建随机基因组"""
    logger.debug("创建随机基因组")
    generator = GenomeGenerator()
    return generator.generate_random()

def create_genome_from_code(code: str) -> Optional[Genome]:
    """从代码创建基因组"""
    logger.debug(f"从代码创建基因组: {code[:100]}...")
    try:
        import ast
        
        # 解析代码为AST
        tree = ast.parse(code)
        
        # 创建根节点
        root = GeneNode(NodeType.FUNCTION_DEF, "generated_function")
        
        # 转换AST为基因组
        for node in ast.walk(tree):
            gene_node = _ast_to_gene_node(node)
            if gene_node and gene_node.node_type != NodeType.FUNCTION_DEF:
                root.add_child(gene_node)
        
        # 如果没有子节点，创建一个简单的返回语句
        if not root.children:
            return_node = GeneNode(NodeType.RETURN_STMT)
            return_node.add_child(GeneNode(NodeType.LIST))
            root.add_child(return_node)
        
        # 创建基因组
        genome = Genome(root=root)
        
        logger.debug(f"成功解析代码，生成基因组")
        return genome
        
    except SyntaxError as e:
        logger.error(f"代码语法错误: {e}")
        return None
    except Exception as e:
        logger.error(f"代码解析失败: {e}")
        return None

def _ast_to_gene_node(ast_node) -> Optional[GeneNode]:
    """将AST节点转换为基因节点"""
    import ast
    
    if isinstance(ast_node, ast.FunctionDef):
        return GeneNode(NodeType.FUNCTION_DEF, ast_node.name)
    elif isinstance(ast_node, ast.Assign):
        return GeneNode(NodeType.ASSIGNMENT)
    elif isinstance(ast_node, ast.If):
        return GeneNode(NodeType.IF_STMT)
    elif isinstance(ast_node, ast.For):
        return GeneNode(NodeType.FOR_LOOP)
    elif isinstance(ast_node, ast.While):
        return GeneNode(NodeType.WHILE_LOOP)
    elif isinstance(ast_node, ast.Return):
        return GeneNode(NodeType.RETURN)
    elif isinstance(ast_node, ast.BinOp):
        op_map = {
            ast.Add: '+', ast.Sub: '-', ast.Mult: '*',
            ast.Div: '/', ast.FloorDiv: '//', ast.Mod: '%'
        }
        op = op_map.get(type(ast_node.op), '+')
        return GeneNode(NodeType.BINARY_OP, op)
    elif isinstance(ast_node, ast.Compare):
        op_map = {
            ast.Lt: '<', ast.Gt: '>', ast.LtE: '<=',
            ast.GtE: '>=', ast.Eq: '==', ast.NotEq: '!='
        }
        if ast_node.ops:
            op = op_map.get(type(ast_node.ops[0]), '==')
            return GeneNode(NodeType.COMPARE, op)
    elif isinstance(ast_node, ast.Call):
        if isinstance(ast_node.func, ast.Name):
            return GeneNode(NodeType.CALL, ast_node.func.id)
    elif isinstance(ast_node, ast.Constant):
        return GeneNode(NodeType.CONSTANT, ast_node.value)
    elif isinstance(ast_node, ast.Name):
        return GeneNode(NodeType.NAME, ast_node.id)
    elif isinstance(ast_node, ast.List):
        return GeneNode(NodeType.LIST)
    elif isinstance(ast_node, ast.Subscript):
        return GeneNode(NodeType.SUBSCRIPT)
    
    return None