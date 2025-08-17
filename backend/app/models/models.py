"""EvoForge数据模型

定义SQLAlchemy数据模型，用于持久化存储:
- 进化任务
- 代信息
- 个体数据
- 适应度指标
- 测试结果
- 工件文件
"""

from datetime import datetime
from typing import Dict, Any, Optional
import json

from sqlalchemy import (
    Column, Integer, String, Text, Float, DateTime, Boolean,
    ForeignKey, JSON, LargeBinary, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session
from sqlalchemy.sql import func

Base = declarative_base()

class Task(Base):
    """进化任务表"""
    __tablename__ = 'tasks'
    
    id = Column(String(36), primary_key=True)  # UUID
    name = Column(String(255), nullable=False)
    description = Column(Text)
    function_signature = Column(Text, nullable=False)
    test_cases = Column(JSON)  # 存储测试用例
    objectives = Column(JSON)  # 优化目标列表
    
    # 进化参数
    population_size = Column(Integer, default=50)
    max_generations = Column(Integer, default=100)
    mutation_rate = Column(Float, default=0.1)
    crossover_rate = Column(Float, default=0.8)
    
    # 资源限制
    timeout_seconds = Column(Integer, default=300)
    memory_limit_mb = Column(Integer, default=128)
    cpu_quota = Column(Integer, default=100000)
    
    # 状态信息
    status = Column(String(20), default='pending')  # pending, running, completed, failed, stopped
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # 错误信息
    error_message = Column(Text)
    
    # 配置和元数据
    config = Column(JSON)  # 完整配置
    task_metadata = Column(JSON)  # 额外元数据
    
    # 关系
    generations = relationship('Generation', back_populates='task', cascade='all, delete-orphan')
    individuals = relationship('Individual', back_populates='task', cascade='all, delete-orphan')
    artifacts = relationship('Artifact', back_populates='task', cascade='all, delete-orphan')
    
    # 索引
    __table_args__ = (
        Index('idx_task_status', 'status'),
        Index('idx_task_created', 'created_at'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'function_signature': self.function_signature,
            'test_cases': self.test_cases,
            'objectives': self.objectives,
            'population_size': self.population_size,
            'max_generations': self.max_generations,
            'mutation_rate': self.mutation_rate,
            'crossover_rate': self.crossover_rate,
            'timeout_seconds': self.timeout_seconds,
            'memory_limit_mb': self.memory_limit_mb,
            'cpu_quota': self.cpu_quota,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error_message': self.error_message,
            'config': self.config,
            'metadata': self.task_metadata
        }

class Generation(Base):
    """代信息表"""
    __tablename__ = 'generations'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(36), ForeignKey('tasks.id'), nullable=False)
    generation_number = Column(Integer, nullable=False)
    
    # 统计信息
    population_size = Column(Integer, nullable=False)
    best_fitness = Column(JSON)  # 最佳适应度
    average_fitness = Column(JSON)  # 平均适应度
    worst_fitness = Column(JSON)  # 最差适应度
    diversity_score = Column(Float)  # 多样性分数
    
    # 时间信息
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    duration_seconds = Column(Float)
    
    # 元数据
    generation_metadata = Column(JSON)
    
    # 关系
    task = relationship('Task', back_populates='generations')
    individuals = relationship('Individual', back_populates='generation', cascade='all, delete-orphan')
    
    # 索引
    __table_args__ = (
        Index('idx_generation_task', 'task_id'),
        Index('idx_generation_number', 'task_id', 'generation_number'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'task_id': self.task_id,
            'generation_number': self.generation_number,
            'population_size': self.population_size,
            'best_fitness': self.best_fitness,
            'average_fitness': self.average_fitness,
            'worst_fitness': self.worst_fitness,
            'diversity_score': self.diversity_score,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'duration_seconds': self.duration_seconds,
            'metadata': self.generation_metadata
        }

class Individual(Base):
    """个体表"""
    __tablename__ = 'individuals'
    
    id = Column(String(36), primary_key=True)  # UUID
    task_id = Column(String(36), ForeignKey('tasks.id'), nullable=False)
    generation_id = Column(Integer, ForeignKey('generations.id'), nullable=False)
    generation_number = Column(Integer, nullable=False)
    
    # 个体信息
    individual_number = Column(Integer, nullable=False)  # 在代中的编号
    parent_ids = Column(JSON)  # 父代个体ID列表
    
    # 基因和代码
    genome_data = Column(JSON)  # 基因组数据
    source_code = Column(Text, nullable=False)  # 生成的源代码
    ast_data = Column(JSON)  # AST数据
    
    # 代码特征
    code_length = Column(Integer)  # 代码长度
    complexity_score = Column(Float)  # 复杂度分数
    
    # 时间信息
    created_at = Column(DateTime, default=datetime.utcnow)
    evaluated_at = Column(DateTime)
    
    # 元数据
    individual_metadata = Column(JSON)
    
    # 关系
    task = relationship('Task', back_populates='individuals')
    generation = relationship('Generation', back_populates='individuals')
    fitness_records = relationship('Fitness', back_populates='individual', cascade='all, delete-orphan')
    test_results = relationship('TestResult', back_populates='individual', cascade='all, delete-orphan')
    
    # 索引
    __table_args__ = (
        Index('idx_individual_task', 'task_id'),
        Index('idx_individual_generation', 'generation_id'),
        Index('idx_individual_number', 'task_id', 'generation_number', 'individual_number'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'task_id': self.task_id,
            'generation_id': self.generation_id,
            'generation_number': self.generation_number,
            'individual_number': self.individual_number,
            'parent_ids': self.parent_ids,
            'genome_data': self.genome_data,
            'source_code': self.source_code,
            'ast_data': self.ast_data,
            'code_length': self.code_length,
            'complexity_score': self.complexity_score,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'evaluated_at': self.evaluated_at.isoformat() if self.evaluated_at else None,
            'metadata': self.individual_metadata
        }

class Fitness(Base):
    """适应度表"""
    __tablename__ = 'fitness'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    individual_id = Column(String(36), ForeignKey('individuals.id'), nullable=False)
    
    # 适应度指标
    objective_name = Column(String(50), nullable=False)  # 目标名称
    value = Column(Float, nullable=False)  # 适应度值
    normalized_value = Column(Float)  # 归一化值
    
    # 测量信息
    measurement_count = Column(Integer, default=1)  # 测量次数
    variance = Column(Float)  # 方差
    confidence_interval = Column(JSON)  # 置信区间
    
    # 时间信息
    measured_at = Column(DateTime, default=datetime.utcnow)
    
    # 元数据
    fitness_metadata = Column(JSON)
    
    # 关系
    individual = relationship('Individual', back_populates='fitness_records')
    
    # 索引
    __table_args__ = (
        Index('idx_fitness_individual', 'individual_id'),
        Index('idx_fitness_objective', 'objective_name'),
        Index('idx_fitness_value', 'objective_name', 'value'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'individual_id': self.individual_id,
            'objective_name': self.objective_name,
            'value': self.value,
            'normalized_value': self.normalized_value,
            'measurement_count': self.measurement_count,
            'variance': self.variance,
            'confidence_interval': self.confidence_interval,
            'measured_at': self.measured_at.isoformat() if self.measured_at else None,
            'metadata': self.fitness_metadata
        }

class TestResult(Base):
    """测试结果表"""
    __tablename__ = 'test_results'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    individual_id = Column(String(36), ForeignKey('individuals.id'), nullable=False)
    
    # 测试信息
    test_name = Column(String(255), nullable=False)
    test_type = Column(String(50))  # unit, property, benchmark
    
    # 结果
    passed = Column(Boolean, nullable=False)
    execution_time = Column(Float)  # 执行时间（秒）
    memory_usage = Column(Integer)  # 内存使用（字节）
    
    # 详细信息
    output = Column(Text)  # 输出
    error_message = Column(Text)  # 错误信息
    stack_trace = Column(Text)  # 堆栈跟踪
    
    # 覆盖率信息
    coverage_data = Column(JSON)  # 覆盖率数据
    
    # 时间信息
    executed_at = Column(DateTime, default=datetime.utcnow)
    
    # 元数据
    test_metadata = Column(JSON)
    
    # 关系
    individual = relationship('Individual', back_populates='test_results')
    
    # 索引
    __table_args__ = (
        Index('idx_test_individual', 'individual_id'),
        Index('idx_test_name', 'test_name'),
        Index('idx_test_passed', 'passed'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'individual_id': self.individual_id,
            'test_name': self.test_name,
            'test_type': self.test_type,
            'passed': self.passed,
            'execution_time': self.execution_time,
            'memory_usage': self.memory_usage,
            'output': self.output,
            'error_message': self.error_message,
            'stack_trace': self.stack_trace,
            'coverage_data': self.coverage_data,
            'executed_at': self.executed_at.isoformat() if self.executed_at else None,
            'metadata': self.test_metadata
        }

class Artifact(Base):
    """工件表"""
    __tablename__ = 'artifacts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(36), ForeignKey('tasks.id'), nullable=False)
    individual_id = Column(String(36), ForeignKey('individuals.id'), nullable=True)
    
    # 工件信息
    name = Column(String(255), nullable=False)
    artifact_type = Column(String(50), nullable=False)  # code, report, log, config
    file_path = Column(String(500))  # 文件路径
    
    # 内容
    content = Column(LargeBinary)  # 二进制内容
    content_text = Column(Text)  # 文本内容
    content_json = Column(JSON)  # JSON内容
    
    # 文件信息
    file_size = Column(Integer)  # 文件大小
    mime_type = Column(String(100))  # MIME类型
    checksum = Column(String(64))  # 校验和
    
    # 时间信息
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 元数据
    artifact_metadata = Column(JSON)
    
    # 关系
    task = relationship('Task', back_populates='artifacts')
    
    # 索引
    __table_args__ = (
        Index('idx_artifact_task', 'task_id'),
        Index('idx_artifact_individual', 'individual_id'),
        Index('idx_artifact_type', 'artifact_type'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'task_id': self.task_id,
            'individual_id': self.individual_id,
            'name': self.name,
            'artifact_type': self.artifact_type,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'mime_type': self.mime_type,
            'checksum': self.checksum,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'metadata': self.artifact_metadata
        }

# 辅助函数
def create_tables(engine):
    """创建所有表"""
    Base.metadata.create_all(engine)

def drop_tables(engine):
    """删除所有表"""
    Base.metadata.drop_all(engine)