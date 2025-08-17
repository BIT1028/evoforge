# -*- coding: utf-8 -*-
"""
数据库管理器 - EvoForge数据库系统核心

实现PostgreSQL + TimescaleDB的完整数据库管理功能：
- 连接池管理
- 事务处理
- TimescaleDB时间序列扩展
- 数据库初始化和迁移
- 健康检查和监控

作者: EvoForge Team
创建时间: 2024
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List, Union
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

try:
    import asyncpg
    import psycopg2
    from psycopg2.pool import ThreadedConnectionPool
except ImportError as e:
    logging.warning(f"数据库依赖包未安装: {e}")
    asyncpg = None
    psycopg2 = None
    ThreadedConnectionPool = None

from ..config.config_manager import ConfigManager
from ..core.logging_system import get_logger
from ..core.error_handler import EvoForgeError

logger = get_logger(__name__)

@dataclass
class ConnectionStats:
    """连接统计信息"""
    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    failed_connections: int = 0
    total_queries: int = 0
    failed_queries: int = 0
    avg_query_time: float = 0.0
    last_health_check: Optional[datetime] = None
    health_status: str = "unknown"

class DatabaseError(EvoForgeError):
    """数据库相关错误"""
    pass

class DatabaseManager:
    """
    数据库管理器
    
    负责管理PostgreSQL + TimescaleDB的所有数据库操作：
    - 连接池管理
    - 异步和同步连接
    - 事务处理
    - TimescaleDB扩展
    - 健康检查
    """
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        self.config_manager = config_manager or ConfigManager()
        self.db_config = self.config_manager.get_database_config()
        
        # 连接池
        self._async_pool: Optional[asyncpg.Pool] = None
        self._sync_pool: Optional[ThreadedConnectionPool] = None
        
        # 统计信息
        self.stats = ConnectionStats()
        
        # 状态标志
        self._initialized = False
        self._timescaledb_enabled = False
        
        logger.info("数据库管理器初始化完成")
    
    async def initialize(self) -> bool:
        """
        初始化数据库系统
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            logger.info("开始初始化数据库系统")
            
            # 检查数据库依赖
            if not self._check_dependencies():
                return False
            
            # 创建异步连接池
            await self._create_async_pool()
            
            # 创建同步连接池
            self._create_sync_pool()
            
            # 检查数据库连接
            if not await self._test_connection():
                logger.error("数据库连接测试失败")
                return False
            
            # 初始化TimescaleDB
            await self._initialize_timescaledb()
            
            # 创建基础表结构
            await self._create_base_tables()
            
            self._initialized = True
            logger.info("数据库系统初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            await self.cleanup()
            return False
    
    def _check_dependencies(self) -> bool:
        """检查数据库依赖包"""
        if asyncpg is None or psycopg2 is None:
            logger.error("数据库依赖包未安装，请运行: pip install asyncpg psycopg2-binary")
            return False
        return True
    
    async def _create_async_pool(self):
        """创建异步连接池"""
        try:
            connection_string = self.db_config.get_connection_string()
            self._async_pool = await asyncpg.create_pool(
                connection_string,
                min_size=2,
                max_size=self.db_config.pool_size,
                command_timeout=self.db_config.pool_timeout
            )
            logger.info(f"异步连接池创建成功，最大连接数: {self.db_config.pool_size}")
            
        except Exception as e:
            logger.error(f"创建异步连接池失败: {e}")
            raise DatabaseError(f"异步连接池创建失败: {e}")
    
    def _create_sync_pool(self):
        """创建同步连接池"""
        try:
            connection_string = self.db_config.get_connection_string()
            self._sync_pool = ThreadedConnectionPool(
                minconn=2,
                maxconn=self.db_config.pool_size,
                dsn=connection_string
            )
            logger.info("同步连接池创建成功")
            
        except Exception as e:
            logger.error(f"创建同步连接池失败: {e}")
            raise DatabaseError(f"同步连接池创建失败: {e}")
    
    async def _test_connection(self) -> bool:
        """测试数据库连接"""
        try:
            async with self.get_async_connection() as conn:
                result = await conn.fetchval("SELECT version()")
                logger.info(f"数据库连接成功: {result[:50]}...")
                return True
                
        except Exception as e:
            logger.error(f"数据库连接测试失败: {e}")
            return False
    
    async def _initialize_timescaledb(self):
        """初始化TimescaleDB扩展"""
        try:
            async with self.get_async_connection() as conn:
                # 检查TimescaleDB扩展是否已安装
                result = await conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'timescaledb')"
                )
                
                if not result:
                    # 尝试创建TimescaleDB扩展
                    try:
                        await conn.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")
                        logger.info("TimescaleDB扩展创建成功")
                        self._timescaledb_enabled = True
                    except Exception as e:
                        logger.warning(f"TimescaleDB扩展创建失败，将使用标准PostgreSQL: {e}")
                        self._timescaledb_enabled = False
                else:
                    logger.info("TimescaleDB扩展已存在")
                    self._timescaledb_enabled = True
                    
        except Exception as e:
            logger.warning(f"TimescaleDB初始化失败: {e}")
            self._timescaledb_enabled = False
    
    async def _create_base_tables(self):
        """创建基础表结构"""
        try:
            async with self.get_async_connection() as conn:
                # 创建实验表
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS experiments (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        description TEXT,
                        config JSONB,
                        status VARCHAR(50) DEFAULT 'created',
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        completed_at TIMESTAMP WITH TIME ZONE
                    )
                """)
                
                # 创建个体表
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS individuals (
                        id SERIAL PRIMARY KEY,
                        experiment_id INTEGER REFERENCES experiments(id),
                        generation INTEGER NOT NULL,
                        genome JSONB NOT NULL,
                        fitness_scores JSONB,
                        metadata JSONB,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """)
                
                # 创建评估表
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS evaluations (
                        id SERIAL PRIMARY KEY,
                        individual_id INTEGER REFERENCES individuals(id),
                        task_id VARCHAR(255),
                        result JSONB,
                        execution_time FLOAT,
                        memory_usage BIGINT,
                        error_message TEXT,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """)
                
                # 创建指标表（时间序列）
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS metrics (
                        time TIMESTAMP WITH TIME ZONE NOT NULL,
                        experiment_id INTEGER,
                        metric_name VARCHAR(100) NOT NULL,
                        metric_value DOUBLE PRECISION,
                        tags JSONB,
                        metadata JSONB
                    )
                """)
                
                # 如果TimescaleDB可用，将metrics表转换为超表
                if self._timescaledb_enabled:
                    try:
                        await conn.execute(
                            "SELECT create_hypertable('metrics', 'time', if_not_exists => TRUE)"
                        )
                        logger.info("metrics表已转换为TimescaleDB超表")
                    except Exception as e:
                        logger.warning(f"创建TimescaleDB超表失败: {e}")
                
                # 创建索引
                await self._create_indexes(conn)
                
                logger.info("基础表结构创建完成")
                
        except Exception as e:
            logger.error(f"创建基础表结构失败: {e}")
            raise DatabaseError(f"表结构创建失败: {e}")
    
    async def _create_indexes(self, conn):
        """创建数据库索引"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_experiments_status ON experiments(status)",
            "CREATE INDEX IF NOT EXISTS idx_experiments_created_at ON experiments(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_individuals_experiment_id ON individuals(experiment_id)",
            "CREATE INDEX IF NOT EXISTS idx_individuals_generation ON individuals(generation)",
            "CREATE INDEX IF NOT EXISTS idx_evaluations_individual_id ON evaluations(individual_id)",
            "CREATE INDEX IF NOT EXISTS idx_evaluations_task_id ON evaluations(task_id)",
            "CREATE INDEX IF NOT EXISTS idx_metrics_time ON metrics(time)",
            "CREATE INDEX IF NOT EXISTS idx_metrics_experiment_id ON metrics(experiment_id)",
            "CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics(metric_name)"
        ]
        
        for index_sql in indexes:
            try:
                await conn.execute(index_sql)
            except Exception as e:
                logger.warning(f"创建索引失败: {index_sql}, 错误: {e}")
    
    @asynccontextmanager
    async def get_async_connection(self):
        """获取异步数据库连接"""
        if not self._async_pool:
            raise DatabaseError("异步连接池未初始化")
        
        conn = None
        try:
            conn = await self._async_pool.acquire()
            self.stats.active_connections += 1
            yield conn
        except Exception as e:
            self.stats.failed_connections += 1
            logger.error(f"获取异步连接失败: {e}")
            raise
        finally:
            if conn:
                await self._async_pool.release(conn)
                self.stats.active_connections -= 1
    
    def get_sync_connection(self):
        """获取同步数据库连接"""
        if not self._sync_pool:
            raise DatabaseError("同步连接池未初始化")
        
        try:
            conn = self._sync_pool.getconn()
            self.stats.active_connections += 1
            return conn
        except Exception as e:
            self.stats.failed_connections += 1
            logger.error(f"获取同步连接失败: {e}")
            raise
    
    def release_sync_connection(self, conn):
        """释放同步数据库连接"""
        if self._sync_pool and conn:
            self._sync_pool.putconn(conn)
            self.stats.active_connections -= 1
    
    async def execute_query(self, query: str, *args) -> List[Dict[str, Any]]:
        """执行查询并返回结果"""
        start_time = datetime.now()
        try:
            async with self.get_async_connection() as conn:
                result = await conn.fetch(query, *args)
                self.stats.total_queries += 1
                
                # 更新平均查询时间
                query_time = (datetime.now() - start_time).total_seconds()
                self.stats.avg_query_time = (
                    (self.stats.avg_query_time * (self.stats.total_queries - 1) + query_time) 
                    / self.stats.total_queries
                )
                
                return [dict(row) for row in result]
                
        except Exception as e:
            self.stats.failed_queries += 1
            logger.error(f"查询执行失败: {query[:100]}..., 错误: {e}")
            raise DatabaseError(f"查询执行失败: {e}")
    
    async def execute_command(self, command: str, *args) -> str:
        """执行命令（INSERT, UPDATE, DELETE等）"""
        start_time = datetime.now()
        try:
            async with self.get_async_connection() as conn:
                result = await conn.execute(command, *args)
                self.stats.total_queries += 1
                
                # 更新平均查询时间
                query_time = (datetime.now() - start_time).total_seconds()
                self.stats.avg_query_time = (
                    (self.stats.avg_query_time * (self.stats.total_queries - 1) + query_time) 
                    / self.stats.total_queries
                )
                
                return result
                
        except Exception as e:
            self.stats.failed_queries += 1
            logger.error(f"命令执行失败: {command[:100]}..., 错误: {e}")
            raise DatabaseError(f"命令执行失败: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """数据库健康检查"""
        try:
            start_time = datetime.now()
            
            # 测试连接
            async with self.get_async_connection() as conn:
                await conn.fetchval("SELECT 1")
            
            response_time = (datetime.now() - start_time).total_seconds()
            
            # 获取数据库统计信息
            db_stats = await self._get_database_stats()
            
            self.stats.last_health_check = datetime.now()
            self.stats.health_status = "healthy"
            
            return {
                "status": "healthy",
                "response_time": response_time,
                "timescaledb_enabled": self._timescaledb_enabled,
                "connection_stats": {
                    "total_connections": self.stats.total_connections,
                    "active_connections": self.stats.active_connections,
                    "failed_connections": self.stats.failed_connections,
                    "total_queries": self.stats.total_queries,
                    "failed_queries": self.stats.failed_queries,
                    "avg_query_time": self.stats.avg_query_time
                },
                "database_stats": db_stats,
                "last_check": self.stats.last_health_check.isoformat()
            }
            
        except Exception as e:
            self.stats.health_status = "unhealthy"
            logger.error(f"数据库健康检查失败: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "last_check": datetime.now().isoformat()
            }
    
    async def _get_database_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        try:
            async with self.get_async_connection() as conn:
                # 获取数据库大小
                db_size = await conn.fetchval(
                    "SELECT pg_size_pretty(pg_database_size(current_database()))"
                )
                
                # 获取表数量
                table_count = await conn.fetchval(
                    "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'"
                )
                
                # 获取连接数
                connection_count = await conn.fetchval(
                    "SELECT count(*) FROM pg_stat_activity"
                )
                
                return {
                    "database_size": db_size,
                    "table_count": table_count,
                    "connection_count": connection_count
                }
                
        except Exception as e:
            logger.warning(f"获取数据库统计信息失败: {e}")
            return {}
    
    async def cleanup(self):
        """清理资源"""
        try:
            logger.info("开始清理数据库资源")
            
            # 关闭异步连接池
            if self._async_pool:
                await self._async_pool.close()
                self._async_pool = None
                logger.info("异步连接池已关闭")
            
            # 关闭同步连接池
            if self._sync_pool:
                self._sync_pool.closeall()
                self._sync_pool = None
                logger.info("同步连接池已关闭")
            
            self._initialized = False
            logger.info("数据库资源清理完成")
            
        except Exception as e:
            logger.error(f"清理数据库资源失败: {e}")
    
    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized
    
    def is_timescaledb_enabled(self) -> bool:
        """检查TimescaleDB是否可用"""
        return self._timescaledb_enabled
    
    def get_stats(self) -> ConnectionStats:
        """获取连接统计信息"""
        return self.stats

# 全局数据库管理器实例
_db_manager: Optional[DatabaseManager] = None

def get_database_manager() -> DatabaseManager:
    """获取全局数据库管理器实例"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager

async def initialize_database() -> bool:
    """初始化全局数据库系统"""
    db_manager = get_database_manager()
    return await db_manager.initialize()

async def cleanup_database():
    """清理全局数据库系统"""
    global _db_manager
    if _db_manager:
        await _db_manager.cleanup()
        _db_manager = None