#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库初始化脚本

根据 comprehensive_implementation_plan.md 任务9要求实现

功能包括：
- 数据库连接测试
- TimescaleDB扩展安装
- 初始表结构创建
- 迁移脚本执行
- 初始数据填充
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from gae.config.config_manager import ConfigManager
from gae.database.database_manager import DatabaseManager, DatabaseError
from gae.database.migration_manager import MigrationManager
from gae.core.logging_system import LoggingSystem

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseInitializer:
    """数据库初始化器"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.db_config = config_manager.get_database_config()
        self.db_manager = None
        self.migration_manager = None
        
        logger.info("数据库初始化器创建完成")
    
    async def initialize(self, force_recreate: bool = False) -> bool:
        """
        初始化数据库系统
        
        Args:
            force_recreate: 是否强制重新创建数据库
            
        Returns:
            bool: 初始化是否成功
        """
        try:
            logger.info("开始数据库系统初始化")
            
            # 1. 验证配置
            if not await self._validate_config():
                return False
            
            # 2. 创建数据库管理器
            self.db_manager = DatabaseManager(self.config_manager)
            
            # 3. 测试数据库连接
            if not await self._test_connection():
                return False
            
            # 4. 初始化数据库管理器
            await self.db_manager.initialize()
            
            # 5. 检查并安装TimescaleDB扩展
            if not await self._setup_timescaledb():
                return False
            
            # 6. 创建迁移管理器
            self.migration_manager = MigrationManager(self.db_manager)
            
            # 7. 执行数据库迁移
            if not await self._run_migrations(force_recreate):
                return False
            
            # 8. 验证表结构
            if not await self._verify_schema():
                return False
            
            # 9. 填充初始数据
            if not await self._populate_initial_data():
                return False
            
            # 10. 运行健康检查
            if not await self._health_check():
                return False
            
            logger.info("数据库系统初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            return False
        finally:
            if self.db_manager:
                await self.db_manager.close()
    
    async def _validate_config(self) -> bool:
        """验证数据库配置"""
        try:
            logger.info("验证数据库配置")
            
            errors = self.db_config.validate()
            if errors:
                logger.error(f"数据库配置验证失败: {errors}")
                return False
            
            logger.info("数据库配置验证通过")
            return True
            
        except Exception as e:
            logger.error(f"配置验证异常: {e}")
            return False
    
    async def _test_connection(self) -> bool:
        """测试数据库连接"""
        try:
            logger.info("测试数据库连接")
            
            # 测试同步连接
            sync_conn = self.db_manager.get_sync_connection()
            if sync_conn:
                with sync_conn:
                    with sync_conn.cursor() as cursor:
                        cursor.execute("SELECT version()")
                        version = cursor.fetchone()[0]
                        logger.info(f"PostgreSQL版本: {version}")
            else:
                logger.error("无法建立同步数据库连接")
                return False
            
            # 测试异步连接
            async_conn = await self.db_manager.get_async_connection()
            if async_conn:
                try:
                    version = await async_conn.fetchval("SELECT version()")
                    logger.info(f"异步连接PostgreSQL版本: {version}")
                finally:
                    await async_conn.close()
            else:
                logger.error("无法建立异步数据库连接")
                return False
            
            logger.info("数据库连接测试通过")
            return True
            
        except Exception as e:
            logger.error(f"数据库连接测试失败: {e}")
            return False
    
    async def _setup_timescaledb(self) -> bool:
        """设置TimescaleDB扩展"""
        try:
            if not self.db_config.enable_timescaledb:
                logger.info("跳过TimescaleDB设置（未启用）")
                return True
            
            logger.info("设置TimescaleDB扩展")
            
            # 检查TimescaleDB是否已安装
            conn = self.db_manager.get_sync_connection()
            with conn:
                with conn.cursor() as cursor:
                    # 检查扩展是否存在
                    cursor.execute(
                        "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'timescaledb')"
                    )
                    timescaledb_exists = cursor.fetchone()[0]
                    
                    if not timescaledb_exists:
                        logger.info("安装TimescaleDB扩展")
                        cursor.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE")
                        conn.commit()
                    else:
                        logger.info("TimescaleDB扩展已存在")
                    
                    # 检查版本
                    cursor.execute("SELECT extversion FROM pg_extension WHERE extname = 'timescaledb'")
                    version = cursor.fetchone()
                    if version:
                        logger.info(f"TimescaleDB版本: {version[0]}")
            
            logger.info("TimescaleDB设置完成")
            return True
            
        except Exception as e:
            logger.error(f"TimescaleDB设置失败: {e}")
            return False
    
    async def _run_migrations(self, force_recreate: bool = False) -> bool:
        """运行数据库迁移"""
        try:
            logger.info("执行数据库迁移")
            
            if force_recreate:
                logger.warning("强制重新创建数据库结构")
                await self.migration_manager.reset_database()
            
            # 扫描迁移文件
            migrations_dir = project_root / "migrations"
            migration_files = await self.migration_manager.scan_migrations(str(migrations_dir))
            
            if not migration_files:
                logger.warning("未找到迁移文件")
                return True
            
            logger.info(f"找到 {len(migration_files)} 个迁移文件")
            
            # 应用迁移
            for migration_file in migration_files:
                success = await self.migration_manager.apply_migration(migration_file)
                if not success:
                    logger.error(f"迁移失败: {migration_file}")
                    return False
                logger.info(f"迁移成功: {migration_file}")
            
            logger.info("数据库迁移完成")
            return True
            
        except Exception as e:
            logger.error(f"数据库迁移失败: {e}")
            return False
    
    async def _verify_schema(self) -> bool:
        """验证数据库表结构"""
        try:
            logger.info("验证数据库表结构")
            
            required_tables = [
                'experiments', 'individuals', 'evaluations', 'metrics'
            ]
            
            conn = self.db_manager.get_sync_connection()
            with conn:
                with conn.cursor() as cursor:
                    for table in required_tables:
                        cursor.execute(
                            "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = %s)",
                            (table,)
                        )
                        exists = cursor.fetchone()[0]
                        
                        if not exists:
                            logger.error(f"缺少必需的表: {table}")
                            return False
                        
                        logger.debug(f"表 {table} 存在")
            
            logger.info("数据库表结构验证通过")
            return True
            
        except Exception as e:
            logger.error(f"表结构验证失败: {e}")
            return False
    
    async def _populate_initial_data(self) -> bool:
        """填充初始数据"""
        try:
            logger.info("填充初始数据")
            
            # 这里可以添加初始数据填充逻辑
            # 例如：默认配置、系统用户等
            
            logger.info("初始数据填充完成")
            return True
            
        except Exception as e:
            logger.error(f"初始数据填充失败: {e}")
            return False
    
    async def _health_check(self) -> bool:
        """运行健康检查"""
        try:
            logger.info("运行数据库健康检查")
            
            health_status = await self.db_manager.health_check()
            
            if health_status['status'] == 'healthy':
                logger.info("数据库健康检查通过")
                logger.info(f"连接统计: {health_status['stats']}")
                return True
            else:
                logger.error(f"数据库健康检查失败: {health_status}")
                return False
            
        except Exception as e:
            logger.error(f"健康检查异常: {e}")
            return False

async def main():
    """主函数"""
    try:
        # 初始化配置管理器
        config_manager = ConfigManager()
        await config_manager.initialize()
        
        # 创建数据库初始化器
        initializer = DatabaseInitializer(config_manager)
        
        # 执行初始化
        success = await initializer.initialize(force_recreate=False)
        
        if success:
            logger.info("数据库系统初始化成功")
            return 0
        else:
            logger.error("数据库系统初始化失败")
            return 1
            
    except Exception as e:
        logger.error(f"初始化过程异常: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)