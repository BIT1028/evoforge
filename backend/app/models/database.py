"""EvoForge数据库管理器

提供数据库连接管理和数据访问层功能:
- 数据库连接池管理
- 会话管理
- 数据访问对象(DAO)
- 事务管理
"""

import logging
from contextlib import contextmanager
from typing import List, Optional, Dict, Any, Generator
from datetime import datetime
import uuid

from sqlalchemy import create_engine, and_, or_, desc, asc
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from .models import (
    Base, Task, Generation, Individual, Fitness, TestResult, Artifact,
    create_tables, drop_tables
)

logger = logging.getLogger(__name__)

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, database_url: str = "sqlite:///evoforge.db", echo: bool = False):
        """初始化数据库管理器
        
        Args:
            database_url: 数据库连接URL
            echo: 是否输出SQL语句
        """
        self.database_url = database_url
        self.engine = create_engine(database_url, echo=echo)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # 创建表
        self.create_tables()
        
        logger.info(f"数据库管理器初始化完成: {database_url}")
    
    def create_tables(self):
        """创建数据库表"""
        try:
            create_tables(self.engine)
            logger.info("数据库表创建成功")
        except Exception as e:
            logger.error(f"创建数据库表失败: {e}")
            raise
    
    def drop_tables(self):
        """删除数据库表"""
        try:
            drop_tables(self.engine)
            logger.info("数据库表删除成功")
        except Exception as e:
            logger.error(f"删除数据库表失败: {e}")
            raise
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """获取数据库会话"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"数据库操作失败: {e}")
            raise
        finally:
            session.close()
    
    # 任务相关操作
    def create_task(self, task_data: Dict[str, Any]) -> Task:
        """创建任务"""
        with self.get_session() as session:
            task = Task(
                id=task_data.get('id', str(uuid.uuid4())),
                name=task_data['name'],
                description=task_data.get('description', ''),
                function_signature=task_data['function_signature'],
                test_cases=task_data['test_cases'],
                objectives=task_data.get('objectives', ['correctness', 'performance']),
                population_size=task_data.get('population_size', 50),
                max_generations=task_data.get('max_generations', 100),
                mutation_rate=task_data.get('mutation_rate', 0.1),
                crossover_rate=task_data.get('crossover_rate', 0.8),
                timeout_seconds=task_data.get('timeout_seconds', 300),
                memory_limit_mb=task_data.get('memory_limit_mb', 128),
                cpu_quota=task_data.get('cpu_quota', 100000),
                config=task_data.get('config', {}),
                metadata=task_data.get('metadata', {})
            )
            session.add(task)
            session.flush()
            return task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        with self.get_session() as session:
            return session.query(Task).filter(Task.id == task_id).first()
    
    def get_tasks(self, status: Optional[str] = None, limit: int = 100) -> List[Task]:
        """获取任务列表"""
        with self.get_session() as session:
            query = session.query(Task)
            if status:
                query = query.filter(Task.status == status)
            return query.order_by(desc(Task.created_at)).limit(limit).all()
    
    def update_task_status(self, task_id: str, status: str, **kwargs) -> bool:
        """更新任务状态"""
        with self.get_session() as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            if not task:
                return False
            
            task.status = status
            
            # 更新时间戳
            if status == 'running' and 'started_at' not in kwargs:
                task.started_at = datetime.utcnow()
            elif status in ['completed', 'failed', 'stopped'] and 'completed_at' not in kwargs:
                task.completed_at = datetime.utcnow()
            
            # 更新其他字段
            for key, value in kwargs.items():
                if hasattr(task, key):
                    setattr(task, key, value)
            
            return True
    
    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        with self.get_session() as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            if not task:
                return False
            session.delete(task)
            return True
    
    # 代相关操作
    def create_generation(self, generation_data: Dict[str, Any]) -> Generation:
        """创建代"""
        with self.get_session() as session:
            generation = Generation(
                task_id=generation_data['task_id'],
                generation_number=generation_data['generation_number'],
                population_size=generation_data['population_size'],
                best_fitness=generation_data.get('best_fitness'),
                average_fitness=generation_data.get('average_fitness'),
                worst_fitness=generation_data.get('worst_fitness'),
                diversity_score=generation_data.get('diversity_score'),
                started_at=generation_data.get('started_at', datetime.utcnow()),
                metadata=generation_data.get('metadata', {})
            )
            session.add(generation)
            session.flush()
            return generation
    
    def get_generations(self, task_id: str) -> List[Generation]:
        """获取任务的所有代"""
        with self.get_session() as session:
            return session.query(Generation).filter(
                Generation.task_id == task_id
            ).order_by(Generation.generation_number).all()
    
    def update_generation(self, generation_id: int, **kwargs) -> bool:
        """更新代信息"""
        with self.get_session() as session:
            generation = session.query(Generation).filter(Generation.id == generation_id).first()
            if not generation:
                return False
            
            for key, value in kwargs.items():
                if hasattr(generation, key):
                    setattr(generation, key, value)
            
            return True
    
    # 个体相关操作
    def create_individual(self, individual_data: Dict[str, Any]) -> Individual:
        """创建个体"""
        with self.get_session() as session:
            individual = Individual(
                id=individual_data.get('id', str(uuid.uuid4())),
                task_id=individual_data['task_id'],
                generation_id=individual_data['generation_id'],
                generation_number=individual_data['generation_number'],
                individual_number=individual_data['individual_number'],
                parent_ids=individual_data.get('parent_ids', []),
                genome_data=individual_data.get('genome_data'),
                source_code=individual_data['source_code'],
                ast_data=individual_data.get('ast_data'),
                code_length=individual_data.get('code_length'),
                complexity_score=individual_data.get('complexity_score'),
                metadata=individual_data.get('metadata', {})
            )
            session.add(individual)
            session.flush()
            return individual
    
    def get_individual(self, individual_id: str) -> Optional[Individual]:
        """获取个体"""
        with self.get_session() as session:
            return session.query(Individual).filter(Individual.id == individual_id).first()
    
    def get_individuals(self, task_id: str, generation_number: Optional[int] = None) -> List[Individual]:
        """获取个体列表"""
        with self.get_session() as session:
            query = session.query(Individual).filter(Individual.task_id == task_id)
            if generation_number is not None:
                query = query.filter(Individual.generation_number == generation_number)
            return query.order_by(Individual.generation_number, Individual.individual_number).all()
    
    def get_best_individuals(self, task_id: str, objective: str = 'correctness', limit: int = 10) -> List[Individual]:
        """获取最佳个体"""
        with self.get_session() as session:
            # 通过适应度表查询最佳个体
            query = session.query(Individual).join(Fitness).filter(
                and_(
                    Individual.task_id == task_id,
                    Fitness.objective_name == objective
                )
            ).order_by(desc(Fitness.value)).limit(limit)
            return query.all()
    
    # 适应度相关操作
    def create_fitness(self, fitness_data: Dict[str, Any]) -> Fitness:
        """创建适应度记录"""
        with self.get_session() as session:
            fitness = Fitness(
                individual_id=fitness_data['individual_id'],
                objective_name=fitness_data['objective_name'],
                value=fitness_data['value'],
                normalized_value=fitness_data.get('normalized_value'),
                measurement_count=fitness_data.get('measurement_count', 1),
                variance=fitness_data.get('variance'),
                confidence_interval=fitness_data.get('confidence_interval'),
                metadata=fitness_data.get('metadata', {})
            )
            session.add(fitness)
            session.flush()
            return fitness
    
    def get_fitness(self, individual_id: str) -> List[Fitness]:
        """获取个体的适应度"""
        with self.get_session() as session:
            return session.query(Fitness).filter(Fitness.individual_id == individual_id).all()
    
    def get_fitness_stats(self, task_id: str, objective: str) -> Dict[str, float]:
        """获取适应度统计信息"""
        with self.get_session() as session:
            from sqlalchemy import func
            
            result = session.query(
                func.max(Fitness.value).label('max_value'),
                func.min(Fitness.value).label('min_value'),
                func.avg(Fitness.value).label('avg_value'),
                func.count(Fitness.value).label('count')
            ).join(Individual).filter(
                and_(
                    Individual.task_id == task_id,
                    Fitness.objective_name == objective
                )
            ).first()
            
            return {
                'max': float(result.max_value) if result.max_value else 0.0,
                'min': float(result.min_value) if result.min_value else 0.0,
                'avg': float(result.avg_value) if result.avg_value else 0.0,
                'count': int(result.count) if result.count else 0
            }
    
    # 测试结果相关操作
    def create_test_result(self, test_data: Dict[str, Any]) -> TestResult:
        """创建测试结果"""
        with self.get_session() as session:
            test_result = TestResult(
                individual_id=test_data['individual_id'],
                test_name=test_data['test_name'],
                test_type=test_data.get('test_type', 'unit'),
                passed=test_data['passed'],
                execution_time=test_data.get('execution_time'),
                memory_usage=test_data.get('memory_usage'),
                output=test_data.get('output'),
                error_message=test_data.get('error_message'),
                stack_trace=test_data.get('stack_trace'),
                coverage_data=test_data.get('coverage_data'),
                metadata=test_data.get('metadata', {})
            )
            session.add(test_result)
            session.flush()
            return test_result
    
    def get_test_results(self, individual_id: str) -> List[TestResult]:
        """获取个体的测试结果"""
        with self.get_session() as session:
            return session.query(TestResult).filter(TestResult.individual_id == individual_id).all()
    
    # 工件相关操作
    def create_artifact(self, artifact_data: Dict[str, Any]) -> Artifact:
        """创建工件"""
        with self.get_session() as session:
            artifact = Artifact(
                task_id=artifact_data['task_id'],
                individual_id=artifact_data.get('individual_id'),
                name=artifact_data['name'],
                artifact_type=artifact_data['artifact_type'],
                file_path=artifact_data.get('file_path'),
                content=artifact_data.get('content'),
                content_text=artifact_data.get('content_text'),
                content_json=artifact_data.get('content_json'),
                file_size=artifact_data.get('file_size'),
                mime_type=artifact_data.get('mime_type'),
                checksum=artifact_data.get('checksum'),
                metadata=artifact_data.get('metadata', {})
            )
            session.add(artifact)
            session.flush()
            return artifact
    
    def get_artifacts(self, task_id: str, artifact_type: Optional[str] = None) -> List[Artifact]:
        """获取工件列表"""
        with self.get_session() as session:
            query = session.query(Artifact).filter(Artifact.task_id == task_id)
            if artifact_type:
                query = query.filter(Artifact.artifact_type == artifact_type)
            return query.order_by(desc(Artifact.created_at)).all()
    
    # 统计和分析
    def get_task_statistics(self, task_id: str) -> Dict[str, Any]:
        """获取任务统计信息"""
        with self.get_session() as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            if not task:
                return {}
            
            # 基本统计
            generation_count = session.query(Generation).filter(Generation.task_id == task_id).count()
            individual_count = session.query(Individual).filter(Individual.task_id == task_id).count()
            
            # 适应度统计
            fitness_stats = {}
            for objective in task.objectives:
                fitness_stats[objective] = self.get_fitness_stats(task_id, objective)
            
            return {
                'task_id': task_id,
                'status': task.status,
                'generation_count': generation_count,
                'individual_count': individual_count,
                'fitness_statistics': fitness_stats,
                'created_at': task.created_at,
                'started_at': task.started_at,
                'completed_at': task.completed_at
            }
    
    def cleanup_old_data(self, days: int = 30) -> int:
        """清理旧数据"""
        from datetime import timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        with self.get_session() as session:
            # 删除旧的已完成任务
            deleted_count = session.query(Task).filter(
                and_(
                    Task.status.in_(['completed', 'failed']),
                    Task.completed_at < cutoff_date
                )
            ).delete()
            
            logger.info(f"清理了 {deleted_count} 个旧任务")
            return deleted_count

# 全局数据库管理器实例
_db_manager: Optional[DatabaseManager] = None

def get_database_manager(database_url: str = "sqlite:///evoforge.db") -> DatabaseManager:
    """获取全局数据库管理器实例"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager(database_url)
    return _db_manager

def init_database(database_url: str = "sqlite:///evoforge.db", echo: bool = False) -> DatabaseManager:
    """初始化数据库"""
    global _db_manager
    _db_manager = DatabaseManager(database_url, echo)
    return _db_manager