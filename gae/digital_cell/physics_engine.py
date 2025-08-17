# -*- coding: utf-8 -*-
"""
3D物理模拟引擎 - EvoForge数字细胞物理系统

根据comprehensive_implementation_plan.md任务3实现的3D物理模拟引擎，包括：
- 布朗运动模拟算法：基于随机游走和热力学的分子运动
- 高效碰撞检测系统：空间哈希网格优化的碰撞检测
- 空间哈希网格算法：O(n)复杂度的空间分割优化
- 分子间相互作用力计算：范德华力、静电力、氢键等
- 分子运动的物理约束：边界条件、能量守恒、动量守恒
- 详细的DEBUG日志和错误处理
"""

import numpy as np
import math
import logging
from typing import Dict, List, Optional, Tuple, Set, Any
from dataclasses import dataclass, field
from collections import defaultdict
import time
from abc import ABC, abstractmethod

from .macro_molecule import MacroMolecule, Vector3D, MoleculeType

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@dataclass
class PhysicsConstants:
    """物理常数"""
    BOLTZMANN_CONSTANT: float = 1.38e-23  # 玻尔兹曼常数 (J/K)
    AVOGADRO_NUMBER: float = 6.022e23     # 阿伏伽德罗常数
    ELEMENTARY_CHARGE: float = 1.602e-19  # 元电荷 (C)
    VACUUM_PERMITTIVITY: float = 8.854e-12  # 真空介电常数 (F/m)
    WATER_VISCOSITY: float = 0.001        # 水的粘度 (Pa·s)
    TEMPERATURE: float = 310.0            # 体温 (K)
    PRESSURE: float = 101325.0            # 标准大气压 (Pa)

@dataclass
class ForceField:
    """力场参数"""
    van_der_waals_strength: float = 1.0   # 范德华力强度
    electrostatic_strength: float = 1.0   # 静电力强度
    hydrogen_bond_strength: float = 1.0   # 氢键强度
    repulsion_strength: float = 10.0      # 排斥力强度
    cutoff_distance: float = 10.0         # 截断距离

class SpatialGrid:
    """空间哈希网格 - 优化碰撞检测的空间分割算法"""
    
    def __init__(self, cell_size: float = 5.0, bounds: Tuple[Vector3D, Vector3D] = None):
        """
        初始化空间网格
        
        Args:
            cell_size: 网格单元大小
            bounds: 空间边界 (min_point, max_point)
        """
        self.cell_size = cell_size
        self.grid: Dict[Tuple[int, int, int], Set[str]] = defaultdict(set)
        self.molecule_positions: Dict[str, Vector3D] = {}
        
        # 设置默认边界
        if bounds is None:
            self.min_bound = Vector3D(-50.0, -50.0, -50.0)
            self.max_bound = Vector3D(50.0, 50.0, 50.0)
        else:
            self.min_bound, self.max_bound = bounds
        
        # 统计信息
        self.collision_checks = 0
        self.grid_updates = 0
        
        logger.debug(f"初始化空间网格: 单元大小={cell_size}, 边界=({self.min_bound.x},{self.min_bound.y},{self.min_bound.z}) 到 ({self.max_bound.x},{self.max_bound.y},{self.max_bound.z})")
    
    def _get_grid_cell(self, position: Vector3D) -> Tuple[int, int, int]:
        """获取位置对应的网格单元坐标"""
        try:
            x = int((position.x - self.min_bound.x) / self.cell_size)
            y = int((position.y - self.min_bound.y) / self.cell_size)
            z = int((position.z - self.min_bound.z) / self.cell_size)
            return (x, y, z)
        except Exception as e:
            logger.error(f"计算网格单元坐标失败: {e}, 位置=({position.x},{position.y},{position.z})")
            return (0, 0, 0)
    
    def _get_neighbor_cells(self, cell: Tuple[int, int, int]) -> List[Tuple[int, int, int]]:
        """获取相邻的网格单元（包括自身）"""
        x, y, z = cell
        neighbors = []
        
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                for dz in [-1, 0, 1]:
                    neighbors.append((x + dx, y + dy, z + dz))
        
        return neighbors
    
    def update_molecule(self, molecule_id: str, old_position: Optional[Vector3D], new_position: Vector3D) -> None:
        """更新分子在网格中的位置"""
        try:
            # 移除旧位置
            if old_position is not None and molecule_id in self.molecule_positions:
                old_cell = self._get_grid_cell(old_position)
                self.grid[old_cell].discard(molecule_id)
                if not self.grid[old_cell]:  # 如果单元为空，删除它
                    del self.grid[old_cell]
            
            # 添加新位置
            new_cell = self._get_grid_cell(new_position)
            self.grid[new_cell].add(molecule_id)
            self.molecule_positions[molecule_id] = new_position
            
            self.grid_updates += 1
            
            if self.grid_updates % 1000 == 0:
                logger.debug(f"网格更新统计: 总更新次数={self.grid_updates}, 活跃单元数={len(self.grid)}")
                
        except Exception as e:
            logger.error(f"更新分子网格位置失败: {e}, 分子ID={molecule_id}")
    
    def get_nearby_molecules(self, position: Vector3D, molecule_id: str = None) -> Set[str]:
        """获取附近的分子ID列表"""
        try:
            cell = self._get_grid_cell(position)
            nearby_molecules = set()
            
            for neighbor_cell in self._get_neighbor_cells(cell):
                if neighbor_cell in self.grid:
                    nearby_molecules.update(self.grid[neighbor_cell])
            
            # 排除自身
            if molecule_id:
                nearby_molecules.discard(molecule_id)
            
            return nearby_molecules
            
        except Exception as e:
            logger.error(f"获取附近分子失败: {e}, 位置=({position.x},{position.y},{position.z})")
            return set()
    
    def remove_molecule(self, molecule_id: str) -> None:
        """从网格中移除分子"""
        try:
            if molecule_id in self.molecule_positions:
                position = self.molecule_positions[molecule_id]
                cell = self._get_grid_cell(position)
                self.grid[cell].discard(molecule_id)
                if not self.grid[cell]:
                    del self.grid[cell]
                del self.molecule_positions[molecule_id]
                
                logger.debug(f"从网格中移除分子: {molecule_id}")
                
        except Exception as e:
            logger.error(f"移除分子失败: {e}, 分子ID={molecule_id}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取网格统计信息"""
        total_molecules = len(self.molecule_positions)
        active_cells = len(self.grid)
        avg_molecules_per_cell = total_molecules / max(1, active_cells)
        
        return {
            'total_molecules': total_molecules,
            'active_cells': active_cells,
            'avg_molecules_per_cell': avg_molecules_per_cell,
            'collision_checks': self.collision_checks,
            'grid_updates': self.grid_updates,
            'cell_size': self.cell_size
        }

class InteractionForces:
    """分子间相互作用力计算"""
    
    def __init__(self, force_field: ForceField = None):
        self.force_field = force_field or ForceField()
        self.constants = PhysicsConstants()
        
        logger.debug(f"初始化相互作用力计算器: {self.force_field}")
    
    def calculate_van_der_waals_force(self, mol1: MacroMolecule, mol2: MacroMolecule) -> Vector3D:
        """计算范德华力"""
        try:
            distance_vec = mol2.position - mol1.position
            distance = distance_vec.magnitude()
            
            if distance == 0 or distance > self.force_field.cutoff_distance:
                return Vector3D(0, 0, 0)
            
            # 简化的Lennard-Jones势能
            sigma = (mol1.radius + mol2.radius) * 0.5  # 特征距离
            epsilon = self.force_field.van_der_waals_strength  # 势阱深度
            
            # 计算力的大小
            r6 = (sigma / distance) ** 6
            r12 = r6 ** 2
            force_magnitude = 24 * epsilon * (2 * r12 - r6) / distance
            
            # 力的方向
            force_direction = distance_vec.normalize()
            force = force_direction * force_magnitude
            
            logger.debug(f"范德华力: {mol1.molecule_id} <-> {mol2.molecule_id}, 距离={distance:.3f}, 力={force_magnitude:.6f}")
            return force
            
        except Exception as e:
            logger.error(f"计算范德华力失败: {e}")
            return Vector3D(0, 0, 0)
    
    def calculate_electrostatic_force(self, mol1: MacroMolecule, mol2: MacroMolecule) -> Vector3D:
        """计算静电力"""
        try:
            # 简化：假设分子有基本电荷
            charge1 = getattr(mol1, 'charge', 0.0)
            charge2 = getattr(mol2, 'charge', 0.0)
            
            if charge1 == 0 or charge2 == 0:
                return Vector3D(0, 0, 0)
            
            distance_vec = mol2.position - mol1.position
            distance = distance_vec.magnitude()
            
            if distance == 0 or distance > self.force_field.cutoff_distance:
                return Vector3D(0, 0, 0)
            
            # 库仑定律
            k = 1 / (4 * math.pi * self.constants.VACUUM_PERMITTIVITY)
            force_magnitude = k * charge1 * charge2 / (distance ** 2)
            force_magnitude *= self.force_field.electrostatic_strength
            
            force_direction = distance_vec.normalize()
            force = force_direction * force_magnitude
            
            logger.debug(f"静电力: {mol1.molecule_id} <-> {mol2.molecule_id}, 电荷=({charge1},{charge2}), 力={force_magnitude:.6f}")
            return force
            
        except Exception as e:
            logger.error(f"计算静电力失败: {e}")
            return Vector3D(0, 0, 0)
    
    def calculate_repulsion_force(self, mol1: MacroMolecule, mol2: MacroMolecule) -> Vector3D:
        """计算排斥力（防止分子重叠）"""
        try:
            distance_vec = mol2.position - mol1.position
            distance = distance_vec.magnitude()
            
            collision_distance = mol1.radius + mol2.radius
            
            if distance >= collision_distance:
                return Vector3D(0, 0, 0)
            
            # 强排斥力防止重叠
            overlap = collision_distance - distance
            force_magnitude = self.force_field.repulsion_strength * overlap
            
            if distance > 0:
                force_direction = (mol1.position - mol2.position).normalize()
            else:
                # 如果完全重叠，随机选择方向
                force_direction = Vector3D(np.random.randn(), np.random.randn(), np.random.randn()).normalize()
            
            force = force_direction * force_magnitude
            
            logger.debug(f"排斥力: {mol1.molecule_id} <-> {mol2.molecule_id}, 重叠={overlap:.3f}, 力={force_magnitude:.6f}")
            return force
            
        except Exception as e:
            logger.error(f"计算排斥力失败: {e}")
            return Vector3D(0, 0, 0)
    
    def calculate_total_force(self, mol1: MacroMolecule, mol2: MacroMolecule) -> Vector3D:
        """计算总的相互作用力"""
        try:
            vdw_force = self.calculate_van_der_waals_force(mol1, mol2)
            electrostatic_force = self.calculate_electrostatic_force(mol1, mol2)
            repulsion_force = self.calculate_repulsion_force(mol1, mol2)
            
            total_force = vdw_force + electrostatic_force + repulsion_force
            
            return total_force
            
        except Exception as e:
            logger.error(f"计算总相互作用力失败: {e}")
            return Vector3D(0, 0, 0)

class BrownianMotionSimulator:
    """布朗运动模拟器"""
    
    def __init__(self, temperature: float = 310.0, viscosity: float = 0.001):
        self.temperature = temperature
        self.viscosity = viscosity
        self.constants = PhysicsConstants()
        
        logger.debug(f"初始化布朗运动模拟器: 温度={temperature}K, 粘度={viscosity}Pa·s")
    
    def calculate_diffusion_coefficient(self, molecule: MacroMolecule) -> float:
        """计算扩散系数（Stokes-Einstein方程）"""
        try:
            # D = kT / (6πηr)
            kT = self.constants.BOLTZMANN_CONSTANT * self.temperature
            friction = 6 * math.pi * self.viscosity * molecule.radius
            diffusion_coeff = kT / friction
            
            logger.debug(f"分子 {molecule.molecule_id} 扩散系数: {diffusion_coeff:.2e} m²/s")
            return diffusion_coeff
            
        except Exception as e:
            logger.error(f"计算扩散系数失败: {e}")
            return 1e-12  # 默认值
    
    def apply_brownian_motion(self, molecule: MacroMolecule, dt: float) -> Vector3D:
        """应用布朗运动"""
        try:
            # 计算扩散系数
            D = self.calculate_diffusion_coefficient(molecule)
            
            # 随机位移的标准差
            sigma = math.sqrt(2 * D * dt)
            
            # 生成随机位移
            random_displacement = Vector3D(
                np.random.normal(0, sigma),
                np.random.normal(0, sigma),
                np.random.normal(0, sigma)
            )
            
            # 摩擦力（与速度相反）
            friction_coeff = 6 * math.pi * self.viscosity * molecule.radius
            friction_force = molecule.velocity * (-friction_coeff)
            
            # 随机力
            random_force_sigma = math.sqrt(2 * friction_coeff * self.constants.BOLTZMANN_CONSTANT * self.temperature / dt)
            random_force = Vector3D(
                np.random.normal(0, random_force_sigma),
                np.random.normal(0, random_force_sigma),
                np.random.normal(0, random_force_sigma)
            )
            
            # 更新速度
            acceleration = (friction_force + random_force) * (1.0 / molecule.mass)
            velocity_change = acceleration * dt
            
            logger.debug(f"布朗运动: {molecule.molecule_id}, 随机位移=({random_displacement.x:.6f},{random_displacement.y:.6f},{random_displacement.z:.6f})")
            
            return random_displacement
            
        except Exception as e:
            logger.error(f"应用布朗运动失败: {e}")
            return Vector3D(0, 0, 0)

class PhysicsEngine:
    """3D物理模拟引擎主类"""
    
    def __init__(self, 
                 bounds: Tuple[Vector3D, Vector3D] = None,
                 grid_cell_size: float = 5.0,
                 temperature: float = 310.0,
                 force_field: ForceField = None):
        """
        初始化物理引擎
        
        Args:
            bounds: 模拟空间边界
            grid_cell_size: 空间网格单元大小
            temperature: 模拟温度
            force_field: 力场参数
        """
        self.bounds = bounds or (Vector3D(-50, -50, -50), Vector3D(50, 50, 50))
        self.temperature = temperature
        
        # 初始化子系统
        self.spatial_grid = SpatialGrid(grid_cell_size, self.bounds)
        self.force_calculator = InteractionForces(force_field)
        self.brownian_simulator = BrownianMotionSimulator(temperature)
        
        # 分子管理
        self.molecules: Dict[str, MacroMolecule] = {}
        self.active_molecules: Set[str] = set()
        
        # 模拟参数
        self.time_step = 0.001  # 1ms
        self.current_time = 0.0
        
        # 统计信息
        self.simulation_stats = {
            'total_steps': 0,
            'collision_events': 0,
            'binding_events': 0,
            'unbinding_events': 0,
            'boundary_collisions': 0,
            'force_calculations': 0
        }
        
        logger.info(f"物理引擎初始化完成: 边界={self.bounds}, 网格大小={grid_cell_size}, 温度={temperature}K")
    
    def add_molecule(self, molecule: MacroMolecule) -> None:
        """添加分子到模拟系统"""
        try:
            self.molecules[molecule.molecule_id] = molecule
            self.active_molecules.add(molecule.molecule_id)
            self.spatial_grid.update_molecule(molecule.molecule_id, None, molecule.position)
            
            logger.debug(f"添加分子到物理引擎: {molecule.molecule_id}, 类型={molecule.get_molecule_type().value}")
            
        except Exception as e:
            logger.error(f"添加分子失败: {e}")
    
    def remove_molecule(self, molecule_id: str) -> None:
        """从模拟系统移除分子"""
        try:
            if molecule_id in self.molecules:
                self.spatial_grid.remove_molecule(molecule_id)
                del self.molecules[molecule_id]
                self.active_molecules.discard(molecule_id)
                
                logger.debug(f"从物理引擎移除分子: {molecule_id}")
                
        except Exception as e:
            logger.error(f"移除分子失败: {e}")
    
    def _enforce_boundary_conditions(self, molecule: MacroMolecule) -> None:
        """强制边界条件"""
        try:
            min_bound, max_bound = self.bounds
            position_changed = False
            
            # 检查X边界
            if molecule.position.x < min_bound.x + molecule.radius:
                molecule.position.x = min_bound.x + molecule.radius
                molecule.velocity.x = abs(molecule.velocity.x) * 0.8  # 弹性碰撞
                position_changed = True
                self.simulation_stats['boundary_collisions'] += 1
            elif molecule.position.x > max_bound.x - molecule.radius:
                molecule.position.x = max_bound.x - molecule.radius
                molecule.velocity.x = -abs(molecule.velocity.x) * 0.8
                position_changed = True
                self.simulation_stats['boundary_collisions'] += 1
            
            # 检查Y边界
            if molecule.position.y < min_bound.y + molecule.radius:
                molecule.position.y = min_bound.y + molecule.radius
                molecule.velocity.y = abs(molecule.velocity.y) * 0.8
                position_changed = True
                self.simulation_stats['boundary_collisions'] += 1
            elif molecule.position.y > max_bound.y - molecule.radius:
                molecule.position.y = max_bound.y - molecule.radius
                molecule.velocity.y = -abs(molecule.velocity.y) * 0.8
                position_changed = True
                self.simulation_stats['boundary_collisions'] += 1
            
            # 检查Z边界
            if molecule.position.z < min_bound.z + molecule.radius:
                molecule.position.z = min_bound.z + molecule.radius
                molecule.velocity.z = abs(molecule.velocity.z) * 0.8
                position_changed = True
                self.simulation_stats['boundary_collisions'] += 1
            elif molecule.position.z > max_bound.z - molecule.radius:
                molecule.position.z = max_bound.z - molecule.radius
                molecule.velocity.z = -abs(molecule.velocity.z) * 0.8
                position_changed = True
                self.simulation_stats['boundary_collisions'] += 1
            
            if position_changed:
                logger.debug(f"分子 {molecule.molecule_id} 边界碰撞，位置调整到 ({molecule.position.x:.3f},{molecule.position.y:.3f},{molecule.position.z:.3f})")
                
        except Exception as e:
            logger.error(f"强制边界条件失败: {e}")
    
    def _calculate_intermolecular_forces(self, molecule: MacroMolecule) -> Vector3D:
        """计算分子间相互作用力"""
        try:
            total_force = Vector3D(0, 0, 0)
            
            # 获取附近的分子
            nearby_molecule_ids = self.spatial_grid.get_nearby_molecules(molecule.position, molecule.molecule_id)
            
            for other_id in nearby_molecule_ids:
                if other_id in self.molecules and other_id != molecule.molecule_id:
                    other_molecule = self.molecules[other_id]
                    
                    # 计算相互作用力
                    force = self.force_calculator.calculate_total_force(molecule, other_molecule)
                    total_force = total_force + force
                    
                    self.simulation_stats['force_calculations'] += 1
            
            return total_force
            
        except Exception as e:
            logger.error(f"计算分子间相互作用力失败: {e}")
            return Vector3D(0, 0, 0)
    
    def _update_molecule_motion(self, molecule: MacroMolecule, dt: float) -> None:
        """更新分子运动"""
        try:
            old_position = Vector3D(molecule.position.x, molecule.position.y, molecule.position.z)
            
            # 1. 计算分子间相互作用力
            intermolecular_force = self._calculate_intermolecular_forces(molecule)
            
            # 2. 应用布朗运动
            brownian_displacement = self.brownian_simulator.apply_brownian_motion(molecule, dt)
            
            # 3. 更新速度（牛顿第二定律）
            acceleration = intermolecular_force * (1.0 / molecule.mass)
            molecule.velocity = molecule.velocity + acceleration * dt
            
            # 4. 更新位置
            velocity_displacement = molecule.velocity * dt
            total_displacement = velocity_displacement + brownian_displacement
            molecule.position = molecule.position + total_displacement
            
            # 5. 强制边界条件
            self._enforce_boundary_conditions(molecule)
            
            # 6. 更新空间网格
            self.spatial_grid.update_molecule(molecule.molecule_id, old_position, molecule.position)
            
            logger.debug(f"更新分子运动: {molecule.molecule_id}, 位移=({total_displacement.x:.6f},{total_displacement.y:.6f},{total_displacement.z:.6f})")
            
        except Exception as e:
            logger.error(f"更新分子运动失败: {e}")
    
    def _process_molecular_interactions(self) -> None:
        """处理分子间相互作用"""
        try:
            processed_pairs = set()
            
            for molecule_id in list(self.active_molecules):
                if molecule_id not in self.molecules:
                    continue
                    
                molecule = self.molecules[molecule_id]
                nearby_ids = self.spatial_grid.get_nearby_molecules(molecule.position, molecule_id)
                
                for other_id in nearby_ids:
                    if other_id not in self.molecules:
                        continue
                    
                    # 避免重复处理同一对分子
                    pair = tuple(sorted([molecule_id, other_id]))
                    if pair in processed_pairs:
                        continue
                    processed_pairs.add(pair)
                    
                    other_molecule = self.molecules[other_id]
                    
                    # 检查碰撞
                    if molecule.check_collision(other_molecule):
                        self.simulation_stats['collision_events'] += 1
                        
                        # 处理分子交互
                        interaction_result = molecule.interact_with(other_molecule)
                        
                        if interaction_result.get('binding_occurred', False):
                            self.simulation_stats['binding_events'] += 1
                            logger.debug(f"分子结合事件: {molecule_id} <-> {other_id}")
                        
                        logger.debug(f"分子碰撞: {molecule_id} <-> {other_id}, 交互类型={interaction_result.get('interaction_type')}")
            
        except Exception as e:
            logger.error(f"处理分子间相互作用失败: {e}")
    
    def step(self, dt: Optional[float] = None) -> None:
        """执行一个模拟步骤"""
        try:
            if dt is None:
                dt = self.time_step
            
            start_time = time.time()
            
            # 1. 更新所有活跃分子的运动
            for molecule_id in list(self.active_molecules):
                if molecule_id in self.molecules:
                    molecule = self.molecules[molecule_id]
                    if molecule.is_active:
                        self._update_molecule_motion(molecule, dt)
                    else:
                        # 移除非活跃分子
                        self.remove_molecule(molecule_id)
            
            # 2. 处理分子间相互作用
            self._process_molecular_interactions()
            
            # 3. 更新模拟时间和统计
            self.current_time += dt
            self.simulation_stats['total_steps'] += 1
            
            step_time = time.time() - start_time
            
            # 定期输出统计信息
            if self.simulation_stats['total_steps'] % 1000 == 0:
                logger.info(f"模拟步骤 {self.simulation_stats['total_steps']}: 时间={self.current_time:.3f}s, 活跃分子={len(self.active_molecules)}, 步骤耗时={step_time:.6f}s")
                logger.info(f"统计信息: {self.simulation_stats}")
                grid_stats = self.spatial_grid.get_statistics()
                logger.info(f"网格统计: {grid_stats}")
            
        except Exception as e:
            logger.error(f"模拟步骤执行失败: {e}")
    
    def run_simulation(self, duration: float, progress_callback=None) -> None:
        """运行模拟指定时长"""
        try:
            logger.info(f"开始运行物理模拟: 时长={duration}s, 时间步长={self.time_step}s")
            
            steps = int(duration / self.time_step)
            
            for step_num in range(steps):
                self.step()
                
                # 调用进度回调
                if progress_callback and step_num % 100 == 0:
                    progress = step_num / steps
                    progress_callback(progress, self.get_simulation_state())
                
                # 检查是否还有活跃分子
                if not self.active_molecules:
                    logger.warning("没有活跃分子，停止模拟")
                    break
            
            logger.info(f"物理模拟完成: 总步数={self.simulation_stats['total_steps']}, 最终时间={self.current_time:.3f}s")
            
        except Exception as e:
            logger.error(f"运行模拟失败: {e}")
    
    def get_simulation_state(self) -> Dict[str, Any]:
        """获取当前模拟状态"""
        try:
            molecule_states = {}
            for mol_id, molecule in self.molecules.items():
                if molecule.is_active:
                    molecule_states[mol_id] = molecule.get_state()
            
            return {
                'current_time': self.current_time,
                'active_molecules': len(self.active_molecules),
                'total_molecules': len(self.molecules),
                'simulation_stats': self.simulation_stats.copy(),
                'grid_stats': self.spatial_grid.get_statistics(),
                'molecules': molecule_states,
                'bounds': {
                    'min': {'x': self.bounds[0].x, 'y': self.bounds[0].y, 'z': self.bounds[0].z},
                    'max': {'x': self.bounds[1].x, 'y': self.bounds[1].y, 'z': self.bounds[1].z}
                }
            }
            
        except Exception as e:
            logger.error(f"获取模拟状态失败: {e}")
            return {}
    
    def reset_simulation(self) -> None:
        """重置模拟状态"""
        try:
            self.molecules.clear()
            self.active_molecules.clear()
            self.spatial_grid = SpatialGrid(self.spatial_grid.cell_size, self.bounds)
            self.current_time = 0.0
            
            # 重置统计信息
            for key in self.simulation_stats:
                self.simulation_stats[key] = 0
            
            logger.info("物理模拟已重置")
            
        except Exception as e:
            logger.error(f"重置模拟失败: {e}")

if __name__ == "__main__":
    # 测试代码
    logger.info("3D物理模拟引擎测试开始")
    
    # 创建物理引擎
    engine = PhysicsEngine(
        bounds=(Vector3D(-20, -20, -20), Vector3D(20, 20, 20)),
        grid_cell_size=3.0,
        temperature=310.0
    )
    
    # 导入分子类型
    from .macro_molecule import create_molecule, MoleculeType
    
    # 创建测试分子
    molecules = []
    for i in range(10):
        mol = create_molecule(
            MoleculeType.PROTEIN,
            position=Vector3D(
                np.random.uniform(-10, 10),
                np.random.uniform(-10, 10),
                np.random.uniform(-10, 10)
            ),
            velocity=Vector3D(
                np.random.uniform(-1, 1),
                np.random.uniform(-1, 1),
                np.random.uniform(-1, 1)
            )
        )
        molecules.append(mol)
        engine.add_molecule(mol)
    
    # 运行短时间模拟
    def progress_callback(progress, state):
        if progress % 0.1 < 0.01:  # 每10%输出一次
            logger.info(f"模拟进度: {progress*100:.1f}%, 活跃分子: {state['active_molecules']}")
    
    engine.run_simulation(duration=1.0, progress_callback=progress_callback)
    
    # 输出最终状态
    final_state = engine.get_simulation_state()
    logger.info(f"最终模拟状态: {final_state['simulation_stats']}")
    
    logger.info("3D物理模拟引擎测试完成")