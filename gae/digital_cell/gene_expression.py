# -*- coding: utf-8 -*-
"""
基因表达系统 - EvoForge核心组件

根据comprehensive_implementation_plan.md重新实现的基因表达系统，包括：
- DNA→mRNA→蛋白质的完整转录翻译流程
- 转录调控机制和激素影响因子
- 安全的代码执行沙箱
- 翻译错误处理和基因完整性验证
"""

import uuid
import logging
import random
import re
import hashlib
import subprocess
import tempfile
import os
import sys
import threading
import time
from typing import Dict, List, Optional, Tuple, Any, Set, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
from collections import defaultdict, deque
import json
import ast
import traceback

# 导入分子系统
from .macro_molecule import (
    MacroMolecule, MoleculeType, Vector3D, BindingSite, BindingSiteType,
    Protein, mRNA, tRNA, Lipid, ResourceToken, EnergyToken, create_molecule
)

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class GeneType(Enum):
    """基因类型"""
    PROTEIN_CODING = "protein_coding"
    REGULATORY = "regulatory"
    STRUCTURAL = "structural"
    FUNCTIONAL = "functional"
    METABOLIC = "metabolic"

class TranscriptionState(Enum):
    """转录状态"""
    INACTIVE = "inactive"
    ACTIVE = "active"
    REPRESSED = "repressed"
    ENHANCED = "enhanced"

class HormoneType(Enum):
    """激素类型"""
    GROWTH_FACTOR = "growth_factor"
    STRESS_HORMONE = "stress_hormone"
    METABOLIC_HORMONE = "metabolic_hormone"
    SIGNALING_MOLECULE = "signaling_molecule"

@dataclass
class Gene:
    """基因数据结构"""
    gene_id: str
    sequence: str
    gene_type: GeneType
    promoter_region: Tuple[int, int]  # 启动子区域
    coding_region: Tuple[int, int]   # 编码区域
    terminator_region: Tuple[int, int]  # 终止子区域
    
    # 调控元件
    transcription_factors: Dict[str, float] = field(default_factory=dict)
    enhancers: List[Tuple[int, int]] = field(default_factory=list)
    silencers: List[Tuple[int, int]] = field(default_factory=list)
    
    # 表达参数
    basal_expression_rate: float = 0.1
    current_expression_rate: float = 0.1
    transcription_state: TranscriptionState = TranscriptionState.INACTIVE
    
    # 功能注释
    function_description: str = ""
    pathway_involvement: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """初始化后处理"""
        self.current_expression_rate = self.basal_expression_rate
        
        # 验证序列完整性
        if not self._validate_sequence():
            logger.warning(f"基因 {self.gene_id} 序列验证失败")
    
    def _validate_sequence(self) -> bool:
        """验证基因序列完整性"""
        if len(self.sequence) < 10:
            return False
        
        # 检查是否包含有效的DNA碱基
        valid_bases = set('ATCG')
        sequence_bases = set(self.sequence.upper())
        
        if not sequence_bases.issubset(valid_bases):
            return False
        
        # 检查区域边界
        total_length = len(self.sequence)
        if (self.promoter_region[1] > total_length or 
            self.coding_region[1] > total_length or 
            self.terminator_region[1] > total_length):
            return False
        
        return True
    
    def get_promoter_sequence(self) -> str:
        """获取启动子序列"""
        start, end = self.promoter_region
        return self.sequence[start:end]
    
    def get_coding_sequence(self) -> str:
        """获取编码序列"""
        start, end = self.coding_region
        return self.sequence[start:end]
    
    def get_terminator_sequence(self) -> str:
        """获取终止子序列"""
        start, end = self.terminator_region
        return self.sequence[start:end]
    
    def calculate_expression_rate(self, transcription_factors: Dict[str, float], 
                                hormones: Dict[str, float]) -> float:
        """计算表达率"""
        expression_rate = self.basal_expression_rate
        
        # 转录因子影响
        for tf_name, tf_level in transcription_factors.items():
            if tf_name in self.transcription_factors:
                tf_effect = self.transcription_factors[tf_name]
                expression_rate *= (1.0 + tf_effect * tf_level)
        
        # 激素影响
        for hormone_name, hormone_level in hormones.items():
            if hormone_name == "stress_hormone" and self.gene_type == GeneType.REGULATORY:
                expression_rate *= (1.0 + 0.5 * hormone_level)
            elif hormone_name == "growth_factor" and self.gene_type == GeneType.PROTEIN_CODING:
                expression_rate *= (1.0 + 0.3 * hormone_level)
        
        # 限制表达率范围
        expression_rate = max(0.0, min(10.0, expression_rate))
        self.current_expression_rate = expression_rate
        
        return expression_rate
    
    def update_transcription_state(self, expression_rate: float) -> None:
        """更新转录状态"""
        if expression_rate < 0.05:
            self.transcription_state = TranscriptionState.REPRESSED
        elif expression_rate < 0.2:
            self.transcription_state = TranscriptionState.INACTIVE
        elif expression_rate < 2.0:
            self.transcription_state = TranscriptionState.ACTIVE
        else:
            self.transcription_state = TranscriptionState.ENHANCED

@dataclass
class Hormone:
    """激素分子"""
    hormone_id: str
    hormone_type: HormoneType
    concentration: float
    target_genes: Set[str] = field(default_factory=set)
    effect_strength: float = 1.0
    half_life: float = 300.0  # 半衰期（秒）
    
    def __post_init__(self):
        self.creation_time = time.time()
    
    def get_current_concentration(self) -> float:
        """获取当前浓度（考虑衰减）"""
        elapsed_time = time.time() - self.creation_time
        decay_factor = 0.5 ** (elapsed_time / self.half_life)
        return self.concentration * decay_factor
    
    def affects_gene(self, gene_id: str) -> bool:
        """检查是否影响特定基因"""
        return gene_id in self.target_genes or len(self.target_genes) == 0

class SafeCodeExecutor:
    """安全代码执行器"""
    
    def __init__(self):
        self.allowed_modules = {
            'math', 'random', 'json', 'time', 'datetime',
            'collections', 'itertools', 'functools'
        }
        self.forbidden_functions = {
            'exec', 'eval', 'compile', '__import__', 'open',
            'file', 'input', 'raw_input', 'reload', 'vars',
            'globals', 'locals', 'dir', 'hasattr', 'getattr',
            'setattr', 'delattr'
        }
        self.max_execution_time = 5.0  # 最大执行时间（秒）
        self.max_memory_usage = 50 * 1024 * 1024  # 最大内存使用（50MB）
    
    def validate_code(self, code: str) -> Tuple[bool, str]:
        """验证代码安全性"""
        try:
            # 解析AST
            tree = ast.parse(code)
            
            # 检查禁用的函数和模块
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    if node.id in self.forbidden_functions:
                        return False, f"禁用函数: {node.id}"
                
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name not in self.allowed_modules:
                            return False, f"禁用模块: {alias.name}"
                
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.module not in self.allowed_modules:
                        return False, f"禁用模块: {node.module}"
            
            return True, "代码验证通过"
        
        except SyntaxError as e:
            return False, f"语法错误: {e}"
        except Exception as e:
            return False, f"验证错误: {e}"
    
    def execute_code(self, code: str, context: Dict[str, Any] = None) -> Tuple[bool, Any, str]:
        """安全执行代码"""
        # 验证代码
        is_valid, message = self.validate_code(code)
        if not is_valid:
            return False, None, message
        
        # 准备执行环境
        safe_globals = {
            '__builtins__': {
                'len': len, 'str': str, 'int': int, 'float': float,
                'bool': bool, 'list': list, 'dict': dict, 'tuple': tuple,
                'set': set, 'range': range, 'enumerate': enumerate,
                'zip': zip, 'map': map, 'filter': filter,
                'sum': sum, 'min': max, 'max': max, 'abs': abs,
                'round': round, 'sorted': sorted, 'reversed': reversed
            }
        }
        
        if context:
            safe_globals.update(context)
        
        try:
            # 使用线程执行以控制超时
            result = {'value': None, 'error': None}
            
            def execute_in_thread():
                try:
                    # 编译并执行代码
                    compiled_code = compile(code, '<gene_expression>', 'exec')
                    exec(compiled_code, safe_globals)
                    
                    # 获取结果（如果有return语句）
                    if 'result' in safe_globals:
                        result['value'] = safe_globals['result']
                    else:
                        result['value'] = "执行完成"
                
                except Exception as e:
                    result['error'] = str(e)
            
            thread = threading.Thread(target=execute_in_thread)
            thread.daemon = True
            thread.start()
            thread.join(timeout=self.max_execution_time)
            
            if thread.is_alive():
                return False, None, "执行超时"
            
            if result['error']:
                return False, None, result['error']
            
            return True, result['value'], "执行成功"
        
        except Exception as e:
            return False, None, f"执行错误: {e}"

class TranscriptionEngine:
    """转录引擎"""
    
    def __init__(self):
        self.rna_polymerase_count = 10
        self.transcription_rate = 0.1  # 每秒转录概率
        self.error_rate = 0.001  # 转录错误率
        
        # 转录统计
        self.stats = {
            'total_transcriptions': 0,
            'successful_transcriptions': 0,
            'failed_transcriptions': 0,
            'transcription_errors': 0
        }
    
    def transcribe_gene(self, gene: Gene, 
                       transcription_factors: Dict[str, float],
                       hormones: Dict[str, float],
                       energy_available: float) -> Optional[mRNA]:
        """转录基因"""
        # 检查能量
        if energy_available < 10.0:
            logger.debug(f"能量不足，无法转录基因 {gene.gene_id}")
            return None
        
        # 计算表达率
        expression_rate = gene.calculate_expression_rate(transcription_factors, hormones)
        gene.update_transcription_state(expression_rate)
        
        # 检查转录概率
        transcription_probability = self.transcription_rate * expression_rate
        
        if random.random() > transcription_probability:
            return None
        
        try:
            # 获取编码序列
            dna_sequence = gene.get_coding_sequence()
            
            # DNA转录为mRNA（T替换为U）
            mrna_sequence = dna_sequence.replace('T', 'U')
            
            # 模拟转录错误
            if random.random() < self.error_rate:
                mrna_sequence = self._introduce_transcription_error(mrna_sequence)
                self.stats['transcription_errors'] += 1
            
            # 创建mRNA分子
            mrna = create_molecule(
                MoleculeType.MRNA,
                sequence=mrna_sequence,
                coding_region=(0, len(mrna_sequence)),
                position=Vector3D(random.uniform(-5, 5), random.uniform(-5, 5), random.uniform(-5, 5))
            )
            
            # 添加基因信息
            mrna.source_gene_id = gene.gene_id
            mrna.gene_type = gene.gene_type
            mrna.transcription_time = time.time()
            
            self.stats['total_transcriptions'] += 1
            self.stats['successful_transcriptions'] += 1
            
            logger.debug(f"成功转录基因 {gene.gene_id} -> mRNA {mrna.molecule_id}")
            return mrna
        
        except Exception as e:
            self.stats['total_transcriptions'] += 1
            self.stats['failed_transcriptions'] += 1
            logger.error(f"转录基因 {gene.gene_id} 失败: {e}")
            return None
    
    def _introduce_transcription_error(self, sequence: str) -> str:
        """引入转录错误"""
        if len(sequence) == 0:
            return sequence
        
        error_type = random.choice(['substitution', 'insertion', 'deletion'])
        position = random.randint(0, len(sequence) - 1)
        
        if error_type == 'substitution':
            bases = ['A', 'U', 'C', 'G']
            new_base = random.choice([b for b in bases if b != sequence[position]])
            sequence = sequence[:position] + new_base + sequence[position + 1:]
        
        elif error_type == 'insertion':
            new_base = random.choice(['A', 'U', 'C', 'G'])
            sequence = sequence[:position] + new_base + sequence[position:]
        
        elif error_type == 'deletion' and len(sequence) > 1:
            sequence = sequence[:position] + sequence[position + 1:]
        
        logger.debug(f"转录错误: {error_type} at position {position}")
        return sequence

class TranslationEngine:
    """翻译引擎"""
    
    def __init__(self):
        self.ribosome_count = 20
        self.translation_rate = 0.2  # 每秒翻译概率
        self.error_rate = 0.0001  # 翻译错误率
        
        # 密码子表（简化版）
        self.codon_table = {
            'UUU': 'Phe', 'UUC': 'Phe', 'UUA': 'Leu', 'UUG': 'Leu',
            'UCU': 'Ser', 'UCC': 'Ser', 'UCA': 'Ser', 'UCG': 'Ser',
            'UAU': 'Tyr', 'UAC': 'Tyr', 'UAA': 'STOP', 'UAG': 'STOP',
            'UGU': 'Cys', 'UGC': 'Cys', 'UGA': 'STOP', 'UGG': 'Trp',
            'CUU': 'Leu', 'CUC': 'Leu', 'CUA': 'Leu', 'CUG': 'Leu',
            'CCU': 'Pro', 'CCC': 'Pro', 'CCA': 'Pro', 'CCG': 'Pro',
            'CAU': 'His', 'CAC': 'His', 'CAA': 'Gln', 'CAG': 'Gln',
            'CGU': 'Arg', 'CGC': 'Arg', 'CGA': 'Arg', 'CGG': 'Arg',
            'AUU': 'Ile', 'AUC': 'Ile', 'AUA': 'Ile', 'AUG': 'Met',
            'ACU': 'Thr', 'ACC': 'Thr', 'ACA': 'Thr', 'ACG': 'Thr',
            'AAU': 'Asn', 'AAC': 'Asn', 'AAA': 'Lys', 'AAG': 'Lys',
            'AGU': 'Ser', 'AGC': 'Ser', 'AGA': 'Arg', 'AGG': 'Arg',
            'GUU': 'Val', 'GUC': 'Val', 'GUA': 'Val', 'GUG': 'Val',
            'GCU': 'Ala', 'GCC': 'Ala', 'GCA': 'Ala', 'GCG': 'Ala',
            'GAU': 'Asp', 'GAC': 'Asp', 'GAA': 'Glu', 'GAG': 'Glu',
            'GGU': 'Gly', 'GGC': 'Gly', 'GGA': 'Gly', 'GGG': 'Gly'
        }
        
        # 翻译统计
        self.stats = {
            'total_translations': 0,
            'successful_translations': 0,
            'failed_translations': 0,
            'translation_errors': 0
        }
    
    def translate_mrna(self, mrna: mRNA, 
                      trna_pool: List[tRNA],
                      energy_available: float) -> Optional[Protein]:
        """翻译mRNA"""
        # 检查能量
        if energy_available < 20.0:
            logger.debug(f"能量不足，无法翻译 mRNA {mrna.molecule_id}")
            return None
        
        # 检查mRNA是否可以翻译
        if not mrna.can_be_translated():
            logger.debug(f"mRNA {mrna.molecule_id} 无法翻译")
            return None
        
        # 检查翻译概率
        if random.random() > self.translation_rate:
            return None
        
        try:
            # 获取编码序列
            coding_sequence = mrna.get_coding_sequence()
            
            # 寻找起始密码子
            start_codon_pos = coding_sequence.find('AUG')
            if start_codon_pos == -1:
                logger.debug(f"mRNA {mrna.molecule_id} 缺少起始密码子")
                return None
            
            # 从起始密码子开始翻译
            amino_acid_sequence = []
            position = start_codon_pos
            
            while position + 3 <= len(coding_sequence):
                codon = coding_sequence[position:position + 3]
                
                # 翻译密码子
                amino_acid = self._translate_codon(codon, trna_pool)
                
                if amino_acid == 'STOP':
                    break
                elif amino_acid is None:
                    # 缺少对应的tRNA
                    logger.debug(f"缺少密码子 {codon} 对应的tRNA")
                    break
                else:
                    amino_acid_sequence.append(amino_acid)
                
                position += 3
                
                # 模拟翻译错误
                if random.random() < self.error_rate:
                    amino_acid_sequence = self._introduce_translation_error(amino_acid_sequence)
                    self.stats['translation_errors'] += 1
            
            # 检查是否成功翻译
            if len(amino_acid_sequence) < 3:  # 最小蛋白质长度
                logger.debug(f"翻译产物过短: {len(amino_acid_sequence)} 个氨基酸")
                return None
            
            # 创建蛋白质
            protein_sequence = ''.join(amino_acid_sequence)
            protein = create_molecule(
                MoleculeType.PROTEIN,
                sequence=protein_sequence,
                position=Vector3D(random.uniform(-10, 10), random.uniform(-10, 10), random.uniform(-10, 10))
            )
            
            # 添加源信息
            protein.source_mrna_id = mrna.molecule_id
            if hasattr(mrna, 'source_gene_id'):
                protein.source_gene_id = mrna.source_gene_id
            if hasattr(mrna, 'gene_type'):
                protein.gene_type = mrna.gene_type
            
            protein.translation_time = time.time()
            
            self.stats['total_translations'] += 1
            self.stats['successful_translations'] += 1
            
            logger.debug(f"成功翻译 mRNA {mrna.molecule_id} -> 蛋白质 {protein.molecule_id}")
            return protein
        
        except Exception as e:
            self.stats['total_translations'] += 1
            self.stats['failed_translations'] += 1
            logger.error(f"翻译 mRNA {mrna.molecule_id} 失败: {e}")
            return None
    
    def _translate_codon(self, codon: str, trna_pool: List[tRNA]) -> Optional[str]:
        """翻译单个密码子"""
        if codon not in self.codon_table:
            return None
        
        amino_acid = self.codon_table[codon]
        
        if amino_acid == 'STOP':
            return 'STOP'
        
        # 寻找匹配的tRNA
        for trna in trna_pool:
            if trna.is_charged and trna.amino_acid == amino_acid:
                return trna.release_amino_acid()
        
        return None
    
    def _introduce_translation_error(self, sequence: List[str]) -> List[str]:
        """引入翻译错误"""
        if len(sequence) == 0:
            return sequence
        
        error_type = random.choice(['substitution', 'frameshift'])
        
        if error_type == 'substitution':
            position = random.randint(0, len(sequence) - 1)
            amino_acids = ['Ala', 'Arg', 'Asn', 'Asp', 'Cys', 'Gln', 'Glu', 'Gly',
                          'His', 'Ile', 'Leu', 'Lys', 'Met', 'Phe', 'Pro', 'Ser',
                          'Thr', 'Trp', 'Tyr', 'Val']
            new_aa = random.choice([aa for aa in amino_acids if aa != sequence[position]])
            sequence[position] = new_aa
        
        elif error_type == 'frameshift':
            # 简化的移码突变（删除一个氨基酸）
            if len(sequence) > 1:
                position = random.randint(0, len(sequence) - 1)
                sequence.pop(position)
        
        logger.debug(f"翻译错误: {error_type}")
        return sequence

class GeneExpressionSystem:
    """基因表达系统"""
    
    def __init__(self):
        # 基因库
        self.genes: Dict[str, Gene] = {}
        
        # 表达引擎
        self.transcription_engine = TranscriptionEngine()
        self.translation_engine = TranslationEngine()
        self.code_executor = SafeCodeExecutor()
        
        # 调控因子
        self.transcription_factors: Dict[str, float] = {}
        self.hormones: Dict[str, Hormone] = {}
        
        # 分子池
        self.mrna_pool: Dict[str, mRNA] = {}
        self.protein_pool: Dict[str, Protein] = {}
        self.trna_pool: List[tRNA] = []
        
        # 系统状态
        self.energy_level = 1000.0
        self.is_active = True
        
        # 统计信息
        self.stats = {
            'genes_added': 0,
            'total_expressions': 0,
            'successful_expressions': 0,
            'failed_expressions': 0,
            'code_executions': 0,
            'execution_errors': 0
        }
        
        logger.info("基因表达系统初始化完成")
    
    def add_gene(self, gene_id: str, sequence: str, gene_type: GeneType = GeneType.PROTEIN_CODING,
                 function_description: str = "") -> bool:
        """添加基因"""
        try:
            # 自动检测区域（简化）
            seq_length = len(sequence)
            promoter_region = (0, min(50, seq_length // 10))
            coding_region = (promoter_region[1], seq_length - min(30, seq_length // 15))
            terminator_region = (coding_region[1], seq_length)
            
            gene = Gene(
                gene_id=gene_id,
                sequence=sequence.upper(),
                gene_type=gene_type,
                promoter_region=promoter_region,
                coding_region=coding_region,
                terminator_region=terminator_region,
                function_description=function_description
            )
            
            self.genes[gene_id] = gene
            self.stats['genes_added'] += 1
            
            logger.info(f"添加基因 {gene_id}，类型: {gene_type.value}，长度: {len(sequence)}")
            return True
        
        except Exception as e:
            logger.error(f"添加基因 {gene_id} 失败: {e}")
            return False
    
    def add_transcription_factor(self, tf_name: str, concentration: float, 
                               target_genes: List[str] = None) -> None:
        """添加转录因子"""
        self.transcription_factors[tf_name] = concentration
        
        # 更新目标基因的转录因子绑定
        if target_genes:
            for gene_id in target_genes:
                if gene_id in self.genes:
                    self.genes[gene_id].transcription_factors[tf_name] = concentration
        
        logger.debug(f"添加转录因子 {tf_name}，浓度: {concentration}")
    
    def add_hormone(self, hormone_id: str, hormone_type: HormoneType, 
                   concentration: float, target_genes: Set[str] = None) -> None:
        """添加激素"""
        hormone = Hormone(
            hormone_id=hormone_id,
            hormone_type=hormone_type,
            concentration=concentration,
            target_genes=target_genes or set()
        )
        
        self.hormones[hormone_id] = hormone
        logger.debug(f"添加激素 {hormone_id}，类型: {hormone_type.value}，浓度: {concentration}")
    
    def add_trna(self, amino_acid: str, anticodon: str, is_charged: bool = True) -> None:
        """添加tRNA"""
        trna = create_molecule(
            MoleculeType.TRNA,
            amino_acid=amino_acid,
            anticodon=anticodon,
            is_charged=is_charged,
            position=Vector3D(random.uniform(-5, 5), random.uniform(-5, 5), random.uniform(-5, 5))
        )
        
        self.trna_pool.append(trna)
        logger.debug(f"添加tRNA，氨基酸: {amino_acid}，反密码子: {anticodon}")
    
    def express_gene(self, gene_id: str) -> Tuple[Optional[mRNA], Optional[Protein]]:
        """表达基因"""
        if gene_id not in self.genes:
            logger.warning(f"基因 {gene_id} 不存在")
            return None, None
        
        if not self.is_active or self.energy_level < 50.0:
            logger.debug(f"系统不活跃或能量不足，无法表达基因 {gene_id}")
            return None, None
        
        try:
            gene = self.genes[gene_id]
            
            # 获取当前激素水平
            current_hormones = {}
            for hormone_id, hormone in self.hormones.items():
                if hormone.affects_gene(gene_id):
                    current_hormones[hormone_id] = hormone.get_current_concentration()
            
            # 转录阶段
            mrna = self.transcription_engine.transcribe_gene(
                gene, self.transcription_factors, current_hormones, self.energy_level
            )
            
            if mrna:
                self.mrna_pool[mrna.molecule_id] = mrna
                self.energy_level -= 10.0  # 消耗转录能量
            
            # 翻译阶段
            protein = None
            if mrna and gene.gene_type == GeneType.PROTEIN_CODING:
                protein = self.translation_engine.translate_mrna(
                    mrna, self.trna_pool, self.energy_level
                )
                
                if protein:
                    self.protein_pool[protein.molecule_id] = protein
                    self.energy_level -= 20.0  # 消耗翻译能量
                    
                    # 如果是功能基因，执行代码
                    if gene.gene_type == GeneType.FUNCTIONAL:
                        self._execute_functional_gene(gene, protein)
            
            self.stats['total_expressions'] += 1
            if mrna or protein:
                self.stats['successful_expressions'] += 1
            else:
                self.stats['failed_expressions'] += 1
            
            logger.debug(f"基因表达完成: {gene_id} -> mRNA: {mrna is not None}, 蛋白质: {protein is not None}")
            return mrna, protein
        
        except Exception as e:
            self.stats['total_expressions'] += 1
            self.stats['failed_expressions'] += 1
            logger.error(f"基因表达失败 {gene_id}: {e}")
            return None, None
    
    def _execute_functional_gene(self, gene: Gene, protein: Protein) -> None:
        """执行功能基因代码"""
        try:
            # 从基因序列生成功能代码（简化示例）
            code_template = f"""
# 功能基因 {gene.gene_id} 的执行代码
# 蛋白质序列: {protein.sequence[:20]}...

def gene_function():
    # 根据蛋白质序列生成功能
    sequence_length = {len(protein.sequence)}
    catalytic_activity = {protein.catalytic_activity}
    
    # 简化的功能实现
    if sequence_length > 50:
        result = "高活性酶"
    elif sequence_length > 20:
        result = "中等活性酶"
    else:
        result = "低活性酶"
    
    return result

result = gene_function()
"""
            
            # 执行代码
            success, result, message = self.code_executor.execute_code(
                code_template, 
                {'protein': protein, 'gene': gene}
            )
            
            self.stats['code_executions'] += 1
            
            if success:
                # 将执行结果存储到蛋白质中
                protein.functional_result = result
                logger.debug(f"功能基因 {gene.gene_id} 执行成功: {result}")
            else:
                self.stats['execution_errors'] += 1
                logger.warning(f"功能基因 {gene.gene_id} 执行失败: {message}")
        
        except Exception as e:
            self.stats['execution_errors'] += 1
            logger.error(f"执行功能基因 {gene.gene_id} 时出错: {e}")
    
    def express_all_genes(self) -> Dict[str, Tuple[Optional[mRNA], Optional[Protein]]]:
        """表达所有基因"""
        results = {}
        
        for gene_id in self.genes.keys():
            mrna, protein = self.express_gene(gene_id)
            results[gene_id] = (mrna, protein)
        
        logger.info(f"批量基因表达完成，处理了 {len(results)} 个基因")
        return results
    
    def cleanup_old_molecules(self, max_age: float = 600.0) -> None:
        """清理老化分子"""
        current_time = time.time()
        
        # 清理老化的mRNA
        old_mrnas = []
        for mrna_id, mrna in self.mrna_pool.items():
            if hasattr(mrna, 'transcription_time'):
                age = current_time - mrna.transcription_time
                if age > max_age:
                    old_mrnas.append(mrna_id)
        
        for mrna_id in old_mrnas:
            del self.mrna_pool[mrna_id]
        
        # 清理老化的蛋白质
        old_proteins = []
        for protein_id, protein in self.protein_pool.items():
            if hasattr(protein, 'translation_time'):
                age = current_time - protein.translation_time
                if age > max_age * 2:  # 蛋白质寿命更长
                    old_proteins.append(protein_id)
        
        for protein_id in old_proteins:
            del self.protein_pool[protein_id]
        
        if old_mrnas or old_proteins:
            logger.debug(f"清理老化分子: {len(old_mrnas)} mRNA, {len(old_proteins)} 蛋白质")
    
    def get_expression_state(self) -> Dict[str, Any]:
        """获取表达系统状态"""
        return {
            'gene_count': len(self.genes),
            'mrna_count': len(self.mrna_pool),
            'protein_count': len(self.protein_pool),
            'trna_count': len(self.trna_pool),
            'transcription_factor_count': len(self.transcription_factors),
            'hormone_count': len(self.hormones),
            'energy_level': self.energy_level,
            'is_active': self.is_active,
            'transcription_stats': self.transcription_engine.stats.copy(),
            'translation_stats': self.translation_engine.stats.copy(),
            'system_stats': self.stats.copy()
        }
    
    def reset_system(self) -> None:
        """重置系统"""
        self.mrna_pool.clear()
        self.protein_pool.clear()
        self.trna_pool.clear()
        self.transcription_factors.clear()
        self.hormones.clear()
        
        self.energy_level = 1000.0
        self.is_active = True
        
        # 重置统计
        self.stats = {
            'genes_added': len(self.genes),
            'total_expressions': 0,
            'successful_expressions': 0,
            'failed_expressions': 0,
            'code_executions': 0,
            'execution_errors': 0
        }
        
        logger.info("基因表达系统已重置")

if __name__ == "__main__":
    # 测试代码
    logger.info("基因表达系统测试开始")
    
    # 创建基因表达系统
    expression_system = GeneExpressionSystem()
    
    # 添加测试基因
    test_gene_sequence = "ATGAAACUGCUGCUGGGCGCGGGCAAGCUGCUGCUGGGCGCGGGCAAGCUGCUGCUGGGCGCGGGCAAGTAG"
    expression_system.add_gene(
        "test_gene_1", 
        test_gene_sequence, 
        GeneType.PROTEIN_CODING,
        "测试蛋白质编码基因"
    )
    
    # 添加功能基因
    functional_gene_sequence = "ATGGGCAAACUGCUGCUGGGCGCGGGCAAGCUGCUGCUGGGCGCGGGCAAGCUGCUGCUGGGCGCGGGCAAGTAG"
    expression_system.add_gene(
        "functional_gene_1", 
        functional_gene_sequence, 
        GeneType.FUNCTIONAL,
        "功能基因示例"
    )
    
    # 添加tRNA
    amino_acids = ['Met', 'Leu', 'Gly', 'Lys', 'Phe', 'Ser', 'Tyr', 'Cys']
    for aa in amino_acids:
        for i in range(3):  # 每种氨基酸添加3个tRNA
            expression_system.add_trna(aa, f"{aa}_{i}")
    
    # 添加转录因子
    expression_system.add_transcription_factor("TF1", 1.5, ["test_gene_1"])
    expression_system.add_transcription_factor("TF2", 0.8, ["functional_gene_1"])
    
    # 添加激素
    expression_system.add_hormone(
        "growth_hormone", 
        HormoneType.GROWTH_FACTOR, 
        2.0, 
        {"test_gene_1", "functional_gene_1"}
    )
    
    # 表达基因
    logger.info("开始基因表达测试...")
    
    for i in range(5):
        logger.info(f"\n=== 表达轮次 {i+1} ===")
        
        # 表达单个基因
        mrna1, protein1 = expression_system.express_gene("test_gene_1")
        mrna2, protein2 = expression_system.express_gene("functional_gene_1")
        
        # 显示结果
        if mrna1:
            logger.info(f"成功转录 test_gene_1: mRNA {mrna1.molecule_id}")
        if protein1:
            logger.info(f"成功翻译 test_gene_1: 蛋白质 {protein1.molecule_id}")
        
        if mrna2:
            logger.info(f"成功转录 functional_gene_1: mRNA {mrna2.molecule_id}")
        if protein2:
            logger.info(f"成功翻译 functional_gene_1: 蛋白质 {protein2.molecule_id}")
            if hasattr(protein2, 'functional_result'):
                logger.info(f"功能执行结果: {protein2.functional_result}")
        
        time.sleep(0.1)
    
    # 批量表达
    logger.info("\n=== 批量基因表达测试 ===")
    results = expression_system.express_all_genes()
    
    for gene_id, (mrna, protein) in results.items():
        logger.info(f"基因 {gene_id}: mRNA={mrna is not None}, 蛋白质={protein is not None}")
    
    # 显示系统状态
    state = expression_system.get_expression_state()
    logger.info(f"\n=== 系统状态 ===")
    logger.info(f"基因数量: {state['gene_count']}")
    logger.info(f"mRNA数量: {state['mrna_count']}")
    logger.info(f"蛋白质数量: {state['protein_count']}")
    logger.info(f"tRNA数量: {state['trna_count']}")
    logger.info(f"能量水平: {state['energy_level']:.1f}")
    logger.info(f"转录统计: {state['transcription_stats']}")
    logger.info(f"翻译统计: {state['translation_stats']}")
    logger.info(f"系统统计: {state['system_stats']}")
    
    # 清理测试
    logger.info("\n=== 清理测试 ===")
    expression_system.cleanup_old_molecules(1.0)  # 1秒后清理
    
    logger.info("基因表达系统测试完成")