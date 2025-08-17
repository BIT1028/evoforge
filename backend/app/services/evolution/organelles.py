import ast
import numpy as np
from typing import List, Dict, Optional, Any, Tuple
from .macro_molecule import MacroMolecule, MoleculeType, BindingSite
from .code_primitives import SyntaxTokenMolecule, VariableMolecule, ASTNodeMolecule
import subprocess
import tempfile
import os
import sys
from io import StringIO
import contextlib

class ASTAssembler(MacroMolecule):
    """AST组装器 - 涌现的核糖体
    
    这是一个复合分子结构，由多个蛋白质分子组装而成。
    它的功能是读取mRNA蓝图，然后从环境中抓取语法令牌和变量，
    组装成AST节点。这模拟了生物细胞中核糖体的翻译过程。
    """
    
    def __init__(self, position: np.ndarray, efficiency: float = 0.8):
        """
        初始化AST组装器
        
        Args:
            position: 3D空间位置
            efficiency: 组装效率 (0-1)
        """
        # 定义结合位点 - 可以与mRNA、语法令牌、变量等结合
        binding_sites = {
            'mrna_slot': BindingSite(shape_id='mrna_ribosome', binding_strength=1.0),
            'syntax_input': BindingSite(shape_id='syntax_to_ast', binding_strength=0.9),
            'variable_input': BindingSite(shape_id='var_expression', binding_strength=0.8),
            'ast_output': BindingSite(shape_id='ast_child', binding_strength=0.9)
        }
        
        super().__init__(
            mol_type=MoleculeType.RIBOSOME_SUBUNIT,
            position=position,
            binding_sites=binding_sites,
            data={
                'efficiency': efficiency,
                'current_instruction': None,
                'instruction_pointer': 0,
                'assembly_buffer': [],  # 正在组装的AST组件
                'completed_nodes': [],  # 已完成的AST节点
                'error_count': 0
            }
        )
        
        # AST组装器需要很高的稳定性
        self.stability = 300.0
        self.max_stability = 300.0
        
        # 设置催化逻辑
        self.catalytic_logic = self._assembly_catalysis
    
    def load_mrna(self, mrna_molecule: MacroMolecule) -> bool:
        """加载mRNA分子（构建蓝图）
        
        Args:
            mrna_molecule: mRNA分子，包含构建指令
            
        Returns:
            bool: 是否成功加载
        """
        if mrna_molecule.type != MoleculeType.MRNA:
            return False
            
        if self.bind_to(mrna_molecule, 'mrna_slot', 'ribosome_binding'):
            self.data['instruction_pointer'] = 0
            return True
        return False
    
    def get_current_instruction(self) -> Optional[Dict[str, Any]]:
        """获取当前指令
        
        Returns:
            Optional[Dict]: 当前指令，如果没有则返回None
        """
        mrna = self._get_bound_mrna()
        if not mrna:
            return None
            
        instructions = mrna.data.get('instructions', [])
        pointer = self.data['instruction_pointer']
        
        if pointer < len(instructions):
            return instructions[pointer]
        return None
    
    def advance_instruction(self):
        """前进到下一条指令"""
        self.data['instruction_pointer'] += 1
    
    def _get_bound_mrna(self) -> Optional[MacroMolecule]:
        """获取结合的mRNA分子
        
        Returns:
            Optional[MacroMolecule]: 结合的mRNA分子
        """
        for mol in self.bound_molecules.values():
            if mol.type == MoleculeType.MRNA:
                return mol
        return None
    
    def _assembly_catalysis(self, substrates: List[MacroMolecule], catalyst: MacroMolecule) -> List[MacroMolecule]:
        """AST组装的催化反应
        
        Args:
            substrates: 底物分子列表（语法令牌、变量等）
            catalyst: 催化剂（自己）
            
        Returns:
            List[MacroMolecule]: 产物分子列表（AST节点）
        """
        try:
            instruction = self.get_current_instruction()
            if not instruction:
                return substrates
            
            # 根据指令类型进行不同的组装
            if instruction['type'] == 'CREATE_FUNCTION':
                return self._assemble_function(substrates, instruction)
            elif instruction['type'] == 'CREATE_ASSIGNMENT':
                return self._assemble_assignment(substrates, instruction)
            elif instruction['type'] == 'CREATE_EXPRESSION':
                return self._assemble_expression(substrates, instruction)
            elif instruction['type'] == 'CREATE_CONTROL_FLOW':
                return self._assemble_control_flow(substrates, instruction)
            else:
                return substrates
                
        except Exception as e:
            self.data['error_count'] += 1
            print(f"AST组装错误: {e}")
            return substrates
    
    def _assemble_function(self, substrates: List[MacroMolecule], instruction: Dict) -> List[MacroMolecule]:
        """组装函数定义
        
        Args:
            substrates: 底物分子
            instruction: 指令
            
        Returns:
            List[MacroMolecule]: 包含新AST节点的分子列表
        """
        # 寻找函数名变量
        func_name = instruction.get('name', 'unnamed_function')
        
        # 创建函数定义AST节点
        ast_node = ASTNodeMolecule(
            node_type='FunctionDef',
            position=self.position + np.random.randn(3) * 0.5,
            ast_data={'name': func_name, 'args': instruction.get('args', [])}
        )
        
        self.data['completed_nodes'].append(ast_node)
        self.advance_instruction()
        
        return substrates + [ast_node]
    
    def _assemble_assignment(self, substrates: List[MacroMolecule], instruction: Dict) -> List[MacroMolecule]:
        """组装赋值语句
        
        Args:
            substrates: 底物分子
            instruction: 指令
            
        Returns:
            List[MacroMolecule]: 包含新AST节点的分子列表
        """
        target = instruction.get('target', 'x')
        
        # 创建赋值AST节点
        ast_node = ASTNodeMolecule(
            node_type='Assign',
            position=self.position + np.random.randn(3) * 0.5,
            ast_data={'target': target}
        )
        
        # 尝试从底物中找到值表达式
        for substrate in substrates:
            if isinstance(substrate, ASTNodeMolecule) and substrate.node_type in ['Constant', 'Name', 'BinOp']:
                ast_node.add_child(substrate)
                break
        
        self.data['completed_nodes'].append(ast_node)
        self.advance_instruction()
        
        return substrates + [ast_node]
    
    def _assemble_expression(self, substrates: List[MacroMolecule], instruction: Dict) -> List[MacroMolecule]:
        """组装表达式
        
        Args:
            substrates: 底物分子
            instruction: 指令
            
        Returns:
            List[MacroMolecule]: 包含新AST节点的分子列表
        """
        expr_type = instruction.get('expr_type', 'Constant')
        
        if expr_type == 'Constant':
            ast_node = ASTNodeMolecule(
                node_type='Constant',
                position=self.position + np.random.randn(3) * 0.5,
                ast_data={'value': instruction.get('value', 0)}
            )
        elif expr_type == 'Name':
            ast_node = ASTNodeMolecule(
                node_type='Name',
                position=self.position + np.random.randn(3) * 0.5,
                ast_data={'id': instruction.get('id', 'x')}
            )
        else:
            # 默认创建常量
            ast_node = ASTNodeMolecule(
                node_type='Constant',
                position=self.position + np.random.randn(3) * 0.5,
                ast_data={'value': 0}
            )
        
        self.data['completed_nodes'].append(ast_node)
        self.advance_instruction()
        
        return substrates + [ast_node]
    
    def _assemble_control_flow(self, substrates: List[MacroMolecule], instruction: Dict) -> List[MacroMolecule]:
        """组装控制流语句
        
        Args:
            substrates: 底物分子
            instruction: 指令
            
        Returns:
            List[MacroMolecule]: 包含新AST节点的分子列表
        """
        control_type = instruction.get('control_type', 'If')
        
        ast_node = ASTNodeMolecule(
            node_type=control_type,
            position=self.position + np.random.randn(3) * 0.5,
            ast_data=instruction.get('data', {})
        )
        
        self.data['completed_nodes'].append(ast_node)
        self.advance_instruction()
        
        return substrates + [ast_node]

class CodeOptimizer(MacroMolecule):
    """代码优化器 - 涌现的高尔基体
    
    对AST组装器生产的代码片段进行后处理，包括优化、重构，
    有时也会引入错误（模拟生物系统中的干扰）。
    """
    
    def __init__(self, position: np.ndarray, optimization_level: float = 0.7):
        """
        初始化代码优化器
        
        Args:
            position: 3D空间位置
            optimization_level: 优化水平 (0-1)
        """
        binding_sites = {
            'ast_input': BindingSite(shape_id='ast_child', binding_strength=0.9),
            'ast_output': BindingSite(shape_id='ast_parent', binding_strength=0.9)
        }
        
        super().__init__(
            mol_type=MoleculeType.PROTEIN,
            position=position,
            binding_sites=binding_sites,
            data={
                'optimization_level': optimization_level,
                'processed_nodes': [],
                'optimization_count': 0,
                'error_introduction_rate': 0.05  # 5%的概率引入错误
            }
        )
        
        self.stability = 250.0
        self.max_stability = 250.0
        self.catalytic_logic = self._optimization_catalysis
    
    def _optimization_catalysis(self, substrates: List[MacroMolecule], catalyst: MacroMolecule) -> List[MacroMolecule]:
        """代码优化的催化反应
        
        Args:
            substrates: 底物分子列表（AST节点）
            catalyst: 催化剂（自己）
            
        Returns:
            List[MacroMolecule]: 优化后的AST节点列表
        """
        optimized_substrates = []
        
        for substrate in substrates:
            if isinstance(substrate, ASTNodeMolecule):
                optimized_node = self._optimize_ast_node(substrate)
                optimized_substrates.append(optimized_node)
                self.data['optimization_count'] += 1
            else:
                optimized_substrates.append(substrate)
        
        return optimized_substrates
    
    def _optimize_ast_node(self, ast_node: ASTNodeMolecule) -> ASTNodeMolecule:
        """优化单个AST节点
        
        Args:
            ast_node: 要优化的AST节点
            
        Returns:
            ASTNodeMolecule: 优化后的AST节点
        """
        # 随机决定是否引入错误（模拟干扰）
        if np.random.random() < self.data['error_introduction_rate']:
            return self._introduce_error(ast_node)
        
        # 根据优化水平决定是否进行优化
        if np.random.random() < self.data['optimization_level']:
            return self._apply_optimization(ast_node)
        
        return ast_node
    
    def _apply_optimization(self, ast_node: ASTNodeMolecule) -> ASTNodeMolecule:
        """应用优化
        
        Args:
            ast_node: AST节点
            
        Returns:
            ASTNodeMolecule: 优化后的节点
        """
        # 常量折叠优化
        if ast_node.node_type == 'BinOp':
            return self._constant_folding(ast_node)
        
        # 死代码消除
        if ast_node.node_type == 'If':
            return self._dead_code_elimination(ast_node)
        
        # 变量重命名优化
        if ast_node.node_type == 'Name':
            return self._variable_renaming(ast_node)
        
        return ast_node
    
    def _constant_folding(self, ast_node: ASTNodeMolecule) -> ASTNodeMolecule:
        """常量折叠优化
        
        Args:
            ast_node: 二元操作AST节点
            
        Returns:
            ASTNodeMolecule: 优化后的节点
        """
        # 简单的常量折叠示例
        if len(ast_node.children) >= 2:
            left = ast_node.children[0]
            right = ast_node.children[1]
            
            if (left.node_type == 'Constant' and right.node_type == 'Constant'):
                # 创建新的常量节点
                try:
                    left_val = left.ast_data.get('value', 0)
                    right_val = right.ast_data.get('value', 0)
                    op = ast_node.ast_data.get('op', '+')
                    
                    if op == '+':
                        result = left_val + right_val
                    elif op == '-':
                        result = left_val - right_val
                    elif op == '*':
                        result = left_val * right_val
                    elif op == '/' and right_val != 0:
                        result = left_val / right_val
                    else:
                        return ast_node
                    
                    optimized_node = ASTNodeMolecule(
                        node_type='Constant',
                        position=ast_node.position,
                        ast_data={'value': result}
                    )
                    return optimized_node
                except:
                    pass
        
        return ast_node
    
    def _dead_code_elimination(self, ast_node: ASTNodeMolecule) -> ASTNodeMolecule:
        """死代码消除
        
        Args:
            ast_node: If语句AST节点
            
        Returns:
            ASTNodeMolecule: 优化后的节点
        """
        # 简单的死代码消除示例
        # 如果条件是常量False，移除整个if语句
        if ast_node.children and ast_node.children[0].node_type == 'Constant':
            condition_value = ast_node.children[0].ast_data.get('value')
            if condition_value is False:
                # 返回空语句
                return ASTNodeMolecule(
                    node_type='Pass',
                    position=ast_node.position
                )
        
        return ast_node
    
    def _variable_renaming(self, ast_node: ASTNodeMolecule) -> ASTNodeMolecule:
        """变量重命名优化
        
        Args:
            ast_node: Name节点
            
        Returns:
            ASTNodeMolecule: 优化后的节点
        """
        # 简单的变量重命名（缩短变量名）
        var_name = ast_node.ast_data.get('id', 'x')
        if len(var_name) > 3:
            # 缩短变量名
            ast_node.ast_data['id'] = var_name[:2]
        
        return ast_node
    
    def _introduce_error(self, ast_node: ASTNodeMolecule) -> ASTNodeMolecule:
        """引入错误（模拟干扰）
        
        Args:
            ast_node: AST节点
            
        Returns:
            ASTNodeMolecule: 可能包含错误的节点
        """
        # 随机引入一些常见错误
        error_type = np.random.choice(['syntax_error', 'logic_error', 'type_error'])
        
        if error_type == 'syntax_error' and ast_node.node_type == 'Name':
            # 引入语法错误：使用无效的变量名
            ast_node.ast_data['id'] = '123invalid'
        elif error_type == 'logic_error' and ast_node.node_type == 'BinOp':
            # 引入逻辑错误：错误的操作符
            ast_node.ast_data['op'] = '/'
        elif error_type == 'type_error' and ast_node.node_type == 'Constant':
            # 引入类型错误：不兼容的类型
            ast_node.ast_data['value'] = 'string' + 123
        
        return ast_node

class CompilerRunner(MacroMolecule):
    """编译器/测试运行器 - 涌现的线粒体
    
    接收完整的AST，将其转换为Python代码并在沙箱中执行测试。
    成功执行产生"能量"（高适应度），失败则"能量耗尽"（低适应度）。
    """
    
    def __init__(self, position: np.ndarray, energy_efficiency: float = 0.8):
        """
        初始化编译器运行器
        
        Args:
            position: 3D空间位置
            energy_efficiency: 能量转换效率
        """
        binding_sites = {
            'ast_input': BindingSite(shape_id='ast_parent', binding_strength=1.0),
            'energy_output': BindingSite(shape_id='energy_production', binding_strength=0.9)
        }
        
        super().__init__(
            mol_type=MoleculeType.PROTEIN,
            position=position,
            binding_sites=binding_sites,
            data={
                'energy_efficiency': energy_efficiency,
                'compilation_count': 0,
                'success_count': 0,
                'error_count': 0,
                'last_output': None,
                'last_error': None
            }
        )
        
        self.stability = 400.0
        self.max_stability = 400.0
        self.catalytic_logic = self._compilation_catalysis
    
    def _compilation_catalysis(self, substrates: List[MacroMolecule], catalyst: MacroMolecule) -> List[MacroMolecule]:
        """编译和执行的催化反应
        
        Args:
            substrates: 底物分子列表（AST节点）
            catalyst: 催化剂（自己）
            
        Returns:
            List[MacroMolecule]: 包含能量令牌的分子列表
        """
        energy_tokens = []
        
        for substrate in substrates:
            if isinstance(substrate, ASTNodeMolecule):
                energy = self._compile_and_execute(substrate)
                if energy > 0:
                    # 创建能量令牌
                    energy_token = MacroMolecule(
                        mol_type=MoleculeType.ENERGY_TOKEN,
                        position=self.position + np.random.randn(3) * 0.5,
                        binding_sites={'consumer': BindingSite(shape_id='energy_consumer')},
                        data={'energy_value': energy}
                    )
                    energy_tokens.append(energy_token)
        
        return substrates + energy_tokens
    
    def _compile_and_execute(self, ast_node: ASTNodeMolecule) -> float:
        """编译并执行AST节点
        
        Args:
            ast_node: 要编译的AST节点
            
        Returns:
            float: 产生的能量值（适应度）
        """
        self.data['compilation_count'] += 1
        
        try:
            # 将AST节点转换为Python AST
            python_ast = ast_node.to_ast_node()
            
            # 如果是模块级别的节点，包装在Module中
            if not isinstance(python_ast, ast.Module):
                python_ast = ast.Module(body=[python_ast], type_ignores=[])
            
            # 编译为代码字符串
            code_string = ast.unparse(python_ast)
            self.data['last_output'] = code_string
            
            # 在沙箱中执行
            energy = self._execute_in_sandbox(code_string)
            
            if energy > 0:
                self.data['success_count'] += 1
            else:
                self.data['error_count'] += 1
            
            return energy * self.data['energy_efficiency']
            
        except Exception as e:
            self.data['error_count'] += 1
            self.data['last_error'] = str(e)
            return 0.0
    
    def _execute_in_sandbox(self, code_string: str) -> float:
        """在沙箱中执行代码
        
        Args:
            code_string: 要执行的Python代码
            
        Returns:
            float: 执行成功度（0-1）
        """
        try:
            # 创建受限的执行环境
            restricted_globals = {
                '__builtins__': {
                    'len': len,
                    'range': range,
                    'print': print,
                    'int': int,
                    'float': float,
                    'str': str,
                    'list': list,
                    'dict': dict,
                    'max': max,
                    'min': min,
                    'sum': sum
                }
            }
            
            # 捕获输出
            output_buffer = StringIO()
            
            with contextlib.redirect_stdout(output_buffer):
                # 编译代码
                compiled_code = compile(code_string, '<generated>', 'exec')
                
                # 执行代码
                exec(compiled_code, restricted_globals)
            
            # 基于代码复杂度和执行成功计算能量
            energy = self._calculate_energy(code_string, output_buffer.getvalue())
            return energy
            
        except SyntaxError:
            return 0.0  # 语法错误，无能量
        except Exception as e:
            # 运行时错误，少量能量（代码至少能编译）
            return 0.1
    
    def _calculate_energy(self, code_string: str, output: str) -> float:
        """计算代码执行产生的能量
        
        Args:
            code_string: 代码字符串
            output: 执行输出
            
        Returns:
            float: 能量值 (0-1)
        """
        base_energy = 0.5  # 基础能量
        
        # 根据代码长度调整
        length_bonus = min(0.3, len(code_string) / 1000)
        
        # 根据输出调整
        output_bonus = 0.1 if output.strip() else 0
        
        # 根据代码复杂度调整
        complexity_bonus = self._estimate_complexity(code_string) * 0.2
        
        total_energy = base_energy + length_bonus + output_bonus + complexity_bonus
        return min(1.0, total_energy)
    
    def _estimate_complexity(self, code_string: str) -> float:
        """估算代码复杂度
        
        Args:
            code_string: 代码字符串
            
        Returns:
            float: 复杂度值 (0-1)
        """
        complexity_indicators = [
            'def ', 'class ', 'if ', 'for ', 'while ',
            'try:', 'except:', 'with ', 'lambda ',
            'import ', 'from '
        ]
        
        complexity_score = 0
        for indicator in complexity_indicators:
            complexity_score += code_string.count(indicator)
        
        return min(1.0, complexity_score / 10)
    
    def get_compilation_stats(self) -> Dict[str, Any]:
        """获取编译统计信息
        
        Returns:
            Dict[str, Any]: 统计信息，包括编译次数、成功次数、错误次数、成功率、最近一次输出与错误等
        """
        return {
            'compilation_count': self.data['compilation_count'],
            'success_count': self.data['success_count'],
            'error_count': self.data['error_count'],
            'success_rate': self.data['success_count'] / max(1, self.data['compilation_count']),
            'last_output': self.data.get('last_output'),
            'last_error': self.data.get('last_error')
        }