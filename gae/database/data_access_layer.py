# -*- coding: utf-8 -*-
"""
数据访问层 - EvoForge数据库访问接口

提供统一的数据库操作接口：
- CRUD操作（创建、读取、更新、删除）
- 查询构建器
- 事务管理
- 批量操作
- 时间序列数据操作

作者: EvoForge Team
创建时间: 2024
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List, Union, Tuple
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from dataclasses import asdict

from .database_manager import DatabaseManager, get_database_manager
from .models import (
    BaseModel, ExperimentModel, IndividualModel, EvaluationModel, MetricModel,
    ExperimentStatus, EvaluationStatus, ModelFactory
)
from ..core.logging_system import get_logger
from ..core.error_handler import EvoForgeError

logger = get_logger(__name__)

class DataAccessError(EvoForgeError):
    """数据访问错误"""
    pass

class QueryBuilder:
    """SQL查询构建器"""
    
    def __init__(self, table_name: str):
        self.table_name = table_name
        self._select_fields = ["*"]
        self._where_conditions = []
        self._order_by = []
        self._limit_value = None
        self._offset_value = None
        self._join_clauses = []
        self._group_by = []
        self._having_conditions = []
        self._params = []
    
    def select(self, *fields: str) -> 'QueryBuilder':
        """选择字段"""
        if fields:
            self._select_fields = list(fields)
        return self
    
    def where(self, condition: str, *params) -> 'QueryBuilder':
        """添加WHERE条件"""
        self._where_conditions.append(condition)
        self._params.extend(params)
        return self
    
    def where_eq(self, field: str, value: Any) -> 'QueryBuilder':
        """添加等于条件"""
        return self.where(f"{field} = ${len(self._params) + 1}", value)
    
    def where_in(self, field: str, values: List[Any]) -> 'QueryBuilder':
        """添加IN条件"""
        if not values:
            return self
        
        placeholders = []
        for value in values:
            self._params.append(value)
            placeholders.append(f"${len(self._params)}")
        
        condition = f"{field} IN ({', '.join(placeholders)})"
        self._where_conditions.append(condition)
        return self
    
    def where_between(self, field: str, start: Any, end: Any) -> 'QueryBuilder':
        """添加BETWEEN条件"""
        return self.where(f"{field} BETWEEN ${len(self._params) + 1} AND ${len(self._params) + 2}", start, end)
    
    def where_like(self, field: str, pattern: str) -> 'QueryBuilder':
        """添加LIKE条件"""
        return self.where(f"{field} LIKE ${len(self._params) + 1}", pattern)
    
    def order_by(self, field: str, direction: str = "ASC") -> 'QueryBuilder':
        """添加排序"""
        self._order_by.append(f"{field} {direction.upper()}")
        return self
    
    def limit(self, count: int) -> 'QueryBuilder':
        """设置限制数量"""
        self._limit_value = count
        return self
    
    def offset(self, count: int) -> 'QueryBuilder':
        """设置偏移量"""
        self._offset_value = count
        return self
    
    def join(self, table: str, condition: str) -> 'QueryBuilder':
        """添加JOIN"""
        self._join_clauses.append(f"JOIN {table} ON {condition}")
        return self
    
    def left_join(self, table: str, condition: str) -> 'QueryBuilder':
        """添加LEFT JOIN"""
        self._join_clauses.append(f"LEFT JOIN {table} ON {condition}")
        return self
    
    def group_by(self, *fields: str) -> 'QueryBuilder':
        """添加GROUP BY"""
        self._group_by.extend(fields)
        return self
    
    def having(self, condition: str, *params) -> 'QueryBuilder':
        """添加HAVING条件"""
        self._having_conditions.append(condition)
        self._params.extend(params)
        return self
    
    def build_select(self) -> Tuple[str, List[Any]]:
        """构建SELECT查询"""
        query_parts = []
        
        # SELECT
        query_parts.append(f"SELECT {', '.join(self._select_fields)}")
        
        # FROM
        query_parts.append(f"FROM {self.table_name}")
        
        # JOIN
        if self._join_clauses:
            query_parts.extend(self._join_clauses)
        
        # WHERE
        if self._where_conditions:
            query_parts.append(f"WHERE {' AND '.join(self._where_conditions)}")
        
        # GROUP BY
        if self._group_by:
            query_parts.append(f"GROUP BY {', '.join(self._group_by)}")
        
        # HAVING
        if self._having_conditions:
            query_parts.append(f"HAVING {' AND '.join(self._having_conditions)}")
        
        # ORDER BY
        if self._order_by:
            query_parts.append(f"ORDER BY {', '.join(self._order_by)}")
        
        # LIMIT
        if self._limit_value is not None:
            query_parts.append(f"LIMIT {self._limit_value}")
        
        # OFFSET
        if self._offset_value is not None:
            query_parts.append(f"OFFSET {self._offset_value}")
        
        query = " ".join(query_parts)
        return query, self._params
    
    def build_count(self) -> Tuple[str, List[Any]]:
        """构建COUNT查询"""
        query_parts = []
        
        # SELECT COUNT
        query_parts.append("SELECT COUNT(*)")
        
        # FROM
        query_parts.append(f"FROM {self.table_name}")
        
        # JOIN
        if self._join_clauses:
            query_parts.extend(self._join_clauses)
        
        # WHERE
        if self._where_conditions:
            query_parts.append(f"WHERE {' AND '.join(self._where_conditions)}")
        
        query = " ".join(query_parts)
        return query, self._params

class DataAccessLayer:
    """数据访问层"""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db_manager = db_manager or get_database_manager()
        
        # 表名映射
        self.table_names = {
            'experiment': 'experiments',
            'individual': 'individuals',
            'evaluation': 'evaluations',
            'metric': 'metrics'
        }
        
        logger.info("数据访问层初始化完成")
    
    def query(self, table_name: str) -> QueryBuilder:
        """创建查询构建器"""
        return QueryBuilder(table_name)
    
    # 实验相关操作
    async def create_experiment(self, experiment: ExperimentModel) -> int:
        """创建实验"""
        try:
            experiment.validate()
            experiment.created_at = datetime.now()
            experiment.updated_at = experiment.created_at
            
            query = """
                INSERT INTO experiments (name, description, config, status, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
            """
            
            result = await self.db_manager.execute_query(
                query,
                experiment.name,
                experiment.description,
                experiment.config,
                experiment.status.value,
                experiment.created_at,
                experiment.updated_at
            )
            
            experiment_id = result[0]['id']
            experiment.id = experiment_id
            
            logger.info(f"实验创建成功，ID: {experiment_id}")
            return experiment_id
            
        except Exception as e:
            logger.error(f"创建实验失败: {e}")
            raise DataAccessError(f"创建实验失败: {e}")
    
    async def get_experiment(self, experiment_id: int) -> Optional[ExperimentModel]:
        """获取实验"""
        try:
            query = "SELECT * FROM experiments WHERE id = $1"
            result = await self.db_manager.execute_query(query, experiment_id)
            
            if not result:
                return None
            
            return ExperimentModel.from_dict(result[0])
            
        except Exception as e:
            logger.error(f"获取实验失败: {e}")
            raise DataAccessError(f"获取实验失败: {e}")
    
    async def update_experiment(self, experiment: ExperimentModel) -> bool:
        """更新实验"""
        try:
            experiment.validate()
            experiment.updated_at = datetime.now()
            
            query = """
                UPDATE experiments 
                SET name = $2, description = $3, config = $4, status = $5, 
                    updated_at = $6, completed_at = $7, total_generations = $8, 
                    total_individuals = $9, best_fitness = $10, metadata = $11
                WHERE id = $1
            """
            
            await self.db_manager.execute_command(
                query,
                experiment.id,
                experiment.name,
                experiment.description,
                experiment.config,
                experiment.status.value,
                experiment.updated_at,
                experiment.completed_at,
                experiment.total_generations,
                experiment.total_individuals,
                experiment.best_fitness,
                experiment.metadata
            )
            
            logger.info(f"实验更新成功，ID: {experiment.id}")
            return True
            
        except Exception as e:
            logger.error(f"更新实验失败: {e}")
            raise DataAccessError(f"更新实验失败: {e}")
    
    async def list_experiments(self, status: Optional[ExperimentStatus] = None, 
                             limit: int = 100, offset: int = 0) -> List[ExperimentModel]:
        """列出实验"""
        try:
            builder = self.query('experiments')
            
            if status:
                builder.where_eq('status', status.value)
            
            builder.order_by('created_at', 'DESC').limit(limit).offset(offset)
            
            query, params = builder.build_select()
            result = await self.db_manager.execute_query(query, *params)
            
            return [ExperimentModel.from_dict(row) for row in result]
            
        except Exception as e:
            logger.error(f"列出实验失败: {e}")
            raise DataAccessError(f"列出实验失败: {e}")
    
    # 个体相关操作
    async def create_individual(self, individual: IndividualModel) -> int:
        """创建个体"""
        try:
            individual.validate()
            individual.created_at = datetime.now()
            
            query = """
                INSERT INTO individuals (experiment_id, generation, genome, fitness_scores, metadata, created_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
            """
            
            result = await self.db_manager.execute_query(
                query,
                individual.experiment_id,
                individual.generation,
                individual.genome,
                individual.fitness_scores,
                individual.metadata,
                individual.created_at
            )
            
            individual_id = result[0]['id']
            individual.id = individual_id
            
            logger.debug(f"个体创建成功，ID: {individual_id}")
            return individual_id
            
        except Exception as e:
            logger.error(f"创建个体失败: {e}")
            raise DataAccessError(f"创建个体失败: {e}")
    
    async def batch_create_individuals(self, individuals: List[IndividualModel]) -> List[int]:
        """批量创建个体"""
        try:
            if not individuals:
                return []
            
            # 验证所有个体
            for individual in individuals:
                individual.validate()
                individual.created_at = datetime.now()
            
            # 构建批量插入查询
            values_parts = []
            params = []
            
            for i, individual in enumerate(individuals):
                base_idx = i * 6
                values_parts.append(f"(${base_idx + 1}, ${base_idx + 2}, ${base_idx + 3}, ${base_idx + 4}, ${base_idx + 5}, ${base_idx + 6})")
                params.extend([
                    individual.experiment_id,
                    individual.generation,
                    individual.genome,
                    individual.fitness_scores,
                    individual.metadata,
                    individual.created_at
                ])
            
            query = f"""
                INSERT INTO individuals (experiment_id, generation, genome, fitness_scores, metadata, created_at)
                VALUES {', '.join(values_parts)}
                RETURNING id
            """
            
            result = await self.db_manager.execute_query(query, *params)
            individual_ids = [row['id'] for row in result]
            
            # 更新个体ID
            for individual, individual_id in zip(individuals, individual_ids):
                individual.id = individual_id
            
            logger.info(f"批量创建个体成功，数量: {len(individual_ids)}")
            return individual_ids
            
        except Exception as e:
            logger.error(f"批量创建个体失败: {e}")
            raise DataAccessError(f"批量创建个体失败: {e}")
    
    async def get_individuals_by_generation(self, experiment_id: int, generation: int) -> List[IndividualModel]:
        """获取指定代的所有个体"""
        try:
            builder = self.query('individuals')
            builder.where_eq('experiment_id', experiment_id)
            builder.where_eq('generation', generation)
            builder.order_by('id')
            
            query, params = builder.build_select()
            result = await self.db_manager.execute_query(query, *params)
            
            return [IndividualModel.from_dict(row) for row in result]
            
        except Exception as e:
            logger.error(f"获取代个体失败: {e}")
            raise DataAccessError(f"获取代个体失败: {e}")
    
    async def get_best_individuals(self, experiment_id: int, limit: int = 10) -> List[IndividualModel]:
        """获取最佳个体"""
        try:
            # 这里简化处理，实际应该根据具体的适应度计算方式来排序
            query = """
                SELECT *, 
                       (SELECT AVG(value::float) FROM jsonb_each_text(fitness_scores)) as avg_fitness
                FROM individuals 
                WHERE experiment_id = $1 
                ORDER BY avg_fitness DESC NULLS LAST
                LIMIT $2
            """
            
            result = await self.db_manager.execute_query(query, experiment_id, limit)
            return [IndividualModel.from_dict(row) for row in result]
            
        except Exception as e:
            logger.error(f"获取最佳个体失败: {e}")
            raise DataAccessError(f"获取最佳个体失败: {e}")
    
    # 评估相关操作
    async def create_evaluation(self, evaluation: EvaluationModel) -> int:
        """创建评估"""
        try:
            evaluation.validate()
            evaluation.created_at = datetime.now()
            
            query = """
                INSERT INTO evaluations (individual_id, task_id, result, execution_time, 
                                       memory_usage, error_message, created_at, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id
            """
            
            result = await self.db_manager.execute_query(
                query,
                evaluation.individual_id,
                evaluation.task_id,
                evaluation.result,
                evaluation.execution_time,
                evaluation.memory_usage,
                evaluation.error_message,
                evaluation.created_at,
                evaluation.metadata
            )
            
            evaluation_id = result[0]['id']
            evaluation.id = evaluation_id
            
            logger.debug(f"评估创建成功，ID: {evaluation_id}")
            return evaluation_id
            
        except Exception as e:
            logger.error(f"创建评估失败: {e}")
            raise DataAccessError(f"创建评估失败: {e}")
    
    async def get_evaluations_by_individual(self, individual_id: int) -> List[EvaluationModel]:
        """获取个体的所有评估"""
        try:
            builder = self.query('evaluations')
            builder.where_eq('individual_id', individual_id)
            builder.order_by('created_at', 'DESC')
            
            query, params = builder.build_select()
            result = await self.db_manager.execute_query(query, *params)
            
            return [EvaluationModel.from_dict(row) for row in result]
            
        except Exception as e:
            logger.error(f"获取个体评估失败: {e}")
            raise DataAccessError(f"获取个体评估失败: {e}")
    
    # 指标相关操作（时间序列）
    async def record_metric(self, metric: MetricModel) -> bool:
        """记录指标"""
        try:
            metric.validate()
            
            query = """
                INSERT INTO metrics (time, experiment_id, metric_name, metric_value, tags, metadata)
                VALUES ($1, $2, $3, $4, $5, $6)
            """
            
            await self.db_manager.execute_command(
                query,
                metric.time,
                metric.experiment_id,
                metric.metric_name,
                metric.metric_value,
                metric.tags,
                metric.metadata
            )
            
            logger.debug(f"指标记录成功: {metric.metric_name} = {metric.metric_value}")
            return True
            
        except Exception as e:
            logger.error(f"记录指标失败: {e}")
            raise DataAccessError(f"记录指标失败: {e}")
    
    async def batch_record_metrics(self, metrics: List[MetricModel]) -> bool:
        """批量记录指标"""
        try:
            if not metrics:
                return True
            
            # 验证所有指标
            for metric in metrics:
                metric.validate()
            
            # 构建批量插入查询
            values_parts = []
            params = []
            
            for i, metric in enumerate(metrics):
                base_idx = i * 6
                values_parts.append(f"(${base_idx + 1}, ${base_idx + 2}, ${base_idx + 3}, ${base_idx + 4}, ${base_idx + 5}, ${base_idx + 6})")
                params.extend([
                    metric.time,
                    metric.experiment_id,
                    metric.metric_name,
                    metric.metric_value,
                    metric.tags,
                    metric.metadata
                ])
            
            query = f"""
                INSERT INTO metrics (time, experiment_id, metric_name, metric_value, tags, metadata)
                VALUES {', '.join(values_parts)}
            """
            
            await self.db_manager.execute_command(query, *params)
            
            logger.info(f"批量记录指标成功，数量: {len(metrics)}")
            return True
            
        except Exception as e:
            logger.error(f"批量记录指标失败: {e}")
            raise DataAccessError(f"批量记录指标失败: {e}")
    
    async def get_metrics(self, experiment_id: Optional[int] = None, 
                         metric_name: Optional[str] = None,
                         start_time: Optional[datetime] = None,
                         end_time: Optional[datetime] = None,
                         limit: int = 1000) -> List[MetricModel]:
        """获取指标数据"""
        try:
            builder = self.query('metrics')
            
            if experiment_id:
                builder.where_eq('experiment_id', experiment_id)
            
            if metric_name:
                builder.where_eq('metric_name', metric_name)
            
            if start_time:
                builder.where('time >= $' + str(len(builder._params) + 1), start_time)
            
            if end_time:
                builder.where('time <= $' + str(len(builder._params) + 1), end_time)
            
            builder.order_by('time', 'DESC').limit(limit)
            
            query, params = builder.build_select()
            result = await self.db_manager.execute_query(query, *params)
            
            return [MetricModel.from_dict(row) for row in result]
            
        except Exception as e:
            logger.error(f"获取指标数据失败: {e}")
            raise DataAccessError(f"获取指标数据失败: {e}")
    
    async def get_metric_aggregation(self, experiment_id: int, metric_name: str,
                                   aggregation: str = 'avg',
                                   time_bucket: str = '1h',
                                   start_time: Optional[datetime] = None,
                                   end_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """获取指标聚合数据（需要TimescaleDB）"""
        try:
            if not self.db_manager.is_timescaledb_enabled():
                logger.warning("TimescaleDB未启用，使用简单聚合")
                return await self._simple_metric_aggregation(experiment_id, metric_name, aggregation)
            
            # 使用TimescaleDB的time_bucket函数
            query = f"""
                SELECT time_bucket('{time_bucket}', time) as bucket,
                       {aggregation}(metric_value) as value,
                       count(*) as count
                FROM metrics 
                WHERE experiment_id = $1 AND metric_name = $2
            """
            
            params = [experiment_id, metric_name]
            
            if start_time:
                query += f" AND time >= ${len(params) + 1}"
                params.append(start_time)
            
            if end_time:
                query += f" AND time <= ${len(params) + 1}"
                params.append(end_time)
            
            query += " GROUP BY bucket ORDER BY bucket"
            
            result = await self.db_manager.execute_query(query, *params)
            return result
            
        except Exception as e:
            logger.error(f"获取指标聚合数据失败: {e}")
            raise DataAccessError(f"获取指标聚合数据失败: {e}")
    
    async def _simple_metric_aggregation(self, experiment_id: int, metric_name: str, 
                                       aggregation: str) -> List[Dict[str, Any]]:
        """简单指标聚合（不使用TimescaleDB）"""
        query = f"""
            SELECT {aggregation}(metric_value) as value, count(*) as count
            FROM metrics 
            WHERE experiment_id = $1 AND metric_name = $2
        """
        
        result = await self.db_manager.execute_query(query, experiment_id, metric_name)
        return result
    
    # 统计和分析
    async def get_experiment_statistics(self, experiment_id: int) -> Dict[str, Any]:
        """获取实验统计信息"""
        try:
            stats = {}
            
            # 基础统计
            query = """
                SELECT 
                    COUNT(*) as total_individuals,
                    MAX(generation) as max_generation,
                    COUNT(DISTINCT generation) as generation_count
                FROM individuals 
                WHERE experiment_id = $1
            """
            result = await self.db_manager.execute_query(query, experiment_id)
            if result:
                stats.update(result[0])
            
            # 评估统计
            query = """
                SELECT 
                    COUNT(*) as total_evaluations,
                    AVG(execution_time) as avg_execution_time,
                    SUM(CASE WHEN error_message IS NOT NULL THEN 1 ELSE 0 END) as failed_evaluations
                FROM evaluations e
                JOIN individuals i ON e.individual_id = i.id
                WHERE i.experiment_id = $1
            """
            result = await self.db_manager.execute_query(query, experiment_id)
            if result:
                stats.update(result[0])
            
            # 适应度统计（简化处理）
            query = """
                SELECT 
                    AVG((SELECT AVG(value::float) FROM jsonb_each_text(fitness_scores))) as avg_fitness,
                    MAX((SELECT AVG(value::float) FROM jsonb_each_text(fitness_scores))) as max_fitness,
                    MIN((SELECT AVG(value::float) FROM jsonb_each_text(fitness_scores))) as min_fitness
                FROM individuals 
                WHERE experiment_id = $1 AND fitness_scores IS NOT NULL
            """
            result = await self.db_manager.execute_query(query, experiment_id)
            if result:
                stats.update(result[0])
            
            return stats
            
        except Exception as e:
            logger.error(f"获取实验统计信息失败: {e}")
            raise DataAccessError(f"获取实验统计信息失败: {e}")
    
    # 事务管理
    @asynccontextmanager
    async def transaction(self):
        """事务上下文管理器"""
        async with self.db_manager.get_async_connection() as conn:
            async with conn.transaction():
                # 创建临时的数据访问层实例，使用当前连接
                temp_dal = DataAccessLayer()
                temp_dal._connection = conn
                yield temp_dal
    
    # 清理和维护
    async def cleanup_old_data(self, days: int = 30) -> Dict[str, int]:
        """清理旧数据"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            cleanup_stats = {}
            
            # 清理旧的指标数据
            query = "DELETE FROM metrics WHERE time < $1"
            result = await self.db_manager.execute_command(query, cutoff_date)
            cleanup_stats['metrics'] = int(result.split()[-1]) if result else 0
            
            # 清理已完成实验的旧评估数据
            query = """
                DELETE FROM evaluations 
                WHERE created_at < $1 
                AND individual_id IN (
                    SELECT i.id FROM individuals i 
                    JOIN experiments e ON i.experiment_id = e.id 
                    WHERE e.status IN ('completed', 'failed', 'cancelled')
                )
            """
            result = await self.db_manager.execute_command(query, cutoff_date)
            cleanup_stats['evaluations'] = int(result.split()[-1]) if result else 0
            
            logger.info(f"数据清理完成: {cleanup_stats}")
            return cleanup_stats
            
        except Exception as e:
            logger.error(f"数据清理失败: {e}")
            raise DataAccessError(f"数据清理失败: {e}")

# 全局数据访问层实例
_data_access_layer: Optional[DataAccessLayer] = None

def get_data_access_layer() -> DataAccessLayer:
    """获取全局数据访问层实例"""
    global _data_access_layer
    if _data_access_layer is None:
        _data_access_layer = DataAccessLayer()
    return _data_access_layer