import numpy as np
import uuid
import time
from typing import Dict, Any, Optional, Callable, List, Set, Tuple
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict

class MoleculeType(Enum):
    """分子类型枚举"""
    PROTEIN = "protein"  # 蛋白质
    MRNA = "mrna"  # 信使RNA
    TRNA = "trna"  # 转运RNA
    DNA = "dna"  # DNA
    LIPID = "lipid"  # 脂质
    RESOURCE_TOKEN = "resource_token"  # 资源令牌（如葡萄糖）
    ENERGY_TOKEN = "energy_token"  # 能量令牌（如ATP）
    SYNTAX_TOKEN = "syntax_token"  # 语法令牌
    VARIABLE = "variable"  # 变量
    AST_NODE = "ast_node"  # AST节点
    RIBOSOME_SUBUNIT = "ribosome_subunit"  # 核糖体亚基
    RNA_POLYMERASE = "rna_polymerase"  # RNA聚合酶

@dataclass
class BindingSite:
    """结合位点数据结构"""
    shape_id: str  # 形状标识符，决定能与哪些分子结合
    bound_to: Optional[str] = None  # 当前结合的分子ID
    binding_strength: float = 1.0  # 结合强度
    is_occupied: bool = False  # 是否被占用
    
    # 动态结合属性
    binding_affinity: float = 0.5  # 结合亲和力 (0.0-1.0)
    cooperativity: float = 1.0  # 协同效应系数
    allosteric_effect: float = 0.0  # 变构效应 (-1.0到1.0)
    
    # 结合历史和统计
    binding_count: int = 0  # 结合次数
    last_binding_time: float = 0.0  # 上次结合时间
    average_binding_duration: float = 0.0  # 平均结合持续时间
    
    # 环境敏感性
    ph_sensitivity: float = 0.1  # pH敏感性
    temperature_sensitivity: float = 0.1  # 温度敏感性
    ionic_strength_sensitivity: float = 0.1  # 离子强度敏感性
    
class MacroMolecule:
    """大分子类 - 系统的基础组成单位
    
    这是整个系统的"原子"，所有功能都通过分子间的物理交互涌现产生。
    每个分子都有物理属性（位置、速度）、结合位点和可能的催化功能。
    """
    
    def __init__(self, 
                 mol_type: MoleculeType,
                 position: np.ndarray,
                 binding_sites: Dict[str, BindingSite],
                 mol_id: Optional[str] = None,
                 data: Optional[Dict[str, Any]] = None):
        """
        初始化大分子
        
        Args:
            mol_type: 分子类型
            position: 在3D空间中的位置坐标 (x, y, z)
            binding_sites: 结合位点字典，键为位点名称
            mol_id: 分子唯一标识符，如果为None则自动生成
            data: 分子特定数据（如DNA序列、蛋白质功能等）
        """
        self.id = mol_id or str(uuid.uuid4())
        self.type = mol_type
        
        # 物理属性
        self.position = np.array(position, dtype=float)
        self.velocity = np.random.randn(3) * 0.1  # 随机布朗运动
        self.mass = 1.0  # 分子质量，影响运动
        self.radius = 0.5  # 分子半径，用于碰撞检测
        
        # 交互核心：结合位点
        self.binding_sites = binding_sites
        
        # 功能逻辑 - 对于酶类分子，定义催化反应
        self.catalytic_logic: Optional[Callable] = None
        
        # 稳定性 - 每个周期会衰减，归零则分子降解
        self.stability = 100.0
        self.max_stability = 100.0
        
        # 分子特定数据
        self.data = data or {}
        
        # 结合的分子列表（形成复合体）
        self.bound_molecules: Dict[str, 'MacroMolecule'] = {}
        
        # 年龄和生命周期
        self.age = 0
        self.max_age = 1000  # 最大生命周期
        self.creation_time = time.time()  # 创建时间
        
        # 分子网络和相互作用
        self.interaction_history: Dict[str, List[float]] = defaultdict(list)  # 相互作用历史
        self.network_neighbors: Set[str] = set()  # 网络邻居
        self.influence_radius = 2.0  # 影响半径
        
        # 环境感知
        self.environmental_state = {
            'ph': 7.0,
            'temperature': 37.0,  # 摄氏度
            'ionic_strength': 0.15,  # mol/L
            'pressure': 1.0,  # atm
            'oxygen_level': 0.21  # 氧气浓度
        }
        
        # 动态平衡
        self.equilibrium_position = np.copy(self.position)
        self.conformational_state = 'native'  # native, denatured, intermediate
        self.activity_level = 1.0  # 活性水平 (0.0-1.0)
        
        # 分子标记和修饰
        self.modifications: Dict[str, Any] = {}  # 翻译后修饰等
        self.tags: Set[str] = set()  # 分子标签
        
        # 能量状态
        self.energy_level = 100.0  # 能量水平
        self.activation_energy = 10.0  # 激活能
        
        # 统计信息
        self.interaction_count = 0
        self.successful_catalysis_count = 0
        self.failed_catalysis_count = 0
        
    def update_physics(self, dt: float = 1.0):
        """更新分子的物理状态
        
        Args:
            dt: 时间步长
        """
        # 更新位置
        self.position += self.velocity * dt
        
        # 添加随机布朗运动（受温度影响）
        temperature_factor = self.environmental_state['temperature'] / 37.0
        brownian_intensity = 0.05 * np.sqrt(temperature_factor)
        brownian_force = np.random.randn(3) * brownian_intensity
        self.velocity += brownian_force * dt
        
        # 速度衰减（摩擦力，受环境粘度影响）
        viscosity_factor = 1.0 + (self.environmental_state['ionic_strength'] - 0.15) * 0.1
        self.velocity *= (0.95 / viscosity_factor)
        
        # 向平衡位置的恢复力
        equilibrium_force = (self.equilibrium_position - self.position) * 0.01
        self.velocity += equilibrium_force * dt
        
        # 稳定性衰减（受环境因素影响）
        stability_decay = self._calculate_stability_decay(dt)
        self.stability -= stability_decay
        
        # 能量衰减
        self.energy_level -= 0.05 * dt
        if self.energy_level < 0:
            self.energy_level = 0
            
        # 年龄增长
        self.age += dt
        
        # 更新构象状态
        self._update_conformational_state()
        
        # 更新活性水平
        self._update_activity_level()
        
    def can_bind_to(self, other: 'MacroMolecule', site_name: str, other_site_name: str) -> bool:
        """检查是否可以与另一个分子结合
        
        Args:
            other: 目标分子
            site_name: 本分子的结合位点名称
            other_site_name: 目标分子的结合位点名称
            
        Returns:
            bool: 是否可以结合
        """
        if site_name not in self.binding_sites or other_site_name not in other.binding_sites:
            return False
            
        my_site = self.binding_sites[site_name]
        other_site = other.binding_sites[other_site_name]
        
        # 基本检查：位点匹配且未被占用
        if (my_site.is_occupied or other_site.is_occupied or 
            my_site.shape_id != other_site.shape_id):
            return False
            
        # 距离检查
        distance = self.distance_to(other)
        if distance > (self.radius + other.radius + 1.0):
            return False
            
        # 构象状态检查
        if (self.conformational_state == 'denatured' or 
            other.conformational_state == 'denatured'):
            return False
            
        # 活性水平检查
        if self.activity_level < 0.1 or other.activity_level < 0.1:
            return False
            
        # 环境因素影响结合概率
        binding_probability = self._calculate_binding_probability(my_site, other_site, other)
        
        return np.random.random() < binding_probability
    
    def bind_to(self, other: 'MacroMolecule', site_name: str, other_site_name: str) -> bool:
        """与另一个分子结合
        
        Args:
            other: 目标分子
            site_name: 本分子的结合位点名称
            other_site_name: 目标分子的结合位点名称
            
        Returns:
            bool: 结合是否成功
        """
        if not self.can_bind_to(other, site_name, other_site_name):
            return False
            
        current_time = time.time()
        my_site = self.binding_sites[site_name]
        other_site = other.binding_sites[other_site_name]
        
        # 执行结合
        my_site.bound_to = other.id
        my_site.is_occupied = True
        my_site.binding_count += 1
        my_site.last_binding_time = current_time
        
        other_site.bound_to = self.id
        other_site.is_occupied = True
        other_site.binding_count += 1
        other_site.last_binding_time = current_time
        
        # 添加到结合分子列表
        self.bound_molecules[other.id] = other
        other.bound_molecules[self.id] = self
        
        # 更新网络邻居
        self.network_neighbors.add(other.id)
        other.network_neighbors.add(self.id)
        
        # 记录相互作用历史
        self.interaction_history[other.id].append(current_time)
        other.interaction_history[self.id].append(current_time)
        
        # 更新统计
        self.interaction_count += 1
        other.interaction_count += 1
        
        # 应用协同效应
        self._apply_cooperative_effects(other, my_site, other_site)
        
        return True
    
    def unbind_from(self, other: 'MacroMolecule'):
        """与另一个分子解除结合
        
        Args:
            other: 要解除结合的分子
        """
        if other.id not in self.bound_molecules:
            return
            
        current_time = time.time()
        
        # 找到结合位点并解除占用，更新结合持续时间
        for site_name, site in self.binding_sites.items():
            if site.bound_to == other.id:
                # 计算结合持续时间
                binding_duration = current_time - site.last_binding_time
                if site.binding_count > 0:
                    site.average_binding_duration = (
                        (site.average_binding_duration * (site.binding_count - 1) + binding_duration) / 
                        site.binding_count
                    )
                
                site.bound_to = None
                site.is_occupied = False
                
        for site_name, site in other.binding_sites.items():
            if site.bound_to == self.id:
                # 计算结合持续时间
                binding_duration = current_time - site.last_binding_time
                if site.binding_count > 0:
                    site.average_binding_duration = (
                        (site.average_binding_duration * (site.binding_count - 1) + binding_duration) / 
                        site.binding_count
                    )
                
                site.bound_to = None
                site.is_occupied = False
                
        # 从结合分子列表中移除
        del self.bound_molecules[other.id]
        del other.bound_molecules[self.id]
        
        # 移除协同效应
        self._remove_cooperative_effects(other)
    
    def execute_catalysis(self, substrates: List['MacroMolecule']) -> List['MacroMolecule']:
        """执行催化反应
        
        Args:
            substrates: 底物分子列表
            
        Returns:
            list: 产物分子列表
        """
        if self.catalytic_logic is None:
            return substrates
            
        # 检查能量是否足够
        if self.energy_level < self.activation_energy:
            self.failed_catalysis_count += 1
            return substrates
            
        # 检查活性水平
        if self.activity_level < 0.2:
            self.failed_catalysis_count += 1
            return substrates
            
        # 检查构象状态
        if self.conformational_state != 'native':
            self.failed_catalysis_count += 1
            return substrates
            
        try:
            # 消耗能量
            self.energy_level -= self.activation_energy
            
            # 执行催化反应（活性水平影响效率）
            products = self.catalytic_logic(substrates, self)
            
            # 根据活性水平决定反应成功率
            if np.random.random() < self.activity_level:
                self.successful_catalysis_count += 1
                
                # 更新催化位点的使用统计
                for site in self.binding_sites.values():
                    if hasattr(site, 'catalytic_count'):
                        site.catalytic_count = getattr(site, 'catalytic_count', 0) + 1
                        
                return products
            else:
                self.failed_catalysis_count += 1
                return substrates
                
        except Exception as e:
            print(f"催化反应失败: {e}")
            self.failed_catalysis_count += 1
            return substrates
    
    def is_degraded(self) -> bool:
        """检查分子是否已降解
        
        Returns:
            bool: 是否已降解
        """
        return self.stability <= 0 or self.age >= self.max_age
    
    def get_complex_molecules(self) -> list['MacroMolecule']:
        """获取与此分子结合形成复合体的所有分子
        
        Returns:
            list: 复合体中的所有分子（包括自己）
        """
        visited = set()
        complex_molecules = []
        
        def dfs(molecule):
            if molecule.id in visited:
                return
            visited.add(molecule.id)
            complex_molecules.append(molecule)
            
            for bound_mol in molecule.bound_molecules.values():
                dfs(bound_mol)
                
        dfs(self)
        return complex_molecules
    
    def distance_to(self, other: 'MacroMolecule') -> float:
        """计算到另一个分子的距离
        
        Args:
            other: 目标分子
            
        Returns:
            float: 欧几里得距离
        """
        return np.linalg.norm(self.position - other.position)
    
    def __repr__(self) -> str:
        return f"<{self.type.value} {self.id[:8]} at {self.position.round(2)}>"
    
    def __str__(self) -> str:
        return self.__repr__()
    
    # ==================== 新增的辅助方法 ====================
    
    def _calculate_stability_decay(self, dt: float) -> float:
        """计算稳定性衰减率
        
        Args:
            dt: 时间步长
            
        Returns:
            float: 稳定性衰减量
        """
        base_decay = 0.1 * dt
        
        # 环境因素影响
        ph_stress = abs(self.environmental_state['ph'] - 7.0) * 0.02
        temp_stress = abs(self.environmental_state['temperature'] - 37.0) / 37.0 * 0.05
        ionic_stress = abs(self.environmental_state['ionic_strength'] - 0.15) * 0.1
        
        environmental_factor = 1.0 + ph_stress + temp_stress + ionic_stress
        
        # 构象状态影响
        conformational_factor = {
            'native': 1.0,
            'intermediate': 1.5,
            'denatured': 3.0
        }.get(self.conformational_state, 1.0)
        
        return base_decay * environmental_factor * conformational_factor
    
    def _update_conformational_state(self):
        """更新分子构象状态"""
        # 基于环境条件和稳定性决定构象
        stability_ratio = self.stability / self.max_stability
        
        if stability_ratio > 0.8:
            self.conformational_state = 'native'
        elif stability_ratio > 0.3:
            # 环境压力可能导致中间态
            stress_level = self._calculate_environmental_stress()
            if stress_level > 0.5:
                self.conformational_state = 'intermediate'
            else:
                self.conformational_state = 'native'
        else:
            self.conformational_state = 'denatured'
    
    def _update_activity_level(self):
        """更新分子活性水平"""
        # 基于构象状态、能量水平和环境条件
        conformational_activity = {
            'native': 1.0,
            'intermediate': 0.5,
            'denatured': 0.1
        }.get(self.conformational_state, 0.1)
        
        energy_factor = min(1.0, self.energy_level / 50.0)
        environmental_factor = 1.0 - self._calculate_environmental_stress()
        
        self.activity_level = conformational_activity * energy_factor * environmental_factor
        self.activity_level = max(0.0, min(1.0, self.activity_level))
    
    def _calculate_environmental_stress(self) -> float:
        """计算环境压力水平
        
        Returns:
            float: 压力水平 (0.0-1.0)
        """
        ph_stress = min(1.0, abs(self.environmental_state['ph'] - 7.0) / 3.0)
        temp_stress = min(1.0, abs(self.environmental_state['temperature'] - 37.0) / 20.0)
        ionic_stress = min(1.0, abs(self.environmental_state['ionic_strength'] - 0.15) / 0.5)
        
        return (ph_stress + temp_stress + ionic_stress) / 3.0
    
    def _calculate_binding_probability(self, my_site: BindingSite, other_site: BindingSite, 
                                     other: 'MacroMolecule') -> float:
        """计算结合概率
        
        Args:
            my_site: 本分子的结合位点
            other_site: 目标分子的结合位点
            other: 目标分子
            
        Returns:
            float: 结合概率 (0.0-1.0)
        """
        # 基础亲和力
        base_probability = (my_site.binding_affinity + other_site.binding_affinity) / 2.0
        
        # 环境因素
        env_factor = 1.0 - self._calculate_environmental_stress()
        
        # 协同效应
        cooperative_factor = 1.0
        if len(self.bound_molecules) > 0:
            cooperative_factor *= (1.0 + my_site.cooperativity * 0.1)
        if len(other.bound_molecules) > 0:
            cooperative_factor *= (1.0 + other_site.cooperativity * 0.1)
        
        # 变构效应
        allosteric_factor = 1.0 + (my_site.allosteric_effect + other_site.allosteric_effect) / 2.0
        
        # 活性水平影响
        activity_factor = (self.activity_level + other.activity_level) / 2.0
        
        probability = (base_probability * env_factor * cooperative_factor * 
                      allosteric_factor * activity_factor)
        
        return max(0.0, min(1.0, probability))
    
    def _apply_cooperative_effects(self, other: 'MacroMolecule', my_site: BindingSite, 
                                 other_site: BindingSite):
        """应用协同效应
        
        Args:
            other: 结合的分子
            my_site: 本分子的结合位点
            other_site: 目标分子的结合位点
        """
        # 增强其他位点的结合亲和力
        for site in self.binding_sites.values():
            if site != my_site and not site.is_occupied:
                site.binding_affinity *= (1.0 + my_site.cooperativity * 0.05)
                site.binding_affinity = min(1.0, site.binding_affinity)
        
        for site in other.binding_sites.values():
            if site != other_site and not site.is_occupied:
                site.binding_affinity *= (1.0 + other_site.cooperativity * 0.05)
                site.binding_affinity = min(1.0, site.binding_affinity)
    
    def _remove_cooperative_effects(self, other: 'MacroMolecule'):
        """移除协同效应
        
        Args:
            other: 解绑的分子
        """
        # 恢复结合亲和力
        for site in self.binding_sites.values():
            if not site.is_occupied:
                site.binding_affinity *= 0.95  # 轻微降低
                site.binding_affinity = max(0.1, site.binding_affinity)
    
    def update_environment(self, new_env: Dict[str, float]):
        """更新环境状态
        
        Args:
            new_env: 新的环境参数
        """
        self.environmental_state.update(new_env)
        
        # 立即重新评估构象和活性
        self._update_conformational_state()
        self._update_activity_level()
    
    def add_modification(self, mod_type: str, mod_data: Any):
        """添加分子修饰
        
        Args:
            mod_type: 修饰类型
            mod_data: 修饰数据
        """
        self.modifications[mod_type] = mod_data
        
        # 某些修饰可能影响活性
        if mod_type in ['phosphorylation', 'methylation', 'acetylation']:
            self._update_activity_level()
    
    def remove_modification(self, mod_type: str):
        """移除分子修饰
        
        Args:
            mod_type: 修饰类型
        """
        if mod_type in self.modifications:
            del self.modifications[mod_type]
            self._update_activity_level()
    
    def add_tag(self, tag: str):
        """添加分子标签
        
        Args:
            tag: 标签名称
        """
        self.tags.add(tag)
    
    def remove_tag(self, tag: str):
        """移除分子标签
        
        Args:
            tag: 标签名称
        """
        self.tags.discard(tag)
    
    def has_tag(self, tag: str) -> bool:
        """检查是否有特定标签
        
        Args:
            tag: 标签名称
            
        Returns:
            bool: 是否有该标签
        """
        return tag in self.tags
    
    def recharge_energy(self, amount: float):
        """补充能量
        
        Args:
            amount: 能量补充量
        """
        self.energy_level = min(100.0, self.energy_level + amount)
    
    def get_network_size(self) -> int:
        """获取分子网络大小
        
        Returns:
            int: 网络中的分子数量
        """
        return len(self.network_neighbors)
    
    def get_binding_efficiency(self) -> float:
        """获取结合效率
        
        Returns:
            float: 结合效率 (0.0-1.0)
        """
        if self.interaction_count == 0:
            return 0.0
            
        successful_bindings = sum(1 for site in self.binding_sites.values() 
                                if site.binding_count > 0)
        return successful_bindings / len(self.binding_sites)
    
    def get_catalytic_efficiency(self) -> float:
        """获取催化效率
        
        Returns:
            float: 催化效率 (0.0-1.0)
        """
        total_attempts = self.successful_catalysis_count + self.failed_catalysis_count
        if total_attempts == 0:
            return 0.0
            
        return self.successful_catalysis_count / total_attempts
    
    def get_status_summary(self) -> Dict[str, Any]:
        """获取分子状态摘要
        
        Returns:
            dict: 状态摘要
        """
        return {
            'id': self.id,
            'type': self.type.value,
            'position': self.position.tolist(),
            'conformational_state': self.conformational_state,
            'activity_level': self.activity_level,
            'stability': self.stability,
            'energy_level': self.energy_level,
            'age': self.age,
            'bound_molecules_count': len(self.bound_molecules),
            'network_size': self.get_network_size(),
            'binding_efficiency': self.get_binding_efficiency(),
            'catalytic_efficiency': self.get_catalytic_efficiency(),
            'environmental_stress': self._calculate_environmental_stress(),
            'modifications': list(self.modifications.keys()),
             'tags': list(self.tags)
         }


class MolecularNetwork:
    """分子网络管理器 - 管理分子间的相互作用和动态平衡"""
    
    def __init__(self):
        """初始化分子网络管理器"""
        self.molecules: Dict[str, MacroMolecule] = {}
        self.interaction_matrix: Dict[Tuple[str, str], float] = {}  # 分子间相互作用强度
        self.reaction_pathways: List[Dict[str, Any]] = []  # 反应路径
        
        # 网络统计
        self.total_interactions = 0
        self.successful_reactions = 0
        self.failed_reactions = 0
        
        # 环境参数
        self.global_environment = {
            'ph': 7.0,
            'temperature': 37.0,
            'ionic_strength': 0.15,
            'pressure': 1.0,
            'oxygen_level': 0.21
        }
        
        # 动态平衡参数
        self.equilibrium_constants: Dict[str, float] = {}
        self.reaction_rates: Dict[str, float] = {}
        
    def add_molecule(self, molecule: MacroMolecule):
        """添加分子到网络
        
        Args:
            molecule: 要添加的分子
        """
        self.molecules[molecule.id] = molecule
        molecule.update_environment(self.global_environment)
        
    def remove_molecule(self, molecule_id: str):
        """从网络中移除分子
        
        Args:
            molecule_id: 分子ID
        """
        if molecule_id in self.molecules:
            molecule = self.molecules[molecule_id]
            
            # 解除所有结合
            for bound_mol in list(molecule.bound_molecules.values()):
                molecule.unbind_from(bound_mol)
                
            # 从网络中移除
            del self.molecules[molecule_id]
            
            # 清理相互作用矩阵
            keys_to_remove = [key for key in self.interaction_matrix.keys() 
                            if molecule_id in key]
            for key in keys_to_remove:
                del self.interaction_matrix[key]
    
    def update_global_environment(self, new_env: Dict[str, float]):
        """更新全局环境
        
        Args:
            new_env: 新的环境参数
        """
        self.global_environment.update(new_env)
        
        # 更新所有分子的环境
        for molecule in self.molecules.values():
            molecule.update_environment(self.global_environment)
    
    def find_nearby_molecules(self, molecule: MacroMolecule, 
                            max_distance: float = 5.0) -> List[MacroMolecule]:
        """查找附近的分子
        
        Args:
            molecule: 中心分子
            max_distance: 最大距离
            
        Returns:
            list: 附近的分子列表
        """
        nearby = []
        for other in self.molecules.values():
            if other.id != molecule.id:
                distance = molecule.distance_to(other)
                if distance <= max_distance:
                    nearby.append(other)
        return nearby
    
    def attempt_binding(self, mol1: MacroMolecule, mol2: MacroMolecule) -> bool:
        """尝试两个分子之间的结合
        
        Args:
            mol1: 分子1
            mol2: 分子2
            
        Returns:
            bool: 是否成功结合
        """
        # 寻找兼容的结合位点
        for site1_name, site1 in mol1.binding_sites.items():
            if site1.is_occupied:
                continue
                
            for site2_name, site2 in mol2.binding_sites.items():
                if site2.is_occupied:
                    continue
                    
                if mol1.can_bind_to(mol2, site1_name, site2_name):
                    success = mol1.bind_to(mol2, site1_name, site2_name)
                    if success:
                        self.total_interactions += 1
                        
                        # 记录相互作用强度
                        interaction_key = tuple(sorted([mol1.id, mol2.id]))
                        current_strength = self.interaction_matrix.get(interaction_key, 0.0)
                        self.interaction_matrix[interaction_key] = current_strength + 1.0
                        
                        return True
        return False
    
    def process_reactions(self, dt: float = 1.0):
        """处理网络中的反应
        
        Args:
            dt: 时间步长
        """
        # 更新所有分子的物理状态
        for molecule in self.molecules.values():
            molecule.update_physics(dt)
        
        # 移除降解的分子
        degraded_molecules = [mol_id for mol_id, mol in self.molecules.items() 
                            if mol.is_degraded()]
        for mol_id in degraded_molecules:
            self.remove_molecule(mol_id)
        
        # 尝试新的结合
        molecules_list = list(self.molecules.values())
        for i, mol1 in enumerate(molecules_list):
            nearby_molecules = self.find_nearby_molecules(mol1)
            
            for mol2 in nearby_molecules:
                if mol2.id not in mol1.bound_molecules:
                    # 随机尝试结合
                    if np.random.random() < 0.1:  # 10%的概率尝试结合
                        self.attempt_binding(mol1, mol2)
        
        # 处理催化反应
        self._process_catalytic_reactions()
        
        # 检查结合稳定性
        self._check_binding_stability(dt)
    
    def _process_catalytic_reactions(self):
        """处理催化反应"""
        for molecule in self.molecules.values():
            if molecule.catalytic_logic is not None and molecule.activity_level > 0.2:
                # 寻找底物
                nearby_molecules = self.find_nearby_molecules(molecule, 2.0)
                
                if len(nearby_molecules) >= 1:
                    # 尝试催化反应
                    substrates = nearby_molecules[:2]  # 最多两个底物
                    products = molecule.execute_catalysis(substrates)
                    
                    if products != substrates:
                        self.successful_reactions += 1
                        
                        # 移除底物，添加产物
                        for substrate in substrates:
                            if substrate.id in self.molecules:
                                self.remove_molecule(substrate.id)
                        
                        for product in products:
                            if isinstance(product, MacroMolecule):
                                self.add_molecule(product)
                    else:
                        self.failed_reactions += 1
    
    def _check_binding_stability(self, dt: float):
        """检查结合稳定性
        
        Args:
            dt: 时间步长
        """
        for molecule in self.molecules.values():
            bound_to_remove = []
            
            for bound_mol in molecule.bound_molecules.values():
                # 计算解绑概率
                unbinding_probability = self._calculate_unbinding_probability(
                    molecule, bound_mol, dt
                )
                
                if np.random.random() < unbinding_probability:
                    bound_to_remove.append(bound_mol)
            
            # 执行解绑
            for bound_mol in bound_to_remove:
                molecule.unbind_from(bound_mol)
    
    def _calculate_unbinding_probability(self, mol1: MacroMolecule, 
                                       mol2: MacroMolecule, dt: float) -> float:
        """计算解绑概率
        
        Args:
            mol1: 分子1
            mol2: 分子2
            dt: 时间步长
            
        Returns:
            float: 解绑概率
        """
        # 基础解绑率
        base_rate = 0.01 * dt
        
        # 环境压力影响
        env_stress = (mol1._calculate_environmental_stress() + 
                     mol2._calculate_environmental_stress()) / 2.0
        
        # 稳定性影响
        stability_factor = min(mol1.stability, mol2.stability) / 100.0
        
        # 活性水平影响
        activity_factor = (mol1.activity_level + mol2.activity_level) / 2.0
        
        unbinding_prob = base_rate * (1.0 + env_stress) * (2.0 - stability_factor) * (2.0 - activity_factor)
        
        return max(0.0, min(1.0, unbinding_prob))
    
    def get_network_statistics(self) -> Dict[str, Any]:
        """获取网络统计信息
        
        Returns:
            dict: 网络统计
        """
        total_molecules = len(self.molecules)
        total_bindings = sum(len(mol.bound_molecules) for mol in self.molecules.values()) // 2
        
        avg_activity = np.mean([mol.activity_level for mol in self.molecules.values()]) if total_molecules > 0 else 0.0
        avg_stability = np.mean([mol.stability for mol in self.molecules.values()]) if total_molecules > 0 else 0.0
        avg_energy = np.mean([mol.energy_level for mol in self.molecules.values()]) if total_molecules > 0 else 0.0
        
        return {
            'total_molecules': total_molecules,
            'total_bindings': total_bindings,
            'total_interactions': self.total_interactions,
            'successful_reactions': self.successful_reactions,
            'failed_reactions': self.failed_reactions,
            'reaction_success_rate': (self.successful_reactions / 
                                    max(1, self.successful_reactions + self.failed_reactions)),
            'average_activity': avg_activity,
            'average_stability': avg_stability,
            'average_energy': avg_energy,
            'network_density': total_bindings / max(1, total_molecules * (total_molecules - 1) / 2),
            'environment': self.global_environment.copy()
        }
    
    def optimize_network(self):
        """优化网络性能"""
        # 移除孤立的低活性分子
        isolated_molecules = []
        for mol_id, mol in self.molecules.items():
            if (len(mol.bound_molecules) == 0 and 
                mol.activity_level < 0.1 and 
                mol.age > mol.max_age * 0.8):
                isolated_molecules.append(mol_id)
        
        for mol_id in isolated_molecules:
            self.remove_molecule(mol_id)
        
        # 为高活性分子补充能量
        for molecule in self.molecules.values():
            if molecule.activity_level > 0.8 and molecule.energy_level < 30.0:
                molecule.recharge_energy(20.0)
    
    def reset_network(self):
        """重置网络"""
        self.molecules.clear()
        self.interaction_matrix.clear()
        self.reaction_pathways.clear()
        self.total_interactions = 0
        self.successful_reactions = 0
        self.failed_reactions = 0