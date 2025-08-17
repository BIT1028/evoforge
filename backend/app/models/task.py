#!/usr/bin/env python3
"""
任务数据模型
"""
from typing import Optional
from uuid import uuid4
from sqlalchemy import String, Text, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.models.base import TimestampMixin

class Task(Base, TimestampMixin):
    """任务模型"""
    __tablename__ = "tasks"
    
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
        comment="任务ID"
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="任务名称")
    description: Mapped[str] = mapped_column(Text, nullable=False, comment="任务描述")
    priority: Mapped[int] = mapped_column(Integer, default=0, comment="优先级")
    category: Mapped[str] = mapped_column(String(50), nullable=False, comment="任务类别")
    template: Mapped[Optional[str]] = mapped_column(Text, comment="任务模板")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否激活")
    
    def __repr__(self):
        return f"<Task(id={self.id}, name={self.name}, priority={self.priority})>"