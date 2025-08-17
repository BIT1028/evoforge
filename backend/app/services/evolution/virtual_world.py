import numpy as np
from typing import List, Dict, Optional, Any, Tuple, Callable
from .digital_cell import DigitalCell
from .macro_molecule import MacroMolecule, MoleculeType
from .meta_genome import MetaGenome
from .physics_engine import PhysicsEngine
import time
import json
from dataclasses import dataclass, asdict
from collections import defaultdict
import threading
import queue

@dataclass
class EnvironmentParameters:
    """环境参数"""
    temperature: float = 310.0  # 温度 (K)
    ph: float = 7.0  # pH值
    ionic_strength: float = 0.15  # 离子强度
    oxygen_level: float = 0.21  # 氧气浓度
    nutrient_density: float = 1.0  # 营养密度
    toxin_level: float = 0.0  # 毒素水平
    radiation_level: float = 0.0  # 辐射水平
    pressure: float = 101325.0  # 压力 (Pa)

@dataclass
class EcosystemStats:
    """生态系统统计信息"""
    timestamp: float
    total_cells: int
    living_cells: int
    dead_cells: int
    total_molecules: int
    average_cell_energy: float
    average_cell_health: float
    average_cell_age: float
    population_density: float
    genetic_diversity: float
    compilation_success_rate: float
    energy_flow_rate: float
    molecular_complexity: float
    environmental_stress: float

@dataclass
class WorldEvent:
    """世界事件"""
    timestamp: float
    event_type: str
    description: str
    affected_cells: List[str]
    parameters: Dict[str, Any]
    severity: float  # 0-1

class EnvironmentController:
    """环境控制器
    
    管理虚拟世界的环境参数，模拟各种环境变化和压力。
    """
    
    def __init__(self, initial_params: Optional[EnvironmentParameters] = None):
        """
        初始化环境控制器
        
        Args:
            initial_params: 初始环境参数
        """
        self.params = initial_params or EnvironmentParameters()
        self.param_history: List[Tuple[float, EnvironmentParameters]] = []
        self.active_events: List[WorldEvent] = []
        self.event_history: List[WorldEvent] = []
        
        # 环境变化模式
        self.fluctuation_patterns = {
            'temperature': {'amplitude': 5.0, 'frequency': 0.01, 'phase': 0.0},
            'ph': {'amplitude': 0.5, 'frequency': 0.005, 'phase': 0.0},
            'nutrient_density': {'amplitude': 0.3, 'frequency': 0.02, 'phase': 0.0}
        }
        
        # 压力事件概率
        self.stress_event_probability = 0.001  # 每次更新0.1%的概率
    
    def update(self, dt: float, world_time: float):
        """更新环境参数
        
        Args:
            dt: 时间步长
            world_time: 世界时间
        """
        # 自然波动
        self._apply_natural_fluctuations(world_time)
        
        # 随机压力事件
        self._check_stress_events(world_time)
        
        # 处理活跃事件
        self._process_active_events(dt)
        
        # 记录历史
        self.param_history.append((world_time, self.params))
        
        # 限制历史长度
        if len(self.param_history) > 1000:
            self.param_history.pop(0)
    
    def _apply_natural_fluctuations(self, world_time: float):
        """应用自然波动
        
        Args:
            world_time: 世界时间
        """
        # 温度波动
        temp_pattern = self.fluctuation_patterns['temperature']
        temp_delta = (temp_pattern['amplitude'] * 
                     np.sin(temp_pattern['frequency'] * world_time + temp_pattern['phase']))
        self.params.temperature = 310.0 + temp_delta
        
        # pH波动
        ph_pattern = self.fluctuation_patterns['ph']
        ph_delta = (ph_pattern['amplitude'] * 
                   np.sin(ph_pattern['frequency'] * world_time + ph_pattern['phase']))
        self.params.ph = 7.0 + ph_delta
        
        # 营养密度波动
        nutrient_pattern = self.fluctuation_patterns['nutrient_density']
        nutrient_delta = (nutrient_pattern['amplitude'] * 
                         np.sin(nutrient_pattern['frequency'] * world_time + nutrient_pattern['phase']))
        self.params.nutrient_density = max(0.1, 1.0 + nutrient_delta)
    
    def _check_stress_events(self, world_time: float):
        """检查压力事件
        
        Args:
            world_time: 世界时间
        """
        if np.random.random() < self.stress_event_probability:
            event_type = np.random.choice([
                'temperature_shock', 'ph_shock', 'toxin_release', 
                'radiation_burst', 'nutrient_depletion', 'pressure_change'
            ])
            
            self._trigger_stress_event(event_type, world_time)
    
    def _trigger_stress_event(self, event_type: str, world_time: float):
        """触发压力事件
        
        Args:
            event_type: 事件类型
            world_time: 世界时间
        """
        event_params = {}
        severity = np.random.uniform(0.3, 1.0)
        
        if event_type == 'temperature_shock':
            delta = np.random.choice([-1, 1]) * np.random.uniform(10, 30)
            event_params['temperature_delta'] = delta
            event_params['duration'] = np.random.uniform(5, 20)
            description = f"温度冲击: {delta:+.1f}K"
            
        elif event_type == 'ph_shock':
            delta = np.random.choice([-1, 1]) * np.random.uniform(1, 3)
            event_params['ph_delta'] = delta
            event_params['duration'] = np.random.uniform(3, 15)
            description = f"pH冲击: {delta:+.1f}"
            
        elif event_type == 'toxin_release':
            toxin_level = np.random.uniform(0.1, 0.8)
            event_params['toxin_level'] = toxin_level
            event_params['duration'] = np.random.uniform(10, 30)
            description = f"毒素释放: {toxin_level:.2f}"
            
        elif event_type == 'radiation_burst':
            radiation = np.random.uniform(0.1, 0.5)
            event_params['radiation_level'] = radiation
            event_params['duration'] = np.random.uniform(2, 10)
            description = f"辐射爆发: {radiation:.2f}"
            
        elif event_type == 'nutrient_depletion':
            depletion = np.random.uniform(0.3, 0.8)
            event_params['nutrient_multiplier'] = 1.0 - depletion
            event_params['duration'] = np.random.uniform(15, 40)
            description = f"营养耗竭: -{depletion*100:.0f}%"
            
        elif event_type == 'pressure_change':
            delta = np.random.choice([-1, 1]) * np.random.uniform(10000, 50000)
            event_params['pressure_delta'] = delta
            event_params['duration'] = np.random.uniform(5, 25)
            description = f"压力变化: {delta:+.0f}Pa"
        
        event = WorldEvent(
            timestamp=world_time,
            event_type=event_type,
            description=description,
            affected_cells=[],  # 将在处理时填充
            parameters=event_params,
            severity=severity
        )
        
        self.active_events.append(event)
        print(f"环境事件触发: {description} (严重程度: {severity:.2f})")
    
    def _process_active_events(self, dt: float):
        """处理活跃事件
        
        Args:
            dt: 时间步长
        """
        events_to_remove = []
        
        for event in self.active_events:
            # 应用事件效果
            self._apply_event_effects(event)
            
            # 减少事件持续时间
            event.parameters['duration'] = event.parameters.get('duration', 0) - dt
            
            # 检查事件是否结束
            if event.parameters.get('duration', 0) <= 0:
                events_to_remove.append(event)
                self.event_history.append(event)
                print(f"环境事件结束: {event.description}")
        
        # 移除结束的事件
        for event in events_to_remove:
            self.active_events.remove(event)
    
    def _apply_event_effects(self, event: WorldEvent):
        """应用事件效果
        
        Args:
            event: 世界事件
        """
        if event.event_type == 'temperature_shock':
            delta = event.parameters.get('temperature_delta', 0)
            self.params.temperature += delta * 0.1  # 逐渐应用效果
            
        elif event.event_type == 'ph_shock':
            delta = event.parameters.get('ph_delta', 0)
            self.params.ph += delta * 0.1
            
        elif event.event_type == 'toxin_release':
            target_level = event.parameters.get('toxin_level', 0)
            self.params.toxin_level = min(target_level, self.params.toxin_level + 0.01)
            
        elif event.event_type == 'radiation_burst':
            target_level = event.parameters.get('radiation_level', 0)
            self.params.radiation_level = min(target_level, self.params.radiation_level + 0.01)
            
        elif event.event_type == 'nutrient_depletion':
            multiplier = event.parameters.get('nutrient_multiplier', 1.0)
            self.params.nutrient_density *= (multiplier + 0.99) / 2  # 逐渐应用
            
        elif event.event_type == 'pressure_change':
            delta = event.parameters.get('pressure_delta', 0)
            self.params.pressure += delta * 0.1
    
    def get_environmental_stress(self) -> float:
        """计算环境压力
        
        Returns:
            float: 环境压力值 (0-1)
        """
        stress = 0.0
        
        # 温度压力
        temp_stress = abs(self.params.temperature - 310.0) / 50.0
        stress += min(1.0, temp_stress) * 0.2
        
        # pH压力
        ph_stress = abs(self.params.ph - 7.0) / 3.0
        stress += min(1.0, ph_stress) * 0.2
        
        # 毒素压力
        stress += self.params.toxin_level * 0.3
        
        # 辐射压力
        stress += self.params.radiation_level * 0.2
        
        # 营养压力
        nutrient_stress = max(0, 1.0 - self.params.nutrient_density)
        stress += nutrient_stress * 0.1
        
        return min(1.0, stress)
    
    def set_parameter(self, param_name: str, value: float):
        """设置环境参数
        
        Args:
            param_name: 参数名称
            value: 参数值
        """
        if hasattr(self.params, param_name):
            setattr(self.params, param_name, value)
    
    def get_parameters(self) -> EnvironmentParameters:
        """获取当前环境参数
        
        Returns:
            EnvironmentParameters: 环境参数
        """
        return self.params

class EcosystemMonitor:
    """生态系统监控器
    
    监控和分析虚拟世界中的生态系统状态。
    """
    
    def __init__(self):
        """初始化生态系统监控器"""
        self.stats_history: List[EcosystemStats] = []
        self.monitoring_interval = 1.0  # 监控间隔（秒）
        self.last_monitoring_time = 0.0
    
    def update(self, world_time: float, cells: List[DigitalCell], 
              molecules: List[MacroMolecule], env_controller: EnvironmentController):
        """更新监控数据
        
        Args:
            world_time: 世界时间
            cells: 细胞列表
            molecules: 分子列表
            env_controller: 环境控制器
        """
        if world_time - self.last_monitoring_time >= self.monitoring_interval:
            stats = self._calculate_ecosystem_stats(world_time, cells, molecules, env_controller)
            self.stats_history.append(stats)
            
            # 限制历史长度
            if len(self.stats_history) > 1000:
                self.stats_history.pop(0)
            
            self.last_monitoring_time = world_time
    
    def _calculate_ecosystem_stats(self, world_time: float, cells: List[DigitalCell], 
                                  molecules: List[MacroMolecule], 
                                  env_controller: EnvironmentController) -> EcosystemStats:
        """计算生态系统统计信息
        
        Args:
            world_time: 世界时间
            cells: 细胞列表
            molecules: 分子列表
            env_controller: 环境控制器
            
        Returns:
            EcosystemStats: 统计信息
        """
        living_cells = [cell for cell in cells if not cell.is_dead()]
        dead_cells = [cell for cell in cells if cell.is_dead()]
        
        # 基础统计
        total_cells = len(cells)
        living_count = len(living_cells)
        dead_count = len(dead_cells)
        total_molecules = len(molecules)
        
        # 细胞平均值
        if living_cells:
            avg_energy = np.mean([cell.energy for cell in living_cells])
            avg_health = np.mean([cell.health for cell in living_cells])
            avg_age = np.mean([cell.age for cell in living_cells])
        else:
            avg_energy = avg_health = avg_age = 0.0
        
        # 种群密度（假设世界体积为1000立方单位）
        world_volume = 1000.0
        population_density = living_count / world_volume
        
        # 遗传多样性
        genetic_diversity = self._calculate_genetic_diversity(living_cells)
        
        # 编译成功率
        compilation_success_rate = self._calculate_compilation_success_rate(living_cells)
        
        # 能量流动率
        energy_flow_rate = self._calculate_energy_flow_rate(living_cells)
        
        # 分子复杂度
        molecular_complexity = self._calculate_molecular_complexity(molecules)
        
        # 环境压力
        environmental_stress = env_controller.get_environmental_stress()
        
        return EcosystemStats(
            timestamp=world_time,
            total_cells=total_cells,
            living_cells=living_count,
            dead_cells=dead_count,
            total_molecules=total_molecules,
            average_cell_energy=avg_energy,
            average_cell_health=avg_health,
            average_cell_age=avg_age,
            population_density=population_density,
            genetic_diversity=genetic_diversity,
            compilation_success_rate=compilation_success_rate,
            energy_flow_rate=energy_flow_rate,
            molecular_complexity=molecular_complexity,
            environmental_stress=environmental_stress
        )
    
    def _calculate_genetic_diversity(self, cells: List[DigitalCell]) -> float:
        """计算遗传多样性
        
        Args:
            cells: 细胞列表
            
        Returns:
            float: 遗传多样性 (0-1)
        """
        if len(cells) < 2:
            return 0.0
        
        # 基于基因组的哈希值计算多样性
        genome_hashes = set()
        for cell in cells:
            genome_str = json.dumps(cell.nucleus.genome_template, sort_keys=True)
            genome_hashes.add(hash(genome_str))
        
        return len(genome_hashes) / len(cells)
    
    def _calculate_compilation_success_rate(self, cells: List[DigitalCell]) -> float:
        """计算编译成功率
        
        Args:
            cells: 细胞列表
            
        Returns:
            float: 编译成功率 (0-1)
        """
        total_successes = 0
        total_attempts = 0
        
        for cell in cells:
            mitochondria = cell.cytoplasm.organelles.get('mitochondria')
            if mitochondria:
                from .organelles import CompilerRunner
                if isinstance(mitochondria, CompilerRunner):
                    stats = mitochondria.get_compilation_stats()
                    total_successes += stats.get('success_count', 0)
                    total_attempts += stats.get('compilation_count', 0)
        
        return total_successes / max(1, total_attempts)
    
    def _calculate_energy_flow_rate(self, cells: List[DigitalCell]) -> float:
        """计算能量流动率
        
        Args:
            cells: 细胞列表
            
        Returns:
            float: 能量流动率
        """
        if not cells:
            return 0.0
        
        # 基于能量历史计算流动率
        total_flow = 0.0
        for cell in cells:
            energy_history = cell.memory.energy_history
            if len(energy_history) >= 2:
                recent_change = abs(energy_history[-1] - energy_history[-2])
                total_flow += recent_change
        
        return total_flow / len(cells)
    
    def _calculate_molecular_complexity(self, molecules: List[MacroMolecule]) -> float:
        """计算分子复杂度
        
        Args:
            molecules: 分子列表
            
        Returns:
            float: 分子复杂度
        """
        if not molecules:
            return 0.0
        
        # 基于分子类型多样性和结合复杂度
        type_counts = defaultdict(int)
        total_bindings = 0
        
        for molecule in molecules:
            type_counts[molecule.type] += 1
            total_bindings += len(molecule.bound_molecules)
        
        type_diversity = len(type_counts) / len(MoleculeType)
        binding_complexity = total_bindings / len(molecules)
        
        return (type_diversity + min(1.0, binding_complexity / 5.0)) / 2
    
    def get_recent_stats(self, count: int = 10) -> List[EcosystemStats]:
        """获取最近的统计信息
        
        Args:
            count: 返回的统计数量
            
        Returns:
            List[EcosystemStats]: 最近的统计信息
        """
        return self.stats_history[-count:]
    
    def get_trend_analysis(self, metric: str, window_size: int = 20) -> Dict[str, float]:
        """获取趋势分析
        
        Args:
            metric: 指标名称
            window_size: 窗口大小
            
        Returns:
            Dict[str, float]: 趋势分析结果
        """
        if len(self.stats_history) < window_size:
            return {'trend': 0.0, 'volatility': 0.0, 'current_value': 0.0}
        
        recent_stats = self.stats_history[-window_size:]
        values = [getattr(stats, metric) for stats in recent_stats]
        
        # 计算趋势（线性回归斜率）
        x = np.arange(len(values))
        trend = np.corrcoef(x, values)[0, 1] if len(values) > 1 else 0.0
        
        # 计算波动性（标准差）
        volatility = np.std(values)
        
        # 当前值
        current_value = values[-1] if values else 0.0
        
        return {
            'trend': trend,
            'volatility': volatility,
            'current_value': current_value,
            'min_value': min(values),
            'max_value': max(values),
            'average_value': np.mean(values)
        }

class VirtualWorld:
    """虚拟世界 - 完整的3D生态系统模拟
    
    虚拟世界是整个系统的顶层容器，管理所有的细胞、分子、
    环境参数和生态系统动态。它提供了一个完整的3D物理环境，
    支持复杂的生物和化学交互。
    """
    
    def __init__(self, 
                 world_size: Tuple[float, float, float] = (100.0, 100.0, 100.0),
                 initial_population: int = 50):
        """
        初始化虚拟世界
        
        Args:
            world_size: 世界大小 (x, y, z)
            initial_population: 初始种群大小
        """
        self.world_size = world_size
        self.world_time = 0.0
        self.update_count = 0
        
        # 核心组件
        self.meta_genome = MetaGenome(initial_population, world_size)
        self.physics_engine = PhysicsEngine(world_size)
        self.env_controller = EnvironmentController()
        self.ecosystem_monitor = EcosystemMonitor()
        
        # 世界状态
        self.is_running = False
        self.update_thread = None
        self.update_queue = queue.Queue()
        
        # 性能监控
        self.performance_stats = {
            'updates_per_second': 0.0,
            'average_update_time': 0.0,
            'last_update_time': 0.0
        }
        
        print(f"虚拟世界已初始化: 大小={world_size}, 初始种群={initial_population}")
    
    def start(self):
        """启动虚拟世界"""
        if self.is_running:
            return
        
        self.is_running = True
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()
        print("虚拟世界已启动")
    
    def stop(self):
        """停止虚拟世界"""
        self.is_running = False
        if self.update_thread:
            self.update_thread.join(timeout=1.0)
        print("虚拟世界已停止")
    
    def _update_loop(self):
        """更新循环"""
        last_time = time.time()
        dt = 0.1  # 100ms更新间隔
        
        while self.is_running:
            start_time = time.time()
            
            try:
                self.update(dt)
                
                # 性能统计
                update_time = time.time() - start_time
                self.performance_stats['last_update_time'] = update_time
                self.performance_stats['average_update_time'] = (
                    self.performance_stats['average_update_time'] * 0.9 + update_time * 0.1
                )
                
                # 控制更新频率
                elapsed = time.time() - last_time
                if elapsed < dt:
                    time.sleep(dt - elapsed)
                
                last_time = time.time()
                
            except Exception as e:
                print(f"虚拟世界更新错误: {e}")
                time.sleep(0.1)
    
    def update(self, dt: float):
        """更新虚拟世界
        
        Args:
            dt: 时间步长
        """
        self.world_time += dt
        self.update_count += 1
        
        # 更新环境
        self.env_controller.update(dt, self.world_time)
        
        # 进化一代（每10次更新）
        if self.update_count % 10 == 0:
            evolution_stats = self.meta_genome.evolve_generation()
            
            # 记录进化事件
            if evolution_stats.best_fitness > 0.8:
                print(f"第{evolution_stats.generation}代: 发现高适应度个体 (适应度: {evolution_stats.best_fitness:.3f})")
        
        # 获取所有分子
        all_molecules = []
        for cell in self.meta_genome.population:
            # 安全地获取细胞分子，处理可能缺少cytoplasm属性的情况
            try:
                if hasattr(cell, 'cytoplasm') and hasattr(cell.cytoplasm, 'molecules'):
                    all_molecules.extend(cell.cytoplasm.molecules)
                elif hasattr(cell, 'molecules'):
                    all_molecules.extend(cell.molecules)
                # 如果都没有，跳过这个细胞
            except Exception as e:
                print(f"DEBUG: 获取细胞分子时出错: {e}，跳过细胞")
        
        # 更新生态系统监控
        self.ecosystem_monitor.update(
            self.world_time, 
            self.meta_genome.population, 
            all_molecules, 
            self.env_controller
        )
        
        # 应用环境压力
        self._apply_environmental_effects()
        
        # 更新性能统计
        if self.update_count % 100 == 0:  # 每100次更新计算一次
            self.performance_stats['updates_per_second'] = 100.0 / (dt * 100)
    
    def _apply_environmental_effects(self):
        """应用环境效果到细胞"""
        env_params = self.env_controller.get_parameters()
        stress_level = self.env_controller.get_environmental_stress()
        
        for cell in self.meta_genome.population:
            # 温度效应
            temp_stress = abs(env_params.temperature - 310.0) / 50.0
            if temp_stress > 0.2:
                cell.health *= (1.0 - temp_stress * 0.01)
            
            # pH效应
            ph_stress = abs(env_params.ph - 7.0) / 3.0
            if ph_stress > 0.3:
                cell.health *= (1.0 - ph_stress * 0.01)
            
            # 毒素效应
            if env_params.toxin_level > 0:
                cell.health *= (1.0 - env_params.toxin_level * 0.02)
                cell.energy *= (1.0 - env_params.toxin_level * 0.01)
            
            # 辐射效应
            if env_params.radiation_level > 0:
                cell.health *= (1.0 - env_params.radiation_level * 0.015)
                # 辐射可能导致突变
                if np.random.random() < env_params.radiation_level * 0.1:
                    cell.nucleus.mutate_genome(env_params.radiation_level)
            
            # 营养效应
            if env_params.nutrient_density < 1.0:
                energy_gain_modifier = env_params.nutrient_density
                cell.energy *= (1.0 + (energy_gain_modifier - 1.0) * 0.01)
            
            # 限制健康和能量范围
            cell.health = max(0.0, min(1.0, cell.health))
            cell.energy = max(0.0, min(cell.max_energy, cell.energy))
    
    def get_world_status(self) -> Dict[str, Any]:
        """获取世界状态
        
        Returns:
            Dict[str, Any]: 世界状态信息
        """
        # 获取最新的生态系统统计
        recent_stats = self.ecosystem_monitor.get_recent_stats(1)
        ecosystem_stats = recent_stats[0] if recent_stats else None
        
        # 获取最佳细胞
        best_cells = self.meta_genome.get_best_cells(3)
        
        return {
            'world_time': self.world_time,
            'update_count': self.update_count,
            'world_size': self.world_size,
            'is_running': self.is_running,
            
            # 环境信息
            'environment': asdict(self.env_controller.get_parameters()),
            'environmental_stress': self.env_controller.get_environmental_stress(),
            'active_events': [asdict(event) for event in self.env_controller.active_events],
            
            # 种群信息
            'population': self.meta_genome.get_population_status(),
            
            # 生态系统统计
            'ecosystem_stats': asdict(ecosystem_stats) if ecosystem_stats else None,
            
            # 最佳个体
            'best_cells': [cell.get_status() for cell in best_cells],
            
            # 性能信息
            'performance': self.performance_stats.copy()
        }
    
    def get_ecosystem_trends(self) -> Dict[str, Dict[str, float]]:
        """获取生态系统趋势
        
        Returns:
            Dict[str, Dict[str, float]]: 趋势分析结果
        """
        metrics = [
            'living_cells', 'average_cell_energy', 'average_cell_health',
            'genetic_diversity', 'compilation_success_rate', 'environmental_stress'
        ]
        
        trends = {}
        for metric in metrics:
            trends[metric] = self.ecosystem_monitor.get_trend_analysis(metric)
        
        return trends
    
    def trigger_environmental_event(self, event_type: str, severity: float = 0.5):
        """手动触发环境事件
        
        Args:
            event_type: 事件类型
            severity: 严重程度 (0-1)
        """
        self.env_controller._trigger_stress_event(event_type, self.world_time)
        print(f"手动触发环境事件: {event_type} (严重程度: {severity})")
    
    def set_environment_parameter(self, param_name: str, value: float):
        """设置环境参数
        
        Args:
            param_name: 参数名称
            value: 参数值
        """
        self.env_controller.set_parameter(param_name, value)
        print(f"环境参数已设置: {param_name} = {value}")
    
    def save_world_state(self, filepath: str):
        """保存世界状态
        
        Args:
            filepath: 文件路径
        """
        world_data = {
            'world_status': self.get_world_status(),
            'ecosystem_history': [asdict(stats) for stats in self.ecosystem_monitor.stats_history],
            'environment_history': [(t, asdict(params)) for t, params in self.env_controller.param_history],
            'event_history': [asdict(event) for event in self.env_controller.event_history]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(world_data, f, indent=2, ensure_ascii=False)
        
        # 同时保存基因组库
        genome_filepath = filepath.replace('.json', '_genomes.json')
        self.meta_genome.save_genome_library(genome_filepath)
        
        print(f"世界状态已保存到: {filepath}")
    
    def load_world_state(self, filepath: str):
        """
        加载世界状态
        
        Args:
            filepath: 文件路径
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            world_data = json.load(f)
        
        # 恢复基本状态
        world_status = world_data.get('world_status', {})
        self.world_time = world_status.get('world_time', 0.0)
        self.update_count = world_status.get('update_count', 0)
        
        # 恢复环境历史
        env_history = world_data.get('environment_history', [])
        self.env_controller.param_history = [
            (t, EnvironmentParameters(**params)) for t, params in env_history
        ]
        
        # 恢复事件历史
        event_history = world_data.get('event_history', [])
        self.env_controller.event_history = [
            WorldEvent(**event_data) for event_data in event_history
        ]
        
        # 恢复生态系统历史
        ecosystem_history = world_data.get('ecosystem_history', [])
        self.ecosystem_monitor.stats_history = [
            EcosystemStats(**stats_data) for stats_data in ecosystem_history
        ]
        
        # 加载基因组库
        genome_filepath = filepath.replace('.json', '_genomes.json')
        try:
            self.meta_genome.load_genome_library(genome_filepath)
        except FileNotFoundError:
            print(f"基因组库文件未找到: {genome_filepath}")
        
        print(f"世界状态已从 {filepath} 加载")
    
    def add_cell(self, cell):
        """
        向虚拟世界添加细胞
        
        Args:
            cell: 要添加的DigitalCell实例
        """
        try:
            # 添加到种群中
            self.meta_genome.population.append(cell)
            
            # 设置细胞在世界中的位置
            if hasattr(cell, 'position'):
                # 随机分配位置
                import random
                cell.position = (
                    random.uniform(0, self.world_size[0]),
                    random.uniform(0, self.world_size[1]),
                    random.uniform(0, self.world_size[2])
                )
            
            # 记录调试信息
            print(f"DEBUG: 成功添加细胞到虚拟世界，当前种群大小: {len(self.meta_genome.population)}")
            
        except Exception as e:
            print(f"ERROR: 添加细胞到虚拟世界失败: {e}")
            import traceback
            traceback.print_exc()
    
    def update_world(self, dt: float = 0.1):
        """
        更新虚拟世界状态
        
        Args:
            dt: 时间步长，默认0.1秒
        """
        try:
            # 调用现有的update方法
            self.update(dt)
            
            # 记录调试信息
            if self.update_count % 100 == 0:  # 每100次更新记录一次
                print(f"DEBUG: 虚拟世界更新 #{self.update_count}, 时间: {self.world_time:.2f}s, 种群: {len(self.meta_genome.population)}")
            
        except Exception as e:
             print(f"ERROR: 虚拟世界更新失败: {e}")
             import traceback
             traceback.print_exc()
    
    def get_ecosystem_stats(self):
        """
        获取生态系统统计信息
        
        Returns:
            dict: 生态系统统计信息
        """
        try:
            # 获取最新的生态系统统计
            recent_stats = self.ecosystem_monitor.get_recent_stats(1)
            if recent_stats:
                stats = recent_stats[0]
                return {
                    'timestamp': stats.timestamp,
                    'total_cells': stats.total_cells,
                    'living_cells': stats.living_cells,
                    'dead_cells': stats.dead_cells,
                    'average_cell_energy': stats.average_cell_energy,
                    'average_cell_health': stats.average_cell_health,
                    'genetic_diversity': stats.genetic_diversity,
                    'compilation_success_rate': stats.compilation_success_rate,
                    'environmental_stress': stats.environmental_stress
                }
            else:
                # 返回默认统计信息
                return {
                    'timestamp': self.world_time,
                    'total_cells': len(self.meta_genome.population),
                    'living_cells': len([c for c in self.meta_genome.population if not getattr(c, 'is_dead', lambda: False)()]),
                    'dead_cells': len([c for c in self.meta_genome.population if getattr(c, 'is_dead', lambda: False)()]),
                    'average_cell_energy': 0.5,
                    'average_cell_health': 0.5,
                    'genetic_diversity': 0.5,
                    'compilation_success_rate': 0.0,
                    'environmental_stress': self.env_controller.get_environmental_stress()
                }
        except Exception as e:
            print(f"ERROR: 获取生态系统统计失败: {e}")
            return {
                'timestamp': self.world_time,
                'total_cells': 0,
                'living_cells': 0,
                'dead_cells': 0,
                'average_cell_energy': 0.0,
                'average_cell_health': 0.0,
                'genetic_diversity': 0.0,
                'compilation_success_rate': 0.0,
                'environmental_stress': 0.0
            }

def create_virtual_world(world_size: Tuple[float, float, float] = (100.0, 100.0, 100.0),
                        initial_population: int = 50) -> VirtualWorld:
    """创建虚拟世界的工厂函数
    
    Args:
        world_size: 世界大小
        initial_population: 初始种群大小
        
    Returns:
        VirtualWorld: 新创建的虚拟世界
    """
    return VirtualWorld(world_size, initial_population)