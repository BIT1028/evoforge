#!/usr/bin/env python3
"""
数据库连接和会话管理
"""
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import structlog

from app.core.config import settings

logger = structlog.get_logger()

# 创建数据库引擎
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_recycle=300,
)

# 创建会话工厂
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# 数据库基类
Base = declarative_base()
metadata = MetaData()

async def create_tables():
    """创建数据库表"""
    logger.info("创建数据库表")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("数据库表创建完成")
    except Exception as e:
        logger.error("数据库表创建失败", error=str(e))
        raise

def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()