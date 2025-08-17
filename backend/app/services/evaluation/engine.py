#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EvoForge 主引擎模块

基于 MacroMolecule 的物理模拟系统，实现分子级的代码生成环境。
该引擎整合了物理模拟、细胞生物学、进化算法和代码生成等核心功能。

作者: EvoForge Team
版本: 5.0.0
"""

import logging
import time
import threading
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from pathlib import Path
import json
import numpy as np

from .core import (
    MacroMolecule, DigitalCell, VirtualWorld, MetaGenome,
    PhysicsEngine, create_digital_cell, create_virtual_world,
    EvolutionStats, EnvironmentParameters, EcosystemStats
)

# 配置日志系统
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('evoforge.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class EvoForgeConfig:
    """EvoForge 引擎配置类"""
    
    # 基础配置
    simulation_name: str = "EvoForge_Simulation"
    max_generations: int = 1000
    population_size: int = 100
    random_seed: Optional[int] = None
    
    # 物理引擎配置
    world_size: Tuple[float, float, float] = (1000.0, 1000.0, 1000.0)
    physics_timestep: float = 0.01
    collision_detection_enabled: bool = True
    spatial_grid_size: int = 50
    
    # 细胞生物学配置
    enable_cellular_biology: bool = True
    initial_cell_energy: float = 100.0
    cell_division_threshold: float = 200.0
    cell_death_threshold: float = 10.0
    max_cell_age: int = 1000
    
    # 进化算法配置
    mutation_rate: float = 0.1
    crossover_rate: float = 0.8
    selection_pressure: float = 2.0
    elitism_ratio: float = 0.1
    diversity_threshold: float = 0.3
    
    # 代码生成配置
    enable_code_generation: bool = True
    max_ast_depth: int = 10
    syntax_complexity: float = 0.5
    optimization_level: int = 2
    
    # 环境配置
    temperature: float = 298.15  # 开尔文
    ph_level: float = 7.0
    nutrient_density: float = 1.0
    toxin_level: float = 0.0
    
    # 性能配置
    enable_multithreading: bool = True
    max_threads: int = 4
    memory_limit_mb: int = 2048
    enable_gpu_acceleration: bool = False
    
    # 调试配置
    debug_mode: bool = False
    log_level: str = "INFO"
    save_snapshots: bool = True
    snapshot_interval: int = 100
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            field.name: getattr(self, field.name)
            for field in self.__dataclass_fields__.values()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EvoForgeConfig':
        """从字典创建配置对象"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class SimulationStats:
    """模拟统计信息"""
    
    generation: int = 0
    total_runtime: float = 0.0
    current_population: int = 0
    best_fitness: float = 0.0
    average_fitness: float = 0.0
    diversity_index: float = 0.0
    
    # 物理统计
    total_molecules: int = 0
    active_reactions: int = 0
    collision_count: int = 0
    
    # 细胞统计
    living_cells: int = 0
    dead_cells: int = 0
    cell_divisions: int = 0
    
    # 代码生成统计
    generated_programs: int = 0
    successful_compilations: int = 0
    optimization_improvements: int = 0
    
    # 性能统计
    fps: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0


class EvoForgeEngine:
    """EvoForge 主引擎类
    
    整合物理模拟、细胞生物学、进化算法和代码生成的核心引擎。
    提供完整的生命周期管理和实时监控功能。
    """
    
    def __init__(self, config: Optional[EvoForgeConfig] = None):
        """初始化 EvoForge 引擎
        
        Args:
            config: 引擎配置，如果为 None 则使用默认配置
        """
        self.config = config or EvoForgeConfig()
        self.stats = SimulationStats()
        
        # 核心组件
        self.physics_engine: Optional[PhysicsEngine] = None
        self.virtual_world: Optional[VirtualWorld] = None
        self.meta_genome: Optional[MetaGenome] = None
        
        # 运行状态
        self.is_running = False
        self.is_paused = False
        self.start_time = 0.0
        self.last_update_time = 0.0
        
        # 线程管理
        self.main_thread: Optional[threading.Thread] = None
        self.update_lock = threading.Lock()
        
        # 回调函数
        self.generation_callbacks: List[Callable[[int, SimulationStats], None]] = []
        self.update_callbacks: List[Callable[[SimulationStats], None]] = []
        
        # 初始化日志
        self._setup_logging()
        
        logger.info(f"EvoForge 引擎初始化完成 - 配置: {self.config.simulation_name}")
    
    def _setup_logging(self):
        """设置日志系统"""
        log_level = getattr(logging, self.config.log_level.upper(), logging.INFO)
        logger.setLevel(log_level)
        
        if self.config.debug_mode:
            logger.setLevel(logging.DEBUG)
            logger.debug("调试模式已启用")
    
    def initialize(self) -> bool:
        """初始化所有核心组件
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            logger.info("开始初始化 EvoForge 核心组件...")
            
            # 设置随机种子
            if self.config.random_seed is not None:
                np.random.seed(self.config.random_seed)
                logger.info(f"设置随机种子: {self.config.random_seed}")
            
            # 初始化物理引擎
            self._initialize_physics_engine()
            
            # 初始化虚拟世界
            self._initialize_virtual_world()
            
            # 初始化元基因组
            self._initialize_meta_genome()
            
            # 验证初始化
            if not self._validate_initialization():
                logger.error("组件初始化验证失败")
                return False
            
            logger.info("EvoForge 核心组件初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"初始化失败: {e}")
            return False
    
    def _initialize_physics_engine(self):
        """初始化物理引擎"""
        logger.info("初始化物理引擎...")
        
        self.physics_engine = PhysicsEngine(
            world_bounds=self.config.world_size,
            timestep=self.config.physics_timestep,
            grid_size=self.config.spatial_grid_size,
            enable_collision_detection=self.config.collision_detection_enabled
        )
        
        logger.info(f"物理引擎初始化完成 - 世界大小: {self.config.world_size}")
    
    def _initialize_virtual_world(self):
        """初始化虚拟世界"""
        if not self.config.enable_cellular_biology:
            logger.info("细胞生物学功能已禁用，跳过虚拟世界初始化")
            return
        
        logger.info("初始化虚拟世界...")
        
        env_params = EnvironmentParameters(
            temperature=self.config.temperature,
            ph_level=self.config.ph_level,
            nutrient_density=self.config.nutrient_density,
            toxin_level=self.config.toxin_level
        )
        
        self.virtual_world = create_virtual_world(
            world_size=self.config.world_size,
            initial_population=0,  # 由进化算法管理
            environment_params=env_params
        )
        
        logger.info(f"虚拟世界初始化完成 - 环境参数: T={self.config.temperature}K, pH={self.config.ph_level}")
    
    def _initialize_meta_genome(self):
        """初始化元基因组"""
        logger.info("初始化元基因组...")
        
        self.meta_genome = MetaGenome(
            population_size=self.config.population_size,
            mutation_rate=self.config.mutation_rate,
            crossover_rate=self.config.crossover_rate,
            selection_pressure=self.config.selection_pressure,
            elitism_ratio=self.config.elitism_ratio
        )
        
        # 初始化种群
        self.meta_genome.initialize_population()
        
        logger.info(f"元基因组初始化完成 - 种群大小: {self.config.population_size}")
    
    def _validate_initialization(self) -> bool:
        """验证初始化是否成功"""
        if self.physics_engine is None:
            logger.error("物理引擎初始化失败")
            return False
        
        if self.config.enable_cellular_biology and self.virtual_world is None:
            logger.error("虚拟世界初始化失败")
            return False
        
        if self.meta_genome is None:
            logger.error("元基因组初始化失败")
            return False
        
        return True
    
    def start(self) -> bool:
        """启动模拟
        
        Returns:
            bool: 启动是否成功
        """
        if self.is_running:
            logger.warning("模拟已在运行中")
            return False
        
        if not self.initialize():
            logger.error("初始化失败，无法启动模拟")
            return False
        
        try:
            self.is_running = True
            self.is_paused = False
            self.start_time = time.time()
            self.last_update_time = self.start_time
            
            if self.config.enable_multithreading:
                self.main_thread = threading.Thread(target=self._run_simulation_loop, daemon=True)
                self.main_thread.start()
                logger.info("多线程模式启动模拟")
            else:
                logger.info("单线程模式启动模拟")
            
            logger.info(f"EvoForge 模拟已启动 - {self.config.simulation_name}")
            return True
            
        except Exception as e:
            logger.error(f"启动模拟失败: {e}")
            self.is_running = False
            return False
    
    def stop(self):
        """停止模拟"""
        if not self.is_running:
            logger.warning("模拟未在运行")
            return
        
        logger.info("正在停止模拟...")
        
        self.is_running = False
        
        if self.main_thread and self.main_thread.is_alive():
            self.main_thread.join(timeout=5.0)
            if self.main_thread.is_alive():
                logger.warning("主线程未能正常结束")
        
        # 停止虚拟世界
        if self.virtual_world:
            self.virtual_world.stop()
        
        logger.info("EvoForge 模拟已停止")
    
    def pause(self):
        """暂停模拟"""
        if not self.is_running:
            logger.warning("模拟未在运行，无法暂停")
            return
        
        self.is_paused = True
        logger.info("模拟已暂停")
    
    def resume(self):
        """恢复模拟"""
        if not self.is_running:
            logger.warning("模拟未在运行，无法恢复")
            return
        
        self.is_paused = False
        self.last_update_time = time.time()
        logger.info("模拟已恢复")
    
    def _run_simulation_loop(self):
        """主模拟循环"""
        logger.info("进入主模拟循环")
        
        try:
            while self.is_running and self.stats.generation < self.config.max_generations:
                if self.is_paused:
                    time.sleep(0.1)
                    continue
                
                current_time = time.time()
                delta_time = current_time - self.last_update_time
                
                # 更新模拟
                self._update_simulation(delta_time)
                
                # 更新统计信息
                self._update_stats(current_time)
                
                # 触发回调
                self._trigger_callbacks()
                
                # 保存快照
                if (self.config.save_snapshots and 
                    self.stats.generation % self.config.snapshot_interval == 0):
                    self._save_snapshot()
                
                self.last_update_time = current_time
                
                # 控制帧率
                time.sleep(max(0, self.config.physics_timestep - delta_time))
                
        except Exception as e:
            logger.error(f"模拟循环异常: {e}")
        finally:
            logger.info("退出主模拟循环")
    
    def _update_simulation(self, delta_time: float):
        """更新模拟状态"""
        with self.update_lock:
            # 更新物理引擎
            if self.physics_engine:
                molecules = self._get_all_molecules()
                self.physics_engine.update(molecules, delta_time)
            
            # 更新虚拟世界
            if self.virtual_world:
                self.virtual_world.update(delta_time)
            
            # 更新元基因组（进化算法）
            if self.meta_genome:
                self.meta_genome.evolve_generation()
                self.stats.generation += 1
    
    def _get_all_molecules(self) -> List[MacroMolecule]:
        """获取所有分子"""
        molecules = []
        
        if self.meta_genome:
            for cell in self.meta_genome.population:
                if isinstance(cell, DigitalCell):
                    molecules.extend(cell.get_all_molecules())
        
        return molecules
    
    def _update_stats(self, current_time: float):
        """更新统计信息"""
        self.stats.total_runtime = current_time - self.start_time
        
        if self.meta_genome:
            evolution_stats = self.meta_genome.get_evolution_stats()
            self.stats.current_population = len(self.meta_genome.population)
            self.stats.best_fitness = evolution_stats.best_fitness
            self.stats.average_fitness = evolution_stats.average_fitness
            self.stats.diversity_index = evolution_stats.diversity_index
            self.stats.living_cells = len([c for c in self.meta_genome.population if c.is_alive()])
        
        if self.physics_engine:
            physics_stats = self.physics_engine.get_stats()
            self.stats.total_molecules = physics_stats.get('total_molecules', 0)
            self.stats.active_reactions = physics_stats.get('active_reactions', 0)
            self.stats.collision_count = physics_stats.get('collision_count', 0)
        
        # 计算 FPS
        if hasattr(self, '_last_fps_time'):
            fps_delta = current_time - self._last_fps_time
            if fps_delta > 0:
                self.stats.fps = 1.0 / fps_delta
        self._last_fps_time = current_time
    
    def _trigger_callbacks(self):
        """触发回调函数"""
        try:
            # 触发更新回调
            for callback in self.update_callbacks:
                callback(self.stats)
            
            # 触发代际回调
            if hasattr(self, '_last_generation') and self._last_generation != self.stats.generation:
                for callback in self.generation_callbacks:
                    callback(self.stats.generation, self.stats)
                self._last_generation = self.stats.generation
        except Exception as e:
            logger.error(f"回调函数执行失败: {e}")
    
    def _save_snapshot(self):
        """保存模拟快照"""
        try:
            snapshot_dir = Path(f"snapshots/{self.config.simulation_name}")
            snapshot_dir.mkdir(parents=True, exist_ok=True)
            
            snapshot_file = snapshot_dir / f"generation_{self.stats.generation:06d}.json"
            
            snapshot_data = {
                'generation': self.stats.generation,
                'timestamp': time.time(),
                'stats': self.stats.__dict__,
                'config': self.config.to_dict()
            }
            
            if self.meta_genome:
                snapshot_data['population'] = self.meta_genome.get_population_state()
            
            with open(snapshot_file, 'w', encoding='utf-8') as f:
                json.dump(snapshot_data, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"快照已保存: {snapshot_file}")
            
        except Exception as e:
            logger.error(f"保存快照失败: {e}")
    
    def add_generation_callback(self, callback: Callable[[int, SimulationStats], None]):
        """添加代际回调函数"""
        self.generation_callbacks.append(callback)
    
    def add_update_callback(self, callback: Callable[[SimulationStats], None]):
        """添加更新回调函数"""
        self.update_callbacks.append(callback)
    
    def get_stats(self) -> SimulationStats:
        """获取当前统计信息"""
        return self.stats
    
    def get_best_individual(self) -> Optional[DigitalCell]:
        """获取最佳个体"""
        if self.meta_genome:
            return self.meta_genome.get_best_cell()
        return None
    
    def save_config(self, filepath: str):
        """保存配置到文件"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.config.to_dict(), f, indent=2, ensure_ascii=False)
            logger.info(f"配置已保存到: {filepath}")
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
    
    def load_config(self, filepath: str) -> bool:
        """从文件加载配置"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            self.config = EvoForgeConfig.from_dict(config_data)
            logger.info(f"配置已从文件加载: {filepath}")
            return True
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            return False


def create_evoforge_engine(config: Optional[EvoForgeConfig] = None) -> EvoForgeEngine:
    """创建 EvoForge 引擎实例
    
    Args:
        config: 引擎配置
    
    Returns:
        EvoForgeEngine: 引擎实例
    """
    return EvoForgeEngine(config)


# 导出主要组件
__all__ = [
    'EvoForgeEngine',
    'EvoForgeConfig', 
    'SimulationStats',
    'create_evoforge_engine'
]