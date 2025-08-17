#!/usr/bin/env python3
"""
数字细胞数据模型
"""
from typing import Optional
from uuid import UUID, uuid4
from sqlalchemy import String, Text, Float, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.sqlite import CHAR
import uuid
from app.core.database import Base
from app.models.base import TimestampMixin

class DigitalCell(Base, TimestampMixin):
    """数字细胞模型"""
    __tablename__ = "digital_cells"
    
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
        comment="细胞ID"
    )
    generation_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("generations.id"),
        nullable=False,
        comment="所属代数ID"
    )
    genome: Mapped[str] = mapped_column(Text, nullable=False, comment="基因序列")
    generated_code: Mapped[Optional[str]] = mapped_column(Text, comment="生成的代码")
    fitness_score: Mapped[Optional[float]] = mapped_column(Float, comment="适应度分数")
    
    # 遗传信息
    parent1_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("digital_cells.id"),
        comment="父代1 ID"
    )
    parent2_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("digital_cells.id"),
        comment="父代2 ID"
    )
    mutation_rate: Mapped[Optional[float]] = mapped_column(Float, comment="变异率")
    
    # 关联关系
    generation: Mapped["Generation"] = relationship(
        "Generation",
        back_populates="digital_cells"
    )
    parent1: Mapped[Optional["DigitalCell"]] = relationship(
        "DigitalCell",
        foreign_keys=[parent1_id],
        remote_side=[id]
    )
    parent2: Mapped[Optional["DigitalCell"]] = relationship(
        "DigitalCell",
        foreign_keys=[parent2_id],
        remote_side=[id]
    )
    
    def __repr__(self):
        return f"<DigitalCell(id={self.id}, fitness={self.fitness_score})>"