import ast
import numpy as np
from typing import Any, Dict, List, Optional, Union
from .macro_molecule import MacroMolecule, MoleculeType, BindingSite

class SyntaxTokenMolecule(MacroMolecule):
    """语法令牌分子
    
    代表Python语法中的基本元素，如关键字、操作符、标点符号等。
    这些分子是构建AST的基础材料。
    """
    
    def __init__(self, token_type: str, token_value: str, position: np.ndarray):
        """
        初始化语法令牌分子
        
        Args:
            token_type: 令牌类型（如'KEYWORD', 'OPERATOR', 'DELIMITER'等）
            token_value: 令牌值（如'def', '+', '('等）
            position: 3D空间位置
        """
        # 定义结合位点 - 语法令牌可以与AST节点结合
        binding_sites = {
            'ast_connector': BindingSite(shape_id='syntax_to_ast', binding_strength=0.8)
        }
        
        super().__init__(
            mol_type=MoleculeType.SYNTAX_TOKEN,
            position=position,
            binding_sites=binding_sites,
            data={
                'token_type': token_type,
                'token_value': token_value,
                'precedence': self._get_precedence(token_type, token_value)
            }
        )
        
        # 语法令牌相对稳定
        self.stability = 150.0
        self.max_stability = 150.0
    
    def _get_precedence(self, token_type: str, token_value: str) -> int:
        """获取操作符优先级
        
        Args:
            token_type: 令牌类型
            token_value: 令牌值
            
        Returns:
            int: 优先级数值，越高优先级越高
        """
        precedence_map = {
            '**': 8,
            '*': 7, '/': 7, '//': 7, '%': 7,
            '+': 6, '-': 6,
            '<<': 5, '>>': 5,
            '&': 4,
            '^': 3,
            '|': 2,
            '==': 1, '!=': 1, '<': 1, '>': 1, '<=': 1, '>=': 1,
            'and': 0, 'or': 0
        }
        return precedence_map.get(token_value, 0)
    
    @property
    def token_type(self) -> str:
        return self.data['token_type']
    
    @property
    def token_value(self) -> str:
        return self.data['token_value']
    
    @property
    def precedence(self) -> int:
        return self.data['precedence']

class VariableMolecule(MacroMolecule):
    """变量分子
    
    代表程序中的变量，包含变量名、类型信息和值。
    可以与其他分子结合形成表达式或赋值语句。
    """
    
    def __init__(self, var_name: str, var_type: Optional[str], position: np.ndarray, value: Any = None):
        """
        初始化变量分子
        
        Args:
            var_name: 变量名
            var_type: 变量类型（如'int', 'str', 'list'等）
            position: 3D空间位置
            value: 变量值（可选）
        """
        # 定义结合位点
        binding_sites = {
            'assignment_left': BindingSite(shape_id='var_assign_left', binding_strength=0.9),
            'assignment_right': BindingSite(shape_id='var_assign_right', binding_strength=0.9),
            'expression': BindingSite(shape_id='var_expression', binding_strength=0.7),
            'function_arg': BindingSite(shape_id='var_func_arg', binding_strength=0.8)
        }
        
        super().__init__(
            mol_type=MoleculeType.VARIABLE,
            position=position,
            binding_sites=binding_sites,
            data={
                'var_name': var_name,
                'var_type': var_type,
                'value': value,
                'scope': 'local',  # 作用域
                'is_mutable': True  # 是否可变
            }
        )
    
    @property
    def var_name(self) -> str:
        return self.data['var_name']
    
    @property
    def var_type(self) -> Optional[str]:
        return self.data['var_type']
    
    @property
    def value(self) -> Any:
        return self.data['value']
    
    @value.setter
    def value(self, new_value: Any):
        if self.data['is_mutable']:
            self.data['value'] = new_value
    
    @property
    def scope(self) -> str:
        return self.data['scope']
    
    @scope.setter
    def scope(self, new_scope: str):
        self.data['scope'] = new_scope

class ASTNodeMolecule(MacroMolecule):
    """AST节点分子
    
    代表抽象语法树中的一个节点，可以是表达式、语句、函数定义等。
    这些分子通过结合形成完整的程序结构。
    """
    
    def __init__(self, node_type: str, position: np.ndarray, ast_data: Optional[Dict] = None):
        """
        初始化AST节点分子
        
        Args:
            node_type: AST节点类型（如'FunctionDef', 'If', 'For', 'Assign'等）
            position: 3D空间位置
            ast_data: AST节点的具体数据
        """
        # 定义结合位点 - AST节点可以与其他AST节点、语法令牌、变量结合
        binding_sites = {
            'parent': BindingSite(shape_id='ast_parent', binding_strength=1.0),
            'child_1': BindingSite(shape_id='ast_child', binding_strength=1.0),
            'child_2': BindingSite(shape_id='ast_child', binding_strength=1.0),
            'child_3': BindingSite(shape_id='ast_child', binding_strength=1.0),
            'syntax_slot': BindingSite(shape_id='syntax_to_ast', binding_strength=0.8),
            'variable_slot': BindingSite(shape_id='var_expression', binding_strength=0.7)
        }
        
        super().__init__(
            mol_type=MoleculeType.AST_NODE,
            position=position,
            binding_sites=binding_sites,
            data={
                'node_type': node_type,
                'ast_data': ast_data or {},
                'children': [],
                'is_complete': False,  # 节点是否构建完成
                'complexity': self._calculate_complexity(node_type)
            }
        )
        
        # AST节点需要更高的稳定性
        self.stability = 200.0
        self.max_stability = 200.0
    
    def _calculate_complexity(self, node_type: str) -> int:
        """计算AST节点的复杂度
        
        Args:
            node_type: 节点类型
            
        Returns:
            int: 复杂度值
        """
        complexity_map = {
            'Module': 1,
            'FunctionDef': 5,
            'ClassDef': 8,
            'If': 3,
            'For': 4,
            'While': 4,
            'Try': 6,
            'With': 3,
            'Assign': 2,
            'AugAssign': 2,
            'Return': 2,
            'Expr': 1,
            'Call': 3,
            'BinOp': 2,
            'UnaryOp': 1,
            'Compare': 2,
            'Name': 1,
            'Constant': 1
        }
        return complexity_map.get(node_type, 1)
    
    @property
    def node_type(self) -> str:
        return self.data['node_type']
    
    @property
    def ast_data(self) -> Dict:
        return self.data['ast_data']
    
    @property
    def children(self) -> List['ASTNodeMolecule']:
        return self.data['children']
    
    @property
    def is_complete(self) -> bool:
        return self.data['is_complete']
    
    @property
    def complexity(self) -> int:
        return self.data['complexity']
    
    def add_child(self, child: 'ASTNodeMolecule'):
        """添加子节点
        
        Args:
            child: 子AST节点
        """
        self.data['children'].append(child)
        # 尝试与子节点建立物理结合
        for site_name in ['child_1', 'child_2', 'child_3']:
            if not self.binding_sites[site_name].is_occupied:
                if child.can_bind_to(self, 'parent', site_name):
                    child.bind_to(self, 'parent', site_name)
                    break
    
    def remove_child(self, child: 'ASTNodeMolecule'):
        """移除子节点
        
        Args:
            child: 要移除的子AST节点
        """
        if child in self.data['children']:
            self.data['children'].remove(child)
            # 解除物理结合
            if child.id in self.bound_molecules:
                self.unbind_from(child)
    
    def to_ast_node(self) -> ast.AST:
        """转换为Python AST节点
        
        Returns:
            ast.AST: Python AST节点对象
        """
        try:
            # 根据节点类型创建对应的AST节点
            node_class = getattr(ast, self.node_type)
            
            # 创建基础节点
            if self.node_type == 'Module':
                return node_class(body=[child.to_ast_node() for child in self.children], type_ignores=[])
            elif self.node_type == 'FunctionDef':
                return node_class(
                    name=self.ast_data.get('name', 'unnamed_function'),
                    args=ast.arguments(
                        posonlyargs=[], args=[], vararg=None, kwonlyargs=[],
                        kw_defaults=[], kwarg=None, defaults=[]
                    ),
                    body=[child.to_ast_node() for child in self.children] or [ast.Pass()],
                    decorator_list=[],
                    returns=None
                )
            elif self.node_type == 'Assign':
                targets = [ast.Name(id=self.ast_data.get('target', 'x'), ctx=ast.Store())]
                value = self.children[0].to_ast_node() if self.children else ast.Constant(value=0)
                return node_class(targets=targets, value=value)
            elif self.node_type == 'Return':
                value = self.children[0].to_ast_node() if self.children else None
                return node_class(value=value)
            elif self.node_type == 'Constant':
                return node_class(value=self.ast_data.get('value', 0))
            elif self.node_type == 'Name':
                return node_class(id=self.ast_data.get('id', 'x'), ctx=ast.Load())
            else:
                # 默认处理
                return node_class()
                
        except Exception as e:
            print(f"转换AST节点失败: {e}")
            return ast.Pass()  # 返回空语句作为fallback
    
    def mark_complete(self):
        """标记节点为完成状态"""
        self.data['is_complete'] = True
        self.stability = self.max_stability  # 恢复稳定性

def create_syntax_token(token_type: str, token_value: str, position: np.ndarray) -> SyntaxTokenMolecule:
    """创建语法令牌分子的工厂函数
    
    Args:
        token_type: 令牌类型
        token_value: 令牌值
        position: 位置
        
    Returns:
        SyntaxTokenMolecule: 语法令牌分子实例
    """
    return SyntaxTokenMolecule(token_type, token_value, position)

def create_variable(var_name: str, var_type: Optional[str], position: np.ndarray, value: Any = None) -> VariableMolecule:
    """创建变量分子的工厂函数
    
    Args:
        var_name: 变量名
        var_type: 变量类型
        position: 位置
        value: 变量值
        
    Returns:
        VariableMolecule: 变量分子实例
    """
    return VariableMolecule(var_name, var_type, position, value)

def create_ast_node(node_type: str, position: np.ndarray, ast_data: Optional[Dict] = None) -> ASTNodeMolecule:
    """创建AST节点分子的工厂函数
    
    Args:
        node_type: AST节点类型
        position: 位置
        ast_data: AST数据
        
    Returns:
        ASTNodeMolecule: AST节点分子实例
    """
    return ASTNodeMolecule(node_type, position, ast_data)