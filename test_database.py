#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库系统测试脚本

用于验证数据库系统的基本功能
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from gae.config.config_manager import ConfigManager
from gae.database.database_manager import DatabaseManager
from gae.database.data_access_layer import DataAccessLayer
from gae.database.models import ExperimentModel, IndividualModel, EvaluationModel, MetricModel

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_database_system():
    """测试数据库系统"""
    try:
        logger.info("开始数据库系统测试")
        
        # 1. 初始化配置管理器
        config_manager = ConfigManager()
        await config_manager.initialize()
        
        # 2. 创建数据库管理器
        db_manager = DatabaseManager(config_manager)
        await db_manager.initialize()
        
        # 3. 创建数据访问层
        dal = DataAccessLayer(db_manager)
        
        # 4. 测试实验CRUD操作
        logger.info("测试实验CRUD操作")
        
        # 创建实验
        experiment_data = {
            "name": "测试实验",
            "description": "这是一个测试实验",
            "config": {"population_size": 100, "generations": 50},
            "status": "pending"
        }
        
        experiment = ExperimentModel(**experiment_data)
        experiment_id = await dal.create_experiment(experiment)
        logger.info(f"创建实验成功，ID: {experiment_id}")
        
        # 读取实验
        retrieved_experiment = await dal.get_experiment(experiment_id)
        if retrieved_experiment:
            logger.info(f"读取实验成功: {retrieved_experiment.name}")
        else:
            logger.error("读取实验失败")
            return False
        
        # 更新实验
        update_data = {"status": "running", "total_generations": 10}
        success = await dal.update_experiment(experiment_id, update_data)
        if success:
            logger.info("更新实验成功")
        else:
            logger.error("更新实验失败")
            return False
        
        # 5. 测试个体操作
        logger.info("测试个体操作")
        
        # 创建个体
        individual_data = {
            "experiment_id": experiment_id,
            "generation": 1,
            "genome": {"weights": [0.1, 0.2, 0.3], "structure": "simple"},
            "fitness_scores": {"accuracy": 0.85, "speed": 0.92}
        }
        
        individual = IndividualModel(**individual_data)
        individual_id = await dal.create_individual(individual)
        logger.info(f"创建个体成功，ID: {individual_id}")
        
        # 批量创建个体
        individuals_data = []
        for i in range(5):
            individuals_data.append({
                "experiment_id": experiment_id,
                "generation": 1,
                "genome": {"weights": [0.1 * i, 0.2 * i, 0.3 * i]},
                "fitness_scores": {"accuracy": 0.8 + i * 0.01}
            })
        
        individual_ids = await dal.batch_create_individuals(individuals_data)
        logger.info(f"批量创建个体成功，数量: {len(individual_ids)}")
        
        # 6. 测试评估操作
        logger.info("测试评估操作")
        
        evaluation_data = {
            "individual_id": individual_id,
            "task_id": "classification_task",
            "result": {"accuracy": 0.85, "precision": 0.82, "recall": 0.88},
            "execution_time": 1.25,
            "memory_usage": 1024 * 1024  # 1MB
        }
        
        evaluation = EvaluationModel(**evaluation_data)
        evaluation_id = await dal.create_evaluation(evaluation)
        logger.info(f"创建评估成功，ID: {evaluation_id}")
        
        # 7. 测试指标操作
        logger.info("测试指标操作")
        
        # 创建时间序列指标
        metrics_data = []
        for i in range(10):
            metrics_data.append({
                "experiment_id": experiment_id,
                "metric_name": "fitness_avg",
                "metric_value": 0.5 + i * 0.05,
                "tags": {"generation": i + 1, "population": "main"}
            })
        
        metric_ids = await dal.batch_create_metrics(metrics_data)
        logger.info(f"批量创建指标成功，数量: {len(metric_ids)}")
        
        # 8. 测试查询操作
        logger.info("测试查询操作")
        
        # 查询实验的所有个体
        individuals = await dal.get_individuals_by_experiment(experiment_id)
        logger.info(f"查询到实验个体数量: {len(individuals)}")
        
        # 查询指定代际的个体
        generation_individuals = await dal.get_individuals_by_generation(experiment_id, 1)
        logger.info(f"查询到第1代个体数量: {len(generation_individuals)}")
        
        # 查询时间序列指标
        metrics = await dal.get_metrics_by_experiment(experiment_id, limit=5)
        logger.info(f"查询到指标数量: {len(metrics)}")
        
        # 9. 测试聚合查询
        logger.info("测试聚合查询")
        
        # 获取实验统计
        stats = await dal.get_experiment_statistics(experiment_id)
        if stats:
            logger.info(f"实验统计: 个体数={stats.get('individual_count', 0)}, 评估数={stats.get('evaluation_count', 0)}")
        
        # 10. 测试事务操作
        logger.info("测试事务操作")
        
        async with dal.transaction() as tx:
            # 在事务中创建多个相关记录
            new_individual_data = {
                "experiment_id": experiment_id,
                "generation": 2,
                "genome": {"weights": [0.5, 0.6, 0.7]},
                "fitness_scores": {"accuracy": 0.90}
            }
            
            new_individual = IndividualModel(**new_individual_data)
            new_individual_id = await dal.create_individual(new_individual)
            
            new_evaluation_data = {
                "individual_id": new_individual_id,
                "task_id": "test_task",
                "result": {"score": 0.90},
                "execution_time": 0.8
            }
            
            new_evaluation = EvaluationModel(**new_evaluation_data)
            await dal.create_evaluation(new_evaluation)
            
            logger.info("事务操作成功")
        
        # 11. 清理测试数据
        logger.info("清理测试数据")
        
        # 删除实验（级联删除相关数据）
        success = await dal.delete_experiment(experiment_id)
        if success:
            logger.info("清理测试数据成功")
        else:
            logger.warning("清理测试数据失败")
        
        # 12. 关闭数据库连接
        await db_manager.close()
        
        logger.info("数据库系统测试完成")
        return True
        
    except Exception as e:
        logger.error(f"数据库系统测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主函数"""
    success = await test_database_system()
    
    if success:
        logger.info("所有测试通过")
        return 0
    else:
        logger.error("测试失败")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)