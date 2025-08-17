#!/usr/bin/env python3
"""
代数数据模型
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Integer, Float, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin

class Generation(Base, TimestampMixin):
    """代数模型"""
    __tablename__ = "generations"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, comment="代数ID")
    generation_number: Mapped[int] = mapped_column(Integer, nullable=False, comment="代数编号")
    population_size: Mapped[int] = mapped_column(Integer, nullable=False, comment="种群大小")
    avg_fitness: Mapped[Optional[float]] = mapped_column(Float, comment="平均适应度")
    max_fitness: Mapped[Optional[float]] = mapped_column(Float, comment="最高适应度")
    min_fitness: Mapped[Optional[float]] = mapped_column(Float, comment="最低适应度")
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), comment="完成时间")
    
    # 关联关系
    digital_cells: Mapped[List["DigitalCell"]] = relationship(
        "DigitalCell",
        back_populates="generation",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<Generation(id={self.id}, number={self.generation_number}, avg_fitness={self.avg_fitness})>"