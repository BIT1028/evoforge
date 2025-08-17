#!/usr/bin/env python3
"""
评估相关数据模型
"""
from typing import Optional
from uuid import uuid4
from sqlalchemy import String, Text, Float, Integer, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin

class EvaluationLog(Base, TimestampMixin):
    """评估日志模型"""
    __tablename__ = "evaluation_logs"
    
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
        comment="评估日志ID"
    )
    digital_cell_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("digital_cells.id"),
        nullable=False,
        comment="数字细胞ID"
    )
    task_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tasks.id"),
        nullable=False,
        comment="任务ID"
    )
    oracle_request: Mapped[Optional[str]] = mapped_column(Text, comment="甲骨文请求")
    oracle_response: Mapped[Optional[str]] = mapped_column(Text, comment="甲骨文响应")
    fitness_score: Mapped[Optional[float]] = mapped_column(Float, comment="适应度分数")
    api_cost: Mapped[Optional[float]] = mapped_column(Numeric(10, 6), comment="API成本")
    execution_time: Mapped[Optional[float]] = mapped_column(Float, comment="执行时间")
    
    # 关联关系
    digital_cell: Mapped["DigitalCell"] = relationship("DigitalCell")
    task: Mapped["Task"] = relationship("Task")
    
    def __repr__(self):
        return f"<EvaluationLog(id={self.id}, fitness={self.fitness_score}, cost={self.api_cost})>"

class ApiCost(Base, TimestampMixin):
    """API成本跟踪模型"""
    __tablename__ = "api_costs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, comment="成本记录ID")
    service_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="服务名称")
    model_name: Mapped[Optional[str]] = mapped_column(String(100), comment="模型名称")
    input_tokens: Mapped[Optional[int]] = mapped_column(Integer, comment="输入token数")
    output_tokens: Mapped[Optional[int]] = mapped_column(Integer, comment="输出token数")
    cost_usd: Mapped[Optional[float]] = mapped_column(Numeric(10, 6), comment="成本（美元）")
    
    def __repr__(self):
        return f"<ApiCost(id={self.id}, service={self.service_name}, cost={self.cost_usd})>"