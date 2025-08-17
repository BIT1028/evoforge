import numpy as np
from typing import List, Dict, Tuple, Set
from collections import defaultdict
import math
from .macro_molecule import MacroMolecule

class SpatialGrid:
    """空间网格 - 用于优化碰撞检测的数据结构
    
    将3D空间划分为网格，只检测相邻网格中的分子碰撞，
    大大减少了O(n²)的碰撞检测复杂度。
    """
    
    def __init__(self, world_size: Tuple[float, float, float], grid_size: float = 2.0):
        """
        初始化空间网格
        
        Args:
            world_size: 世界大小 (width, height, depth)
            grid_size: 网格大小，应该略大于最大分子半径的2倍
        """
        self.world_size = np.array(world_size)
        self.grid_size = grid_size
        self.grid_dims = (self.world_size / grid_size).astype(int) + 1
        
        # 网格字典：grid_coord -> set of molecule_ids
        self.grid: Dict[Tuple[int, int, int], Set[str]] = defaultdict(set)
        
        # 分子位置缓存：molecule_id -> grid_coord
        self.molecule_positions: Dict[str, Tuple[int, int, int]] = {}
    
    def _get_grid_coord(self, position: np.ndarray) -> Tuple[int, int, int]:
        """获取位置对应的网格坐标
        
        Args:
            position: 3D位置
            
        Returns:
            Tuple[int, int, int]: 网格坐标
        """
        coord = (position / self.grid_size).astype(int)
        # 确保坐标在有效范围内
        coord = np.clip(coord, 0, self.grid_dims - 1)
        return tuple(coord)
    
    def update_molecule(self, molecule: MacroMolecule):
        """更新分子在网格中的位置
        
        Args:
            molecule: 要更新的分子
        """
        new_coord = self._get_grid_coord(molecule.position)
        old_coord = self.molecule_positions.get(molecule.id)
        
        # 如果位置发生变化，更新网格
        if old_coord != new_coord:
            if old_coord is not None:
                self.grid[old_coord].discard(molecule.id)
                if not self.grid[old_coord]:  # 如果网格为空，删除它
                    del self.grid[old_coord]
            
            self.grid[new_coord].add(molecule.id)
            self.molecule_positions[molecule.id] = new_coord
    
    def remove_molecule(self, molecule_id: str):
        """从网格中移除分子
        
        Args:
            molecule_id: 分子ID
        """
        if molecule_id in self.molecule_positions:
            coord = self.molecule_positions[molecule_id]
            self.grid[coord].discard(molecule_id)
            if not self.grid[coord]:
                del self.grid[coord]
            del self.molecule_positions[molecule_id]
    
    def get_nearby_molecules(self, molecule: MacroMolecule) -> Set[str]:
        """获取分子附近的所有分子ID
        
        Args:
            molecule: 目标分子
            
        Returns:
            Set[str]: 附近分子的ID集合
        """
        coord = self._get_grid_coord(molecule.position)
        nearby_molecules = set()
        
        # 检查当前网格和相邻的26个网格
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                for dz in [-1, 0, 1]:
                    check_coord = (coord[0] + dx, coord[1] + dy, coord[2] + dz)
                    if (0 <= check_coord[0] < self.grid_dims[0] and
                        0 <= check_coord[1] < self.grid_dims[1] and
                        0 <= check_coord[2] < self.grid_dims[2]):
                        nearby_molecules.update(self.grid.get(check_coord, set()))
        
        # 移除自己
        nearby_molecules.discard(molecule.id)
        return nearby_molecules

class PhysicsEngine:
    """物理引擎 - 处理分子间的物理交互
    
    负责分子运动、碰撞检测、结合/解离反应和边界处理。
    这是整个系统的物理基础，所有涌现行为都基于这些基本物理规则。
    """
    
    def __init__(self, world_size: Tuple[float, float, float] = (50.0, 50.0, 50.0)):
        """
        初始化物理引擎
        
        Args:
            world_size: 世界边界大小
        """
        self.world_size = np.array(world_size)
        self.spatial_grid = SpatialGrid(world_size)
        
        # 物理常数
        self.interaction_radius = 1.5  # 分子交互半径
        self.binding_probability = 0.1  # 基础结合概率
        self.unbinding_probability = 0.01  # 基础解离概率
        self.collision_damping = 0.8  # 碰撞阻尼系数
        
        # 统计信息
        self.collision_count = 0
        self.binding_count = 0
        self.unbinding_count = 0
    
    def update_molecules(self, molecules: Dict[str, MacroMolecule], dt: float = 1.0):
        """更新所有分子的物理状态
        
        Args:
            molecules: 分子字典
            dt: 时间步长
        """
        # 1. 更新分子物理状态
        for molecule in molecules.values():
            molecule.update_physics(dt)
            self._enforce_boundary(molecule)
            self.spatial_grid.update_molecule(molecule)
        
        # 2. 处理分子间交互
        self._process_interactions(molecules)
        
        # 3. 处理自发解离
        self._process_spontaneous_unbinding(molecules)
    
    def _enforce_boundary(self, molecule: MacroMolecule):
        """强制分子保持在世界边界内
        
        Args:
            molecule: 要处理的分子
        """
        # 检查每个维度的边界
        for i in range(3):
            if molecule.position[i] < molecule.radius:
                molecule.position[i] = molecule.radius
                molecule.velocity[i] = abs(molecule.velocity[i]) * self.collision_damping
            elif molecule.position[i] > self.world_size[i] - molecule.radius:
                molecule.position[i] = self.world_size[i] - molecule.radius
                molecule.velocity[i] = -abs(molecule.velocity[i]) * self.collision_damping
    
    def _process_interactions(self, molecules: Dict[str, MacroMolecule]):
        """处理分子间的交互
        
        Args:
            molecules: 分子字典
        """
        processed_pairs = set()
        
        for molecule in molecules.values():
            nearby_ids = self.spatial_grid.get_nearby_molecules(molecule)
            
            for other_id in nearby_ids:
                if other_id not in molecules:
                    continue
                    
                # 避免重复处理同一对分子
                pair = tuple(sorted([molecule.id, other_id]))
                if pair in processed_pairs:
                    continue
                processed_pairs.add(pair)
                
                other = molecules[other_id]
                distance = molecule.distance_to(other)
                
                # 检查是否在交互范围内
                if distance <= self.interaction_radius:
                    self._handle_collision(molecule, other)
                    self._attempt_binding(molecule, other)
    
    def _handle_collision(self, mol1: MacroMolecule, mol2: MacroMolecule):
        """处理两个分子的碰撞
        
        Args:
            mol1: 分子1
            mol2: 分子2
        """
        self.collision_count += 1
        
        # 计算碰撞向量
        collision_vector = mol1.position - mol2.position
        distance = np.linalg.norm(collision_vector)
        
        if distance < mol1.radius + mol2.radius and distance > 0:
            # 标准化碰撞向量
            collision_normal = collision_vector / distance
            
            # 分离重叠的分子
            overlap = mol1.radius + mol2.radius - distance
            separation = collision_normal * overlap * 0.5
            
            mol1.position += separation
            mol2.position -= separation
            
            # 计算相对速度
            relative_velocity = mol1.velocity - mol2.velocity
            velocity_along_normal = np.dot(relative_velocity, collision_normal)
            
            # 如果分子正在分离，不处理碰撞
            if velocity_along_normal > 0:
                return
            
            # 计算冲量（假设弹性碰撞）
            restitution = 0.7  # 恢复系数
            impulse_magnitude = -(1 + restitution) * velocity_along_normal
            impulse_magnitude /= (1/mol1.mass + 1/mol2.mass)
            
            impulse = impulse_magnitude * collision_normal
            
            # 应用冲量
            mol1.velocity += impulse / mol1.mass
            mol2.velocity -= impulse / mol2.mass
            
            # 应用阻尼
            mol1.velocity *= self.collision_damping
            mol2.velocity *= self.collision_damping
    
    def _attempt_binding(self, mol1: MacroMolecule, mol2: MacroMolecule):
        """尝试两个分子结合
        
        Args:
            mol1: 分子1
            mol2: 分子2
        """
        # 如果已经结合，跳过
        if mol2.id in mol1.bound_molecules:
            return
        
        # 寻找匹配的结合位点
        for site1_name, site1 in mol1.binding_sites.items():
            if site1.is_occupied:
                continue
                
            for site2_name, site2 in mol2.binding_sites.items():
                if site2.is_occupied:
                    continue
                
                # 检查位点是否匹配
                if site1.shape_id == site2.shape_id:
                    # 计算结合概率
                    binding_prob = self._calculate_binding_probability(mol1, mol2, site1, site2)
                    
                    if np.random.random() < binding_prob:
                        success = mol1.bind_to(mol2, site1_name, site2_name)
                        if success:
                            self.binding_count += 1
                            self._on_binding_formed(mol1, mol2)
                            return  # 一次只结合一个位点
    
    def _calculate_binding_probability(self, mol1: MacroMolecule, mol2: MacroMolecule, 
                                     site1, site2) -> float:
        """计算两个分子结合的概率
        
        Args:
            mol1: 分子1
            mol2: 分子2
            site1: 分子1的结合位点
            site2: 分子2的结合位点
            
        Returns:
            float: 结合概率 (0-1)
        """
        base_prob = self.binding_probability
        
        # 根据结合强度调整概率
        strength_factor = (site1.binding_strength + site2.binding_strength) / 2
        
        # 根据分子相对速度调整概率（速度越慢越容易结合）
        relative_speed = np.linalg.norm(mol1.velocity - mol2.velocity)
        speed_factor = max(0.1, 1.0 - relative_speed * 0.5)
        
        # 根据分子稳定性调整概率
        stability_factor = min(mol1.stability, mol2.stability) / 100.0
        
        return base_prob * strength_factor * speed_factor * stability_factor
    
    def _process_spontaneous_unbinding(self, molecules: Dict[str, MacroMolecule]):
        """处理自发解离反应
        
        Args:
            molecules: 分子字典
        """
        unbinding_pairs = []
        
        for molecule in molecules.values():
            for bound_mol in list(molecule.bound_molecules.values()):
                # 计算解离概率
                unbinding_prob = self._calculate_unbinding_probability(molecule, bound_mol)
                
                if np.random.random() < unbinding_prob:
                    unbinding_pairs.append((molecule, bound_mol))
        
        # 执行解离
        for mol1, mol2 in unbinding_pairs:
            mol1.unbind_from(mol2)
            self.unbinding_count += 1
            self._on_binding_broken(mol1, mol2)
    
    def _calculate_unbinding_probability(self, mol1: MacroMolecule, mol2: MacroMolecule) -> float:
        """计算两个分子解离的概率
        
        Args:
            mol1: 分子1
            mol2: 分子2
            
        Returns:
            float: 解离概率 (0-1)
        """
        base_prob = self.unbinding_probability
        
        # 根据分子稳定性调整概率（稳定性越低越容易解离）
        stability_factor = 2.0 - min(mol1.stability, mol2.stability) / 100.0
        
        # 根据分子年龄调整概率（年龄越大越容易解离）
        age_factor = 1.0 + (mol1.age + mol2.age) / 2000.0
        
        return min(1.0, base_prob * stability_factor * age_factor)
    
    def _on_binding_formed(self, mol1: MacroMolecule, mol2: MacroMolecule):
        """结合形成时的回调
        
        Args:
            mol1: 分子1
            mol2: 分子2
        """
        # 结合时稍微增加稳定性
        mol1.stability = min(mol1.max_stability, mol1.stability + 5.0)
        mol2.stability = min(mol2.max_stability, mol2.stability + 5.0)
        
        # 减少运动（结合的分子运动更慢）
        mol1.velocity *= 0.8
        mol2.velocity *= 0.8
    
    def _on_binding_broken(self, mol1: MacroMolecule, mol2: MacroMolecule):
        """结合断裂时的回调
        
        Args:
            mol1: 分子1
            mol2: 分子2
        """
        # 解离时给分子一些随机速度
        separation_force = np.random.randn(3) * 0.2
        mol1.velocity += separation_force
        mol2.velocity -= separation_force
    
    def get_statistics(self) -> Dict[str, int]:
        """获取物理引擎统计信息
        
        Returns:
            Dict[str, int]: 统计信息字典
        """
        return {
            'collision_count': self.collision_count,
            'binding_count': self.binding_count,
            'unbinding_count': self.unbinding_count
        }
    
    def reset_statistics(self):
        """重置统计信息"""
        self.collision_count = 0
        self.binding_count = 0
        self.unbinding_count = 0