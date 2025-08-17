#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EvoForge 系统启动脚本

简化的启动接口，用于快速启动和测试系统
"""

import sys
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from main import EvoForgeSystem

def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('evoforge_startup.log', encoding='utf-8')
        ]
    )

def create_default_config():
    """创建默认配置文件"""
    config_dir = Path("config")
    config_dir.mkdir(exist_ok=True)
    
    config_file = config_dir / "system_config.json"
    
    if not config_file.exists():
        default_config = {
            "database": {
                "host": "localhost",
                "port": 5432,
                "name": "evoforge",
                "user": "evoforge",
                "password": "password",
                "pool_size": 10,
                "timeout": 30
            },
            "logging": {
                "level": "INFO",
                "format": "detailed",
                "file_path": "logs/evoforge.log",
                "max_file_size": 10485760,
                "backup_count": 5,
                "enable_console": True,
                "enable_file": True
            },
            "security": {
                "enable_sandbox": True,
                "max_execution_time": 30,
                "max_memory_mb": 512,
                "allowed_modules": ["math", "random", "json"],
                "blocked_functions": ["exec", "eval", "__import__"]
            },
            "performance": {
                "max_threads": 8,
                "max_processes": 4,
                "cache_size_mb": 256,
                "gc_threshold": 1000
            },
            "modules": {
                "digital_cell": {
                    "enabled": True,
                    "max_molecules": 10000,
                    "simulation_step": 0.01,
                    "space_size": [100.0, 100.0, 100.0]
                },
                "gene_expression": {
                    "enabled": True,
                    "max_genes": 1000,
                    "transcription_rate": 0.1,
                    "translation_rate": 0.05
                },
                "evolution_engine": {
                    "enabled": True,
                    "population_size": 50,
                    "max_generations": 100,
                    "mutation_rate": 0.1,
                    "crossover_rate": 0.8
                },
                "multimodal_oracle": {
                    "enabled": True,
                    "cache_enabled": True,
                    "max_cache_size": 1000
                },
                "secure_executor": {
                    "enabled": True,
                    "default_security_level": "MEDIUM",
                    "enable_docker": False,
                    "enable_wasm": True
                }
            }
        }
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)
        
        print(f"创建默认配置文件: {config_file}")
    
    return str(config_file)

def create_experiment_config():
    """创建示例实验配置"""
    config_dir = Path("experiments")
    config_dir.mkdir(exist_ok=True)
    
    experiment_file = config_dir / "test_experiment.json"
    
    if not experiment_file.exists():
        experiment_config = {
            "name": "test_experiment",
            "description": "基础测试实验",
            "type": "evolution",
            "parameters": {
                "population_size": 20,
                "generations": 10,
                "mutation_rate": 0.15,
                "crossover_rate": 0.7,
                "selection_pressure": 1.5
            },
            "fitness_function": {
                "type": "multi_objective",
                "objectives": [
                    "complexity",
                    "efficiency",
                    "stability"
                ],
                "weights": [0.4, 0.4, 0.2]
            },
            "termination_criteria": {
                "max_generations": 10,
                "target_fitness": 0.95,
                "stagnation_limit": 5
            },
            "output": {
                "save_population": True,
                "save_statistics": True,
                "save_best_individuals": True,
                "output_directory": "results/test_experiment"
            }
        }
        
        with open(experiment_file, 'w', encoding='utf-8') as f:
            json.dump(experiment_config, f, indent=2, ensure_ascii=False)
        
        print(f"创建示例实验配置: {experiment_file}")
    
    return str(experiment_file)

def quick_test():
    """快速测试系统功能"""
    print("\n=== EvoForge 快速测试 ===")
    
    # 设置日志
    setup_logging()
    logger = logging.getLogger("quick_test")
    
    try:
        # 创建配置文件
        config_file = create_default_config()
        experiment_file = create_experiment_config()
        
        # 创建系统实例
        logger.info("创建系统实例")
        system = EvoForgeSystem(config_path=config_file)
        
        # 启动系统
        logger.info("启动系统")
        if not system.start():
            logger.error("系统启动失败")
            return False
        
        # 测试系统状态
        logger.info("检查系统状态")
        status = system.get_status()
        print(f"系统状态: {status['system']['is_running']}")
        print(f"模块数量: {len(status['modules'])}")
        
        # 测试分子创建
        logger.info("测试分子创建")
        molecules = system.create_test_molecules(5)
        print(f"创建分子数量: {len(molecules)}")
        
        # 测试实验运行
        logger.info("测试实验运行")
        with open(experiment_file, 'r', encoding='utf-8') as f:
            experiment_config = json.load(f)
        
        result = system.run_evolution_experiment(experiment_config)
        print(f"实验结果: {result['status']}")
        
        # 关闭系统
        logger.info("关闭系统")
        system.shutdown()
        
        print("\n✅ 快速测试完成，所有功能正常")
        return True
        
    except Exception as e:
        logger.error(f"快速测试失败: {e}")
        print(f"\n❌ 快速测试失败: {e}")
        return False

def interactive_start():
    """交互式启动"""
    print("\n=== EvoForge 交互式启动 ===")
    
    # 设置日志
    setup_logging()
    logger = logging.getLogger("interactive_start")
    
    try:
        # 创建配置文件
        config_file = create_default_config()
        
        # 创建系统实例
        logger.info("创建系统实例")
        system = EvoForgeSystem(config_path=config_file)
        
        # 启动系统
        logger.info("启动系统")
        if not system.start():
            logger.error("系统启动失败")
            return
        
        try:
            # 运行交互模式
            system.run_interactive_mode()
        except KeyboardInterrupt:
            logger.info("接收到中断信号")
        finally:
            # 关闭系统
            logger.info("关闭系统")
            system.shutdown()
        
    except Exception as e:
        logger.error(f"交互式启动失败: {e}")
        print(f"\n❌ 交互式启动失败: {e}")

def main():
    """主函数"""
    print("EvoForge 系统启动脚本")
    print("1. 快速测试")
    print("2. 交互式启动")
    print("3. 退出")
    
    while True:
        try:
            choice = input("\n请选择操作 (1-3): ").strip()
            
            if choice == "1":
                quick_test()
                break
            elif choice == "2":
                interactive_start()
                break
            elif choice == "3":
                print("退出")
                break
            else:
                print("无效选择，请输入 1-3")
        
        except KeyboardInterrupt:
            print("\n退出")
            break
        except EOFError:
            print("\n退出")
            break

if __name__ == "__main__":
    main()