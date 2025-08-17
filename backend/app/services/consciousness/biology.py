"""生物学模拟模块 - 实现基因表达的完整生物学过程

本模块模拟了从基因到蛋白质的完整生物学过程:
- Gene: 基因，存储AST形式的遗传信息
- mRNA: 信使RNA，线性指令序列
- Protein: 蛋白质，可执行的功能模块
- Transcriber: 转录器，Gene -> mRNA
- Translator: 翻译器，mRNA -> Protein
- AminoAcidRegistry: 氨基酸注册表，安全的基础操作
"""

import ast
import json
import random
import logging
import traceback
from typing import Dict, List, Any, Optional, Callable, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import copy
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

class InstructionType(Enum):
    """mRNA指令类型枚举"""
    LOAD_VAR = "load_var"
    LOAD_CONST = "load_const"
    STORE_VAR = "store_var"
    CALL_AMINO_ACID = "call_amino_acid"
    JUMP = "jump"
    JUMP_IF_TRUE = "jump_if_true"
    JUMP_IF_FALSE = "jump_if_false"
    COMPARE = "compare"
    BUILD_LIST = "build_list"
    BUILD_DICT = "build_dict"
    GET_ITEM = "get_item"
    SET_ITEM = "set_item"
    LOOP_START = "loop_start"
    LOOP_END = "loop_end"
    RETURN = "return"

@dataclass
class Gene:
    """基因类 - 存储AST形式的遗传信息
    
    基因是遗传信息的基本单位，使用Python AST来表示代码结构。
    支持序列化存储和反序列化恢复。
    """
    id: str
    ast_tree: ast.AST
    metadata: Dict[str, Any] = field(default_factory=dict)
    creation_time: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """初始化后处理"""
        if not self.id:
            self.id = str(uuid.uuid4())[:8]
        
        # 添加调试信息
        logger.debug(f"[GENE_DEBUG] 创建基因 {self.id}, AST类型: {type(self.ast_tree).__name__}")
        
        # 记录基因复杂度
        self.metadata['complexity'] = self._calculate_complexity()
        self.metadata['node_count'] = self._count_nodes()
        
    def _calculate_complexity(self) -> int:
        """计算基因复杂度"""
        try:
            complexity = 0
            for node in ast.walk(self.ast_tree):
                if isinstance(node, (ast.For, ast.While)):
                    complexity += 3
                elif isinstance(node, (ast.If, ast.Try)):
                    complexity += 2
                elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    complexity += 5
                else:
                    complexity += 1
            return complexity
        except Exception as e:
            logger.warning(f"[GENE_DEBUG] 计算复杂度失败: {e}")
            return 0
    
    def _count_nodes(self) -> int:
        """计算AST节点数量"""
        try:
            return len(list(ast.walk(self.ast_tree)))
        except Exception as e:
            logger.warning(f"[GENE_DEBUG] 计算节点数量失败: {e}")
            return 0
    
    def to_json(self) -> Dict[str, Any]:
        """将基因序列化为JSON格式"""
        try:
            return {
                'id': self.id,
                'ast_dict': self._ast_to_dict(self.ast_tree),
                'metadata': self.metadata,
                'creation_time': self.creation_time.isoformat()
            }
        except Exception as e:
            logger.error(f"[GENE_DEBUG] 基因序列化失败: {e}")
            return {'id': self.id, 'error': str(e)}
    
    @classmethod
    def from_json(cls, json_data: Dict[str, Any]) -> 'Gene':
        """从JSON格式反序列化基因"""
        try:
            ast_tree = cls._dict_to_ast(json_data['ast_dict'])
            gene = cls(
                id=json_data['id'],
                ast_tree=ast_tree,
                metadata=json_data.get('metadata', {})
            )
            if 'creation_time' in json_data:
                gene.creation_time = datetime.fromisoformat(json_data['creation_time'])
            return gene
        except Exception as e:
            logger.error(f"[GENE_DEBUG] 基因反序列化失败: {e}")
            # 返回一个简单的基因作为后备
            return cls(id=json_data.get('id', 'error'), ast_tree=ast.parse('pass'))
    
    def _ast_to_dict(self, node: ast.AST) -> Dict[str, Any]:
        """将AST节点转换为字典"""
        result = {'type': type(node).__name__}
        
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                result[field] = [self._ast_to_dict(item) if isinstance(item, ast.AST) else item for item in value]
            elif isinstance(value, ast.AST):
                result[field] = self._ast_to_dict(value)
            else:
                result[field] = value
        
        return result
    
    @staticmethod
    def _dict_to_ast(data: Dict[str, Any]) -> ast.AST:
        """将字典转换为AST节点"""
        node_type = getattr(ast, data['type'])
        node = node_type()
        
        for field, value in data.items():
            if field == 'type':
                continue
            
            if isinstance(value, list):
                setattr(node, field, [Gene._dict_to_ast(item) if isinstance(item, dict) and 'type' in item else item for item in value])
            elif isinstance(value, dict) and 'type' in value:
                setattr(node, field, Gene._dict_to_ast(value))
            else:
                setattr(node, field, value)
        
        return node
    
    def to_code(self) -> str:
        """将基因转换为Python代码字符串"""
        try:
            return ast.unparse(self.ast_tree)
        except Exception as e:
            logger.error(f"[GENE_DEBUG] 基因转代码失败: {e}")
            return "# 基因转换失败\npass"

@dataclass
class mRNA:
    """信使RNA类 - 线性指令序列
    
    mRNA是从基因转录而来的线性指令序列，便于翻译器执行。
    每个指令都是一个元组，包含指令类型和参数。
    """
    id: str
    instructions: List[Tuple[InstructionType, Any]]
    source_gene_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    creation_time: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """初始化后处理"""
        if not self.id:
            self.id = str(uuid.uuid4())[:8]
        
        logger.debug(f"[mRNA_DEBUG] 创建mRNA {self.id}, 指令数量: {len(self.instructions)}")
        
        # 记录指令统计
        self.metadata['instruction_count'] = len(self.instructions)
        self.metadata['instruction_types'] = self._count_instruction_types()
    
    def _count_instruction_types(self) -> Dict[str, int]:
        """统计指令类型分布"""
        counts = {}
        for instruction_type, _ in self.instructions:
            type_name = instruction_type.value
            counts[type_name] = counts.get(type_name, 0) + 1
        return counts
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'instructions': [(inst_type.value, arg) for inst_type, arg in self.instructions],
            'source_gene_id': self.source_gene_id,
            'metadata': self.metadata,
            'creation_time': self.creation_time.isoformat()
        }

@dataclass
class Protein:
    """蛋白质类 - 可执行的功能模块
    
    蛋白质是从mRNA翻译而来的可执行功能模块，
    封装了特定的计算能力和行为模式。
    """
    id: str
    function: Callable
    source_mrna_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    creation_time: datetime = field(default_factory=datetime.now)
    execution_count: int = 0
    total_execution_time: float = 0.0
    
    def __post_init__(self):
        """初始化后处理"""
        if not self.id:
            self.id = str(uuid.uuid4())[:8]
        
        logger.debug(f"[PROTEIN_DEBUG] 创建蛋白质 {self.id}")
        
        # 记录蛋白质特性
        self.metadata['complexity'] = self.metadata.get('complexity', 1)
        self.metadata['function_type'] = type(self.function).__name__
    
    def execute(self, *args, **kwargs) -> Any:
        """执行蛋白质功能
        
        在安全环境中执行蛋白质的功能，并记录执行统计信息。
        """
        import time
        
        start_time = time.time()
        self.execution_count += 1
        
        try:
            logger.debug(f"[PROTEIN_DEBUG] 执行蛋白质 {self.id}, 第 {self.execution_count} 次")
            result = self.function(*args, **kwargs)
            
            execution_time = time.time() - start_time
            self.total_execution_time += execution_time
            
            logger.debug(f"[PROTEIN_DEBUG] 蛋白质 {self.id} 执行成功, 耗时: {execution_time:.4f}s")
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.total_execution_time += execution_time
            
            logger.error(f"[PROTEIN_DEBUG] 蛋白质 {self.id} 执行失败: {e}")
            logger.error(f"[PROTEIN_DEBUG] 异常堆栈: {traceback.format_exc()}")
            raise
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计信息"""
        avg_time = self.total_execution_time / max(self.execution_count, 1)
        return {
            'execution_count': self.execution_count,
            'total_execution_time': self.total_execution_time,
            'average_execution_time': avg_time,
            'efficiency_score': 1.0 / (avg_time + 0.001)  # 效率分数
        }

class AminoAcidRegistry:
    """氨基酸注册表 - 管理安全的基础操作
    
    氨基酸是程序能够使用的最基本的安全操作，
    所有复杂的功能都必须通过这些基础操作组合而成。
    """
    
    def __init__(self):
        """初始化氨基酸注册表"""
        self._amino_acids: Dict[str, Callable] = {}
        self._register_basic_amino_acids()
        
        logger.debug(f"[AMINO_ACID_DEBUG] 初始化氨基酸注册表, 注册了 {len(self._amino_acids)} 个氨基酸")
    
    def _register_basic_amino_acids(self):
        """注册基础氨基酸操作"""
        # 数学运算
        self.register('safe_add', self._safe_add)
        self.register('safe_subtract', self._safe_subtract)
        self.register('safe_multiply', self._safe_multiply)
        self.register('safe_divide', self._safe_divide)
        self.register('safe_modulo', self._safe_modulo)
        self.register('safe_power', self._safe_power)
        
        # 比较操作
        self.register('safe_equal', self._safe_equal)
        self.register('safe_not_equal', self._safe_not_equal)
        self.register('safe_less_than', self._safe_less_than)
        self.register('safe_greater_than', self._safe_greater_than)
        self.register('safe_less_equal', self._safe_less_equal)
        self.register('safe_greater_equal', self._safe_greater_equal)
        
        # 逻辑操作
        self.register('safe_and', self._safe_and)
        self.register('safe_or', self._safe_or)
        self.register('safe_not', self._safe_not)
        
        # 列表操作
        self.register('safe_list_append', self._safe_list_append)
        self.register('safe_list_get', self._safe_list_get)
        self.register('safe_list_set', self._safe_list_set)
        self.register('safe_list_length', self._safe_list_length)
        self.register('safe_list_slice', self._safe_list_slice)
        
        # 控制流
        self.register('safe_if_then_else', self._safe_if_then_else)
        self.register('safe_loop_n_times', self._safe_loop_n_times)
        
        # 高级操作
        self.register('safe_min', self._safe_min)
        self.register('safe_max', self._safe_max)
        self.register('safe_abs', self._safe_abs)
        self.register('safe_sum', self._safe_sum)
        
        logger.debug(f"[AMINO_ACID_DEBUG] 注册了 {len(self._amino_acids)} 个基础氨基酸")
    
    def register(self, name: str, function: Callable):
        """注册新的氨基酸操作"""
        self._amino_acids[name] = function
        logger.debug(f"[AMINO_ACID_DEBUG] 注册氨基酸: {name}")
    
    def get(self, name: str) -> Optional[Callable]:
        """获取氨基酸操作"""
        return self._amino_acids.get(name)
    
    def list_amino_acids(self) -> List[str]:
        """列出所有可用的氨基酸"""
        return list(self._amino_acids.keys())
    
    # 安全的数学操作
    def _safe_add(self, a, b):
        """安全加法"""
        try:
            result = a + b
            # 防止数值溢出
            if isinstance(result, (int, float)) and abs(result) > 1e10:
                return 1e10 if result > 0 else -1e10
            return result
        except Exception:
            return 0
    
    def _safe_subtract(self, a, b):
        """安全减法"""
        try:
            result = a - b
            if isinstance(result, (int, float)) and abs(result) > 1e10:
                return 1e10 if result > 0 else -1e10
            return result
        except Exception:
            return 0
    
    def _safe_multiply(self, a, b):
        """安全乘法"""
        try:
            result = a * b
            if isinstance(result, (int, float)) and abs(result) > 1e10:
                return 1e10 if result > 0 else -1e10
            return result
        except Exception:
            return 0
    
    def _safe_divide(self, a, b):
        """安全除法"""
        try:
            if b == 0:
                return float('inf') if a > 0 else float('-inf') if a < 0 else 0
            result = a / b
            if isinstance(result, (int, float)) and abs(result) > 1e10:
                return 1e10 if result > 0 else -1e10
            return result
        except Exception:
            return 0
    
    def _safe_modulo(self, a, b):
        """安全取模"""
        try:
            if b == 0:
                return 0
            return a % b
        except Exception:
            return 0
    
    def _safe_power(self, a, b):
        """安全幂运算"""
        try:
            # 限制指数大小
            if abs(b) > 100:
                b = 100 if b > 0 else -100
            result = a ** b
            if isinstance(result, (int, float)) and abs(result) > 1e10:
                return 1e10 if result > 0 else -1e10
            return result
        except Exception:
            return 0
    
    # 安全的比较操作
    def _safe_equal(self, a, b):
        """安全相等比较"""
        try:
            return a == b
        except Exception:
            return False
    
    def _safe_not_equal(self, a, b):
        """安全不等比较"""
        try:
            return a != b
        except Exception:
            return True
    
    def _safe_less_than(self, a, b):
        """安全小于比较"""
        try:
            return a < b
        except Exception:
            return False
    
    def _safe_greater_than(self, a, b):
        """安全大于比较"""
        try:
            return a > b
        except Exception:
            return False
    
    def _safe_less_equal(self, a, b):
        """安全小于等于比较"""
        try:
            return a <= b
        except Exception:
            return False
    
    def _safe_greater_equal(self, a, b):
        """安全大于等于比较"""
        try:
            return a >= b
        except Exception:
            return False
    
    # 安全的逻辑操作
    def _safe_and(self, a, b):
        """安全逻辑与"""
        try:
            return bool(a) and bool(b)
        except Exception:
            return False
    
    def _safe_or(self, a, b):
        """安全逻辑或"""
        try:
            return bool(a) or bool(b)
        except Exception:
            return False
    
    def _safe_not(self, a):
        """安全逻辑非"""
        try:
            return not bool(a)
        except Exception:
            return True
    
    # 安全的列表操作
    def _safe_list_append(self, lst, item):
        """安全列表追加"""
        try:
            if not isinstance(lst, list):
                lst = []
            # 限制列表长度
            if len(lst) >= 1000:
                return lst
            lst.append(item)
            return lst
        except Exception:
            return []
    
    def _safe_list_get(self, lst, index):
        """安全列表获取"""
        try:
            if not isinstance(lst, list) or not isinstance(index, int):
                return None
            if 0 <= index < len(lst):
                return lst[index]
            return None
        except Exception:
            return None
    
    def _safe_list_set(self, lst, index, value):
        """安全列表设置"""
        try:
            if not isinstance(lst, list) or not isinstance(index, int):
                return lst
            if 0 <= index < len(lst):
                lst[index] = value
            return lst
        except Exception:
            return lst
    
    def _safe_list_length(self, lst):
        """安全列表长度"""
        try:
            if isinstance(lst, list):
                return len(lst)
            return 0
        except Exception:
            return 0
    
    def _safe_list_slice(self, lst, start, end):
        """安全列表切片"""
        try:
            if not isinstance(lst, list):
                return []
            start = max(0, min(start, len(lst)))
            end = max(start, min(end, len(lst)))
            return lst[start:end]
        except Exception:
            return []
    
    # 安全的控制流
    def _safe_if_then_else(self, condition, then_value, else_value):
        """安全条件选择"""
        try:
            return then_value if bool(condition) else else_value
        except Exception:
            return else_value
    
    def _safe_loop_n_times(self, n, body_func):
        """安全循环执行"""
        try:
            if not callable(body_func) or not isinstance(n, int):
                return None
            # 限制循环次数
            n = max(0, min(n, 1000))
            result = None
            for i in range(n):
                result = body_func(i)
            return result
        except Exception:
            return None
    
    # 高级操作
    def _safe_min(self, *args):
        """安全最小值"""
        try:
            if not args:
                return 0
            return min(args)
        except Exception:
            return 0
    
    def _safe_max(self, *args):
        """安全最大值"""
        try:
            if not args:
                return 0
            return max(args)
        except Exception:
            return 0
    
    def _safe_abs(self, a):
        """安全绝对值"""
        try:
            return abs(a)
        except Exception:
            return 0
    
    def _safe_sum(self, lst):
        """安全求和"""
        try:
            if isinstance(lst, list):
                return sum(lst)
            return 0
        except Exception:
            return 0

class Transcriber:
    """转录器 - 将基因(AST)转录为mRNA(指令序列)
    
    转录器负责将基因中的AST结构转换为线性的指令序列，
    这个过程模拟了生物学中的转录过程。
    """
    
    def __init__(self, amino_acid_registry: AminoAcidRegistry):
        """初始化转录器"""
        self.amino_acid_registry = amino_acid_registry
        self.instruction_counter = 0
        
        logger.debug(f"[TRANSCRIBER_DEBUG] 初始化转录器")
    
    def transcribe(self, gene: Gene) -> mRNA:
        """将基因转录为mRNA
        
        Args:
            gene: 要转录的基因
            
        Returns:
            转录得到的mRNA
        """
        logger.debug(f"[TRANSCRIBER_DEBUG] 开始转录基因 {gene.id}")
        
        try:
            self.instruction_counter = 0
            instructions = []
            
            # 遍历AST并生成指令
            self._transcribe_node(gene.ast_tree, instructions)
            
            # 添加返回指令
            instructions.append((InstructionType.RETURN, None))
            
            mrna = mRNA(
                id=f"mrna_{gene.id}",
                instructions=instructions,
                source_gene_id=gene.id,
                metadata={
                    'transcription_time': datetime.now().isoformat(),
                    'source_complexity': gene.metadata.get('complexity', 0)
                }
            )
            
            logger.debug(f"[TRANSCRIBER_DEBUG] 转录完成, 生成 {len(instructions)} 条指令")
            return mrna
            
        except Exception as e:
            logger.error(f"[TRANSCRIBER_DEBUG] 转录失败: {e}")
            logger.error(f"[TRANSCRIBER_DEBUG] 异常堆栈: {traceback.format_exc()}")
            
            # 返回一个简单的mRNA作为后备
            return mRNA(
                id=f"mrna_{gene.id}_error",
                instructions=[(InstructionType.RETURN, None)],
                source_gene_id=gene.id
            )
    
    def _transcribe_node(self, node: ast.AST, instructions: List[Tuple[InstructionType, Any]]):
        """转录单个AST节点"""
        try:
            if isinstance(node, ast.Module):
                for stmt in node.body:
                    self._transcribe_node(stmt, instructions)
            
            elif isinstance(node, ast.Assign):
                # 赋值语句: target = value
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self._transcribe_node(node.value, instructions)
                        instructions.append((InstructionType.STORE_VAR, target.id))
            
            elif isinstance(node, ast.BinOp):
                # 二元操作: left op right
                self._transcribe_node(node.left, instructions)
                self._transcribe_node(node.right, instructions)
                
                op_map = {
                    ast.Add: 'safe_add',
                    ast.Sub: 'safe_subtract',
                    ast.Mult: 'safe_multiply',
                    ast.Div: 'safe_divide',
                    ast.Mod: 'safe_modulo',
                    ast.Pow: 'safe_power'
                }
                
                op_name = op_map.get(type(node.op), 'safe_add')
                instructions.append((InstructionType.CALL_AMINO_ACID, op_name))
            
            elif isinstance(node, ast.Compare):
                # 比较操作
                self._transcribe_node(node.left, instructions)
                
                for i, (op, comparator) in enumerate(zip(node.ops, node.comparators)):
                    self._transcribe_node(comparator, instructions)
                    
                    op_map = {
                        ast.Eq: 'safe_equal',
                        ast.NotEq: 'safe_not_equal',
                        ast.Lt: 'safe_less_than',
                        ast.Gt: 'safe_greater_than',
                        ast.LtE: 'safe_less_equal',
                        ast.GtE: 'safe_greater_equal'
                    }
                    
                    op_name = op_map.get(type(op), 'safe_equal')
                    instructions.append((InstructionType.CALL_AMINO_ACID, op_name))
            
            elif isinstance(node, ast.Name):
                # 变量名
                instructions.append((InstructionType.LOAD_VAR, node.id))
            
            elif isinstance(node, ast.Constant):
                # 常量
                instructions.append((InstructionType.LOAD_CONST, node.value))
            
            elif isinstance(node, ast.List):
                # 列表
                for elt in node.elts:
                    self._transcribe_node(elt, instructions)
                instructions.append((InstructionType.BUILD_LIST, len(node.elts)))
            
            elif isinstance(node, ast.If):
                # 条件语句
                self._transcribe_node(node.test, instructions)
                
                # 生成跳转标签
                else_label = f"else_{self.instruction_counter}"
                end_label = f"end_{self.instruction_counter}"
                self.instruction_counter += 1
                
                instructions.append((InstructionType.JUMP_IF_FALSE, else_label))
                
                # then分支
                for stmt in node.body:
                    self._transcribe_node(stmt, instructions)
                
                instructions.append((InstructionType.JUMP, end_label))
                instructions.append((InstructionType.JUMP, else_label))  # else标签
                
                # else分支
                for stmt in node.orelse:
                    self._transcribe_node(stmt, instructions)
                
                instructions.append((InstructionType.JUMP, end_label))  # end标签
            
            elif isinstance(node, ast.For):
                # for循环
                self._transcribe_node(node.iter, instructions)
                
                loop_label = f"loop_{self.instruction_counter}"
                end_label = f"end_loop_{self.instruction_counter}"
                self.instruction_counter += 1
                
                instructions.append((InstructionType.LOOP_START, loop_label))
                
                # 循环体
                for stmt in node.body:
                    self._transcribe_node(stmt, instructions)
                
                instructions.append((InstructionType.LOOP_END, end_label))
            
            elif isinstance(node, ast.Return):
                # 返回语句
                if node.value:
                    self._transcribe_node(node.value, instructions)
                else:
                    instructions.append((InstructionType.LOAD_CONST, None))
                instructions.append((InstructionType.RETURN, None))
            
            else:
                # 未知节点类型，记录警告
                logger.warning(f"[TRANSCRIBER_DEBUG] 未知AST节点类型: {type(node).__name__}")
                instructions.append((InstructionType.LOAD_CONST, None))
        
        except Exception as e:
            logger.error(f"[TRANSCRIBER_DEBUG] 转录节点失败: {e}")
            instructions.append((InstructionType.LOAD_CONST, None))

class Translator:
    """翻译器 - 将mRNA(指令序列)翻译为Protein(可执行函数)
    
    翻译器是一个虚拟机，负责执行mRNA中的指令序列，
    并将其封装为可复用的蛋白质功能模块。
    """
    
    def __init__(self, amino_acid_registry: AminoAcidRegistry):
        """初始化翻译器"""
        self.amino_acid_registry = amino_acid_registry
        
        logger.debug(f"[TRANSLATOR_DEBUG] 初始化翻译器")
    
    def translate(self, mrna: mRNA) -> Protein:
        """将mRNA翻译为蛋白质
        
        Args:
            mrna: 要翻译的mRNA
            
        Returns:
            翻译得到的蛋白质
        """
        logger.debug(f"[TRANSLATOR_DEBUG] 开始翻译mRNA {mrna.id}")
        
        try:
            # 创建蛋白质函数
            def protein_function(*args, **kwargs):
                return self._execute_instructions(mrna.instructions, args, kwargs)
            
            protein = Protein(
                id=f"protein_{mrna.id}",
                function=protein_function,
                source_mrna_id=mrna.id,
                metadata={
                    'translation_time': datetime.now().isoformat(),
                    'instruction_count': len(mrna.instructions),
                    'source_complexity': mrna.metadata.get('source_complexity', 0)
                }
            )
            
            logger.debug(f"[TRANSLATOR_DEBUG] 翻译完成, 创建蛋白质 {protein.id}")
            return protein
            
        except Exception as e:
            logger.error(f"[TRANSLATOR_DEBUG] 翻译失败: {e}")
            logger.error(f"[TRANSLATOR_DEBUG] 异常堆栈: {traceback.format_exc()}")
            
            # 返回一个简单的蛋白质作为后备
            def dummy_function(*args, **kwargs):
                return None
            
            return Protein(
                id=f"protein_{mrna.id}_error",
                function=dummy_function,
                source_mrna_id=mrna.id
            )
    
    def _execute_instructions(self, instructions: List[Tuple[InstructionType, Any]], 
                            args: Tuple, kwargs: Dict) -> Any:
        """执行指令序列
        
        Args:
            instructions: 指令列表
            args: 位置参数
            kwargs: 关键字参数
            
        Returns:
            执行结果
        """
        try:
            # 初始化虚拟机状态
            stack = []
            memory = dict(kwargs)
            
            # 将位置参数存储到内存中
            for i, arg in enumerate(args):
                memory[f"arg_{i}"] = arg
            
            instruction_pointer = 0
            jump_labels = self._build_jump_table(instructions)
            
            logger.debug(f"[TRANSLATOR_DEBUG] 开始执行 {len(instructions)} 条指令")
            
            # 执行指令循环
            while instruction_pointer < len(instructions):
                try:
                    instruction_type, arg = instructions[instruction_pointer]
                    
                    logger.debug(f"[TRANSLATOR_DEBUG] 执行指令 {instruction_pointer}: {instruction_type.value} {arg}")
                    
                    if instruction_type == InstructionType.LOAD_VAR:
                        value = memory.get(arg, 0)
                        stack.append(value)
                        logger.debug(f"[TRANSLATOR_DEBUG] 加载变量 {arg} = {value}")
                    
                    elif instruction_type == InstructionType.LOAD_CONST:
                        stack.append(arg)
                        logger.debug(f"[TRANSLATOR_DEBUG] 加载常量 {arg}")
                    
                    elif instruction_type == InstructionType.STORE_VAR:
                        if stack:
                            value = stack.pop()
                            memory[arg] = value
                            logger.debug(f"[TRANSLATOR_DEBUG] 存储变量 {arg} = {value}")
                    
                    elif instruction_type == InstructionType.CALL_AMINO_ACID:
                        amino_acid_func = self.amino_acid_registry.get(arg)
                        if amino_acid_func and len(stack) >= 2:
                            b = stack.pop()
                            a = stack.pop()
                            result = amino_acid_func(a, b)
                            stack.append(result)
                            logger.debug(f"[TRANSLATOR_DEBUG] 调用氨基酸 {arg}({a}, {b}) = {result}")
                        elif amino_acid_func and len(stack) >= 1:
                            a = stack.pop()
                            result = amino_acid_func(a)
                            stack.append(result)
                            logger.debug(f"[TRANSLATOR_DEBUG] 调用氨基酸 {arg}({a}) = {result}")
                    
                    elif instruction_type == InstructionType.BUILD_LIST:
                        list_size = arg
                        elements = []
                        for _ in range(min(list_size, len(stack))):
                            elements.insert(0, stack.pop())
                        stack.append(elements)
                        logger.debug(f"[TRANSLATOR_DEBUG] 构建列表 {elements}")
                    
                    elif instruction_type == InstructionType.JUMP:
                        if arg in jump_labels:
                            instruction_pointer = jump_labels[arg]
                            continue
                    
                    elif instruction_type == InstructionType.JUMP_IF_TRUE:
                        if stack and bool(stack.pop()) and arg in jump_labels:
                            instruction_pointer = jump_labels[arg]
                            continue
                    
                    elif instruction_type == InstructionType.JUMP_IF_FALSE:
                        if stack and not bool(stack.pop()) and arg in jump_labels:
                            instruction_pointer = jump_labels[arg]
                            continue
                    
                    elif instruction_type == InstructionType.RETURN:
                        result = stack[-1] if stack else None
                        logger.debug(f"[TRANSLATOR_DEBUG] 返回结果: {result}")
                        return result
                    
                    instruction_pointer += 1
                    
                    # 防止无限循环
                    if instruction_pointer > 10000:
                        logger.warning(f"[TRANSLATOR_DEBUG] 指令执行超过限制，强制退出")
                        break
                
                except Exception as e:
                    logger.error(f"[TRANSLATOR_DEBUG] 执行指令失败: {e}")
                    instruction_pointer += 1
            
            # 返回栈顶元素或None
            result = stack[-1] if stack else None
            logger.debug(f"[TRANSLATOR_DEBUG] 执行完成，最终结果: {result}")
            return result
            
        except Exception as e:
            logger.error(f"[TRANSLATOR_DEBUG] 指令执行失败: {e}")
            logger.error(f"[TRANSLATOR_DEBUG] 异常堆栈: {traceback.format_exc()}")
            return None
    
    def _build_jump_table(self, instructions: List[Tuple[InstructionType, Any]]) -> Dict[str, int]:
        """构建跳转标签表"""
        jump_table = {}
        for i, (instruction_type, arg) in enumerate(instructions):
            if instruction_type == InstructionType.JUMP and isinstance(arg, str):
                jump_table[arg] = i
        return jump_table