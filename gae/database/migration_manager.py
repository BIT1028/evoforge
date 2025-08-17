# -*- coding: utf-8 -*-
"""
迁移管理器 - EvoForge数据库迁移系统

负责数据库版本控制和结构更新：
- 迁移文件管理
- 版本控制
- 自动迁移执行
- 回滚支持
- 迁移状态跟踪

作者: EvoForge Team
创建时间: 2024
"""

import os
import re
import hashlib
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass

from .database_manager import DatabaseManager, get_database_manager
from ..core.logging_system import get_logger
from ..core.error_handler import EvoForgeError

logger = get_logger(__name__)

class MigrationError(EvoForgeError):
    """迁移错误"""
    pass

@dataclass
class Migration:
    """迁移信息"""
    version: str
    name: str
    file_path: str
    up_sql: str
    down_sql: Optional[str] = None
    checksum: Optional[str] = None
    applied_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.checksum is None:
            self.checksum = self._calculate_checksum()
    
    def _calculate_checksum(self) -> str:
        """计算SQL内容的校验和"""
        content = self.up_sql + (self.down_sql or "")
        return hashlib.md5(content.encode('utf-8')).hexdigest()

class MigrationManager:
    """迁移管理器"""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None, 
                 migrations_dir: Optional[str] = None):
        self.db_manager = db_manager or get_database_manager()
        
        # 默认迁移目录
        if migrations_dir is None:
            project_root = Path(__file__).parent.parent.parent
            self.migrations_dir = project_root / "migrations"
        else:
            self.migrations_dir = Path(migrations_dir)
        
        # 确保迁移目录存在
        self.migrations_dir.mkdir(parents=True, exist_ok=True)
        
        # 迁移文件名模式
        self.migration_pattern = re.compile(r'^(\d{14})_([a-zA-Z0-9_]+)\.sql$')
        
        logger.info(f"迁移管理器初始化完成，迁移目录: {self.migrations_dir}")
    
    async def initialize_migration_table(self):
        """初始化迁移表"""
        try:
            create_table_sql = """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version VARCHAR(14) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    checksum VARCHAR(32) NOT NULL,
                    applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    execution_time_ms INTEGER,
                    success BOOLEAN DEFAULT TRUE
                );
                
                CREATE INDEX IF NOT EXISTS idx_schema_migrations_applied_at 
                ON schema_migrations(applied_at);
            """
            
            await self.db_manager.execute_command(create_table_sql)
            logger.info("迁移表初始化完成")
            
        except Exception as e:
            logger.error(f"初始化迁移表失败: {e}")
            raise MigrationError(f"初始化迁移表失败: {e}")
    
    def scan_migration_files(self) -> List[Migration]:
        """扫描迁移文件"""
        try:
            migrations = []
            
            for file_path in sorted(self.migrations_dir.glob('*.sql')):
                match = self.migration_pattern.match(file_path.name)
                if not match:
                    logger.warning(f"跳过无效的迁移文件: {file_path.name}")
                    continue
                
                version, name = match.groups()
                
                # 读取文件内容
                content = file_path.read_text(encoding='utf-8')
                
                # 解析UP和DOWN部分
                up_sql, down_sql = self._parse_migration_content(content)
                
                migration = Migration(
                    version=version,
                    name=name,
                    file_path=str(file_path),
                    up_sql=up_sql,
                    down_sql=down_sql
                )
                
                migrations.append(migration)
            
            logger.info(f"扫描到 {len(migrations)} 个迁移文件")
            return migrations
            
        except Exception as e:
            logger.error(f"扫描迁移文件失败: {e}")
            raise MigrationError(f"扫描迁移文件失败: {e}")
    
    def _parse_migration_content(self, content: str) -> Tuple[str, Optional[str]]:
        """解析迁移文件内容"""
        # 查找-- +migrate Up和-- +migrate Down标记
        up_match = re.search(r'--\s*\+migrate\s+Up\s*\n(.*?)(?=--\s*\+migrate\s+Down|$)', 
                            content, re.DOTALL | re.IGNORECASE)
        down_match = re.search(r'--\s*\+migrate\s+Down\s*\n(.*?)$', 
                             content, re.DOTALL | re.IGNORECASE)
        
        up_sql = up_match.group(1).strip() if up_match else content.strip()
        down_sql = down_match.group(1).strip() if down_match else None
        
        return up_sql, down_sql
    
    async def get_applied_migrations(self) -> Dict[str, Migration]:
        """获取已应用的迁移"""
        try:
            query = """
                SELECT version, name, checksum, applied_at, execution_time_ms, success
                FROM schema_migrations 
                ORDER BY version
            """
            
            result = await self.db_manager.execute_query(query)
            
            applied = {}
            for row in result:
                migration = Migration(
                    version=row['version'],
                    name=row['name'],
                    file_path="",  # 已应用的迁移不需要文件路径
                    up_sql="",
                    down_sql=None,
                    checksum=row['checksum'],
                    applied_at=row['applied_at']
                )
                applied[row['version']] = migration
            
            return applied
            
        except Exception as e:
            logger.error(f"获取已应用迁移失败: {e}")
            raise MigrationError(f"获取已应用迁移失败: {e}")
    
    async def get_pending_migrations(self) -> List[Migration]:
        """获取待应用的迁移"""
        try:
            all_migrations = self.scan_migration_files()
            applied_migrations = await self.get_applied_migrations()
            
            pending = []
            for migration in all_migrations:
                if migration.version not in applied_migrations:
                    pending.append(migration)
                else:
                    # 检查校验和是否匹配
                    applied = applied_migrations[migration.version]
                    if applied.checksum != migration.checksum:
                        logger.warning(f"迁移 {migration.version} 的校验和不匹配")
            
            logger.info(f"发现 {len(pending)} 个待应用的迁移")
            return pending
            
        except Exception as e:
            logger.error(f"获取待应用迁移失败: {e}")
            raise MigrationError(f"获取待应用迁移失败: {e}")
    
    async def apply_migration(self, migration: Migration) -> bool:
        """应用单个迁移"""
        try:
            start_time = datetime.now()
            
            logger.info(f"开始应用迁移: {migration.version}_{migration.name}")
            
            # 在事务中执行迁移
            async with self.db_manager.get_async_connection() as conn:
                async with conn.transaction():
                    # 执行迁移SQL
                    await conn.execute(migration.up_sql)
                    
                    # 记录迁移状态
                    execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
                    
                    await conn.execute(
                        """
                        INSERT INTO schema_migrations (version, name, checksum, applied_at, execution_time_ms, success)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        """,
                        migration.version,
                        migration.name,
                        migration.checksum,
                        start_time,
                        execution_time,
                        True
                    )
            
            logger.info(f"迁移应用成功: {migration.version}_{migration.name} ({execution_time}ms)")
            return True
            
        except Exception as e:
            logger.error(f"应用迁移失败: {migration.version}_{migration.name}: {e}")
            
            # 记录失败状态
            try:
                execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
                await self.db_manager.execute_command(
                    """
                    INSERT INTO schema_migrations (version, name, checksum, applied_at, execution_time_ms, success)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (version) DO UPDATE SET
                        execution_time_ms = EXCLUDED.execution_time_ms,
                        success = EXCLUDED.success
                    """,
                    migration.version,
                    migration.name,
                    migration.checksum,
                    start_time,
                    execution_time,
                    False
                )
            except:
                pass  # 忽略记录失败状态的错误
            
            raise MigrationError(f"应用迁移失败: {migration.version}_{migration.name}: {e}")
    
    async def apply_all_pending_migrations(self) -> int:
        """应用所有待应用的迁移"""
        try:
            await self.initialize_migration_table()
            
            pending_migrations = await self.get_pending_migrations()
            
            if not pending_migrations:
                logger.info("没有待应用的迁移")
                return 0
            
            applied_count = 0
            for migration in pending_migrations:
                if await self.apply_migration(migration):
                    applied_count += 1
                else:
                    logger.error(f"迁移应用失败，停止后续迁移: {migration.version}_{migration.name}")
                    break
            
            logger.info(f"成功应用 {applied_count}/{len(pending_migrations)} 个迁移")
            return applied_count
            
        except Exception as e:
            logger.error(f"应用迁移失败: {e}")
            raise MigrationError(f"应用迁移失败: {e}")
    
    async def rollback_migration(self, version: str) -> bool:
        """回滚指定版本的迁移"""
        try:
            # 获取迁移信息
            applied_migrations = await self.get_applied_migrations()
            if version not in applied_migrations:
                logger.warning(f"迁移 {version} 未应用，无需回滚")
                return False
            
            # 查找迁移文件
            all_migrations = self.scan_migration_files()
            migration_to_rollback = None
            for migration in all_migrations:
                if migration.version == version:
                    migration_to_rollback = migration
                    break
            
            if not migration_to_rollback:
                raise MigrationError(f"找不到迁移文件: {version}")
            
            if not migration_to_rollback.down_sql:
                raise MigrationError(f"迁移 {version} 没有回滚SQL")
            
            logger.info(f"开始回滚迁移: {version}")
            
            # 在事务中执行回滚
            async with self.db_manager.get_async_connection() as conn:
                async with conn.transaction():
                    # 执行回滚SQL
                    await conn.execute(migration_to_rollback.down_sql)
                    
                    # 删除迁移记录
                    await conn.execute(
                        "DELETE FROM schema_migrations WHERE version = $1",
                        version
                    )
            
            logger.info(f"迁移回滚成功: {version}")
            return True
            
        except Exception as e:
            logger.error(f"回滚迁移失败: {version}: {e}")
            raise MigrationError(f"回滚迁移失败: {version}: {e}")
    
    def create_migration_file(self, name: str, up_sql: str, down_sql: Optional[str] = None) -> str:
        """创建迁移文件"""
        try:
            # 生成版本号（时间戳）
            version = datetime.now().strftime('%Y%m%d%H%M%S')
            
            # 清理名称
            clean_name = re.sub(r'[^a-zA-Z0-9_]', '_', name.lower())
            
            # 生成文件名
            filename = f"{version}_{clean_name}.sql"
            file_path = self.migrations_dir / filename
            
            # 生成文件内容
            content = f"-- +migrate Up\n{up_sql}\n"
            if down_sql:
                content += f"\n-- +migrate Down\n{down_sql}\n"
            
            # 写入文件
            file_path.write_text(content, encoding='utf-8')
            
            logger.info(f"迁移文件创建成功: {filename}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"创建迁移文件失败: {e}")
            raise MigrationError(f"创建迁移文件失败: {e}")
    
    async def get_migration_status(self) -> Dict[str, any]:
        """获取迁移状态"""
        try:
            all_migrations = self.scan_migration_files()
            applied_migrations = await self.get_applied_migrations()
            pending_migrations = await self.get_pending_migrations()
            
            status = {
                'total_migrations': len(all_migrations),
                'applied_migrations': len(applied_migrations),
                'pending_migrations': len(pending_migrations),
                'last_applied': None,
                'migrations': []
            }
            
            # 获取最后应用的迁移
            if applied_migrations:
                last_version = max(applied_migrations.keys())
                status['last_applied'] = {
                    'version': last_version,
                    'name': applied_migrations[last_version].name,
                    'applied_at': applied_migrations[last_version].applied_at
                }
            
            # 构建迁移列表
            for migration in all_migrations:
                migration_info = {
                    'version': migration.version,
                    'name': migration.name,
                    'file_path': migration.file_path,
                    'checksum': migration.checksum,
                    'applied': migration.version in applied_migrations
                }
                
                if migration.version in applied_migrations:
                    applied = applied_migrations[migration.version]
                    migration_info.update({
                        'applied_at': applied.applied_at,
                        'checksum_match': applied.checksum == migration.checksum
                    })
                
                status['migrations'].append(migration_info)
            
            return status
            
        except Exception as e:
            logger.error(f"获取迁移状态失败: {e}")
            raise MigrationError(f"获取迁移状态失败: {e}")
    
    async def validate_migrations(self) -> List[Dict[str, any]]:
        """验证迁移完整性"""
        try:
            issues = []
            
            all_migrations = self.scan_migration_files()
            applied_migrations = await self.get_applied_migrations()
            
            # 检查校验和不匹配
            for migration in all_migrations:
                if migration.version in applied_migrations:
                    applied = applied_migrations[migration.version]
                    if applied.checksum != migration.checksum:
                        issues.append({
                            'type': 'checksum_mismatch',
                            'version': migration.version,
                            'name': migration.name,
                            'message': '迁移文件已被修改，校验和不匹配'
                        })
            
            # 检查孤立的应用记录
            for version, applied in applied_migrations.items():
                if not any(m.version == version for m in all_migrations):
                    issues.append({
                        'type': 'orphaned_record',
                        'version': version,
                        'name': applied.name,
                        'message': '数据库中有迁移记录但找不到对应的迁移文件'
                    })
            
            # 检查版本号顺序
            versions = [m.version for m in all_migrations]
            for i in range(1, len(versions)):
                if versions[i] <= versions[i-1]:
                    issues.append({
                        'type': 'version_order',
                        'version': versions[i],
                        'message': '迁移版本号顺序错误'
                    })
            
            if issues:
                logger.warning(f"发现 {len(issues)} 个迁移问题")
            else:
                logger.info("迁移验证通过")
            
            return issues
            
        except Exception as e:
            logger.error(f"验证迁移失败: {e}")
            raise MigrationError(f"验证迁移失败: {e}")

# 全局迁移管理器实例
_migration_manager: Optional[MigrationManager] = None

def get_migration_manager() -> MigrationManager:
    """获取全局迁移管理器实例"""
    global _migration_manager
    if _migration_manager is None:
        _migration_manager = MigrationManager()
    return _migration_manager