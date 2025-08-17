"""细胞生物学模拟模块 - 实现数字细胞和集体智能涌现

本模块实现了完整的细胞生物学系统，通过基本的生物学操作让集体智能自然涌现：
- DigitalCell: 数字细胞，包含完整的细胞器结构
- 细胞器系统: Nucleus、Mitochondrion、Ribosome、ProteinProcessor
- 生物分子: Gene、mRNA、Protein、Glycoprotein
- 激素系统: 全局信号调控机制
- 细胞间互动: 基于糖蛋白的识别和交互
- 虚拟世界: 环境管理和细胞生态系统

注意：本模块不包含任何人为的意识模拟，所有智能行为都通过基本生物学操作自然涌现。
"""

import logging
import random
import time
import json
import uuid
import math
from typing import Dict, List, Any, Optional, Tuple, Set, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict, deque
import numpy as np

logger = logging.getLogger(__name__)

# 全局常量
BASE_METABOLIC_RATE = 1.0  # 基础代谢率
MAX_ENERGY_LEVEL = 200.0   # 最大能量水平
MIN_ENERGY_LEVEL = 0.0     # 最小能量水平
DEFAULT_EFFICIENCY = 1.0   # 默认效率

class HormoneType(Enum):
    """激素类型枚举"""
    STRESS = "stress"                    # 压力激素
    GROWTH = "growth"                    # 生长激素
    RESOURCE_SCARCITY = "resource_scarcity"  # 资源稀缺激素
    COOPERATION = "cooperation"          # 合作激素
    COMPETITION = "competition"          # 竞争激素
    REPRODUCTION = "reproduction"        # 繁殖激素
    IMMUNE = "immune"                    # 免疫激素
    NEUROTRANSMITTER = "neurotransmitter"  # 神经递质

class ProteinType(Enum):
    """蛋白质类型枚举"""
    METABOLIC = "metabolic"              # 代谢蛋白
    STRUCTURAL = "structural"            # 结构蛋白
    REGULATORY = "regulatory"            # 调节蛋白
    TRANSPORT = "transport"              # 运输蛋白
    DEFENSE = "defense"                  # 防御蛋白
    SIGNALING = "signaling"              # 信号蛋白
    SURFACE = "surface"                  # 表面蛋白
    ENZYME = "enzyme"                    # 酶蛋白

class CellState(Enum):
    """细胞状态枚举"""
    HEALTHY = "healthy"                  # 健康
    STRESSED = "stressed"                # 压力状态
    GROWING = "growing"                  # 生长状态
    REPRODUCING = "reproducing"          # 繁殖状态
    DYING = "dying"                      # 死亡状态
    COOPERATING = "cooperating"          # 合作状态
    COMPETING = "competing"              # 竞争状态

@dataclass
class Gene:
    """基因类 - 遗传信息的基本单位
    
    基因包含编码信息和调控信息，可以被转录为mRNA。
    """
    id: str
    sequence: str                        # 基因序列（编码信息）
    promoter_strength: float = 1.0       # 启动子强度（影响转录率）
    regulatory_elements: Dict[str, float] = field(default_factory=dict)  # 调控元件
    protein_type: ProteinType = ProteinType.METABOLIC
    expression_level: float = 0.0        # 当前表达水平
    mutation_rate: float = 0.01          # 变异率
    
    def __post_init__(self):
        """初始化后处理"""
        logger.debug(f"[GENE_DEBUG] 创建基因 {self.id}, 类型: {self.protein_type.value}")
    
    def can_be_transcribed(self, hormones: Dict[str, float]) -> bool:
        """检查基因是否可以被转录
        
        Args:
            hormones: 当前激素水平
            
        Returns:
            是否可以转录
        """
        # 基础转录概率
        transcription_probability = self.promoter_strength
        
        # 激素调控
        for hormone_type, level in hormones.items():
            if hormone_type in self.regulatory_elements:
                regulation_factor = self.regulatory_elements[hormone_type]
                transcription_probability *= (1.0 + regulation_factor * level)
        
        # 随机性
        can_transcribe = random.random() < transcription_probability
        
        logger.debug(f"[GENE_DEBUG] 基因 {self.id} 转录检查: {can_transcribe}, 概率: {transcription_probability:.3f}")
        return can_transcribe
    
    def mutate(self) -> 'Gene':
        """基因变异
        
        Returns:
            变异后的基因副本
        """
        if random.random() < self.mutation_rate:
            # 创建变异副本
            mutated_gene = Gene(
                id=f"{self.id}_mut_{random.randint(1000, 9999)}",
                sequence=self._mutate_sequence(self.sequence),
                promoter_strength=max(0.1, min(2.0, self.promoter_strength + random.gauss(0, 0.1))),
                regulatory_elements=self.regulatory_elements.copy(),
                protein_type=self.protein_type,
                mutation_rate=self.mutation_rate
            )
            
            logger.debug(f"[GENE_DEBUG] 基因 {self.id} 发生变异 -> {mutated_gene.id}")
            return mutated_gene
        
        return self
    
    def _mutate_sequence(self, sequence: str) -> str:
        """序列变异
        
        Args:
            sequence: 原始序列
            
        Returns:
            变异后的序列
        """
        if not sequence:
            return sequence
        
        # 简单的点突变
        sequence_list = list(sequence)
        mutation_count = max(1, int(len(sequence) * 0.01))  # 1%的位点发生变异
        
        for _ in range(mutation_count):
            pos = random.randint(0, len(sequence_list) - 1)
            # 随机替换字符
            sequence_list[pos] = random.choice('ATCG')
        
        return ''.join(sequence_list)

@dataclass
class mRNA:
    """信使RNA类 - 基因转录产物
    
    mRNA携带基因的编码信息，可以被翻译为蛋白质。
    """
    id: str
    gene_id: str                         # 来源基因ID
    sequence: str                        # mRNA序列
    stability: float = 1.0               # 稳定性（影响降解速度）
    translation_efficiency: float = 1.0  # 翻译效率
    creation_time: float = field(default_factory=time.time)
    
    def __post_init__(self):
        """初始化后处理"""
        logger.debug(f"[MRNA_DEBUG] 创建mRNA {self.id}, 来源基因: {self.gene_id}")
    
    def is_degraded(self, current_time: float) -> bool:
        """检查mRNA是否已降解
        
        Args:
            current_time: 当前时间
            
        Returns:
            是否已降解
        """
        age = current_time - self.creation_time
        degradation_probability = 1.0 - math.exp(-age / (self.stability * 10.0))
        
        is_degraded = random.random() < degradation_probability
        
        if is_degraded:
            logger.debug(f"[MRNA_DEBUG] mRNA {self.id} 已降解, 年龄: {age:.2f}")
        
        return is_degraded

@dataclass
class Protein:
    """蛋白质类 - 功能执行单元
    
    蛋白质是细胞的功能执行者，可以执行各种生物学功能。
    """
    id: str
    gene_id: str                         # 来源基因ID
    protein_type: ProteinType
    function_code: str                   # 功能代码（可执行逻辑）
    activity_level: float = 1.0          # 活性水平
    stability: float = 1.0               # 稳定性
    energy_cost: float = 1.0             # 执行能量消耗
    metadata: Dict[str, Any] = field(default_factory=dict)
    creation_time: float = field(default_factory=time.time)
    
    def __post_init__(self):
        """初始化后处理"""
        logger.debug(f"[PROTEIN_DEBUG] 创建蛋白质 {self.id}, 类型: {self.protein_type.value}")
    
    def execute_function(self, cell_context: Dict[str, Any]) -> Dict[str, Any]:
        """执行蛋白质功能
        
        Args:
            cell_context: 细胞上下文信息
            
        Returns:
            执行结果
        """
        logger.debug(f"[PROTEIN_DEBUG] 蛋白质 {self.id} 开始执行功能")
        
        try:
            # 根据蛋白质类型执行不同功能
            if self.protein_type == ProteinType.METABOLIC:
                return self._execute_metabolic_function(cell_context)
            elif self.protein_type == ProteinType.SIGNALING:
                return self._execute_signaling_function(cell_context)
            elif self.protein_type == ProteinType.DEFENSE:
                return self._execute_defense_function(cell_context)
            elif self.protein_type == ProteinType.TRANSPORT:
                return self._execute_transport_function(cell_context)
            else:
                return self._execute_generic_function(cell_context)
                
        except Exception as e:
            logger.error(f"[PROTEIN_DEBUG] 蛋白质 {self.id} 执行失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def _execute_metabolic_function(self, cell_context: Dict[str, Any]) -> Dict[str, Any]:
        """执行代谢功能"""
        energy_production = self.activity_level * 5.0
        return {
            'success': True,
            'energy_produced': energy_production,
            'function_type': 'metabolic'
        }
    
    def _execute_signaling_function(self, cell_context: Dict[str, Any]) -> Dict[str, Any]:
        """执行信号功能"""
        hormone_type = self.metadata.get('hormone_type', 'stress')
        hormone_amount = self.activity_level * 0.1
        
        return {
            'success': True,
            'hormone_secreted': {hormone_type: hormone_amount},
            'function_type': 'signaling'
        }
    
    def _execute_defense_function(self, cell_context: Dict[str, Any]) -> Dict[str, Any]:
        """执行防御功能"""
        defense_strength = self.activity_level * 2.0
        return {
            'success': True,
            'defense_boost': defense_strength,
            'function_type': 'defense'
        }
    
    def _execute_transport_function(self, cell_context: Dict[str, Any]) -> Dict[str, Any]:
        """执行运输功能"""
        transport_efficiency = self.activity_level * 1.5
        return {
            'success': True,
            'transport_efficiency': transport_efficiency,
            'function_type': 'transport'
        }
    
    def _execute_generic_function(self, cell_context: Dict[str, Any]) -> Dict[str, Any]:
        """执行通用功能"""
        return {
            'success': True,
            'generic_effect': self.activity_level,
            'function_type': 'generic'
        }
    
    def is_degraded(self, current_time: float) -> bool:
        """检查蛋白质是否已降解"""
        age = current_time - self.creation_time
        degradation_probability = 1.0 - math.exp(-age / (self.stability * 20.0))
        
        is_degraded = random.random() < degradation_probability
        
        if is_degraded:
            logger.debug(f"[PROTEIN_DEBUG] 蛋白质 {self.id} 已降解, 年龄: {age:.2f}")
        
        return is_degraded

@dataclass
class Glycoprotein:
    """糖蛋白类 - 用于细胞识别与交互
    
    糖蛋白基于蛋白质，附加糖链模式，用于细胞间的识别和交互。
    """
    protein_base: Protein
    glycan_pattern: str                  # 糖链模式（细胞身份标识）
    binding_affinity: float = 1.0       # 结合亲和力
    
    def __post_init__(self):
        """初始化后处理"""
        logger.debug(f"[GLYCOPROTEIN_DEBUG] 创建糖蛋白，基础蛋白: {self.protein_base.id}, 糖链: {self.glycan_pattern}")
    
    def check_compatibility(self, other_glycoprotein: 'Glycoprotein') -> float:
        """检查与另一个糖蛋白的兼容性
        
        Args:
            other_glycoprotein: 另一个糖蛋白
            
        Returns:
            兼容性分数 (0-1)
        """
        # 简单的模式匹配算法
        pattern1 = self.glycan_pattern
        pattern2 = other_glycoprotein.glycan_pattern
        
        if not pattern1 or not pattern2:
            return 0.0
        
        # 计算相似度
        min_len = min(len(pattern1), len(pattern2))
        matches = sum(1 for i in range(min_len) if pattern1[i] == pattern2[i])
        
        similarity = matches / max(len(pattern1), len(pattern2))
        compatibility = similarity * self.binding_affinity * other_glycoprotein.binding_affinity
        
        logger.debug(f"[GLYCOPROTEIN_DEBUG] 糖蛋白兼容性检查: {compatibility:.3f}")
        return compatibility

class Nucleus:
    """细胞核 - 基因组管理中心
    
    细胞核管理细胞的遗传信息，控制基因表达。
    """
    
    def __init__(self, genome: Dict[str, Gene]):
        """初始化细胞核
        
        Args:
            genome: 基因组字典
        """
        self.genome = genome
        self.active_genes: Set[str] = set()
        self.transcription_factors: Dict[str, float] = {}
        
        logger.debug(f"[NUCLEUS_DEBUG] 初始化细胞核，基因数量: {len(genome)}")
    
    def regulate_gene_expression(self, hormones: Dict[str, float]) -> List[str]:
        """调控基因表达
        
        Args:
            hormones: 激素水平
            
        Returns:
            活跃基因ID列表
        """
        logger.debug(f"[NUCLEUS_DEBUG] 开始基因表达调控，激素水平: {hormones}")
        
        self.active_genes.clear()
        
        for gene_id, gene in self.genome.items():
            if gene.can_be_transcribed(hormones):
                self.active_genes.add(gene_id)
                gene.expression_level = min(1.0, gene.expression_level + 0.1)
            else:
                gene.expression_level = max(0.0, gene.expression_level - 0.05)
        
        logger.debug(f"[NUCLEUS_DEBUG] 活跃基因数量: {len(self.active_genes)}")
        return list(self.active_genes)
    
    def get_gene(self, gene_id: str) -> Optional[Gene]:
        """获取基因
        
        Args:
            gene_id: 基因ID
            
        Returns:
            基因对象或None
        """
        return self.genome.get(gene_id)
    
    def add_gene(self, gene: Gene):
        """添加基因
        
        Args:
            gene: 基因对象
        """
        self.genome[gene.id] = gene
        logger.debug(f"[NUCLEUS_DEBUG] 添加基因: {gene.id}")
    
    def mutate_genome(self) -> Dict[str, Gene]:
        """基因组变异
        
        Returns:
            变异后的基因组
        """
        mutated_genome = {}
        
        for gene_id, gene in self.genome.items():
            mutated_gene = gene.mutate()
            mutated_genome[mutated_gene.id] = mutated_gene
        
        logger.debug(f"[NUCLEUS_DEBUG] 基因组变异完成")
        return mutated_genome

class Mitochondrion:
    """线粒体 - 细胞能量工厂
    
    线粒体负责细胞的能量生产和消耗管理。
    """
    
    def __init__(self, efficiency: float = DEFAULT_EFFICIENCY):
        """初始化线粒体
        
        Args:
            efficiency: 能量转换效率
        """
        self.efficiency = efficiency
        self.energy_level = 100.0  # 初始能量
        self.max_energy = MAX_ENERGY_LEVEL
        self.energy_production_rate = 5.0
        self.maintenance_cost = 0.5
        
        logger.debug(f"[MITOCHONDRION_DEBUG] 初始化线粒体，效率: {efficiency}, 初始能量: {self.energy_level}")
    
    def consume_energy(self, amount: float) -> bool:
        """消耗能量
        
        Args:
            amount: 消耗量
            
        Returns:
            是否成功消耗
        """
        cost = amount / self.efficiency
        
        if self.energy_level >= cost:
            self.energy_level -= cost
            logger.debug(f"[MITOCHONDRION_DEBUG] 消耗能量 {cost:.2f}, 剩余: {self.energy_level:.2f}")
            return True
        else:
            logger.debug(f"[MITOCHONDRION_DEBUG] 能量不足，需要: {cost:.2f}, 剩余: {self.energy_level:.2f}")
            return False
    
    def produce_energy(self, amount: float):
        """生产能量
        
        Args:
            amount: 生产量
        """
        produced = amount * self.efficiency
        self.energy_level = min(self.max_energy, self.energy_level + produced)
        
        logger.debug(f"[MITOCHONDRION_DEBUG] 生产能量 {produced:.2f}, 当前: {self.energy_level:.2f}")
    
    def metabolic_cycle(self) -> float:
        """代谢周期
        
        Returns:
            净能量变化
        """
        # 基础能量生产
        base_production = self.energy_production_rate * self.efficiency
        self.produce_energy(base_production)
        
        # 维持成本
        maintenance_consumed = self.consume_energy(self.maintenance_cost)
        
        net_change = base_production - (self.maintenance_cost / self.efficiency if maintenance_consumed else 0)
        
        logger.debug(f"[MITOCHONDRION_DEBUG] 代谢周期完成，净变化: {net_change:.2f}")
        return net_change
    
    def get_energy_ratio(self) -> float:
        """获取能量比例
        
        Returns:
            能量比例 (0-1)
        """
        return self.energy_level / self.max_energy
    
    def is_energy_critical(self) -> bool:
        """检查能量是否处于危险水平
        
        Returns:
            是否能量危险
        """
        return self.energy_level < (self.max_energy * 0.2)

class Ribosome:
    """核糖体 - mRNA翻译器
    
    核糖体将mRNA翻译为蛋白质。
    """
    
    def __init__(self):
        """初始化核糖体"""
        self.translation_rate = 1.0
        self.error_rate = 0.01
        
        logger.debug(f"[RIBOSOME_DEBUG] 初始化核糖体")
    
    def translate(self, mrna: mRNA, gene: Gene, mitochondrion: Mitochondrion) -> Optional[Protein]:
        """翻译mRNA为蛋白质
        
        Args:
            mrna: mRNA对象
            gene: 对应的基因
            mitochondrion: 线粒体（提供能量）
            
        Returns:
            翻译产生的蛋白质或None
        """
        logger.debug(f"[RIBOSOME_DEBUG] 开始翻译mRNA {mrna.id}")
        
        # 检查能量
        translation_energy_cost = 2.0
        if not mitochondrion.consume_energy(translation_energy_cost):
            logger.debug(f"[RIBOSOME_DEBUG] 翻译失败：能量不足")
            return None
        
        # 翻译错误检查
        if random.random() < self.error_rate:
            logger.debug(f"[RIBOSOME_DEBUG] 翻译错误，产生错误蛋白质")
            return None
        
        # 创建蛋白质
        protein = Protein(
            id=f"protein_{mrna.id}_{random.randint(1000, 9999)}",
            gene_id=gene.id,
            protein_type=gene.protein_type,
            function_code=self._generate_function_code(gene),
            activity_level=mrna.translation_efficiency * self.translation_rate,
            stability=1.0 + random.gauss(0, 0.1),
            energy_cost=1.0 + random.gauss(0, 0.2),
            metadata=self._generate_protein_metadata(gene)
        )
        
        logger.debug(f"[RIBOSOME_DEBUG] 翻译完成，产生蛋白质: {protein.id}")
        return protein
    
    def _generate_function_code(self, gene: Gene) -> str:
        """生成蛋白质功能代码
        
        Args:
            gene: 基因对象
            
        Returns:
            功能代码字符串
        """
        # 基于基因序列生成简单的功能代码
        return f"function_{gene.protein_type.value}_{hash(gene.sequence) % 10000}"
    
    def _generate_protein_metadata(self, gene: Gene) -> Dict[str, Any]:
        """生成蛋白质元数据
        
        Args:
            gene: 基因对象
            
        Returns:
            元数据字典
        """
        metadata = {
            'source_gene': gene.id,
            'protein_family': gene.protein_type.value
        }
        
        # 根据蛋白质类型添加特定元数据
        if gene.protein_type == ProteinType.SURFACE:
            metadata['is_surface_protein'] = True
            metadata['membrane_location'] = 'outer'
        elif gene.protein_type == ProteinType.SIGNALING:
            metadata['hormone_type'] = random.choice(list(HormoneType)).value
        
        return metadata

class ProteinProcessor:
    """蛋白质处理器 - 模拟高尔基体/内质网
    
    对新生成的蛋白质进行后处理，包括糖基化等修饰。
    """
    
    def __init__(self):
        """初始化蛋白质处理器"""
        self.glycosylation_rate = 0.3  # 糖基化概率
        
        logger.debug(f"[PROTEIN_PROCESSOR_DEBUG] 初始化蛋白质处理器")
    
    def process(self, protein: Protein, cell_state: Dict[str, Any]) -> Union[Protein, Glycoprotein]:
        """处理蛋白质
        
        Args:
            protein: 原始蛋白质
            cell_state: 细胞状态
            
        Returns:
            处理后的蛋白质或糖蛋白
        """
        logger.debug(f"[PROTEIN_PROCESSOR_DEBUG] 开始处理蛋白质 {protein.id}")
        
        # 检查是否需要糖基化
        if self._should_glycosylate(protein, cell_state):
            glycan_pattern = self._generate_glycan_pattern(cell_state)
            glycoprotein = Glycoprotein(
                protein_base=protein,
                glycan_pattern=glycan_pattern,
                binding_affinity=1.0 + random.gauss(0, 0.1)
            )
            
            logger.debug(f"[PROTEIN_PROCESSOR_DEBUG] 蛋白质 {protein.id} 糖基化为糖蛋白")
            return glycoprotein
        
        # 其他修饰（暂时返回原蛋白质）
        logger.debug(f"[PROTEIN_PROCESSOR_DEBUG] 蛋白质 {protein.id} 处理完成（无修饰）")
        return protein
    
    def _should_glycosylate(self, protein: Protein, cell_state: Dict[str, Any]) -> bool:
        """判断是否应该糖基化
        
        Args:
            protein: 蛋白质对象
            cell_state: 细胞状态
            
        Returns:
            是否应该糖基化
        """
        # 表面蛋白更容易糖基化
        if protein.metadata.get('is_surface_protein', False):
            return random.random() < (self.glycosylation_rate * 2.0)
        
        # 信号蛋白也可能糖基化
        if protein.protein_type == ProteinType.SIGNALING:
            return random.random() < self.glycosylation_rate
        
        return random.random() < (self.glycosylation_rate * 0.5)
    
    def _generate_glycan_pattern(self, cell_state: Dict[str, Any]) -> str:
        """生成糖链模式
        
        Args:
            cell_state: 细胞状态
            
        Returns:
            糖链模式字符串
        """
        # 基于细胞状态生成糖链模式
        base_pattern = cell_state.get('cell_id', 'unknown')[:4]
        
        # 添加随机变化
        pattern_chars = list('ABCDEFGH')
        pattern_length = random.randint(4, 8)
        
        pattern = base_pattern + ''.join(random.choices(pattern_chars, k=pattern_length - len(base_pattern)))
        
        logger.debug(f"[PROTEIN_PROCESSOR_DEBUG] 生成糖链模式: {pattern}")
        return pattern

class HormoneSystem:
    """激素系统 - 全局信号调控
    
    管理全局激素水平，影响所有细胞的行为。
    """
    
    def __init__(self):
        """初始化激素系统"""
        self.hormones: Dict[str, float] = {
            hormone_type.value: 0.0 for hormone_type in HormoneType
        }
        self.decay_rate = 0.95  # 激素衰减率
        self.max_hormone_level = 10.0
        
        logger.debug(f"[HORMONE_SYSTEM_DEBUG] 初始化激素系统")
    
    def add_hormone(self, hormone_type: str, amount: float):
        """添加激素
        
        Args:
            hormone_type: 激素类型
            amount: 激素量
        """
        if hormone_type in self.hormones:
            self.hormones[hormone_type] = min(
                self.max_hormone_level,
                self.hormones[hormone_type] + amount
            )
            
            logger.debug(f"[HORMONE_SYSTEM_DEBUG] 添加激素 {hormone_type}: +{amount:.3f}, 当前: {self.hormones[hormone_type]:.3f}")
    
    def decay_hormones(self):
        """激素衰减"""
        for hormone_type in self.hormones:
            old_level = self.hormones[hormone_type]
            self.hormones[hormone_type] *= self.decay_rate
            
            if old_level > 0.01:  # 只记录显著变化
                logger.debug(f"[HORMONE_SYSTEM_DEBUG] 激素 {hormone_type} 衰减: {old_level:.3f} -> {self.hormones[hormone_type]:.3f}")
    
    def get_hormone_levels(self) -> Dict[str, float]:
        """获取激素水平
        
        Returns:
            激素水平字典
        """
        return self.hormones.copy()
    
    def environmental_hormone_production(self, environment_state: Dict[str, Any]):
        """环境激素产生
        
        Args:
            environment_state: 环境状态
        """
        # 资源稀缺时产生压力激素
        resource_level = environment_state.get('resource_level', 1.0)
        if resource_level < 0.5:
            stress_amount = (0.5 - resource_level) * 2.0
            self.add_hormone(HormoneType.STRESS.value, stress_amount)
            self.add_hormone(HormoneType.RESOURCE_SCARCITY.value, stress_amount)
        
        # 环境变化产生适应激素
        change_rate = environment_state.get('change_rate', 0.0)
        if change_rate > 0.3:
            self.add_hormone(HormoneType.STRESS.value, change_rate * 0.5)
        
        # 种群密度影响
        population_density = environment_state.get('population_density', 0.5)
        if population_density > 0.8:
            self.add_hormone(HormoneType.COMPETITION.value, (population_density - 0.8) * 5.0)
        elif population_density < 0.3:
            self.add_hormone(HormoneType.COOPERATION.value, (0.3 - population_density) * 3.0)
        
        logger.debug(f"[HORMONE_SYSTEM_DEBUG] 环境激素产生完成")

class DigitalCell:
    """数字细胞 - 完整的细胞生物学模拟单元
    
    数字细胞包含完整的细胞器结构和生物学功能，通过基本的生物学操作
    实现复杂的行为和集体智能的涌现。
    """
    
    def __init__(self, cell_id: str, initial_genome: Dict[str, Gene], 
                 initial_energy: float = 100.0):
        """初始化数字细胞
        
        Args:
            cell_id: 细胞唯一标识
            initial_genome: 初始基因组
            initial_energy: 初始能量
        """
        self.cell_id = cell_id
        self.state = CellState.HEALTHY
        self.age = 0.0
        self.generation = 0
        
        # 细胞器初始化
        self.nucleus = Nucleus(initial_genome)
        self.mitochondrion = Mitochondrion(efficiency=1.0 + random.gauss(0, 0.1))
        self.ribosome = Ribosome()
        self.protein_processor = ProteinProcessor()
        
        # 设置初始能量
        self.mitochondrion.energy_level = initial_energy
        
        # 生物分子存储
        self.mrnas: Dict[str, mRNA] = {}
        self.proteins: Dict[str, Union[Protein, Glycoprotein]] = {}
        self.surface_glycoproteins: Dict[str, Glycoprotein] = {}
        
        # 细胞状态
        self.stress_level = 0.0
        self.growth_rate = 1.0
        self.reproduction_readiness = 0.0
        self.cooperation_tendency = 0.5
        self.competition_tendency = 0.5
        
        # 交互历史
        self.interaction_history: List[Dict[str, Any]] = []
        self.neighbor_cells: Set[str] = set()
        
        # 行为统计
        self.behavior_stats = {
            'energy_produced': 0.0,
            'proteins_synthesized': 0,
            'interactions_count': 0,
            'cooperation_events': 0,
            'competition_events': 0
        }
        
        logger.debug(f"[CELL_DEBUG] 初始化数字细胞 {cell_id}")
    
    def update(self, hormone_levels: Dict[str, float], 
               environment_state: Dict[str, Any]) -> Dict[str, Any]:
        """细胞更新周期
        
        Args:
            hormone_levels: 全局激素水平
            environment_state: 环境状态
            
        Returns:
            细胞状态更新结果
        """
        logger.debug(f"[CELL_DEBUG] 细胞 {self.cell_id} 开始更新周期")
        
        update_result = {
            'cell_id': self.cell_id,
            'energy_change': 0.0,
            'proteins_produced': [],
            'hormones_secreted': {},
            'state_changes': [],
            'interactions': []
        }
        
        try:
            # 1. 代谢周期
            energy_change = self.mitochondrion.metabolic_cycle()
            update_result['energy_change'] = energy_change
            self.behavior_stats['energy_produced'] += max(0, energy_change)
            
            # 2. 基因表达调控
            active_genes = self.nucleus.regulate_gene_expression(hormone_levels)
            
            # 3. 转录过程
            new_mrnas = self._transcribe_genes(active_genes)
            
            # 4. 翻译过程
            new_proteins = self._translate_mrnas()
            update_result['proteins_produced'] = [p.id for p in new_proteins]
            
            # 5. 蛋白质处理
            processed_proteins = self._process_proteins(new_proteins)
            
            # 6. 蛋白质功能执行
            function_results = self._execute_protein_functions()
            
            # 7. 激素分泌
            secreted_hormones = self._secrete_hormones(function_results)
            update_result['hormones_secreted'] = secreted_hormones
            
            # 8. 细胞状态更新
            state_changes = self._update_cell_state(hormone_levels, environment_state)
            update_result['state_changes'] = state_changes
            
            # 9. 分子降解
            self._degrade_molecules()
            
            # 10. 年龄增长
            self.age += 1.0
            
            logger.debug(f"[CELL_DEBUG] 细胞 {self.cell_id} 更新完成")
            
        except Exception as e:
            logger.error(f"[CELL_DEBUG] 细胞 {self.cell_id} 更新失败: {e}")
            update_result['error'] = str(e)
        
        return update_result
    
    def _transcribe_genes(self, active_genes: List[str]) -> List[mRNA]:
        """转录活跃基因
        
        Args:
            active_genes: 活跃基因ID列表
            
        Returns:
            新产生的mRNA列表
        """
        new_mrnas = []
        
        for gene_id in active_genes:
            gene = self.nucleus.get_gene(gene_id)
            if gene and self.mitochondrion.consume_energy(1.0):  # 转录消耗能量
                mrna = mRNA(
                    id=f"mrna_{gene_id}_{random.randint(1000, 9999)}",
                    gene_id=gene_id,
                    sequence=gene.sequence,
                    stability=1.0 + random.gauss(0, 0.1),
                    translation_efficiency=gene.expression_level
                )
                
                self.mrnas[mrna.id] = mrna
                new_mrnas.append(mrna)
                
                logger.debug(f"[CELL_DEBUG] 转录产生mRNA {mrna.id}")
        
        return new_mrnas
    
    def _translate_mrnas(self) -> List[Protein]:
        """翻译mRNA为蛋白质
        
        Returns:
            新产生的蛋白质列表
        """
        new_proteins = []
        
        for mrna in list(self.mrnas.values()):
            gene = self.nucleus.get_gene(mrna.gene_id)
            if gene:
                protein = self.ribosome.translate(mrna, gene, self.mitochondrion)
                if protein:
                    self.proteins[protein.id] = protein
                    new_proteins.append(protein)
                    self.behavior_stats['proteins_synthesized'] += 1
                    
                    logger.debug(f"[CELL_DEBUG] 翻译产生蛋白质 {protein.id}")
        
        return new_proteins
    
    def _process_proteins(self, proteins: List[Protein]) -> List[Union[Protein, Glycoprotein]]:
        """处理新生成的蛋白质
        
        Args:
            proteins: 新生成的蛋白质列表
            
        Returns:
            处理后的蛋白质/糖蛋白列表
        """
        processed_proteins = []
        
        cell_state = {
            'cell_id': self.cell_id,
            'state': self.state.value,
            'energy_level': self.mitochondrion.energy_level
        }
        
        for protein in proteins:
            processed = self.protein_processor.process(protein, cell_state)
            
            # 更新存储
            self.proteins[protein.id] = processed
            
            # 如果是糖蛋白且是表面蛋白，添加到表面糖蛋白
            if isinstance(processed, Glycoprotein) and processed.protein_base.metadata.get('is_surface_protein', False):
                self.surface_glycoproteins[processed.protein_base.id] = processed
                logger.debug(f"[CELL_DEBUG] 添加表面糖蛋白 {processed.protein_base.id}")
            
            processed_proteins.append(processed)
        
        return processed_proteins
    
    def _execute_protein_functions(self) -> List[Dict[str, Any]]:
        """执行蛋白质功能
        
        Returns:
            蛋白质功能执行结果列表
        """
        function_results = []
        
        cell_context = {
            'cell_id': self.cell_id,
            'energy_level': self.mitochondrion.energy_level,
            'state': self.state.value,
            'age': self.age
        }
        
        for protein_id, protein_obj in self.proteins.items():
            if isinstance(protein_obj, Glycoprotein):
                protein = protein_obj.protein_base
            else:
                protein = protein_obj
            
            # 检查能量是否足够
            if self.mitochondrion.consume_energy(protein.energy_cost):
                result = protein.execute_function(cell_context)
                result['protein_id'] = protein_id
                function_results.append(result)
                
                logger.debug(f"[CELL_DEBUG] 执行蛋白质 {protein_id} 功能: {result.get('function_type', 'unknown')}")
        
        return function_results
    
    def _secrete_hormones(self, function_results: List[Dict[str, Any]]) -> Dict[str, float]:
        """分泌激素
        
        Args:
            function_results: 蛋白质功能执行结果
            
        Returns:
            分泌的激素字典
        """
        secreted_hormones = defaultdict(float)
        
        for result in function_results:
            if result.get('success') and 'hormone_secreted' in result:
                for hormone_type, amount in result['hormone_secreted'].items():
                    secreted_hormones[hormone_type] += amount
        
        # 基于细胞状态分泌激素
        if self.state == CellState.STRESSED:
            secreted_hormones[HormoneType.STRESS.value] += 0.1
        elif self.state == CellState.COOPERATING:
            secreted_hormones[HormoneType.COOPERATION.value] += 0.05
        elif self.state == CellState.COMPETING:
            secreted_hormones[HormoneType.COMPETITION.value] += 0.05
        
        # 能量危险时分泌压力激素
        if self.mitochondrion.is_energy_critical():
            secreted_hormones[HormoneType.STRESS.value] += 0.2
            secreted_hormones[HormoneType.RESOURCE_SCARCITY.value] += 0.1
        
        logger.debug(f"[CELL_DEBUG] 细胞 {self.cell_id} 分泌激素: {dict(secreted_hormones)}")
        return dict(secreted_hormones)
    
    def _update_cell_state(self, hormone_levels: Dict[str, float], 
                          environment_state: Dict[str, Any]) -> List[str]:
        """更新细胞状态
        
        Args:
            hormone_levels: 激素水平
            environment_state: 环境状态
            
        Returns:
            状态变化列表
        """
        state_changes = []
        old_state = self.state
        
        # 基于激素水平调整状态
        stress_level = hormone_levels.get(HormoneType.STRESS.value, 0.0)
        cooperation_level = hormone_levels.get(HormoneType.COOPERATION.value, 0.0)
        competition_level = hormone_levels.get(HormoneType.COMPETITION.value, 0.0)
        
        # 更新内部倾向
        self.stress_level = stress_level
        self.cooperation_tendency = min(1.0, self.cooperation_tendency + cooperation_level * 0.1)
        self.competition_tendency = min(1.0, self.competition_tendency + competition_level * 0.1)
        
        # 状态转换逻辑
        if stress_level > 0.5 or self.mitochondrion.is_energy_critical():
            self.state = CellState.STRESSED
        elif cooperation_level > competition_level and cooperation_level > 0.3:
            self.state = CellState.COOPERATING
        elif competition_level > cooperation_level and competition_level > 0.3:
            self.state = CellState.COMPETING
        elif self.mitochondrion.get_energy_ratio() > 0.8 and self.age < 50:
            self.state = CellState.GROWING
        else:
            self.state = CellState.HEALTHY
        
        # 检查死亡条件
        if (self.mitochondrion.energy_level <= 0 or 
            self.age > 200 or 
            stress_level > 2.0):
            self.state = CellState.DYING
        
        if old_state != self.state:
            state_changes.append(f"{old_state.value} -> {self.state.value}")
            logger.debug(f"[CELL_DEBUG] 细胞 {self.cell_id} 状态变化: {old_state.value} -> {self.state.value}")
        
        return state_changes
    
    def _degrade_molecules(self):
        """分子降解过程"""
        current_time = time.time()
        
        # mRNA降解
        degraded_mrnas = []
        for mrna_id, mrna in self.mrnas.items():
            if mrna.is_degraded(current_time):
                degraded_mrnas.append(mrna_id)
        
        for mrna_id in degraded_mrnas:
            del self.mrnas[mrna_id]
            logger.debug(f"[CELL_DEBUG] mRNA {mrna_id} 已降解")
        
        # 蛋白质降解
        degraded_proteins = []
        for protein_id, protein_obj in self.proteins.items():
            if isinstance(protein_obj, Glycoprotein):
                protein = protein_obj.protein_base
            else:
                protein = protein_obj
            
            if protein.is_degraded(current_time):
                degraded_proteins.append(protein_id)
        
        for protein_id in degraded_proteins:
            if protein_id in self.surface_glycoproteins:
                del self.surface_glycoproteins[protein_id]
            del self.proteins[protein_id]
            logger.debug(f"[CELL_DEBUG] 蛋白质 {protein_id} 已降解")
    
    def interact_with_cell(self, other_cell: 'DigitalCell') -> Dict[str, Any]:
        """与另一个细胞交互
        
        Args:
            other_cell: 另一个细胞
            
        Returns:
            交互结果
        """
        logger.debug(f"[CELL_DEBUG] 细胞 {self.cell_id} 与 {other_cell.cell_id} 开始交互")
        
        interaction_result = {
            'interaction_type': 'none',
            'compatibility': 0.0,
            'energy_transfer': 0.0,
            'information_exchange': False,
            'cooperation_established': False,
            'competition_occurred': False
        }
        
        # 计算细胞兼容性
        compatibility = self._calculate_cell_compatibility(other_cell)
        interaction_result['compatibility'] = compatibility
        
        # 基于兼容性和细胞状态决定交互类型
        if compatibility > 0.7 and (self.state == CellState.COOPERATING or 
                                   other_cell.state == CellState.COOPERATING):
            # 合作交互
            interaction_result.update(self._cooperate_with_cell(other_cell))
            self.behavior_stats['cooperation_events'] += 1
            
        elif compatibility < 0.3 or (self.state == CellState.COMPETING or 
                                    other_cell.state == CellState.COMPETING):
            # 竞争交互
            interaction_result.update(self._compete_with_cell(other_cell))
            self.behavior_stats['competition_events'] += 1
            
        else:
            # 中性交互
            interaction_result.update(self._neutral_interaction(other_cell))
        
        # 记录交互历史
        self.interaction_history.append({
            'timestamp': time.time(),
            'other_cell': other_cell.cell_id,
            'result': interaction_result
        })
        
        self.neighbor_cells.add(other_cell.cell_id)
        self.behavior_stats['interactions_count'] += 1
        
        logger.debug(f"[CELL_DEBUG] 交互完成: {interaction_result['interaction_type']}")
        return interaction_result
    
    def _calculate_cell_compatibility(self, other_cell: 'DigitalCell') -> float:
        """计算细胞兼容性
        
        Args:
            other_cell: 另一个细胞
            
        Returns:
            兼容性分数 (0-1)
        """
        if not self.surface_glycoproteins or not other_cell.surface_glycoproteins:
            return 0.5  # 默认中等兼容性
        
        compatibility_scores = []
        
        # 比较表面糖蛋白
        for gp1 in self.surface_glycoproteins.values():
            for gp2 in other_cell.surface_glycoproteins.values():
                score = gp1.check_compatibility(gp2)
                compatibility_scores.append(score)
        
        if compatibility_scores:
            avg_compatibility = sum(compatibility_scores) / len(compatibility_scores)
        else:
            avg_compatibility = 0.5
        
        # 考虑细胞状态的影响
        state_modifier = 1.0
        if self.state == other_cell.state:
            state_modifier = 1.2  # 相同状态增加兼容性
        elif (self.state == CellState.COMPETING and other_cell.state == CellState.COOPERATING) or \
             (self.state == CellState.COOPERATING and other_cell.state == CellState.COMPETING):
            state_modifier = 0.8  # 对立状态降低兼容性
        
        final_compatibility = min(1.0, avg_compatibility * state_modifier)
        
        logger.debug(f"[CELL_DEBUG] 细胞兼容性: {final_compatibility:.3f}")
        return final_compatibility
    
    def _cooperate_with_cell(self, other_cell: 'DigitalCell') -> Dict[str, Any]:
        """与细胞合作
        
        Args:
            other_cell: 合作对象
            
        Returns:
            合作结果
        """
        cooperation_result = {
            'interaction_type': 'cooperation',
            'energy_transfer': 0.0,
            'information_exchange': True,
            'cooperation_established': True
        }
        
        # 能量共享（能量多的帮助能量少的）
        my_energy_ratio = self.mitochondrion.get_energy_ratio()
        other_energy_ratio = other_cell.mitochondrion.get_energy_ratio()
        
        if my_energy_ratio > other_energy_ratio + 0.2:
            # 我帮助对方
            transfer_amount = min(10.0, (my_energy_ratio - other_energy_ratio) * 20.0)
            if self.mitochondrion.consume_energy(transfer_amount):
                other_cell.mitochondrion.produce_energy(transfer_amount * 0.8)  # 传输损失
                cooperation_result['energy_transfer'] = transfer_amount
                logger.debug(f"[CELL_DEBUG] 能量转移: {self.cell_id} -> {other_cell.cell_id}, 量: {transfer_amount:.2f}")
        
        elif other_energy_ratio > my_energy_ratio + 0.2:
            # 对方帮助我
            transfer_amount = min(10.0, (other_energy_ratio - my_energy_ratio) * 20.0)
            if other_cell.mitochondrion.consume_energy(transfer_amount):
                self.mitochondrion.produce_energy(transfer_amount * 0.8)
                cooperation_result['energy_transfer'] = -transfer_amount  # 负值表示接受
                logger.debug(f"[CELL_DEBUG] 能量转移: {other_cell.cell_id} -> {self.cell_id}, 量: {transfer_amount:.2f}")
        
        # 信息交换（基因/蛋白质信息共享）
        if random.random() < 0.3:  # 30%概率进行信息交换
            self._exchange_genetic_information(other_cell)
        
        return cooperation_result
    
    def _compete_with_cell(self, other_cell: 'DigitalCell') -> Dict[str, Any]:
        """与细胞竞争
        
        Args:
            other_cell: 竞争对象
            
        Returns:
            竞争结果
        """
        competition_result = {
            'interaction_type': 'competition',
            'energy_transfer': 0.0,
            'competition_occurred': True,
            'winner': None
        }
        
        # 简单的竞争机制：比较总体实力
        my_strength = self._calculate_cell_strength()
        other_strength = other_cell._calculate_cell_strength()
        
        if my_strength > other_strength:
            # 我获胜，获得一些资源
            energy_gain = min(5.0, other_strength * 0.1)
            self.mitochondrion.produce_energy(energy_gain)
            other_cell.mitochondrion.consume_energy(energy_gain * 0.5)
            
            competition_result['energy_transfer'] = energy_gain
            competition_result['winner'] = self.cell_id
            
            logger.debug(f"[CELL_DEBUG] 竞争获胜: {self.cell_id} vs {other_cell.cell_id}")
            
        elif other_strength > my_strength:
            # 对方获胜
            energy_loss = min(5.0, my_strength * 0.1)
            other_cell.mitochondrion.produce_energy(energy_loss)
            self.mitochondrion.consume_energy(energy_loss * 0.5)
            
            competition_result['energy_transfer'] = -energy_loss
            competition_result['winner'] = other_cell.cell_id
            
            logger.debug(f"[CELL_DEBUG] 竞争失败: {self.cell_id} vs {other_cell.cell_id}")
        
        return competition_result
    
    def _neutral_interaction(self, other_cell: 'DigitalCell') -> Dict[str, Any]:
        """中性交互
        
        Args:
            other_cell: 交互对象
            
        Returns:
            交互结果
        """
        return {
            'interaction_type': 'neutral',
            'information_exchange': random.random() < 0.1  # 10%概率交换信息
        }
    
    def _calculate_cell_strength(self) -> float:
        """计算细胞实力
        
        Returns:
            实力值
        """
        strength = 0.0
        
        # 能量水平
        strength += self.mitochondrion.get_energy_ratio() * 30.0
        
        # 蛋白质数量和质量
        strength += len(self.proteins) * 2.0
        
        # 基因组大小
        strength += len(self.nucleus.genome) * 1.0
        
        # 年龄因子（年轻有优势，但太年轻经验不足）
        age_factor = 1.0
        if self.age < 10:
            age_factor = 0.8  # 太年轻
        elif self.age > 100:
            age_factor = 0.9  # 老化
        
        strength *= age_factor
        
        return strength
    
    def _exchange_genetic_information(self, other_cell: 'DigitalCell'):
        """交换遗传信息
        
        Args:
            other_cell: 交换对象
        """
        # 简单的基因交换机制
        my_genes = list(self.nucleus.genome.keys())
        other_genes = list(other_cell.nucleus.genome.keys())
        
        if my_genes and other_genes:
            # 随机选择一个基因进行交换
            if random.random() < 0.5 and len(other_genes) > 0:
                # 获得对方的一个基因
                gene_id = random.choice(other_genes)
                gene_copy = other_cell.nucleus.get_gene(gene_id)
                if gene_copy:
                    # 创建基因副本
                    new_gene = Gene(
                        id=f"{gene_copy.id}_copy_{self.cell_id}",
                        sequence=gene_copy.sequence,
                        promoter_strength=gene_copy.promoter_strength,
                        regulatory_elements=gene_copy.regulatory_elements.copy(),
                        protein_type=gene_copy.protein_type,
                        mutation_rate=gene_copy.mutation_rate
                    )
                    self.nucleus.add_gene(new_gene)
                    
                    logger.debug(f"[CELL_DEBUG] 基因交换: {other_cell.cell_id} -> {self.cell_id}, 基因: {gene_id}")
    
    def reproduce(self) -> Optional['DigitalCell']:
        """细胞繁殖
        
        Returns:
            新的子细胞或None
        """
        # 检查繁殖条件
        if (self.state != CellState.DYING and 
            self.mitochondrion.get_energy_ratio() > 0.7 and 
            len(self.proteins) > 5 and 
            self.age > 20):
            
            # 消耗能量进行繁殖
            reproduction_cost = self.mitochondrion.max_energy * 0.4
            if self.mitochondrion.consume_energy(reproduction_cost):
                
                # 创建变异的基因组
                mutated_genome = self.nucleus.mutate_genome()
                
                # 创建子细胞
                child_cell = DigitalCell(
                    cell_id=f"{self.cell_id}_child_{random.randint(1000, 9999)}",
                    initial_genome=mutated_genome,
                    initial_energy=self.mitochondrion.energy_level * 0.3
                )
                
                child_cell.generation = self.generation + 1
                
                # 继承一些特性
                child_cell.cooperation_tendency = self.cooperation_tendency + random.gauss(0, 0.1)
                child_cell.competition_tendency = self.competition_tendency + random.gauss(0, 0.1)
                
                # 限制在合理范围内
                child_cell.cooperation_tendency = max(0.0, min(1.0, child_cell.cooperation_tendency))
                child_cell.competition_tendency = max(0.0, min(1.0, child_cell.competition_tendency))
                
                logger.debug(f"[CELL_DEBUG] 细胞 {self.cell_id} 繁殖产生 {child_cell.cell_id}")
                return child_cell
        
        return None
    
    def get_status(self) -> Dict[str, Any]:
        """获取细胞状态
        
        Returns:
            细胞状态字典
        """
        return {
            'cell_id': self.cell_id,
            'state': self.state.value,
            'age': self.age,
            'generation': self.generation,
            'energy_level': self.mitochondrion.energy_level,
            'energy_ratio': self.mitochondrion.get_energy_ratio(),
            'genome_size': len(self.nucleus.genome),
            'active_genes': len(self.nucleus.active_genes),
            'mrna_count': len(self.mrnas),
            'protein_count': len(self.proteins),
            'surface_glycoproteins': len(self.surface_glycoproteins),
            'stress_level': self.stress_level,
            'cooperation_tendency': self.cooperation_tendency,
            'competition_tendency': self.competition_tendency,
            'neighbor_count': len(self.neighbor_cells),
            'behavior_stats': self.behavior_stats.copy()
        }
    
    def is_alive(self) -> bool:
        """检查细胞是否存活
        
        Returns:
            是否存活
        """
        return self.state != CellState.DYING and self.mitochondrion.energy_level > 0

class VirtualWorld:
    """虚拟世界 - 细胞生态系统环境
    
    管理细胞群体、环境条件、资源分配和生态系统动力学。
    """
    
    def __init__(self, world_size: Tuple[int, int] = (100, 100), 
                 initial_resources: float = 1000.0):
        """初始化虚拟世界
        
        Args:
            world_size: 世界大小 (宽度, 高度)
            initial_resources: 初始资源量
        """
        self.world_size = world_size
        self.cells: Dict[str, DigitalCell] = {}
        self.hormone_system = HormoneSystem()
        
        # 环境状态
        self.total_resources = initial_resources
        self.resource_regeneration_rate = 10.0
        self.environmental_pressure = 0.0
        self.complexity_level = 0.5
        
        # 统计信息
        self.cycle_count = 0
        self.population_history: List[int] = []
        self.resource_history: List[float] = []
        self.cooperation_events: List[Dict[str, Any]] = []
        self.competition_events: List[Dict[str, Any]] = []
        
        # 生态系统指标
        self.biodiversity_index = 0.0
        self.cooperation_index = 0.0
        self.competition_index = 0.0
        self.collective_intelligence_score = 0.0
        
        logger.debug(f"[WORLD_DEBUG] 初始化虚拟世界，大小: {world_size}, 初始资源: {initial_resources}")
    
    def add_cell(self, cell: DigitalCell):
        """添加细胞到世界
        
        Args:
            cell: 要添加的细胞
        """
        self.cells[cell.cell_id] = cell
        logger.debug(f"[WORLD_DEBUG] 添加细胞 {cell.cell_id} 到世界")
    
    def remove_cell(self, cell_id: str):
        """从世界移除细胞
        
        Args:
            cell_id: 要移除的细胞ID
        """
        if cell_id in self.cells:
            del self.cells[cell_id]
            logger.debug(f"[WORLD_DEBUG] 从世界移除细胞 {cell_id}")
    
    def update_world(self) -> Dict[str, Any]:
        """更新世界状态
        
        Returns:
            世界更新结果
        """
        self.cycle_count += 1
        logger.debug(f"[WORLD_DEBUG] 开始世界更新周期 #{self.cycle_count}")
        
        update_result = {
            'cycle': self.cycle_count,
            'population': len(self.cells),
            'alive_cells': 0,
            'total_energy': 0.0,
            'total_proteins': 0,
            'interactions': 0,
            'births': 0,
            'deaths': 0,
            'hormone_levels': {},
            'ecosystem_metrics': {}
        }
        
        try:
            # 1. 环境激素产生
            environment_state = self._get_environment_state()
            self.hormone_system.environmental_hormone_production(environment_state)
            
            # 2. 更新所有细胞
            cell_updates = self._update_all_cells(environment_state)
            
            # 3. 处理细胞间交互
            interactions = self._process_cell_interactions()
            update_result['interactions'] = len(interactions)
            
            # 4. 处理细胞繁殖
            new_cells = self._process_cell_reproduction()
            update_result['births'] = len(new_cells)
            
            # 5. 移除死亡细胞
            dead_cells = self._remove_dead_cells()
            update_result['deaths'] = len(dead_cells)
            
            # 6. 资源管理
            self._manage_resources()
            
            # 7. 激素衰减
            self.hormone_system.decay_hormones()
            
            # 8. 计算生态系统指标
            ecosystem_metrics = self._calculate_ecosystem_metrics()
            update_result['ecosystem_metrics'] = ecosystem_metrics
            
            # 9. 更新统计信息
            self._update_statistics(update_result)
            
            # 10. 收集最终统计
            alive_cells = [cell for cell in self.cells.values() if cell.is_alive()]
            update_result['alive_cells'] = len(alive_cells)
            update_result['total_energy'] = sum(cell.mitochondrion.energy_level for cell in alive_cells)
            update_result['total_proteins'] = sum(len(cell.proteins) for cell in alive_cells)
            update_result['hormone_levels'] = self.hormone_system.get_hormone_levels()
            
            logger.debug(f"[WORLD_DEBUG] 世界更新完成，存活细胞: {update_result['alive_cells']}")
            
        except Exception as e:
            logger.error(f"[WORLD_DEBUG] 世界更新失败: {e}")
            update_result['error'] = str(e)
        
        return update_result
    
    def _get_environment_state(self) -> Dict[str, Any]:
        """获取环境状态
        
        Returns:
            环境状态字典
        """
        population_density = len(self.cells) / (self.world_size[0] * self.world_size[1] / 100)
        resource_level = min(1.0, self.total_resources / 1000.0)
        
        return {
            'population_density': population_density,
            'resource_level': resource_level,
            'environmental_pressure': self.environmental_pressure,
            'complexity_level': self.complexity_level,
            'change_rate': self._calculate_change_rate()
        }
    
    def _calculate_change_rate(self) -> float:
        """计算环境变化率
        
        Returns:
            变化率
        """
        if len(self.population_history) < 2:
            return 0.0
        
        current_pop = self.population_history[-1]
        previous_pop = self.population_history[-2]
        
        if previous_pop == 0:
            return 1.0 if current_pop > 0 else 0.0
        
        change_rate = abs(current_pop - previous_pop) / previous_pop
        return min(1.0, change_rate)
    
    def _update_all_cells(self, environment_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """更新所有细胞
        
        Args:
            environment_state: 环境状态
            
        Returns:
            细胞更新结果列表
        """
        cell_updates = []
        hormone_levels = self.hormone_system.get_hormone_levels()
        
        for cell in list(self.cells.values()):
            if cell.is_alive():
                update_result = cell.update(hormone_levels, environment_state)
                cell_updates.append(update_result)
                
                # 收集细胞分泌的激素
                if 'hormones_secreted' in update_result:
                    for hormone_type, amount in update_result['hormones_secreted'].items():
                        self.hormone_system.add_hormone(hormone_type, amount)
        
        return cell_updates
    
    def _process_cell_interactions(self) -> List[Dict[str, Any]]:
        """处理细胞间交互
        
        Returns:
            交互结果列表
        """
        interactions = []
        alive_cells = [cell for cell in self.cells.values() if cell.is_alive()]
        
        # 随机配对进行交互
        random.shuffle(alive_cells)
        
        for i in range(0, len(alive_cells) - 1, 2):
            cell1 = alive_cells[i]
            cell2 = alive_cells[i + 1]
            
            # 检查是否应该交互（基于距离、状态等）
            if self._should_cells_interact(cell1, cell2):
                interaction_result = cell1.interact_with_cell(cell2)
                interactions.append(interaction_result)
                
                # 记录合作和竞争事件
                if interaction_result['interaction_type'] == 'cooperation':
                    self.cooperation_events.append({
                        'cycle': self.cycle_count,
                        'cells': [cell1.cell_id, cell2.cell_id],
                        'result': interaction_result
                    })
                elif interaction_result['interaction_type'] == 'competition':
                    self.competition_events.append({
                        'cycle': self.cycle_count,
                        'cells': [cell1.cell_id, cell2.cell_id],
                        'result': interaction_result
                    })
        
        return interactions
    
    def _should_cells_interact(self, cell1: DigitalCell, cell2: DigitalCell) -> bool:
        """判断两个细胞是否应该交互
        
        Args:
            cell1: 细胞1
            cell2: 细胞2
            
        Returns:
            是否应该交互
        """
        # 基本交互概率
        base_probability = 0.3
        
        # 状态影响
        if (cell1.state in [CellState.COOPERATING, CellState.COMPETING] or 
            cell2.state in [CellState.COOPERATING, CellState.COMPETING]):
            base_probability += 0.3
        
        # 能量水平影响
        if (cell1.mitochondrion.is_energy_critical() or 
            cell2.mitochondrion.is_energy_critical()):
            base_probability += 0.2
        
        return random.random() < base_probability
    
    def _process_cell_reproduction(self) -> List[DigitalCell]:
        """处理细胞繁殖
        
        Returns:
            新生细胞列表
        """
        new_cells = []
        
        for cell in list(self.cells.values()):
            if cell.is_alive():
                child_cell = cell.reproduce()
                if child_cell:
                    self.add_cell(child_cell)
                    new_cells.append(child_cell)
        
        return new_cells
    
    def _remove_dead_cells(self) -> List[str]:
        """移除死亡细胞
        
        Returns:
            死亡细胞ID列表
        """
        dead_cells = []
        
        for cell_id, cell in list(self.cells.items()):
            if not cell.is_alive():
                dead_cells.append(cell_id)
                self.remove_cell(cell_id)
        
        return dead_cells
    
    def _manage_resources(self):
        """管理世界资源"""
        # 资源再生
        self.total_resources += self.resource_regeneration_rate
        
        # 资源消耗（基于细胞数量）
        resource_consumption = len(self.cells) * 0.5
        self.total_resources = max(0.0, self.total_resources - resource_consumption)
        
        # 资源稀缺影响环境压力
        if self.total_resources < 100.0:
            self.environmental_pressure = min(1.0, self.environmental_pressure + 0.1)
        else:
            self.environmental_pressure = max(0.0, self.environmental_pressure - 0.05)
    
    def _calculate_ecosystem_metrics(self) -> Dict[str, float]:
        """计算生态系统指标
        
        Returns:
            生态系统指标字典
        """
        alive_cells = [cell for cell in self.cells.values() if cell.is_alive()]
        
        if not alive_cells:
            return {
                'biodiversity_index': 0.0,
                'cooperation_index': 0.0,
                'competition_index': 0.0,
                'collective_intelligence_score': 0.0,
                'average_age': 0.0,
                'average_energy': 0.0
            }
        
        # 生物多样性指数（基于基因组差异）
        genome_sizes = [len(cell.nucleus.genome) for cell in alive_cells]
        biodiversity = np.std(genome_sizes) / (np.mean(genome_sizes) + 1e-6) if genome_sizes else 0.0
        
        # 合作指数
        total_cooperation = sum(cell.behavior_stats['cooperation_events'] for cell in alive_cells)
        cooperation_index = total_cooperation / max(len(alive_cells), 1)
        
        # 竞争指数
        total_competition = sum(cell.behavior_stats['competition_events'] for cell in alive_cells)
        competition_index = total_competition / max(len(alive_cells), 1)
        
        # 集体智能分数（基于交互复杂性和协调性）
        total_interactions = sum(cell.behavior_stats['interactions_count'] for cell in alive_cells)
        avg_interactions = total_interactions / max(len(alive_cells), 1)
        
        # 考虑合作与竞争的平衡
        balance_factor = 1.0 - abs(cooperation_index - competition_index) / max(cooperation_index + competition_index, 1.0)
        
        collective_intelligence = (avg_interactions * 0.4 + 
                                 cooperation_index * 0.3 + 
                                 biodiversity * 0.2 + 
                                 balance_factor * 0.1)
        
        # 其他指标
        average_age = sum(cell.age for cell in alive_cells) / len(alive_cells)
        average_energy = sum(cell.mitochondrion.energy_level for cell in alive_cells) / len(alive_cells)
        
        metrics = {
            'biodiversity_index': float(biodiversity),
            'cooperation_index': float(cooperation_index),
            'competition_index': float(competition_index),
            'collective_intelligence_score': float(collective_intelligence),
            'average_age': float(average_age),
            'average_energy': float(average_energy)
        }
        
        # 更新实例变量
        self.biodiversity_index = metrics['biodiversity_index']
        self.cooperation_index = metrics['cooperation_index']
        self.competition_index = metrics['competition_index']
        self.collective_intelligence_score = metrics['collective_intelligence_score']
        
        return metrics
    
    def _update_statistics(self, update_result: Dict[str, Any]):
        """更新统计信息
        
        Args:
            update_result: 更新结果
        """
        self.population_history.append(update_result['population'])
        self.resource_history.append(self.total_resources)
        
        # 保持历史记录在合理长度
        max_history_length = 1000
        if len(self.population_history) > max_history_length:
            self.population_history = self.population_history[-max_history_length:]
        if len(self.resource_history) > max_history_length:
            self.resource_history = self.resource_history[-max_history_length:]
        
        # 清理旧的事件记录
        cutoff_cycle = self.cycle_count - 100
        self.cooperation_events = [e for e in self.cooperation_events if e['cycle'] > cutoff_cycle]
        self.competition_events = [e for e in self.competition_events if e['cycle'] > cutoff_cycle]
    
    def get_world_status(self) -> Dict[str, Any]:
        """获取世界状态
        
        Returns:
            世界状态字典
        """
        alive_cells = [cell for cell in self.cells.values() if cell.is_alive()]
        
        return {
            'cycle_count': self.cycle_count,
            'world_size': self.world_size,
            'total_cells': len(self.cells),
            'alive_cells': len(alive_cells),
            'total_resources': self.total_resources,
            'environmental_pressure': self.environmental_pressure,
            'complexity_level': self.complexity_level,
            'hormone_levels': self.hormone_system.get_hormone_levels(),
            'ecosystem_metrics': {
                'biodiversity_index': self.biodiversity_index,
                'cooperation_index': self.cooperation_index,
                'competition_index': self.competition_index,
                'collective_intelligence_score': self.collective_intelligence_score
            },
            'population_trend': self.population_history[-10:] if self.population_history else [],
            'resource_trend': self.resource_history[-10:] if self.resource_history else [],
            'recent_cooperation_events': len([e for e in self.cooperation_events if e['cycle'] > self.cycle_count - 10]),
            'recent_competition_events': len([e for e in self.competition_events if e['cycle'] > self.cycle_count - 10])
        }
    
    def create_initial_population(self, population_size: int, 
                                base_genome: Optional[Dict[str, Gene]] = None) -> List[DigitalCell]:
        """创建初始种群
        
        Args:
            population_size: 种群大小
            base_genome: 基础基因组（可选）
            
        Returns:
            创建的细胞列表
        """
        if base_genome is None:
            base_genome = self._create_default_genome()
        
        created_cells = []
        
        for i in range(population_size):
            # 为每个细胞创建略有不同的基因组
            cell_genome = {}
            for gene_id, gene in base_genome.items():
                mutated_gene = gene.mutate() if random.random() < 0.3 else gene
                cell_genome[mutated_gene.id] = mutated_gene
            
            cell = DigitalCell(
                cell_id=f"cell_{i:04d}",
                initial_genome=cell_genome,
                initial_energy=80.0 + random.gauss(0, 20.0)
            )
            
            # 随机化一些初始特性
            cell.cooperation_tendency = random.uniform(0.2, 0.8)
            cell.competition_tendency = random.uniform(0.2, 0.8)
            
            self.add_cell(cell)
            created_cells.append(cell)
        
        logger.debug(f"[WORLD_DEBUG] 创建初始种群，大小: {population_size}")
        return created_cells
    
    def _create_default_genome(self) -> Dict[str, Gene]:
        """创建默认基因组
        
        Returns:
            默认基因组字典
        """
        default_genes = {}
        
        # 基础代谢基因
        default_genes['metabolic_1'] = Gene(
            id='metabolic_1',
            sequence='ATCGATCGATCG' * 10,
            promoter_strength=1.0,
            protein_type=ProteinType.METABOLIC,
            regulatory_elements={HormoneType.STRESS.value: -0.2}
        )
        
        # 信号基因
        default_genes['signaling_1'] = Gene(
            id='signaling_1',
            sequence='GCTAGCTAGCTA' * 8,
            promoter_strength=0.8,
            protein_type=ProteinType.SIGNALING,
            regulatory_elements={HormoneType.COOPERATION.value: 0.3}
        )
        
        # 防御基因
        default_genes['defense_1'] = Gene(
            id='defense_1',
            sequence='TGCATGCATGCA' * 6,
            promoter_strength=0.6,
            protein_type=ProteinType.DEFENSE,
            regulatory_elements={HormoneType.STRESS.value: 0.5}
        )
        
        # 表面蛋白基因
        default_genes['surface_1'] = Gene(
            id='surface_1',
            sequence='ACGTACGTACGT' * 12,
            promoter_strength=0.7,
            protein_type=ProteinType.SURFACE,
            regulatory_elements={HormoneType.COOPERATION.value: 0.2}
        )
        
        # 运输蛋白基因
        default_genes['transport_1'] = Gene(
            id='transport_1',
            sequence='CGATCGATCGAT' * 9,
            promoter_strength=0.9,
            protein_type=ProteinType.TRANSPORT,
            regulatory_elements={HormoneType.RESOURCE_SCARCITY.value: 0.4}
        )
        
        return default_genes

# 工厂函数
def create_digital_cell(cell_id: str, genome_size: int = 5) -> DigitalCell:
    """创建数字细胞的工厂函数
    
    Args:
        cell_id: 细胞ID
        genome_size: 基因组大小
        
    Returns:
        创建的数字细胞
    """
    # 创建随机基因组
    genome = {}
    protein_types = list(ProteinType)
    
    for i in range(genome_size):
        protein_type = random.choice(protein_types)
        gene = Gene(
            id=f"gene_{i:03d}",
            sequence=''.join(random.choices('ATCG', k=random.randint(50, 200))),
            promoter_strength=random.uniform(0.5, 1.5),
            protein_type=protein_type,
            regulatory_elements={
                random.choice(list(HormoneType)).value: random.uniform(-0.5, 0.5)
                for _ in range(random.randint(1, 3))
            }
        )
        genome[gene.id] = gene
    
    return DigitalCell(cell_id, genome)

def create_virtual_world(world_size: Tuple[int, int] = (50, 50), 
                        initial_population: int = 20) -> VirtualWorld:
    """创建虚拟世界的工厂函数
    
    Args:
        world_size: 世界大小
        initial_population: 初始种群大小
        
    Returns:
        创建的虚拟世界
    """
    world = VirtualWorld(world_size)
    world.create_initial_population(initial_population)
    
    return world

# 导出的主要类和函数
__all__ = [
    # 枚举
    'HormoneType', 'ProteinType', 'CellState',
    # 生物分子
    'Gene', 'mRNA', 'Protein', 'Glycoprotein',
    # 细胞器
    'Nucleus', 'Mitochondrion', 'Ribosome', 'ProteinProcessor',
    # 系统
    'HormoneSystem', 'DigitalCell', 'VirtualWorld',
    # 工厂函数
    'create_digital_cell', 'create_virtual_world'
]