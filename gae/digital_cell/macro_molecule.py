# -*- coding: utf-8 -*-
"""
MacroMolecule分子系统 - EvoForge数字细胞核心组件

根据comprehensive_implementation_plan.md重新实现的分子系统，包括：
- MacroMolecule基础类：位置、速度、结合位点、稳定性、降解机制
- 六种分子类型：protein、mrna、trna、lipid、resource_token、energy_token
- 布朗运动、碰撞检测、分子交互逻辑
- 结合位点系统：结合亲和力、特异性识别、动态结合/解离
- 催化逻辑系统：蛋白质催化功能、反应速率、底物特异性
"""

import numpy as np
import uuid
import logging
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import random
import math
from abc import ABC, abstractmethod

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class MoleculeType(Enum):
    """分子类型枚举"""
    PROTEIN = "protein"
    MRNA = "mrna"
    TRNA = "trna"
    LIPID = "lipid"
    RESOURCE_TOKEN = "resource_token"
    ENERGY_TOKEN = "energy_token"

class BindingSiteType(Enum):
    """结合位点类型"""
    CATALYTIC = "catalytic"  # 催化位点
    ALLOSTERIC = "allosteric"  # 变构位点
    SUBSTRATE = "substrate"  # 底物结合位点
    COFACTOR = "cofactor"  # 辅因子结合位点
    REGULATORY = "regulatory"  # 调节位点

@dataclass
class Vector3D:
    """3D向量类"""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    
    def __add__(self, other: 'Vector3D') -> 'Vector3D':
        return Vector3D(self.x + other.x, self.y + other.y, self.z + other.z)
    
    def __sub__(self, other: 'Vector3D') -> 'Vector3D':
        return Vector3D(self.x - other.x, self.y - other.y, self.z - other.z)
    
    def __mul__(self, scalar: float) -> 'Vector3D':
        return Vector3D(self.x * scalar, self.y * scalar, self.z * scalar)
    
    def magnitude(self) -> float:
        """计算向量长度"""
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)
    
    def normalize(self) -> 'Vector3D':
        """归一化向量"""
        mag = self.magnitude()
        if mag == 0:
            return Vector3D(0, 0, 0)
        return Vector3D(self.x/mag, self.y/mag, self.z/mag)
    
    def distance_to(self, other: 'Vector3D') -> float:
        """计算到另一个点的距离"""
        return (self - other).magnitude()

@dataclass
class BindingSite:
    """分子结合位点"""
    site_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    site_type: BindingSiteType = BindingSiteType.SUBSTRATE
    affinity: float = 1.0  # 结合亲和力 (0-1)
    specificity: Dict[str, float] = field(default_factory=dict)  # 特异性识别
    is_occupied: bool = False
    bound_molecule_id: Optional[str] = None
    binding_energy: float = 0.0  # 结合能
    position: Vector3D = field(default_factory=Vector3D)  # 相对于分子中心的位置
    
    def can_bind_to(self, target_site: 'BindingSite', molecule_type: MoleculeType) -> bool:
        """检查是否可以与目标位点结合"""
        if self.is_occupied or target_site.is_occupied:
            return False
        
        # 检查特异性
        type_key = molecule_type.value
        if type_key in self.specificity:
            return self.specificity[type_key] > 0.5
        
        # 默认低亲和力结合
        return self.affinity > 0.3
    
    def bind_to(self, target_site: 'BindingSite', molecule_id: str) -> float:
        """与目标位点结合，返回结合能"""
        if not self.can_bind_to(target_site, MoleculeType.PROTEIN):  # 简化处理
            return 0.0
        
        self.is_occupied = True
        self.bound_molecule_id = molecule_id
        target_site.is_occupied = True
        target_site.bound_molecule_id = molecule_id
        
        # 计算结合能
        binding_energy = (self.affinity + target_site.affinity) * 0.5
        self.binding_energy = binding_energy
        target_site.binding_energy = binding_energy
        
        logger.debug(f"结合位点 {self.site_id} 与 {target_site.site_id} 结合，结合能: {binding_energy}")
        return binding_energy
    
    def unbind(self) -> float:
        """解除结合，返回释放的能量"""
        if not self.is_occupied:
            return 0.0
        
        released_energy = self.binding_energy
        self.is_occupied = False
        self.bound_molecule_id = None
        self.binding_energy = 0.0
        
        logger.debug(f"结合位点 {self.site_id} 解除结合，释放能量: {released_energy}")
        return released_energy

class MacroMolecule(ABC):
    """分子基础类 - 所有分子的抽象基类"""
    
    def __init__(self, 
                 molecule_id: Optional[str] = None,
                 position: Optional[Vector3D] = None,
                 velocity: Optional[Vector3D] = None,
                 mass: float = 1.0,
                 radius: float = 1.0,
                 stability: float = 1.0):
        """
        初始化分子
        
        Args:
            molecule_id: 分子唯一标识符
            position: 3D位置
            velocity: 3D速度向量
            mass: 分子质量
            radius: 分子半径
            stability: 分子稳定性 (0-1)
        """
        self.molecule_id = molecule_id or str(uuid.uuid4())
        self.position = position or Vector3D()
        self.velocity = velocity or Vector3D()
        self.mass = mass
        self.radius = radius
        self.stability = stability
        
        # 分子状态
        self.age = 0.0  # 分子年龄
        self.energy = 100.0  # 分子能量
        self.is_active = True
        self.degradation_rate = 0.01  # 降解速率
        
        # 结合位点
        self.binding_sites: Dict[str, BindingSite] = {}
        
        # 物理属性
        self.temperature = 310.0  # 体温 (K)
        self.diffusion_coefficient = 1.0  # 扩散系数
        
        # 交互历史
        self.interaction_history: List[Dict[str, Any]] = []
        
        logger.debug(f"创建分子 {self.molecule_id}，类型: {self.get_molecule_type()}")
    
    @abstractmethod
    def get_molecule_type(self) -> MoleculeType:
        """获取分子类型"""
        pass
    
    def add_binding_site(self, site: BindingSite) -> None:
        """添加结合位点"""
        self.binding_sites[site.site_id] = site
        logger.debug(f"分子 {self.molecule_id} 添加结合位点 {site.site_id}")
    
    def remove_binding_site(self, site_id: str) -> bool:
        """移除结合位点"""
        if site_id in self.binding_sites:
            site = self.binding_sites[site_id]
            if site.is_occupied:
                site.unbind()
            del self.binding_sites[site_id]
            logger.debug(f"分子 {self.molecule_id} 移除结合位点 {site_id}")
            return True
        return False
    
    def get_available_binding_sites(self) -> List[BindingSite]:
        """获取可用的结合位点"""
        return [site for site in self.binding_sites.values() if not site.is_occupied]
    
    def brownian_motion(self, dt: float, temperature: float = 310.0) -> None:
        """布朗运动模拟"""
        # 计算布朗运动的随机力
        kB = 1.38e-23  # 玻尔兹曼常数
        friction_coeff = 6 * math.pi * 0.001 * self.radius  # 摩擦系数
        
        # 随机力的标准差
        sigma = math.sqrt(2 * kB * temperature * friction_coeff / dt)
        
        # 生成随机力
        random_force = Vector3D(
            random.gauss(0, sigma),
            random.gauss(0, sigma),
            random.gauss(0, sigma)
        )
        
        # 更新速度（考虑摩擦和随机力）
        friction_force = self.velocity * (-friction_coeff)
        total_force = random_force + friction_force
        acceleration = total_force * (1.0 / self.mass)
        
        self.velocity = self.velocity + acceleration * dt
        
        # 更新位置
        self.position = self.position + self.velocity * dt
        
        logger.debug(f"分子 {self.molecule_id} 布朗运动: 位置 ({self.position.x:.3f}, {self.position.y:.3f}, {self.position.z:.3f})")
    
    def check_collision(self, other: 'MacroMolecule') -> bool:
        """检查与另一个分子的碰撞"""
        distance = self.position.distance_to(other.position)
        collision_distance = self.radius + other.radius
        
        is_collision = distance <= collision_distance
        if is_collision:
            logger.debug(f"分子碰撞检测: {self.molecule_id} 与 {other.molecule_id}，距离: {distance:.3f}")
        
        return is_collision
    
    def interact_with(self, other: 'MacroMolecule') -> Dict[str, Any]:
        """与另一个分子交互"""
        interaction_result = {
            'timestamp': self.age,
            'partner_id': other.molecule_id,
            'partner_type': other.get_molecule_type().value,
            'interaction_type': 'collision',
            'energy_change': 0.0,
            'binding_occurred': False
        }
        
        # 检查是否可以结合
        my_sites = self.get_available_binding_sites()
        other_sites = other.get_available_binding_sites()
        
        if my_sites and other_sites:
            # 尝试结合
            for my_site in my_sites:
                for other_site in other_sites:
                    if my_site.can_bind_to(other_site, other.get_molecule_type()):
                        binding_energy = my_site.bind_to(other_site, other.molecule_id)
                        if binding_energy > 0:
                            interaction_result['interaction_type'] = 'binding'
                            interaction_result['energy_change'] = -binding_energy  # 结合释放能量
                            interaction_result['binding_occurred'] = True
                            
                            # 更新分子能量
                            self.energy += binding_energy * 0.5
                            other.energy += binding_energy * 0.5
                            
                            logger.debug(f"分子结合: {self.molecule_id} 与 {other.molecule_id}，能量变化: {binding_energy}")
                            break
                if interaction_result['binding_occurred']:
                    break
        
        # 记录交互历史
        self.interaction_history.append(interaction_result)
        other.interaction_history.append({
            **interaction_result,
            'partner_id': self.molecule_id,
            'partner_type': self.get_molecule_type().value
        })
        
        return interaction_result
    
    def degrade(self, dt: float) -> bool:
        """分子降解过程"""
        # 年龄增长
        self.age += dt
        
        # 能量衰减
        energy_loss = self.degradation_rate * dt * (1.0 - self.stability)
        self.energy -= energy_loss
        
        # 稳定性随时间降低
        stability_loss = self.degradation_rate * dt * 0.1
        self.stability = max(0.0, self.stability - stability_loss)
        
        # 检查是否应该降解
        degradation_probability = (1.0 - self.stability) * self.degradation_rate * dt
        should_degrade = random.random() < degradation_probability or self.energy <= 0
        
        if should_degrade:
            self.is_active = False
            # 解除所有结合
            for site in self.binding_sites.values():
                if site.is_occupied:
                    site.unbind()
            
            logger.debug(f"分子 {self.molecule_id} 降解，年龄: {self.age:.2f}，稳定性: {self.stability:.3f}")
        
        return should_degrade
    
    def get_state(self) -> Dict[str, Any]:
        """获取分子状态信息"""
        return {
            'molecule_id': self.molecule_id,
            'type': self.get_molecule_type().value,
            'position': {'x': self.position.x, 'y': self.position.y, 'z': self.position.z},
            'velocity': {'x': self.velocity.x, 'y': self.velocity.y, 'z': self.velocity.z},
            'mass': self.mass,
            'radius': self.radius,
            'stability': self.stability,
            'age': self.age,
            'energy': self.energy,
            'is_active': self.is_active,
            'binding_sites_count': len(self.binding_sites),
            'occupied_sites_count': len([s for s in self.binding_sites.values() if s.is_occupied]),
            'interaction_count': len(self.interaction_history)
        }

class Protein(MacroMolecule):
    """蛋白质分子"""
    
    def __init__(self, 
                 sequence: str = "",
                 fold_structure: Optional[Dict[str, Any]] = None,
                 catalytic_activity: float = 0.0,
                 **kwargs):
        super().__init__(**kwargs)
        self.sequence = sequence  # 氨基酸序列
        self.fold_structure = fold_structure or {}  # 折叠结构
        self.catalytic_activity = catalytic_activity  # 催化活性
        self.substrate_specificity: Dict[str, float] = {}  # 底物特异性
        
        # 蛋白质特有属性
        self.is_enzyme = catalytic_activity > 0.1
        self.allosteric_sites: Dict[str, BindingSite] = {}  # 变构位点
        
        # 根据序列长度设置物理属性
        if sequence:
            self.mass = len(sequence) * 110.0  # 平均氨基酸分子量
            self.radius = max(1.0, len(sequence) * 0.1)
        
        # 添加默认结合位点
        if self.is_enzyme:
            catalytic_site = BindingSite(
                site_type=BindingSiteType.CATALYTIC,
                affinity=catalytic_activity,
                specificity={'substrate': 0.8}
            )
            self.add_binding_site(catalytic_site)
    
    def get_molecule_type(self) -> MoleculeType:
        return MoleculeType.PROTEIN
    
    def catalyze_reaction(self, substrate: 'MacroMolecule', product_type: MoleculeType) -> Optional['MacroMolecule']:
        """催化反应"""
        if not self.is_enzyme or self.catalytic_activity <= 0:
            return None
        
        # 检查底物特异性
        substrate_type = substrate.get_molecule_type().value
        if substrate_type in self.substrate_specificity:
            specificity = self.substrate_specificity[substrate_type]
            if specificity < 0.5:
                return None
        
        # 计算反应速率
        reaction_rate = self.catalytic_activity * self.stability
        reaction_probability = reaction_rate * 0.1  # 简化的反应概率
        
        if random.random() < reaction_probability:
            # 创建产物（简化实现）
            product = self._create_product(product_type, substrate)
            
            # 消耗能量
            energy_cost = 10.0
            self.energy -= energy_cost
            
            logger.debug(f"蛋白质 {self.molecule_id} 催化反应: {substrate_type} -> {product_type.value}")
            return product
        
        return None
    
    def _create_product(self, product_type: MoleculeType, substrate: 'MacroMolecule') -> 'MacroMolecule':
        """创建反应产物（简化实现）"""
        # 这里应该根据具体的反应类型创建相应的产物
        # 为了简化，我们创建一个基本的分子
        if product_type == MoleculeType.PROTEIN:
            return Protein(position=substrate.position)
        elif product_type == MoleculeType.ENERGY_TOKEN:
            return EnergyToken(position=substrate.position)
        else:
            # 返回一个通用的分子（这里需要具体的实现）
            return ResourceToken(position=substrate.position)

class mRNA(MacroMolecule):
    """信使RNA分子"""
    
    def __init__(self, 
                 sequence: str = "",
                 coding_region: Tuple[int, int] = (0, 0),
                 **kwargs):
        super().__init__(**kwargs)
        self.sequence = sequence  # RNA序列
        self.coding_region = coding_region  # 编码区域
        self.translation_efficiency = 0.8  # 翻译效率
        
        # mRNA特有属性
        self.ribosome_binding_sites: List[BindingSite] = []
        self.degradation_rate = 0.05  # mRNA降解较快
        
        # 根据序列长度设置物理属性
        if sequence:
            self.mass = len(sequence) * 330.0  # 平均核苷酸分子量
            self.radius = max(0.5, len(sequence) * 0.05)
        
        # 添加核糖体结合位点
        ribosome_site = BindingSite(
            site_type=BindingSiteType.SUBSTRATE,
            affinity=0.7,
            specificity={'ribosome': 0.9}
        )
        self.add_binding_site(ribosome_site)
        self.ribosome_binding_sites.append(ribosome_site)
    
    def get_molecule_type(self) -> MoleculeType:
        return MoleculeType.MRNA
    
    def get_coding_sequence(self) -> str:
        """获取编码序列"""
        start, end = self.coding_region
        if start < len(self.sequence) and end <= len(self.sequence):
            return self.sequence[start:end]
        return ""
    
    def can_be_translated(self) -> bool:
        """检查是否可以被翻译"""
        return (len(self.get_coding_sequence()) > 0 and 
                self.stability > 0.3 and 
                self.energy > 10.0)

class tRNA(MacroMolecule):
    """转运RNA分子"""
    
    def __init__(self, 
                 anticodon: str = "",
                 amino_acid: str = "",
                 **kwargs):
        super().__init__(**kwargs)
        self.anticodon = anticodon  # 反密码子
        self.amino_acid = amino_acid  # 携带的氨基酸
        self.is_charged = bool(amino_acid)  # 是否携带氨基酸
        
        # tRNA特有属性
        self.charging_efficiency = 0.9  # 充电效率
        self.mass = 25000.0  # tRNA分子量约25kDa
        self.radius = 2.0
        
        # 添加氨基酸结合位点
        aa_site = BindingSite(
            site_type=BindingSiteType.SUBSTRATE,
            affinity=0.8,
            specificity={'amino_acid': 0.95}
        )
        self.add_binding_site(aa_site)
    
    def get_molecule_type(self) -> MoleculeType:
        return MoleculeType.TRNA
    
    def charge_with_amino_acid(self, amino_acid: str) -> bool:
        """装载氨基酸"""
        if self.is_charged:
            return False
        
        if random.random() < self.charging_efficiency:
            self.amino_acid = amino_acid
            self.is_charged = True
            self.energy -= 5.0  # 消耗能量
            
            logger.debug(f"tRNA {self.molecule_id} 装载氨基酸: {amino_acid}")
            return True
        
        return False
    
    def release_amino_acid(self) -> Optional[str]:
        """释放氨基酸"""
        if not self.is_charged:
            return None
        
        released_aa = self.amino_acid
        self.amino_acid = ""
        self.is_charged = False
        
        logger.debug(f"tRNA {self.molecule_id} 释放氨基酸: {released_aa}")
        return released_aa

class Lipid(MacroMolecule):
    """脂质分子"""
    
    def __init__(self, 
                 lipid_type: str = "phospholipid",
                 hydrophobic_tail_length: int = 16,
                 **kwargs):
        super().__init__(**kwargs)
        self.lipid_type = lipid_type
        self.hydrophobic_tail_length = hydrophobic_tail_length
        self.is_membrane_component = True
        
        # 脂质特有属性
        self.fluidity = 0.7  # 膜流动性
        self.phase_transition_temp = 273.0  # 相变温度
        self.mass = hydrophobic_tail_length * 14.0 + 200.0  # 估算分子量
        self.radius = 1.5
        
        # 脂质分子相对稳定
        self.degradation_rate = 0.001
        self.stability = 0.95
    
    def get_molecule_type(self) -> MoleculeType:
        return MoleculeType.LIPID
    
    def form_membrane_patch(self, other_lipids: List['Lipid']) -> bool:
        """形成膜片段"""
        if len(other_lipids) < 10:  # 需要足够的脂质分子
            return False
        
        # 简化的膜形成逻辑
        membrane_formation_probability = min(0.9, len(other_lipids) * 0.05)
        
        if random.random() < membrane_formation_probability:
            logger.debug(f"脂质 {self.molecule_id} 参与形成膜结构，涉及 {len(other_lipids)} 个脂质分子")
            return True
        
        return False

class ResourceToken(MacroMolecule):
    """资源令牌分子"""
    
    def __init__(self, 
                 resource_type: str = "generic",
                 resource_value: float = 1.0,
                 **kwargs):
        super().__init__(**kwargs)
        self.resource_type = resource_type
        self.resource_value = resource_value
        
        # 资源令牌属性
        self.is_consumable = True
        self.mass = 100.0
        self.radius = 0.5
        self.stability = 0.8
        self.degradation_rate = 0.02
    
    def get_molecule_type(self) -> MoleculeType:
        return MoleculeType.RESOURCE_TOKEN
    
    def consume(self, amount: float = None) -> float:
        """消耗资源"""
        if amount is None:
            amount = self.resource_value
        
        consumed = min(amount, self.resource_value)
        self.resource_value -= consumed
        
        if self.resource_value <= 0:
            self.is_active = False
        
        logger.debug(f"资源令牌 {self.molecule_id} 消耗 {consumed}，剩余: {self.resource_value}")
        return consumed

class EnergyToken(MacroMolecule):
    """能量令牌分子"""
    
    def __init__(self, 
                 energy_value: float = 10.0,
                 energy_type: str = "ATP",
                 **kwargs):
        super().__init__(**kwargs)
        self.energy_value = energy_value
        self.energy_type = energy_type
        
        # 能量令牌属性
        self.is_high_energy = energy_value > 5.0
        self.mass = 507.0 if energy_type == "ATP" else 100.0  # ATP分子量
        self.radius = 0.8
        self.stability = 0.7
        self.degradation_rate = 0.03
    
    def get_molecule_type(self) -> MoleculeType:
        return MoleculeType.ENERGY_TOKEN
    
    def release_energy(self, amount: float = None) -> float:
        """释放能量"""
        if amount is None:
            amount = self.energy_value
        
        released = min(amount, self.energy_value)
        self.energy_value -= released
        
        if self.energy_value <= 0:
            self.is_active = False
        
        logger.debug(f"能量令牌 {self.molecule_id} 释放能量 {released}，剩余: {self.energy_value}")
        return released
    
    def transfer_energy_to(self, target: MacroMolecule, amount: float = None) -> float:
        """向目标分子转移能量"""
        if amount is None:
            amount = min(self.energy_value, 10.0)  # 默认转移量
        
        transferred = self.release_energy(amount)
        target.energy += transferred
        
        logger.debug(f"能量转移: {self.molecule_id} -> {target.molecule_id}，转移量: {transferred}")
        return transferred

# 分子工厂函数
def create_molecule(molecule_type: MoleculeType, **kwargs) -> MacroMolecule:
    """分子工厂函数"""
    molecule_classes = {
        MoleculeType.PROTEIN: Protein,
        MoleculeType.MRNA: mRNA,
        MoleculeType.TRNA: tRNA,
        MoleculeType.LIPID: Lipid,
        MoleculeType.RESOURCE_TOKEN: ResourceToken,
        MoleculeType.ENERGY_TOKEN: EnergyToken
    }
    
    if molecule_type not in molecule_classes:
        raise ValueError(f"未知的分子类型: {molecule_type}")
    
    molecule_class = molecule_classes[molecule_type]
    molecule = molecule_class(**kwargs)
    
    logger.debug(f"创建分子: {molecule_type.value}，ID: {molecule.molecule_id}")
    return molecule

if __name__ == "__main__":
    # 测试代码
    logger.info("MacroMolecule分子系统测试开始")
    
    # 创建不同类型的分子
    protein = create_molecule(MoleculeType.PROTEIN, 
                            sequence="MKLLVLGLGAGVGKTTLLRQIGKN", 
                            catalytic_activity=0.8)
    
    mrna = create_molecule(MoleculeType.MRNA, 
                         sequence="AUGAAACUGCUGCUGGGCGCGGGCAAG",
                         coding_region=(0, 27))
    
    energy_token = create_molecule(MoleculeType.ENERGY_TOKEN, 
                                 energy_value=20.0)
    
    # 测试分子交互
    logger.info("测试分子交互")
    interaction = protein.interact_with(mrna)
    logger.info(f"交互结果: {interaction}")
    
    # 测试布朗运动
    logger.info("测试布朗运动")
    for i in range(5):
        protein.brownian_motion(0.1)
        logger.info(f"步骤 {i+1}: 位置 ({protein.position.x:.3f}, {protein.position.y:.3f}, {protein.position.z:.3f})")
    
    # 测试分子状态
    logger.info("分子状态信息:")
    for molecule in [protein, mrna, energy_token]:
        state = molecule.get_state()
        logger.info(f"{state['type']}: {state}")
    
    logger.info("MacroMolecule分子系统测试完成")