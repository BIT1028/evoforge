# -*- coding: utf-8 -*-
"""
DigitalCell数字细胞系统 - EvoForge核心组件

根据comprehensive_implementation_plan.md重新实现的数字细胞系统，包括：
- DigitalCell类：3D空间物理模拟器
- 细胞器系统：Nucleus、Mitochondrion、Ribosome、ProteinProcessor
- 分子容器和索引系统
- 细胞生命周期循环：分子运动、交互、表达、催化、降解
- 糖蛋白系统：细胞间识别和交互
"""

import numpy as np
import uuid
import logging
import threading
import time
from typing import Dict, List, Optional, Tuple, Any, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
import random
import math
from abc import ABC, abstractmethod
from collections import defaultdict, deque
import json

# 导入分子系统
from .macro_molecule import (
    MacroMolecule, MoleculeType, Vector3D, BindingSite, BindingSiteType,
    Protein, mRNA, tRNA, Lipid, ResourceToken, EnergyToken, create_molecule
)
from .physics_engine import PhysicsEngine, PhysicsConstants

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class OrganelleType(Enum):
    """细胞器类型"""
    NUCLEUS = "nucleus"
    MITOCHONDRION = "mitochondrion"
    RIBOSOME = "ribosome"
    PROTEIN_PROCESSOR = "protein_processor"
    MEMBRANE = "membrane"
    CYTOPLASM = "cytoplasm"

class CellState(Enum):
    """细胞状态"""
    HEALTHY = "healthy"
    STRESSED = "stressed"
    DIVIDING = "dividing"
    DYING = "dying"
    DEAD = "dead"

@dataclass
class SpatialIndex:
    """3D空间索引系统"""
    grid_size: float = 10.0
    bounds: Tuple[Vector3D, Vector3D] = field(default_factory=lambda: (Vector3D(-100, -100, -100), Vector3D(100, 100, 100)))
    grid: Dict[Tuple[int, int, int], Set[str]] = field(default_factory=lambda: defaultdict(set))
    
    def get_grid_coord(self, position: Vector3D) -> Tuple[int, int, int]:
        """获取网格坐标"""
        return (
            int(position.x // self.grid_size),
            int(position.y // self.grid_size),
            int(position.z // self.grid_size)
        )
    
    def add_molecule(self, molecule_id: str, position: Vector3D) -> None:
        """添加分子到空间索引"""
        grid_coord = self.get_grid_coord(position)
        self.grid[grid_coord].add(molecule_id)
    
    def remove_molecule(self, molecule_id: str, position: Vector3D) -> None:
        """从空间索引移除分子"""
        grid_coord = self.get_grid_coord(position)
        self.grid[grid_coord].discard(molecule_id)
    
    def update_molecule_position(self, molecule_id: str, old_pos: Vector3D, new_pos: Vector3D) -> None:
        """更新分子位置"""
        old_coord = self.get_grid_coord(old_pos)
        new_coord = self.get_grid_coord(new_pos)
        
        if old_coord != new_coord:
            self.grid[old_coord].discard(molecule_id)
            self.grid[new_coord].add(molecule_id)
    
    def get_nearby_molecules(self, position: Vector3D, radius: float = 20.0) -> Set[str]:
        """获取附近的分子"""
        nearby = set()
        grid_radius = int(math.ceil(radius / self.grid_size))
        center_coord = self.get_grid_coord(position)
        
        for dx in range(-grid_radius, grid_radius + 1):
            for dy in range(-grid_radius, grid_radius + 1):
                for dz in range(-grid_radius, grid_radius + 1):
                    coord = (
                        center_coord[0] + dx,
                        center_coord[1] + dy,
                        center_coord[2] + dz
                    )
                    nearby.update(self.grid.get(coord, set()))
        
        return nearby

class Organelle(ABC):
    """细胞器基础类"""
    
    def __init__(self, 
                 organelle_id: Optional[str] = None,
                 position: Optional[Vector3D] = None,
                 size: float = 10.0):
        self.organelle_id = organelle_id or str(uuid.uuid4())
        self.position = position or Vector3D()
        self.size = size
        self.is_active = True
        self.energy_level = 100.0
        self.efficiency = 1.0
        
        # 细胞器内分子容器
        self.internal_molecules: Dict[str, MacroMolecule] = {}
        self.processing_queue: deque = deque()
        
        logger.debug(f"创建细胞器 {self.get_organelle_type().value}，ID: {self.organelle_id}")
    
    @abstractmethod
    def get_organelle_type(self) -> OrganelleType:
        """获取细胞器类型"""
        pass
    
    @abstractmethod
    def process_molecules(self, dt: float, cell_context: 'DigitalCell') -> List[MacroMolecule]:
        """处理分子，返回产生的新分子"""
        pass
    
    def can_accept_molecule(self, molecule: MacroMolecule) -> bool:
        """检查是否可以接受分子"""
        return self.is_active and len(self.internal_molecules) < 1000
    
    def accept_molecule(self, molecule: MacroMolecule) -> bool:
        """接受分子"""
        if not self.can_accept_molecule(molecule):
            return False
        
        self.internal_molecules[molecule.molecule_id] = molecule
        self.processing_queue.append(molecule.molecule_id)
        
        logger.debug(f"细胞器 {self.organelle_id} 接受分子 {molecule.molecule_id}")
        return True
    
    def release_molecule(self, molecule_id: str) -> Optional[MacroMolecule]:
        """释放分子"""
        if molecule_id in self.internal_molecules:
            molecule = self.internal_molecules.pop(molecule_id)
            logger.debug(f"细胞器 {self.organelle_id} 释放分子 {molecule_id}")
            return molecule
        return None
    
    def update_energy(self, energy_change: float) -> None:
        """更新能量水平"""
        self.energy_level = max(0.0, min(100.0, self.energy_level + energy_change))
        self.efficiency = self.energy_level / 100.0

class Nucleus(Organelle):
    """细胞核"""
    
    def __init__(self, **kwargs):
        super().__init__(size=20.0, **kwargs)
        self.dna_sequences: Dict[str, str] = {}  # 基因序列
        self.transcription_factors: Dict[str, float] = {}  # 转录因子
        self.chromatin_state = "open"  # 染色质状态
        self.transcription_rate = 0.1
    
    def get_organelle_type(self) -> OrganelleType:
        return OrganelleType.NUCLEUS
    
    def add_gene(self, gene_id: str, sequence: str) -> None:
        """添加基因序列"""
        self.dna_sequences[gene_id] = sequence
        logger.debug(f"细胞核添加基因 {gene_id}，长度: {len(sequence)}")
    
    def transcribe_gene(self, gene_id: str) -> Optional[mRNA]:
        """转录基因"""
        if gene_id not in self.dna_sequences:
            return None
        
        if self.energy_level < 10.0:
            return None
        
        # 检查转录因子
        transcription_probability = self.transcription_rate * self.efficiency
        if gene_id in self.transcription_factors:
            transcription_probability *= self.transcription_factors[gene_id]
        
        if random.random() < transcription_probability:
            dna_sequence = self.dna_sequences[gene_id]
            # DNA转录为mRNA（T替换为U）
            mrna_sequence = dna_sequence.replace('T', 'U')
            
            mrna = create_molecule(
                MoleculeType.MRNA,
                sequence=mrna_sequence,
                coding_region=(0, len(mrna_sequence)),
                position=self.position
            )
            
            # 消耗能量
            self.update_energy(-5.0)
            
            logger.debug(f"细胞核转录基因 {gene_id} -> mRNA {mrna.molecule_id}")
            return mrna
        
        return None
    
    def process_molecules(self, dt: float, cell_context: 'DigitalCell') -> List[MacroMolecule]:
        """处理分子"""
        produced_molecules = []
        
        # 处理转录请求
        while self.processing_queue and len(produced_molecules) < 10:
            molecule_id = self.processing_queue.popleft()
            if molecule_id in self.internal_molecules:
                molecule = self.internal_molecules[molecule_id]
                
                # 如果是转录因子蛋白质，更新转录因子水平
                if isinstance(molecule, Protein) and hasattr(molecule, 'target_gene'):
                    target_gene = getattr(molecule, 'target_gene')
                    self.transcription_factors[target_gene] = molecule.catalytic_activity
        
        # 自发转录
        if random.random() < 0.1 * dt:  # 10%概率每秒
            for gene_id in list(self.dna_sequences.keys())[:3]:  # 限制同时转录的基因数
                mrna = self.transcribe_gene(gene_id)
                if mrna:
                    produced_molecules.append(mrna)
        
        return produced_molecules

class Mitochondrion(Organelle):
    """线粒体"""
    
    def __init__(self, **kwargs):
        super().__init__(size=8.0, **kwargs)
        self.atp_production_rate = 2.0
        self.oxygen_level = 100.0
        self.glucose_level = 100.0
    
    def get_organelle_type(self) -> OrganelleType:
        return OrganelleType.MITOCHONDRION
    
    def produce_atp(self, glucose_consumed: float, oxygen_consumed: float) -> List[EnergyToken]:
        """产生ATP"""
        if self.glucose_level < glucose_consumed or self.oxygen_level < oxygen_consumed:
            return []
        
        # 消耗葡萄糖和氧气
        self.glucose_level -= glucose_consumed
        self.oxygen_level -= oxygen_consumed
        
        # 产生ATP（简化的细胞呼吸）
        atp_count = int(glucose_consumed * 30)  # 1个葡萄糖产生约30个ATP
        atp_molecules = []
        
        for _ in range(min(atp_count, 10)):  # 限制同时产生的ATP数量
            atp = create_molecule(
                MoleculeType.ENERGY_TOKEN,
                energy_value=30.0,
                energy_type="ATP",
                position=self.position
            )
            atp_molecules.append(atp)
        
        logger.debug(f"线粒体 {self.organelle_id} 产生 {len(atp_molecules)} 个ATP")
        return atp_molecules
    
    def process_molecules(self, dt: float, cell_context: 'DigitalCell') -> List[MacroMolecule]:
        """处理分子"""
        produced_molecules = []
        
        # 处理资源分子
        glucose_consumed = 0.0
        oxygen_consumed = 0.0
        
        while self.processing_queue:
            molecule_id = self.processing_queue.popleft()
            if molecule_id in self.internal_molecules:
                molecule = self.internal_molecules[molecule_id]
                
                if isinstance(molecule, ResourceToken):
                    if molecule.resource_type == "glucose":
                        glucose_consumed += molecule.consume()
                    elif molecule.resource_type == "oxygen":
                        oxygen_consumed += molecule.consume()
                    
                    # 移除消耗完的分子
                    if not molecule.is_active:
                        self.release_molecule(molecule_id)
        
        # 产生ATP
        if glucose_consumed > 0 and oxygen_consumed > 0:
            atp_molecules = self.produce_atp(glucose_consumed, oxygen_consumed)
            produced_molecules.extend(atp_molecules)
        
        # 自动补充氧气和葡萄糖（简化）
        self.oxygen_level = min(100.0, self.oxygen_level + 1.0 * dt)
        self.glucose_level = min(100.0, self.glucose_level + 0.5 * dt)
        
        return produced_molecules

class Ribosome(Organelle):
    """核糖体"""
    
    def __init__(self, **kwargs):
        super().__init__(size=3.0, **kwargs)
        self.translation_rate = 0.2
        self.current_mrna: Optional[mRNA] = None
        self.translation_position = 0
        self.amino_acid_sequence = []
    
    def get_organelle_type(self) -> OrganelleType:
        return OrganelleType.RIBOSOME
    
    def start_translation(self, mrna: mRNA) -> bool:
        """开始翻译"""
        if self.current_mrna is not None or not mrna.can_be_translated():
            return False
        
        self.current_mrna = mrna
        self.translation_position = 0
        self.amino_acid_sequence = []
        
        logger.debug(f"核糖体 {self.organelle_id} 开始翻译 mRNA {mrna.molecule_id}")
        return True
    
    def translate_codon(self, codon: str, trna_pool: List[tRNA]) -> Optional[str]:
        """翻译密码子"""
        # 简化的密码子表
        codon_table = {
            'UUU': 'Phe', 'UUC': 'Phe', 'UUA': 'Leu', 'UUG': 'Leu',
            'UCU': 'Ser', 'UCC': 'Ser', 'UCA': 'Ser', 'UCG': 'Ser',
            'UAU': 'Tyr', 'UAC': 'Tyr', 'UAA': 'STOP', 'UAG': 'STOP',
            'UGU': 'Cys', 'UGC': 'Cys', 'UGA': 'STOP', 'UGG': 'Trp',
            'AUG': 'Met'  # 起始密码子
        }
        
        if codon in codon_table:
            amino_acid = codon_table[codon]
            if amino_acid == 'STOP':
                return 'STOP'
            
            # 寻找匹配的tRNA
            for trna in trna_pool:
                if trna.is_charged and trna.amino_acid == amino_acid:
                    return trna.release_amino_acid()
        
        return None
    
    def process_molecules(self, dt: float, cell_context: 'DigitalCell') -> List[MacroMolecule]:
        """处理分子"""
        produced_molecules = []
        
        # 处理新的mRNA
        while self.processing_queue and self.current_mrna is None:
            molecule_id = self.processing_queue.popleft()
            if molecule_id in self.internal_molecules:
                molecule = self.internal_molecules[molecule_id]
                if isinstance(molecule, mRNA):
                    if self.start_translation(molecule):
                        break
        
        # 继续翻译
        if self.current_mrna and random.random() < self.translation_rate * dt:
            coding_seq = self.current_mrna.get_coding_sequence()
            
            if self.translation_position + 3 <= len(coding_seq):
                codon = coding_seq[self.translation_position:self.translation_position + 3]
                
                # 获取可用的tRNA
                trna_pool = [mol for mol in cell_context.molecules.values() 
                           if isinstance(mol, tRNA) and mol.is_charged]
                
                amino_acid = self.translate_codon(codon, trna_pool)
                
                if amino_acid == 'STOP':
                    # 翻译完成，产生蛋白质
                    protein_sequence = ''.join(self.amino_acid_sequence)
                    protein = create_molecule(
                        MoleculeType.PROTEIN,
                        sequence=protein_sequence,
                        position=self.position
                    )
                    produced_molecules.append(protein)
                    
                    # 重置翻译状态
                    self.current_mrna = None
                    self.translation_position = 0
                    self.amino_acid_sequence = []
                    
                    logger.debug(f"核糖体 {self.organelle_id} 完成蛋白质翻译，序列长度: {len(protein_sequence)}")
                
                elif amino_acid:
                    self.amino_acid_sequence.append(amino_acid)
                    self.translation_position += 3
                    
                    # 消耗能量
                    self.update_energy(-1.0)
        
        return produced_molecules

class ProteinProcessor(Organelle):
    """蛋白质处理器（内质网/高尔基体）"""
    
    def __init__(self, **kwargs):
        super().__init__(size=15.0, **kwargs)
        self.folding_efficiency = 0.8
        self.modification_types = ['phosphorylation', 'glycosylation', 'ubiquitination']
    
    def get_organelle_type(self) -> OrganelleType:
        return OrganelleType.PROTEIN_PROCESSOR
    
    def fold_protein(self, protein: Protein) -> bool:
        """折叠蛋白质"""
        if random.random() < self.folding_efficiency:
            # 简化的蛋白质折叠
            protein.fold_structure = {
                'alpha_helices': random.randint(1, 5),
                'beta_sheets': random.randint(0, 3),
                'loops': random.randint(2, 8),
                'stability': random.uniform(0.7, 1.0)
            }
            
            # 根据折叠结构调整催化活性
            if protein.fold_structure['stability'] > 0.8:
                protein.catalytic_activity *= 1.2
            
            logger.debug(f"蛋白质 {protein.molecule_id} 折叠成功")
            return True
        
        logger.debug(f"蛋白质 {protein.molecule_id} 折叠失败")
        return False
    
    def modify_protein(self, protein: Protein) -> None:
        """修饰蛋白质"""
        modification = random.choice(self.modification_types)
        
        if not hasattr(protein, 'modifications'):
            protein.modifications = []
        
        protein.modifications.append(modification)
        
        # 修饰影响蛋白质功能
        if modification == 'phosphorylation':
            protein.catalytic_activity *= 1.1
        elif modification == 'glycosylation':
            protein.stability *= 1.1
        elif modification == 'ubiquitination':
            protein.degradation_rate *= 2.0  # 标记降解
        
        logger.debug(f"蛋白质 {protein.molecule_id} 进行 {modification} 修饰")
    
    def process_molecules(self, dt: float, cell_context: 'DigitalCell') -> List[MacroMolecule]:
        """处理分子"""
        processed_molecules = []
        
        while self.processing_queue:
            molecule_id = self.processing_queue.popleft()
            if molecule_id in self.internal_molecules:
                molecule = self.internal_molecules[molecule_id]
                
                if isinstance(molecule, Protein):
                    # 折叠蛋白质
                    if not hasattr(molecule, 'fold_structure') or not molecule.fold_structure:
                        self.fold_protein(molecule)
                    
                    # 随机修饰
                    if random.random() < 0.3:
                        self.modify_protein(molecule)
                    
                    # 处理完成，准备释放
                    processed_molecules.append(molecule)
                    self.release_molecule(molecule_id)
        
        return processed_molecules

class GlycoproteinSystem:
    """糖蛋白系统 - 细胞间识别和交互"""
    
    def __init__(self, cell_id: str):
        self.cell_id = cell_id
        self.surface_proteins: Dict[str, Protein] = {}
        self.recognition_patterns: Dict[str, float] = {}  # 识别模式
        self.cell_type_markers: Set[str] = set()  # 细胞类型标记
        
    def add_surface_protein(self, protein: Protein, marker_type: str = "generic") -> None:
        """添加表面蛋白"""
        self.surface_proteins[protein.molecule_id] = protein
        self.cell_type_markers.add(marker_type)
        
        # 生成识别模式
        pattern_key = f"{marker_type}_{len(protein.sequence)}"
        self.recognition_patterns[pattern_key] = protein.catalytic_activity
        
        logger.debug(f"细胞 {self.cell_id} 添加表面蛋白 {protein.molecule_id}，标记: {marker_type}")
    
    def recognize_cell(self, other_system: 'GlycoproteinSystem') -> float:
        """识别另一个细胞"""
        recognition_score = 0.0
        
        # 比较识别模式
        common_patterns = set(self.recognition_patterns.keys()) & set(other_system.recognition_patterns.keys())
        
        for pattern in common_patterns:
            similarity = 1.0 - abs(self.recognition_patterns[pattern] - other_system.recognition_patterns[pattern])
            recognition_score += similarity
        
        # 归一化
        if common_patterns:
            recognition_score /= len(common_patterns)
        
        logger.debug(f"细胞识别: {self.cell_id} -> {other_system.cell_id}，得分: {recognition_score:.3f}")
        return recognition_score
    
    def can_interact_with(self, other_system: 'GlycoproteinSystem') -> bool:
        """检查是否可以与另一个细胞交互"""
        recognition_score = self.recognize_cell(other_system)
        return recognition_score > 0.5

class DigitalCell:
    """数字细胞 - 3D空间物理模拟器"""
    
    def __init__(self, 
                 cell_id: Optional[str] = None,
                 position: Optional[Vector3D] = None,
                 radius: float = 50.0):
        """
        初始化数字细胞
        
        Args:
            cell_id: 细胞唯一标识符
            position: 细胞位置
            radius: 细胞半径
        """
        self.cell_id = cell_id or str(uuid.uuid4())
        self.position = position or Vector3D()
        self.radius = radius
        
        # 细胞状态
        self.state = CellState.HEALTHY
        self.age = 0.0
        self.energy = 1000.0
        self.health = 100.0
        self.division_threshold = 2000.0
        
        # 分子容器和索引
        self.molecules: Dict[str, MacroMolecule] = {}
        self.spatial_index = SpatialIndex()
        self.molecule_counts: Dict[MoleculeType, int] = defaultdict(int)
        
        # 3D物理模拟引擎集成
        bounds_size = radius * 2
        self.physics_engine = PhysicsEngine(
            bounds=(Vector3D(-bounds_size/2, -bounds_size/2, -bounds_size/2), 
                   Vector3D(bounds_size/2, bounds_size/2, bounds_size/2)),
            temperature=310.0  # 37°C in Kelvin
        )
        
        # 细胞器
        self.organelles: Dict[str, Organelle] = {}
        self._initialize_organelles()
        
        # 糖蛋白系统
        self.glycoprotein_system = GlycoproteinSystem(self.cell_id)
        
        # 生命周期控制
        self.cycle_time = 0.0
        self.cycle_duration = 1.0  # 1秒一个周期
        self.is_running = False
        self.simulation_thread: Optional[threading.Thread] = None
        
        # 环境参数
        self.temperature = 310.0  # 体温
        self.ph = 7.4
        self.osmolarity = 300.0
        
        # 统计信息
        self.stats = {
            'total_interactions': 0,
            'successful_bindings': 0,
            'molecules_created': 0,
            'molecules_degraded': 0,
            'energy_consumed': 0.0,
            'physics_steps': 0,
            'collision_events': 0
        }
        
        logger.info(f"创建数字细胞 {self.cell_id}，位置: ({self.position.x}, {self.position.y}, {self.position.z})")
        logger.debug(f"细胞 {self.cell_id} 物理引擎初始化完成")
    
    def _initialize_organelles(self) -> None:
        """初始化细胞器"""
        # 创建细胞核
        nucleus = Nucleus(position=Vector3D(0, 0, 0))
        self.organelles[nucleus.organelle_id] = nucleus
        
        # 创建线粒体
        for i in range(3):
            mito = Mitochondrion(
                position=Vector3D(
                    random.uniform(-20, 20),
                    random.uniform(-20, 20),
                    random.uniform(-20, 20)
                )
            )
            self.organelles[mito.organelle_id] = mito
        
        # 创建核糖体
        for i in range(5):
            ribosome = Ribosome(
                position=Vector3D(
                    random.uniform(-30, 30),
                    random.uniform(-30, 30),
                    random.uniform(-30, 30)
                )
            )
            self.organelles[ribosome.organelle_id] = ribosome
        
        # 创建蛋白质处理器
        processor = ProteinProcessor(
            position=Vector3D(
                random.uniform(-15, 15),
                random.uniform(-15, 15),
                random.uniform(-15, 15)
            )
        )
        self.organelles[processor.organelle_id] = processor
        
        logger.debug(f"细胞 {self.cell_id} 初始化了 {len(self.organelles)} 个细胞器")
    
    def add_molecule(self, molecule: MacroMolecule) -> bool:
        """添加分子到细胞"""
        if len(self.molecules) >= 10000:  # 限制分子数量
            return False
        
        # 确保分子位置在细胞边界内
        distance_from_center = molecule.position.magnitude()
        if distance_from_center > self.radius - molecule.radius:
            # 调整位置到细胞内
            direction = molecule.position.normalize() if distance_from_center > 0 else Vector3D(1, 0, 0)
            molecule.position = direction * (self.radius - molecule.radius - 1.0)
        
        self.molecules[molecule.molecule_id] = molecule
        self.spatial_index.add_molecule(molecule.molecule_id, molecule.position)
        self.physics_engine.add_molecule(molecule)  # 添加到物理引擎
        self.molecule_counts[molecule.get_molecule_type()] += 1
        self.stats['molecules_created'] += 1
        
        logger.debug(f"细胞 {self.cell_id} 添加分子 {molecule.molecule_id}，位置: {molecule.position}")
        return True
    
    def remove_molecule(self, molecule_id: str) -> Optional[MacroMolecule]:
        """移除分子"""
        if molecule_id in self.molecules:
            molecule = self.molecules.pop(molecule_id)
            self.spatial_index.remove_molecule(molecule_id, molecule.position)
            self.physics_engine.remove_molecule(molecule_id)  # 从物理引擎移除
            self.molecule_counts[molecule.get_molecule_type()] -= 1
            self.stats['molecules_degraded'] += 1
            
            logger.debug(f"细胞 {self.cell_id} 移除分子 {molecule_id}")
            return molecule
        return None
    
    def get_molecules_by_type(self, molecule_type: MoleculeType) -> List[MacroMolecule]:
        """按类型获取分子"""
        return [mol for mol in self.molecules.values() 
                if mol.get_molecule_type() == molecule_type and mol.is_active]
    
    def get_nearby_molecules(self, position: Vector3D, radius: float = 20.0) -> List[MacroMolecule]:
        """获取附近的分子"""
        nearby_ids = self.spatial_index.get_nearby_molecules(position, radius)
        nearby_molecules = []
        
        for mol_id in nearby_ids:
            if mol_id in self.molecules:
                molecule = self.molecules[mol_id]
                if molecule.position.distance_to(position) <= radius:
                    nearby_molecules.append(molecule)
        
        return nearby_molecules
    
    def simulate_molecular_motion(self, dt: float) -> None:
        """模拟分子运动（使用物理引擎）"""
        # 使用物理引擎进行分子运动模拟
        physics_results = self.physics_engine.step(dt)
        
        # 更新分子位置和速度
        for molecule_id, molecule in self.molecules.items():
            if not molecule.is_active:
                continue
            
            old_position = Vector3D(molecule.position.x, molecule.position.y, molecule.position.z)
            
            # 从物理引擎获取更新后的位置和速度
            if molecule_id in physics_results['updated_molecules']:
                physics_data = physics_results['updated_molecules'][molecule_id]
                molecule.position = physics_data['position']
                molecule.velocity = physics_data['velocity']
            
            # 更新空间索引
            self.spatial_index.update_molecule_position(molecule.molecule_id, old_position, molecule.position)
        
        # 更新统计信息
        self.stats['physics_steps'] += 1
        self.stats['collision_events'] += physics_results.get('collision_count', 0)
    
    def simulate_molecular_interactions(self, dt: float) -> None:
        """模拟分子交互（使用物理引擎碰撞检测）"""
        interaction_count = 0
        max_interactions = 100  # 限制每次循环的交互数量
        
        # 从物理引擎获取碰撞信息
        physics_results = self.physics_engine.get_simulation_state()
        collision_pairs = physics_results.get('recent_collisions', [])
        
        # 处理物理引擎检测到的碰撞
        for collision in collision_pairs[:max_interactions]:
            mol_id1, mol_id2 = collision['molecule1_id'], collision['molecule2_id']
            
            if mol_id1 in self.molecules and mol_id2 in self.molecules:
                molecule1 = self.molecules[mol_id1]
                molecule2 = self.molecules[mol_id2]
                
                if molecule1.is_active and molecule2.is_active:
                    # 执行分子交互
                    interaction_result = molecule1.interact_with(molecule2)
                    self.stats['total_interactions'] += 1
                    
                    if interaction_result['binding_occurred']:
                        self.stats['successful_bindings'] += 1
                        logger.debug(f"分子结合: {mol_id1} <-> {mol_id2}")
                    
                    interaction_count += 1
        
        # 补充随机交互（用于非碰撞的化学反应）
        if interaction_count < max_interactions // 2:
            molecules_list = list(self.molecules.values())
            random.shuffle(molecules_list)
            
            for molecule1 in molecules_list[:max_interactions - interaction_count]:
                if not molecule1.is_active:
                    continue
                
                # 获取附近的分子
                nearby_molecules = self.get_nearby_molecules(molecule1.position, 15.0)
                
                for molecule2 in nearby_molecules[:3]:  # 限制每个分子的交互数量
                    if (molecule2.molecule_id != molecule1.molecule_id and 
                        molecule2.is_active and 
                        random.random() < 0.1):  # 10%概率进行化学反应
                        
                        interaction_result = molecule1.interact_with(molecule2)
                        self.stats['total_interactions'] += 1
                        
                        if interaction_result['binding_occurred']:
                            self.stats['successful_bindings'] += 1
                        
                        interaction_count += 1
                        break
                
                if interaction_count >= max_interactions:
                    break
    
    def process_organelles(self, dt: float) -> None:
        """处理细胞器"""
        for organelle in self.organelles.values():
            if not organelle.is_active:
                continue
            
            # 细胞器处理分子
            produced_molecules = organelle.process_molecules(dt, self)
            
            # 添加产生的分子
            for molecule in produced_molecules:
                if self.add_molecule(molecule):
                    # 如果是表面蛋白，添加到糖蛋白系统
                    if isinstance(molecule, Protein) and hasattr(molecule, 'is_surface_protein'):
                        if getattr(molecule, 'is_surface_protein'):
                            self.glycoprotein_system.add_surface_protein(molecule)
    
    def simulate_degradation(self, dt: float) -> None:
        """模拟分子降解"""
        molecules_to_remove = []
        
        for molecule in self.molecules.values():
            if molecule.degrade(dt):
                molecules_to_remove.append(molecule.molecule_id)
        
        # 移除降解的分子
        for mol_id in molecules_to_remove:
            self.remove_molecule(mol_id)
    
    def update_cell_state(self, dt: float) -> None:
        """更新细胞状态"""
        self.age += dt
        
        # 计算能量消耗
        base_metabolism = 1.0 * dt
        organelle_cost = len(self.organelles) * 0.1 * dt
        molecule_cost = len(self.molecules) * 0.01 * dt
        
        total_cost = base_metabolism + organelle_cost + molecule_cost
        self.energy -= total_cost
        self.stats['energy_consumed'] += total_cost
        
        # 从ATP分子获取能量
        atp_molecules = self.get_molecules_by_type(MoleculeType.ENERGY_TOKEN)
        for atp in atp_molecules[:5]:  # 限制同时使用的ATP数量
            if isinstance(atp, EnergyToken):
                energy_gained = atp.release_energy(10.0)
                self.energy += energy_gained
                if not atp.is_active:
                    self.remove_molecule(atp.molecule_id)
        
        # 更新健康状态
        if self.energy < 100:
            self.health -= 1.0 * dt
            self.state = CellState.STRESSED
        elif self.energy > 500:
            self.health = min(100.0, self.health + 0.5 * dt)
            self.state = CellState.HEALTHY
        
        # 检查细胞死亡
        if self.health <= 0 or self.energy <= 0:
            self.state = CellState.DYING
            self.is_running = False
        
        # 检查细胞分裂
        if self.energy > self.division_threshold and self.health > 80:
            self.state = CellState.DIVIDING
    
    def life_cycle_step(self, dt: float) -> None:
        """生命周期步骤（完整的细胞模拟循环）"""
        if self.state == CellState.DEAD or self.state == CellState.DYING:
            return
        
        try:
            # 1. 物理模拟：分子运动和碰撞检测
            self.simulate_molecular_motion(dt)
            
            # 2. 化学反应：分子交互和结合
            self.simulate_molecular_interactions(dt)
            
            # 3. 生物过程：细胞器处理
            self.process_organelles(dt)
            
            # 4. 分子生命周期：降解和回收
            self.simulate_degradation(dt)
            
            # 5. 细胞状态：能量、健康和生命周期管理
            self.update_cell_state(dt)
            
            # 6. 环境适应：温度、pH等参数调节
            self._adapt_to_environment(dt)
            
            self.cycle_time += dt
            
            # 定期日志输出
            if int(self.cycle_time) % 10 == 0 and self.cycle_time - dt < int(self.cycle_time):
                logger.debug(f"细胞 {self.cell_id} 生命周期: 时间={self.cycle_time:.1f}s, 能量={self.energy:.1f}, 分子数={len(self.molecules)}")
            
        except Exception as e:
            logger.error(f"细胞 {self.cell_id} 生命周期错误: {e}")
            self.state = CellState.STRESSED
    
    def _adapt_to_environment(self, dt: float) -> None:
        """环境适应机制"""
        try:
            # 温度适应
            target_temp = 310.0  # 37°C
            temp_diff = abs(self.temperature - target_temp)
            if temp_diff > 5.0:
                # 温度偏差过大，消耗额外能量维持稳态
                energy_cost = temp_diff * 0.1 * dt
                self.energy -= energy_cost
                self.stats['energy_consumed'] += energy_cost
                
                if temp_diff > 15.0:
                    self.health -= 0.5 * dt  # 极端温度损害健康
            
            # pH适应
            target_ph = 7.4
            ph_diff = abs(self.ph - target_ph)
            if ph_diff > 0.5:
                # pH偏差影响酶活性
                for organelle in self.organelles.values():
                    if hasattr(organelle, 'efficiency'):
                        organelle.efficiency *= (1.0 - ph_diff * 0.1)
            
            # 渗透压适应
            target_osmolarity = 300.0
            osm_diff = abs(self.osmolarity - target_osmolarity)
            if osm_diff > 50.0:
                # 渗透压失衡影响细胞体积
                volume_change = osm_diff / 1000.0
                self.radius *= (1.0 + volume_change)
                
                # 更新物理引擎边界
                new_boundary = Vector3D(self.radius*2, self.radius*2, self.radius*2)
                self.physics_engine.boundary_size = new_boundary
            
            # 分子密度调节
            molecule_density = len(self.molecules) / (4/3 * 3.14159 * self.radius**3)
            if molecule_density > 0.001:  # 过度拥挤
                # 增加分子降解率
                for molecule in list(self.molecules.values())[:10]:
                    if random.random() < 0.05:  # 5%概率额外降解
                        molecule.stability *= 0.95
            
            logger.debug(f"细胞 {self.cell_id} 环境适应: 温度={self.temperature:.1f}K, pH={self.ph:.1f}, 渗透压={self.osmolarity:.1f}")
            
        except Exception as e:
            logger.error(f"细胞 {self.cell_id} 环境适应错误: {e}")
    
    def start_simulation(self) -> None:
        """开始模拟"""
        if self.is_running:
            return
        
        self.is_running = True
        
        def simulation_loop():
            last_time = time.time()
            
            while self.is_running:
                current_time = time.time()
                dt = min(current_time - last_time, 0.1)  # 限制最大时间步长
                
                if dt > 0.01:  # 最小时间步长
                    self.life_cycle_step(dt)
                    last_time = current_time
                
                time.sleep(0.01)  # 100 FPS
        
        self.simulation_thread = threading.Thread(target=simulation_loop, daemon=True)
        self.simulation_thread.start()
        
        logger.info(f"细胞 {self.cell_id} 开始模拟")
    
    def stop_simulation(self) -> None:
        """停止模拟"""
        self.is_running = False
        if self.simulation_thread:
            self.simulation_thread.join(timeout=1.0)
        
        logger.info(f"细胞 {self.cell_id} 停止模拟")
    
    def get_state(self) -> Dict[str, Any]:
        """获取细胞状态"""
        physics_state = self.physics_engine.get_simulation_state()
        
        return {
            'cell_id': self.cell_id,
            'position': {'x': self.position.x, 'y': self.position.y, 'z': self.position.z},
            'radius': self.radius,
            'state': self.state.value,
            'age': self.age,
            'energy': self.energy,
            'health': self.health,
            'molecule_count': len(self.molecules),
            'molecule_counts': dict(self.molecule_counts),
            'organelle_count': len(self.organelles),
            'cycle_time': self.cycle_time,
            'is_running': self.is_running,
            'stats': self.stats.copy(),
            'physics_state': {
                'total_kinetic_energy': physics_state.get('total_kinetic_energy', 0.0),
                'average_velocity': physics_state.get('average_velocity', 0.0),
                'collision_rate': physics_state.get('collision_rate', 0.0),
                'spatial_distribution': physics_state.get('spatial_distribution', {})
            },
            'environment': {
                'temperature': self.temperature,
                'ph': self.ph,
                'osmolarity': self.osmolarity
            }
        }
    
    def add_gene(self, gene_id: str, sequence: str) -> bool:
        """添加基因到细胞核"""
        nucleus = None
        for organelle in self.organelles.values():
            if isinstance(organelle, Nucleus):
                nucleus = organelle
                break
        
        if nucleus:
            nucleus.add_gene(gene_id, sequence)
            logger.info(f"细胞 {self.cell_id} 添加基因 {gene_id}")
            return True
        
        return False
    
    def interact_with_cell(self, other_cell: 'DigitalCell') -> Dict[str, Any]:
        """与另一个细胞交互"""
        # 检查距离
        distance = self.position.distance_to(other_cell.position)
        interaction_distance = self.radius + other_cell.radius + 10.0
        
        if distance > interaction_distance:
            return {'interaction': False, 'reason': 'too_far'}
        
        # 糖蛋白识别
        can_interact = self.glycoprotein_system.can_interact_with(other_cell.glycoprotein_system)
        
        if not can_interact:
            return {'interaction': False, 'reason': 'recognition_failed'}
        
        # 交换分子（简化）
        exchanged_molecules = 0
        my_molecules = list(self.molecules.values())[:5]
        
        for molecule in my_molecules:
            if random.random() < 0.1:  # 10%概率交换
                if other_cell.add_molecule(molecule):
                    self.remove_molecule(molecule.molecule_id)
                    exchanged_molecules += 1
        
        logger.info(f"细胞交互: {self.cell_id} <-> {other_cell.cell_id}，交换分子: {exchanged_molecules}")
        
        return {
            'interaction': True,
            'distance': distance,
            'exchanged_molecules': exchanged_molecules,
            'recognition_score': self.glycoprotein_system.recognize_cell(other_cell.glycoprotein_system)
        }
    
    def divide_cell(self) -> Optional['DigitalCell']:
        """细胞分裂（创建子细胞）"""
        if self.state != CellState.DIVIDING or self.energy < self.division_threshold:
            return None
        
        try:
            # 创建子细胞
            daughter_position = Vector3D(
                self.position.x + random.uniform(-20, 20),
                self.position.y + random.uniform(-20, 20),
                self.position.z + random.uniform(-20, 20)
            )
            
            daughter_cell = DigitalCell(
                position=daughter_position,
                radius=self.radius * 0.8  # 子细胞稍小
            )
            
            # 分配资源
            energy_split = self.energy * 0.4  # 给子细胞40%能量
            self.energy -= energy_split
            daughter_cell.energy = energy_split
            
            # 复制部分分子
            molecules_to_copy = list(self.molecules.values())[:len(self.molecules)//3]
            for molecule in molecules_to_copy:
                molecule_copy = create_molecule(
                    molecule.get_molecule_type(),
                    position=Vector3D(
                        daughter_position.x + random.uniform(-10, 10),
                        daughter_position.y + random.uniform(-10, 10),
                        daughter_position.z + random.uniform(-10, 10)
                    )
                )
                daughter_cell.add_molecule(molecule_copy)
            
            # 复制基因
            for organelle in self.organelles.values():
                if isinstance(organelle, Nucleus):
                    for gene_id, sequence in organelle.dna_sequences.items():
                        daughter_cell.add_gene(gene_id, sequence)
            
            # 重置分裂状态
            self.state = CellState.HEALTHY
            self.division_threshold *= 1.2  # 增加下次分裂阈值
            
            logger.info(f"细胞分裂: {self.cell_id} -> {daughter_cell.cell_id}")
            return daughter_cell
            
        except Exception as e:
            logger.error(f"细胞分裂错误: {e}")
            self.state = CellState.STRESSED
            return None

if __name__ == "__main__":
    # 测试代码
    logger.info("DigitalCell数字细胞系统测试开始")
    
    # 创建数字细胞
    cell = DigitalCell(position=Vector3D(0, 0, 0))
    
    # 添加基因
    cell.add_gene("test_gene", "ATGAAACUGCUGCUGGGCGCGGGCAAG")
    
    # 添加一些初始分子
    for i in range(10):
        protein = create_molecule(MoleculeType.PROTEIN, 
                                sequence="MKLLVLGLGAGVGKTTLLRQIGKN",
                                position=Vector3D(random.uniform(-20, 20), 
                                                 random.uniform(-20, 20), 
                                                 random.uniform(-20, 20)))
        cell.add_molecule(protein)
    
    for i in range(5):
        atp = create_molecule(MoleculeType.ENERGY_TOKEN,
                            energy_value=30.0,
                            position=Vector3D(random.uniform(-20, 20), 
                                             random.uniform(-20, 20), 
                                             random.uniform(-20, 20)))
        cell.add_molecule(atp)
    
    # 开始模拟
    cell.start_simulation()
    
    # 运行一段时间
    logger.info("运行模拟 5 秒...")
    time.sleep(5)
    
    # 获取状态
    state = cell.get_state()
    logger.info(f"细胞状态: {state}")
    
    # 停止模拟
    cell.stop_simulation()
    
    logger.info("DigitalCell数字细胞系统测试完成")