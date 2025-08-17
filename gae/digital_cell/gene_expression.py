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
        decay_factor = 0.5