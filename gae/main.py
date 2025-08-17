#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EvoForge 主系统启动器 - 核心实现文件

根据 comprehensive_implementation_plan.md 文档重新实现

功能包括：
- 系统初始化和配置
- 模块生命周期管理
- 统一的启动和关闭流程
- 系统状态监控
- 命令行接口
"""

import sys
import os
import time
import signal
import argparse
import json
import threading
import asyncio
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
import logging
from datetime import datetime
import traceback
from contextlib import asynccontextmanager

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 导入核心模块
from config.config_manager import ConfigManager, SystemConfig
from core.module_coordinator import ModuleCoordinator, ModuleInfo, ModuleType
from core.logging_system import LoggingSystem, get_logging_system
from core.error_handler import ErrorHandler, get_error_handler, with_error_handling

# 导入业务模块
from gae.digital_cell.macro_molecule import MacroMolecule, create_molecule, MoleculeType
from gae.digital_cell.digital_cell import DigitalCell
from gae.digital_cell.gene_expression import GeneExpressionSystem
from gae.engine.engine import EnhancedEvolutionEngine, EvolutionConfig
from gae.llm_oracle.fitness import MultiModalOracle
from gae.sandbox.secure_executor import SecureExecutor

class SystemState:
    """系统状态管理"""
    
    def __init__(self):
        self.is_running = False
        self.is_shutting_down = False
        self.start_time: Optional[datetime] = None
        self.modules_loaded = False
        self.config_loaded = False
        self.error_count = 0
        self.last_error: Optional[str] = None
        self._lock = threading.RLock()
    
    def set_running(self, running: bool):
        with self._lock:
            self.is_running = running
            if running and not self.start_time:
                self.start_time = datetime.now()
    
    def set_shutting_down(self, shutting_down: bool):
        with self._lock:
            self.is_shutting_down = shutting_down
    
    def increment_error_count(self, error_message: str = None):
        with self._lock:
            self.error_count += 1
            if error_message:
                self.last_error = error_message
    
    def get_uptime(self) -> float:
        with self._lock:
            if self.start_time:
                return (datetime.now() - self.start_time).total_seconds()
            return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "is_running": self.is_running,
                "is_shutting_down": self.is_shutting_down,
                "start_time": self.start_time.isoformat() if self.start_time else None,
                "uptime_seconds": self.get_uptime(),
                "modules_loaded": self.modules_loaded,
                "config_loaded": self.config_loaded,
                "error_count": self.error_count,
                "last_error": self.last_error
            }

class EvoForgeSystem:
    """EvoForge 主系统类"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "config/system_config.json"
        self.state = SystemState()
        
        # 核心组件
        self.config_manager: Optional[ConfigManager] = None
        self.module_coordinator: Optional[ModuleCoordinator] = None
        self.logging_system: Optional[LoggingSystem] = None
        self.error_handler: Optional[ErrorHandler] = None
        
        # 业务模块
        self.digital_cell: Optional[DigitalCell] = None
        self.gene_expression: Optional[GeneExpressionSystem] = None
        self.evolution_engine: Optional[EnhancedEvolutionEngine] = None
        self.multimodal_oracle: Optional[MultiModalOracle] = None
        self.secure_executor: Optional[SecureExecutor] = None
        
        # 系统配置
        self.system_config: Optional[SystemConfig] = None
        
        # 信号处理
        self._setup_signal_handlers()
        
        # 日志记录器（临时，直到日志系统初始化）
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def _setup_signal_handlers(self):
        """设置信号处理器"""
        def signal_handler(signum, frame):
            self.logger.info(f"接收到信号 {signum}，开始优雅关闭")
            self.shutdown()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Windows 特定信号
        if hasattr(signal, 'SIGBREAK'):
            signal.signal(signal.SIGBREAK, signal_handler)
    
    @with_error_handling()
    def initialize(self) -> bool:
        """初始化系统"""
        try:
            self.logger.info("开始初始化 EvoForge 系统")
            
            # 1. 初始化配置管理器
            if not self._initialize_config():
                return False
            
            # 2. 初始化日志系统
            if not self._initialize_logging():
                return False
            
            # 3. 初始化错误处理器
            if not self._initialize_error_handler():
                return False
            
            # 4. 初始化模块协调器
            if not self._initialize_module_coordinator():
                return False
            
            # 5. 初始化业务模块
            if not self._initialize_business_modules():
                return False
            
            self.state.modules_loaded = True
            self.logger.info("EvoForge 系统初始化完成")
            return True
            
        except Exception as e:
            self.logger.error(f"系统初始化失败: {e}")
            self.state.increment_error_count(str(e))
            return False
    
    def _initialize_config(self) -> bool:
        """初始化配置管理器"""
        try:
            self.logger.info("初始化配置管理器")
            self.config_manager = ConfigManager()
            
            # 加载系统配置
            config_file = Path(self.config_path)
            if config_file.exists():
                self.system_config = self.config_manager.load_config(str(config_file), SystemConfig)
            else:
                # 创建默认配置
                self.system_config = SystemConfig()
                self.config_manager.save_config()
                self.logger.info(f"创建默认配置文件: {config_file}")
            
            self.state.config_loaded = True
            self.logger.info("配置管理器初始化完成")
            return True
            
        except Exception as e:
            self.logger.error(f"配置管理器初始化失败: {e}")
            return False
    
    def _initialize_logging(self) -> bool:
        """初始化日志系统"""
        try:
            self.logger.info("初始化日志系统")
            self.logging_system = get_logging_system()
            
            # 配置日志系统
            if self.system_config and self.system_config.logging:
                # 将LoggingConfig转换为LogConfig
                from core.logging_system import LogConfig, LogLevel, LogFormat
                
                # 转换日志级别
                level_mapping = {
                    "TRACE": LogLevel.TRACE,
                    "DEBUG": LogLevel.DEBUG,
                    "INFO": LogLevel.INFO,
                    "WARNING": LogLevel.WARNING,
                    "ERROR": LogLevel.ERROR,
                    "CRITICAL": LogLevel.CRITICAL
                }
                
                log_config = LogConfig(
                     level=level_mapping.get(self.system_config.logging.level.upper(), LogLevel.INFO),
                     format_type=LogFormat.DETAILED,
                     console_output=self.system_config.logging.console_output,
                     file_output=True,
                     file_path=self.system_config.logging.file_path or "logs/evoforge.log",
                     max_file_size=self.system_config.logging.max_file_size,
                     backup_count=self.system_config.logging.backup_count
                 )
                
                self.logging_system = LoggingSystem(log_config)
            
            # 更新日志记录器
            self.logger = self.logging_system.get_logger(self.__class__.__name__)
            
            self.logger.info("日志系统初始化完成")
            return True
            
        except Exception as e:
            self.logger.error(f"日志系统初始化失败: {e}")
            return False
    
    def _initialize_error_handler(self) -> bool:
        """初始化错误处理器"""
        try:
            self.logger.info("初始化错误处理器")
            self.error_handler = get_error_handler()
            
            self.logger.info("错误处理器初始化完成")
            return True
            
        except Exception as e:
            self.logger.error(f"错误处理器初始化失败: {e}")
            return False
    
    def _initialize_module_coordinator(self) -> bool:
        """初始化模块协调器"""
        try:
            self.logger.info("初始化模块协调器")
            self.module_coordinator = ModuleCoordinator()
            
            self.logger.info("模块协调器初始化完成")
            return True
            
        except Exception as e:
            self.logger.error(f"模块协调器初始化失败: {e}")
            return False
    
    def _initialize_business_modules(self) -> bool:
        """初始化业务模块"""
        try:
            self.logger.info("初始化业务模块")
            
            # 初始化数字细胞系统
            self.logger.info("初始化数字细胞系统")
            self.digital_cell = DigitalCell()
            
            # 数字细胞系统已初始化
            self.logger.debug("数字细胞系统初始化完成")
            
            # 初始化基因表达系统
            self.logger.info("初始化基因表达系统")
            self.gene_expression = GeneExpressionSystem()
            
            # 基因表达系统已初始化
            self.logger.debug("基因表达系统初始化完成")
            
            # 初始化进化引擎
            self.logger.info("初始化进化引擎")
            evolution_config = EvolutionConfig(
                population_size=50,
                max_generations=100,
                mutation_rate=0.1,
                crossover_rate=0.8
            )
            self.evolution_engine = EnhancedEvolutionEngine(evolution_config)
            
            # 进化引擎已初始化
            self.logger.debug("进化引擎初始化完成")
            
            # 初始化多模态评估系统
            self.logger.info("初始化多模态评估系统")
            self.multimodal_oracle = MultiModalOracle()
            
            # 多模态评估系统已初始化
            self.logger.debug("多模态评估系统初始化完成")
            
            # 初始化安全执行器
            self.logger.info("初始化安全执行器")
            self.secure_executor = SecureExecutor()
            
            # 安全执行器已初始化
            self.logger.debug("安全执行器初始化完成")
            
            # 所有业务模块已初始化完成
            self.logger.info("所有业务模块初始化完成")
            
            self.logger.info("业务模块初始化完成")
            return True
            
        except Exception as e:
            self.logger.error(f"业务模块初始化失败: {e}")
            return False
    
    @with_error_handling()
    def start(self) -> bool:
        """启动系统"""
        try:
            if self.state.is_running:
                self.logger.warning("系统已经在运行中")
                return True
            
            self.logger.info("启动 EvoForge 系统")
            
            # 初始化系统
            if not self.initialize():
                self.logger.error("系统初始化失败，无法启动")
                return False
            
            # 设置运行状态
            self.state.set_running(True)
            
            self.logger.info("EvoForge 系统启动成功")
            return True
            
        except Exception as e:
            self.logger.error(f"系统启动失败: {e}")
            self.state.increment_error_count(str(e))
            return False
    
    @with_error_handling()
    def shutdown(self) -> bool:
        """关闭系统"""
        try:
            if self.state.is_shutting_down:
                self.logger.warning("系统已经在关闭过程中")
                return True
            
            self.logger.info("开始关闭 EvoForge 系统")
            self.state.set_shutting_down(True)
            
            # 停止所有模块
            if self.module_coordinator:
                self.logger.info("停止所有模块")
                self.module_coordinator.stop_all_modules()
            
            # 关闭业务模块
            self._shutdown_business_modules()
            
            # 关闭核心组件
            self._shutdown_core_components()
            
            # 设置运行状态
            self.state.set_running(False)
            self.state.set_shutting_down(False)
            
            self.logger.info("EvoForge 系统关闭完成")
            return True
            
        except Exception as e:
            self.logger.error(f"系统关闭失败: {e}")
            self.state.increment_error_count(str(e))
            return False
    
    def _shutdown_business_modules(self):
        """关闭业务模块"""
        try:
            # 关闭安全执行器
            if self.secure_executor:
                self.logger.info("关闭安全执行器")
                # 这里应该调用具体的关闭方法
                self.secure_executor = None
            
            # 关闭多模态评估系统
            if self.multimodal_oracle:
                self.logger.info("关闭多模态评估系统")
                # 这里应该调用具体的关闭方法
                self.multimodal_oracle = None
            
            # 关闭进化引擎
            if self.evolution_engine:
                self.logger.info("关闭进化引擎")
                # 这里应该调用具体的关闭方法
                self.evolution_engine = None
            
            # 关闭基因表达系统
            if self.gene_expression:
                self.logger.info("关闭基因表达系统")
                # 这里应该调用具体的关闭方法
                self.gene_expression = None
            
            # 关闭数字细胞系统
            if self.digital_cell:
                self.logger.info("关闭数字细胞系统")
                # 这里应该调用具体的关闭方法
                self.digital_cell = None
            
        except Exception as e:
            self.logger.error(f"关闭业务模块失败: {e}")
    
    def _shutdown_core_components(self):
        """关闭核心组件"""
        try:
            # 关闭错误处理器
            if self.error_handler:
                self.logger.info("关闭错误处理器")
                self.error_handler.shutdown()
                self.error_handler = None
            
            # 关闭模块协调器
            if self.module_coordinator:
                self.logger.info("关闭模块协调器")
                self.module_coordinator.shutdown()
                self.module_coordinator = None
            
            # 关闭日志系统（最后关闭）
            if self.logging_system:
                self.logger.info("关闭日志系统")
                self.logging_system.shutdown()
                self.logging_system = None
            
        except Exception as e:
            print(f"关闭核心组件失败: {e}")  # 使用print因为日志系统可能已关闭
    
    def get_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        status = {
            "system": self.state.to_dict(),
            "modules": {},
            "health": {},
            "errors": {}
        }
        
        # 获取模块状态
        if self.module_coordinator:
            status["modules"] = self.module_coordinator.get_module_status()
        
        # 获取健康状态
        if self.error_handler:
            status["health"] = self.error_handler.get_health_status()
            status["errors"] = self.error_handler.get_error_statistics()
        
        return status
    
    def run_evolution_experiment(self, experiment_config: Dict[str, Any]) -> Dict[str, Any]:
        """运行进化实验"""
        if not self.state.is_running:
            raise RuntimeError("系统未运行，无法执行实验")
        
        if not self.evolution_engine:
            raise RuntimeError("进化引擎未初始化")
        
        self.logger.info(f"开始运行进化实验: {experiment_config.get('name', 'unnamed')}")
        
        try:
            # 这里应该实现具体的实验逻辑
            # 目前只是一个占位符
            result = {
                "experiment_id": experiment_config.get("name", "experiment"),
                "status": "completed",
                "generations": 0,
                "best_fitness": 0.0,
                "population_size": self.evolution_engine.config.population_size,
                "start_time": datetime.now().isoformat(),
                "end_time": datetime.now().isoformat(),
                "duration_seconds": 0.0
            }
            
            self.logger.info(f"进化实验完成: {result['experiment_id']}")
            return result
            
        except Exception as e:
            self.logger.error(f"进化实验失败: {e}")
            raise
    
    def create_test_molecules(self, count: int = 10) -> List[MacroMolecule]:
        """创建测试分子"""
        if not self.state.is_running:
            raise RuntimeError("系统未运行，无法创建分子")
        
        molecules = []
        molecule_types = list(MoleculeType)
        
        for i in range(count):
            mol_type = molecule_types[i % len(molecule_types)]
            molecule = create_molecule(mol_type, f"test_{mol_type.value}_{i}")
            molecules.append(molecule)
        
        self.logger.info(f"创建了 {len(molecules)} 个测试分子")
        return molecules
    
    def run_interactive_mode(self):
        """运行交互模式"""
        self.logger.info("进入交互模式")
        
        print("\n=== EvoForge 交互模式 ===")
        print("可用命令:")
        print("  status - 显示系统状态")
        print("  health - 显示健康状态")
        print("  errors - 显示错误统计")
        print("  molecules <count> - 创建测试分子")
        print("  experiment <name> - 运行进化实验")
        print("  help - 显示帮助")
        print("  quit - 退出")
        print()
        
        while self.state.is_running and not self.state.is_shutting_down:
            try:
                command = input("EvoForge> ").strip().lower()
                
                if command == "quit" or command == "exit":
                    break
                elif command == "status":
                    status = self.get_status()
                    print(json.dumps(status, indent=2, ensure_ascii=False))
                elif command == "health":
                    if self.error_handler:
                        health = self.error_handler.get_health_status()
                        print(json.dumps(health, indent=2, ensure_ascii=False))
                elif command == "errors":
                    if self.error_handler:
                        errors = self.error_handler.get_error_statistics()
                        print(json.dumps(errors, indent=2, ensure_ascii=False))
                elif command.startswith("molecules"):
                    parts = command.split()
                    count = int(parts[1]) if len(parts) > 1 else 5
                    molecules = self.create_test_molecules(count)
                    print(f"创建了 {len(molecules)} 个分子")
                    for mol in molecules:
                        print(f"  - {mol.molecule_id}: {mol.molecule_type.value}")
                elif command.startswith("experiment"):
                    parts = command.split()
                    name = parts[1] if len(parts) > 1 else "test_experiment"
                    config = {"name": name}
                    result = self.run_evolution_experiment(config)
                    print(json.dumps(result, indent=2, ensure_ascii=False))
                elif command == "help":
                    print("可用命令:")
                    print("  status - 显示系统状态")
                    print("  health - 显示健康状态")
                    print("  errors - 显示错误统计")
                    print("  molecules <count> - 创建测试分子")
                    print("  experiment <name> - 运行进化实验")
                    print("  help - 显示帮助")
                    print("  quit - 退出")
                elif command:
                    print(f"未知命令: {command}，输入 'help' 查看可用命令")
                
            except KeyboardInterrupt:
                print("\n接收到中断信号")
                break
            except EOFError:
                print("\n接收到EOF")
                break
            except Exception as e:
                print(f"命令执行错误: {e}")
        
        print("退出交互模式")

def create_argument_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="EvoForge - 数字生命进化系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py --start                    # 启动系统
  python main.py --interactive              # 启动交互模式
  python main.py --config custom.json      # 使用自定义配置
  python main.py --experiment test.json    # 运行实验
        """
    )
    
    parser.add_argument(
        "--config", "-c",
        type=str,
        default="config/system_config.json",
        help="配置文件路径 (默认: config/system_config.json)"
    )
    
    parser.add_argument(
        "--start", "-s",
        action="store_true",
        help="启动系统"
    )
    
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="启动交互模式"
    )
    
    parser.add_argument(
        "--experiment", "-e",
        type=str,
        help="运行指定的实验配置文件"
    )
    
    parser.add_argument(
        "--status",
        action="store_true",
        help="显示系统状态并退出"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="启用详细日志输出"
    )
    
    parser.add_argument(
        "--debug", "-d",
        action="store_true",
        help="启用调试模式"
    )
    
    return parser

def main():
    """主函数"""
    # 解析命令行参数
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # 配置基础日志
    log_level = logging.DEBUG if args.debug else (logging.INFO if args.verbose else logging.WARNING)
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('evoforge.log', encoding='utf-8')
        ]
    )
    
    logger = logging.getLogger("main")
    logger.info("EvoForge 系统启动")
    
    try:
        # 创建系统实例
        system = EvoForgeSystem(config_path=args.config)
        
        # 根据参数执行不同操作
        if args.status:
            # 只显示状态
            if system.start():
                status = system.get_status()
                print(json.dumps(status, indent=2, ensure_ascii=False))
                system.shutdown()
            else:
                logger.error("系统启动失败")
                sys.exit(1)
        
        elif args.experiment:
            # 运行实验
            if system.start():
                try:
                    # 加载实验配置
                    with open(args.experiment, 'r', encoding='utf-8') as f:
                        experiment_config = json.load(f)
                    
                    # 运行实验
                    result = system.run_evolution_experiment(experiment_config)
                    print(json.dumps(result, indent=2, ensure_ascii=False))
                    
                except FileNotFoundError:
                    logger.error(f"实验配置文件不存在: {args.experiment}")
                    sys.exit(1)
                except Exception as e:
                    logger.error(f"实验运行失败: {e}")
                    sys.exit(1)
                finally:
                    system.shutdown()
            else:
                logger.error("系统启动失败")
                sys.exit(1)
        
        elif args.interactive or args.start:
            # 启动系统
            if system.start():
                try:
                    if args.interactive:
                        # 交互模式
                        system.run_interactive_mode()
                    else:
                        # 守护模式
                        logger.info("系统运行中，按 Ctrl+C 退出")
                        while system.state.is_running:
                            time.sleep(1)
                except KeyboardInterrupt:
                    logger.info("接收到中断信号")
                finally:
                    system.shutdown()
            else:
                logger.error("系统启动失败")
                sys.exit(1)
        
        else:
            # 显示帮助
            parser.print_help()
    
    except Exception as e:
        logger.error(f"程序执行失败: {e}")
        logger.debug(traceback.format_exc())
        sys.exit(1)
    
    logger.info("EvoForge 系统退出")

if __name__ == "__main__":
    main()