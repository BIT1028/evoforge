"""遗传算子模块 - 实现变异和交叉操作

本模块实现了各种遗传算子:
- 点变异: 节点替换、常量微扰、运算符替换
- 结构变异: 子树插入/删除、提升、内联
- 交叉: 类型匹配的子树交换
- 修复器: 语法检查和约束修复
"""

import random
import logging
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass
from enum import Enum
import copy

from .genome import Genome, GeneNode, NodeType, OperatorType, GenomeGenerator

logger = logging.getLogger(__name__)

class MutationType(Enum):
    """变异类型枚举"""
    POINT_MUTATION = "point_mutation"  # 点变异
    CONSTANT_PERTURBATION = "constant_perturbation"  # 常量微扰
    OPERATOR_REPLACEMENT = "operator_replacement"  # 运算符替换
    SUBTREE_INSERTION = "subtree_insertion"  # 子树插入
    SUBTREE_DELETION = "subtree_deletion"  # 子树删除
    SUBTREE_REPLACEMENT = "subtree_replacement"  # 子树替换
    HOIST_MUTATION = "hoist_mutation"  # 提升变异
    SHRINK_MUTATION = "shrink_mutation"  # 收缩变异

class CrossoverType(Enum):
    """交叉类型枚举"""
    SUBTREE_CROSSOVER = "subtree_crossover"  # 子树交叉
    UNIFORM_CROSSOVER = "uniform_crossover"  # 均匀交叉
    ONE_POINT_CROSSOVER = "one_point_crossover"  # 单点交叉

@dataclass
class MutationConfig:
    """变异配置"""
    point_mutation_rate: float = 0.1
    constant_perturbation_rate: float = 0.05
    operator_replacement_rate: float = 0.05
    subtree_insertion_rate: float = 0.02
    subtree_deletion_rate: float = 0.02
    subtree_replacement_rate: float = 0.03
    hoist_mutation_rate: float = 0.01
    shrink_mutation_rate: float = 0.01
    
    # 变异强度参数
    constant_perturbation_std: float = 1.0
    max_new_subtree_depth: int = 3
    max_insertion_attempts: int = 5

@dataclass
class CrossoverConfig:
    """交叉配置"""
    subtree_crossover_rate: float = 0.9
    uniform_crossover_rate: float = 0.05
    one_point_crossover_rate: float = 0.05
    
    # 交叉约束
    max_depth_after_crossover: int = 6
    type_matching_required: bool = True
    preserve_semantics: bool = True

class GeneticOperators:
    """遗传算子类 - 实现各种变异和交叉操作"""
    
    def __init__(self, mutation_config: Optional[MutationConfig] = None,
                 crossover_config: Optional[CrossoverConfig] = None):
        """初始化遗传算子
        
        Args:
            mutation_config: 变异配置
            crossover_config: 交叉配置
        """
        self.mutation_config = mutation_config or MutationConfig()
        self.crossover_config = crossover_config or CrossoverConfig()
        self.generator = GenomeGenerator(max_depth=3, max_nodes=10)
        
        logger.debug("初始化遗传算子")
    
    def mutate(self, genome: Genome) -> Genome:
        """对基因组进行变异
        
        Args:
            genome: 输入基因组
            
        Returns:
            变异后的基因组
        """
        logger.debug("开始基因组变异")
        
        # 深拷贝避免修改原基因组
        mutated = genome.copy()
        
        # 随机选择变异类型
        mutation_types = [
            (MutationType.POINT_MUTATION, self.mutation_config.point_mutation_rate),
            (MutationType.CONSTANT_PERTURBATION, self.mutation_config.constant_perturbation_rate),
            (MutationType.OPERATOR_REPLACEMENT, self.mutation_config.operator_replacement_rate),
            (MutationType.SUBTREE_INSERTION, self.mutation_config.subtree_insertion_rate),
            (MutationType.SUBTREE_DELETION, self.mutation_config.subtree_deletion_rate),
            (MutationType.SUBTREE_REPLACEMENT, self.mutation_config.subtree_replacement_rate),
            (MutationType.HOIST_MUTATION, self.mutation_config.hoist_mutation_rate),
            (MutationType.SHRINK_MUTATION, self.mutation_config.shrink_mutation_rate),
        ]
        
        # 应用多个变异
        for mutation_type, rate in mutation_types:
            if random.random() < rate:
                logger.debug(f"应用变异: {mutation_type}")
                try:
                    if mutation_type == MutationType.POINT_MUTATION:
                        self._point_mutation(mutated)
                    elif mutation_type == MutationType.CONSTANT_PERTURBATION:
                        self._constant_perturbation(mutated)
                    elif mutation_type == MutationType.OPERATOR_REPLACEMENT:
                        self._operator_replacement(mutated)
                    elif mutation_type == MutationType.SUBTREE_INSERTION:
                        self._subtree_insertion(mutated)
                    elif mutation_type == MutationType.SUBTREE_DELETION:
                        self._subtree_deletion(mutated)
                    elif mutation_type == MutationType.SUBTREE_REPLACEMENT:
                        self._subtree_replacement(mutated)
                    elif mutation_type == MutationType.HOIST_MUTATION:
                        self._hoist_mutation(mutated)
                    elif mutation_type == MutationType.SHRINK_MUTATION:
                        self._shrink_mutation(mutated)
                except Exception as e:
                    logger.error(f"变异失败: {mutation_type}, 错误: {e}")
        
        # 修复和验证
        self._repair_genome(mutated)
        
        logger.debug("基因组变异完成")
        return mutated
    
    def crossover(self, parent1: Genome, parent2: Genome) -> Tuple[Genome, Genome]:
        """对两个基因组进行交叉
        
        Args:
            parent1: 父代1
            parent2: 父代2
            
        Returns:
            交叉后的两个子代
        """
        logger.debug("开始基因组交叉")
        
        # 深拷贝
        child1 = parent1.copy()
        child2 = parent2.copy()
        
        # 选择交叉类型
        rand = random.random()
        if rand < self.crossover_config.subtree_crossover_rate:
            logger.debug("应用子树交叉")
            self._subtree_crossover(child1, child2)
        elif rand < (self.crossover_config.subtree_crossover_rate + 
                    self.crossover_config.uniform_crossover_rate):
            logger.debug("应用均匀交叉")
            self._uniform_crossover(child1, child2)
        else:
            logger.debug("应用单点交叉")
            self._one_point_crossover(child1, child2)
        
        # 修复和验证
        self._repair_genome(child1)
        self._repair_genome(child2)
        
        logger.debug("基因组交叉完成")
        return child1, child2
    
    def _point_mutation(self, genome: Genome) -> None:
        """点变异 - 随机替换一个节点"""
        logger.debug("执行点变异")
        
        nodes = self._collect_all_nodes(genome.root)
        if not nodes:
            return
        
        # 随机选择一个节点
        target_node = random.choice(nodes)
        
        # 根据节点类型进行替换
        if target_node.node_type == NodeType.CONSTANT:
            target_node.value = random.randint(0, 100)
        elif target_node.node_type == NodeType.NAME:
            names = ["numbers", "result", "temp", "i", "j", "n", "key"]
            target_node.value = random.choice(names)
        elif target_node.node_type == NodeType.BINARY_OP:
            ops = ["+", "-", "*", "//", "%"]
            target_node.value = random.choice(ops)
        elif target_node.node_type == NodeType.COMPARE:
            ops = ["<", ">", "<=", ">=", "==", "!="]
            target_node.value = random.choice(ops)
        elif target_node.node_type == NodeType.CALL:
            functions = ["len", "range", "min", "max", "sum"]
            target_node.value = random.choice(functions)
        
        logger.debug(f"点变异完成: {target_node.node_type}")
    
    def _constant_perturbation(self, genome: Genome) -> None:
        """常量微扰 - 对数值常量进行小幅调整"""
        logger.debug("执行常量微扰")
        
        nodes = self._collect_all_nodes(genome.root)
        constant_nodes = [n for n in nodes if n.node_type == NodeType.CONSTANT 
                         and isinstance(n.value, (int, float))]
        
        if not constant_nodes:
            return
        
        target_node = random.choice(constant_nodes)
        
        # 高斯扰动
        if isinstance(target_node.value, int):
            perturbation = int(random.gauss(0, self.mutation_config.constant_perturbation_std))
            target_node.value = max(0, target_node.value + perturbation)
        else:
            perturbation = random.gauss(0, self.mutation_config.constant_perturbation_std)
            target_node.value = max(0.0, target_node.value + perturbation)
        
        logger.debug(f"常量微扰完成: {target_node.value}")
    
    def _operator_replacement(self, genome: Genome) -> None:
        """运算符替换"""
        logger.debug("执行运算符替换")
        
        nodes = self._collect_all_nodes(genome.root)
        op_nodes = [n for n in nodes if n.node_type in [NodeType.BINARY_OP, NodeType.COMPARE]]
        
        if not op_nodes:
            return
        
        target_node = random.choice(op_nodes)
        
        if target_node.node_type == NodeType.BINARY_OP:
            ops = ["+", "-", "*", "//", "%"]
            current_op = target_node.value
            available_ops = [op for op in ops if op != current_op]
            if available_ops:
                target_node.value = random.choice(available_ops)
        elif target_node.node_type == NodeType.COMPARE:
            ops = ["<", ">", "<=", ">=", "==", "!="]
            current_op = target_node.value
            available_ops = [op for op in ops if op != current_op]
            if available_ops:
                target_node.value = random.choice(available_ops)
        
        logger.debug(f"运算符替换完成: {target_node.value}")
    
    def _subtree_insertion(self, genome: Genome) -> None:
        """子树插入 - 在随机位置插入新的子树"""
        logger.debug("执行子树插入")
        
        nodes = self._collect_all_nodes(genome.root)
        if not nodes:
            return
        
        # 选择插入点
        target_node = random.choice(nodes)
        
        # 生成新子树
        new_subtree = self._generate_random_subtree(depth=2)
        if new_subtree:
            target_node.add_child(new_subtree)
            logger.debug("子树插入完成")
    
    def _subtree_deletion(self, genome: Genome) -> None:
        """子树删除 - 删除随机子树"""
        logger.debug("执行子树删除")
        
        nodes = self._collect_all_nodes(genome.root)
        nodes_with_children = [n for n in nodes if n.children]
        
        if not nodes_with_children:
            return
        
        target_node = random.choice(nodes_with_children)
        if target_node.children:
            removed_child = target_node.children.pop(random.randint(0, len(target_node.children) - 1))
            logger.debug(f"删除子树: {removed_child.node_type}")
    
    def _subtree_replacement(self, genome: Genome) -> None:
        """子树替换 - 用新子树替换现有子树"""
        logger.debug("执行子树替换")
        
        nodes = self._collect_all_nodes(genome.root)
        if len(nodes) <= 1:  # 保留根节点
            return
        
        # 选择要替换的节点(不包括根节点)
        target_node = random.choice(nodes[1:])
        
        # 生成新子树
        new_subtree = self._generate_random_subtree(depth=2)
        if new_subtree:
            # 找到父节点并替换
            parent = self._find_parent(genome.root, target_node)
            if parent:
                for i, child in enumerate(parent.children):
                    if child is target_node:
                        parent.children[i] = new_subtree
                        logger.debug("子树替换完成")
                        break
    
    def _hoist_mutation(self, genome: Genome) -> None:
        """提升变异 - 将子树提升到父节点位置"""
        logger.debug("执行提升变异")
        
        nodes = self._collect_all_nodes(genome.root)
        nodes_with_children = [n for n in nodes if n.children]
        
        if not nodes_with_children:
            return
        
        target_node = random.choice(nodes_with_children)
        if target_node.children:
            # 随机选择一个子节点提升
            child_to_hoist = random.choice(target_node.children)
            
            # 找到父节点
            parent = self._find_parent(genome.root, target_node)
            if parent:
                for i, child in enumerate(parent.children):
                    if child is target_node:
                        parent.children[i] = child_to_hoist
                        logger.debug("提升变异完成")
                        break
    
    def _shrink_mutation(self, genome: Genome) -> None:
        """收缩变异 - 简化复杂表达式"""
        logger.debug("执行收缩变异")
        
        nodes = self._collect_all_nodes(genome.root)
        complex_nodes = [n for n in nodes if len(n.children) > 1]
        
        if not complex_nodes:
            return
        
        target_node = random.choice(complex_nodes)
        
        # 随机保留一个子节点
        if target_node.children:
            kept_child = random.choice(target_node.children)
            target_node.children = [kept_child]
            logger.debug("收缩变异完成")
    
    def _subtree_crossover(self, genome1: Genome, genome2: Genome) -> None:
        """子树交叉 - 交换两个基因组的子树"""
        logger.debug("执行子树交叉")
        
        nodes1 = self._collect_all_nodes(genome1.root)
        nodes2 = self._collect_all_nodes(genome2.root)
        
        if len(nodes1) <= 1 or len(nodes2) <= 1:
            return
        
        # 选择交叉点(不包括根节点)
        node1 = random.choice(nodes1[1:])
        node2 = random.choice(nodes2[1:])
        
        # 找到父节点
        parent1 = self._find_parent(genome1.root, node1)
        parent2 = self._find_parent(genome2.root, node2)
        
        if parent1 and parent2:
            # 交换子树
            for i, child in enumerate(parent1.children):
                if child is node1:
                    parent1.children[i] = node2
                    break
            
            for i, child in enumerate(parent2.children):
                if child is node2:
                    parent2.children[i] = node1
                    break
            
            logger.debug("子树交叉完成")
    
    def _uniform_crossover(self, genome1: Genome, genome2: Genome) -> None:
        """均匀交叉 - 随机交换对应节点"""
        logger.debug("执行均匀交叉")
        
        nodes1 = self._collect_all_nodes(genome1.root)
        nodes2 = self._collect_all_nodes(genome2.root)
        
        # 对应位置的节点有50%概率交换值
        min_len = min(len(nodes1), len(nodes2))
        for i in range(min_len):
            if random.random() < 0.5 and nodes1[i].node_type == nodes2[i].node_type:
                nodes1[i].value, nodes2[i].value = nodes2[i].value, nodes1[i].value
        
        logger.debug("均匀交叉完成")
    
    def _one_point_crossover(self, genome1: Genome, genome2: Genome) -> None:
        """单点交叉 - 在随机点交换后续部分"""
        logger.debug("执行单点交叉")
        
        nodes1 = self._collect_all_nodes(genome1.root)
        nodes2 = self._collect_all_nodes(genome2.root)
        
        if len(nodes1) <= 1 or len(nodes2) <= 1:
            return
        
        # 选择交叉点
        crossover_point = random.randint(1, min(len(nodes1), len(nodes2)) - 1)
        
        # 交换后续节点的值
        for i in range(crossover_point, min(len(nodes1), len(nodes2))):
            if nodes1[i].node_type == nodes2[i].node_type:
                nodes1[i].value, nodes2[i].value = nodes2[i].value, nodes1[i].value
        
        logger.debug(f"单点交叉完成，交叉点: {crossover_point}")
    
    def _repair_genome(self, genome: Genome) -> None:
        """修复基因组 - 确保语法正确性和约束满足"""
        logger.debug("开始基因组修复")
        
        try:
            # 检查复杂度约束
            complexity = genome.get_complexity()
            
            # 如果深度过深，进行收缩
            if complexity["depth"] > 6:
                logger.debug(f"深度过深({complexity['depth']})，进行收缩")
                self._reduce_depth(genome.root, max_depth=6)
            
            # 如果节点过多，进行简化
            if complexity["nodes"] > 50:
                logger.debug(f"节点过多({complexity['nodes']})，进行简化")
                self._reduce_nodes(genome.root, max_nodes=50)
            
            # 确保有返回语句
            self._ensure_return_statement(genome)
            
            # 验证语法
            is_valid, errors = genome.validate()
            if not is_valid:
                logger.warning(f"修复后仍有错误: {errors}")
            
        except Exception as e:
            logger.error(f"基因组修复失败: {e}")
    
    def _reduce_depth(self, node: GeneNode, max_depth: int, current_depth: int = 1) -> None:
        """减少树的深度"""
        if current_depth >= max_depth:
            # 移除所有子节点
            node.children.clear()
            return
        
        for child in node.children:
            self._reduce_depth(child, max_depth, current_depth + 1)
    
    def _reduce_nodes(self, node: GeneNode, max_nodes: int) -> None:
        """减少节点数量"""
        total_nodes = node.count_nodes()
        if total_nodes <= max_nodes:
            return
        
        # 随机移除一些子节点
        nodes_to_remove = total_nodes - max_nodes
        all_nodes = self._collect_all_nodes(node)
        
        for _ in range(min(nodes_to_remove, len(all_nodes) // 2)):
            if len(all_nodes) > 1:
                node_to_remove = random.choice(all_nodes[1:])  # 不移除根节点
                parent = self._find_parent(node, node_to_remove)
                if parent and node_to_remove in parent.children:
                    parent.children.remove(node_to_remove)
                    all_nodes.remove(node_to_remove)
    
    def _ensure_return_statement(self, genome: Genome) -> None:
        """确保函数有返回语句"""
        nodes = self._collect_all_nodes(genome.root)
        has_return = any(n.node_type == NodeType.RETURN_STMT for n in nodes)
        
        if not has_return:
            logger.debug("添加返回语句")
            return_stmt = GeneNode(NodeType.RETURN_STMT)
            return_expr = GeneNode(NodeType.NAME, "result")
            return_stmt.add_child(return_expr)
            genome.root.add_child(return_stmt)
    
    def _collect_all_nodes(self, root: GeneNode) -> List[GeneNode]:
        """收集所有节点"""
        nodes = [root]
        for child in root.children:
            nodes.extend(self._collect_all_nodes(child))
        return nodes
    
    def _find_parent(self, root: GeneNode, target: GeneNode) -> Optional[GeneNode]:
        """查找目标节点的父节点"""
        if target in root.children:
            return root
        
        for child in root.children:
            parent = self._find_parent(child, target)
            if parent:
                return parent
        
        return None
    
    def _generate_random_subtree(self, depth: int = 2) -> Optional[GeneNode]:
        """生成随机子树"""
        try:
            temp_generator = GenomeGenerator(max_depth=depth, max_nodes=10)
            temp_genome = temp_generator.generate_random()
            return temp_genome.root.children[0] if temp_genome.root.children else None
        except Exception as e:
            logger.error(f"生成随机子树失败: {e}")
            return None

# 便利函数
def mutate_genome(genome: Genome, 
                 mutation_config: Optional[MutationConfig] = None) -> Genome:
    """对基因组进行变异"""
    operators = GeneticOperators(mutation_config=mutation_config)
    return operators.mutate(genome)

def crossover_genomes(parent1: Genome, parent2: Genome,
                     crossover_config: Optional[CrossoverConfig] = None) -> Tuple[Genome, Genome]:
    """对两个基因组进行交叉 - 实现类型匹配的子树交换
    
    Args:
        parent1: 父代1
        parent2: 父代2
        crossover_config: 交叉配置
        
    Returns:
        两个子代基因组
    """
    operators = GeneticOperators(crossover_config=crossover_config)
    return operators.crossover(parent1, parent2)