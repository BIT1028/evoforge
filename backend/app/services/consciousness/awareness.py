#!/usr/bin/env python3
"""
意识服务 - 自我感知与反思模块
"""
import asyncio
import time
from typing import Dict, List, Optional, Any
import structlog
from datetime import datetime, timedelta

from app.core.database import SessionLocal
from app.models.digital_cell import DigitalCell
from app.models.generation import Generation
from app.models.evaluation import EvaluationLog
from app.core.websocket import WebSocketManager

logger = structlog.get_logger()

class ConsciousnessService:
    """意识服务 - 负责系统的自我感知和反思"""
    
    def __init__(self, websocket_manager: WebSocketManager):
        self.websocket_manager = websocket_manager
        self.awareness_data = {
            "system_state": "idle",
            "current_generation": 0,
            "total_cells_created": 0,
            "best_fitness_ever": 0.0,
            "evolution_insights": [],
            "performance_trends": [],
            "last_reflection_time": None
        }
        self.reflection_interval = 300  # 5分钟反思一次
        self.running = False
    
    async def start_consciousness_loop(self):
        """启动意识循环"""
        self.running = True
        logger.info("意识服务启动")
        
        while self.running:
            try:
                await self.perform_reflection()
                await self.update_awareness()
                await self.broadcast_consciousness_state()
                
                # 等待下一次反思
                await asyncio.sleep(self.reflection_interval)
                
            except Exception as e:
                logger.error("意识循环异常", error=str(e))
                await asyncio.sleep(30)  # 异常时短暂等待
    
    async def stop_consciousness_loop(self):
        """停止意识循环"""
        self.running = False
        logger.info("意识服务停止")
    
    async def perform_reflection(self):
        """执行自我反思"""
        try:
            db = SessionLocal()
            
            # 获取最近的进化数据
            recent_generations = db.query(Generation).order_by(
                Generation.generation_number.desc()
            ).limit(10).all()
            
            if not recent_generations:
                return
            
            # 分析进化趋势
            insights = await self._analyze_evolution_trends(recent_generations, db)
            
            # 更新意识数据
            self.awareness_data["evolution_insights"] = insights
            self.awareness_data["last_reflection_time"] = datetime.now().isoformat()
            
            # 记录反思结果
            logger.info("完成自我反思", insights_count=len(insights))
            
            db.close()
            
        except Exception as e:
            logger.error("自我反思失败", error=str(e))
    
    async def _analyze_evolution_trends(self, generations: List[Generation], db) -> List[Dict[str, Any]]:
        """分析进化趋势"""
        insights = []
        
        if len(generations) < 2:
            return insights
        
        # 分析适应度趋势
        fitness_trend = self._analyze_fitness_trend(generations)
        if fitness_trend:
            insights.append(fitness_trend)
        
        # 分析多样性趋势
        diversity_trend = await self._analyze_diversity_trend(generations, db)
        if diversity_trend:
            insights.append(diversity_trend)
        
        # 分析停滞检测
        stagnation_analysis = self._detect_stagnation(generations)
        if stagnation_analysis:
            insights.append(stagnation_analysis)
        
        # 分析创新模式
        innovation_analysis = await self._analyze_innovation_patterns(generations, db)
        if innovation_analysis:
            insights.append(innovation_analysis)
        
        return insights
    
    def _analyze_fitness_trend(self, generations: List[Generation]) -> Optional[Dict[str, Any]]:
        """分析适应度趋势"""
        try:
            recent_avg = [g.average_fitness for g in generations[:5]]
            older_avg = [g.average_fitness for g in generations[5:]]
            
            if not older_avg:
                return None
            
            recent_mean = sum(recent_avg) / len(recent_avg)
            older_mean = sum(older_avg) / len(older_avg)
            
            improvement_rate = (recent_mean - older_mean) / older_mean * 100
            
            if improvement_rate > 5:
                trend = "improving"
                message = f"适应度持续改善，提升率: {improvement_rate:.1f}%"
            elif improvement_rate < -5:
                trend = "declining"
                message = f"适应度出现下降，下降率: {abs(improvement_rate):.1f}%"
            else:
                trend = "stable"
                message = f"适应度保持稳定，变化率: {improvement_rate:.1f}%"
            
            return {
                "type": "fitness_trend",
                "trend": trend,
                "message": message,
                "improvement_rate": improvement_rate,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error("适应度趋势分析失败", error=str(e))
            return None
    
    async def _analyze_diversity_trend(self, generations: List[Generation], db) -> Optional[Dict[str, Any]]:
        """分析种群多样性趋势"""
        try:
            # 计算最近几代的基因多样性
            diversity_scores = []
            
            for gen in generations[:5]:
                cells = db.query(DigitalCell).filter(
                    DigitalCell.generation_id == gen.id
                ).all()
                
                if len(cells) > 1:
                    # 简单的多样性度量：基因序列的唯一性
                    unique_genes = len(set(cell.gene_sequence for cell in cells))
                    diversity = unique_genes / len(cells)
                    diversity_scores.append(diversity)
            
            if len(diversity_scores) < 2:
                return None
            
            avg_diversity = sum(diversity_scores) / len(diversity_scores)
            
            if avg_diversity > 0.8:
                status = "high"
                message = f"种群多样性良好 ({avg_diversity:.2f})，有利于探索新解"
            elif avg_diversity > 0.5:
                status = "medium"
                message = f"种群多样性中等 ({avg_diversity:.2f})，需要平衡探索与利用"
            else:
                status = "low"
                message = f"种群多样性较低 ({avg_diversity:.2f})，可能陷入局部最优"
            
            return {
                "type": "diversity_trend",
                "status": status,
                "message": message,
                "diversity_score": avg_diversity,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error("多样性趋势分析失败", error=str(e))
            return None
    
    def _detect_stagnation(self, generations: List[Generation]) -> Optional[Dict[str, Any]]:
        """检测进化停滞"""
        try:
            if len(generations) < 5:
                return None
            
            # 检查最近5代的最高适应度变化
            recent_best = [g.max_fitness for g in generations[:5]]
            
            # 计算变化幅度
            max_fitness = max(recent_best)
            min_fitness = min(recent_best)
            variation = (max_fitness - min_fitness) / max_fitness if max_fitness > 0 else 0
            
            if variation < 0.01:  # 变化小于1%
                return {
                    "type": "stagnation_detection",
                    "status": "stagnant",
                    "message": f"检测到进化停滞，最近5代适应度变化仅{variation*100:.2f}%",
                    "variation": variation,
                    "recommendation": "建议增加变异率或引入新的遗传操作",
                    "timestamp": datetime.now().isoformat()
                }
            
            return None
            
        except Exception as e:
            logger.error("停滞检测失败", error=str(e))
            return None
    
    async def _analyze_innovation_patterns(self, generations: List[Generation], db) -> Optional[Dict[str, Any]]:
        """分析创新模式"""
        try:
            # 分析最近几代中的高分个体
            innovation_count = 0
            total_evaluated = 0
            
            for gen in generations[:3]:
                cells = db.query(DigitalCell).filter(
                    DigitalCell.generation_id == gen.id,
                    DigitalCell.fitness_score > gen.average_fitness * 1.2  # 超过平均20%
                ).all()
                
                innovation_count += len(cells)
                
                total_cells = db.query(DigitalCell).filter(
                    DigitalCell.generation_id == gen.id
                ).count()
                
                total_evaluated += total_cells
            
            if total_evaluated == 0:
                return None
            
            innovation_rate = innovation_count / total_evaluated
            
            if innovation_rate > 0.1:
                status = "high"
                message = f"创新活跃，{innovation_rate*100:.1f}%的个体表现优异"
            elif innovation_rate > 0.05:
                status = "medium"
                message = f"创新适中，{innovation_rate*100:.1f}%的个体表现优异"
            else:
                status = "low"
                message = f"创新较少，仅{innovation_rate*100:.1f}%的个体表现优异"
            
            return {
                "type": "innovation_analysis",
                "status": status,
                "message": message,
                "innovation_rate": innovation_rate,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error("创新模式分析失败", error=str(e))
            return None
    
    async def update_awareness(self):
        """更新系统感知状态"""
        try:
            db = SessionLocal()
            
            # 更新基本统计
            latest_generation = db.query(Generation).order_by(
                Generation.generation_number.desc()
            ).first()
            
            if latest_generation:
                self.awareness_data["current_generation"] = latest_generation.generation_number
                self.awareness_data["best_fitness_ever"] = max(
                    self.awareness_data["best_fitness_ever"],
                    latest_generation.max_fitness or 0
                )
            
            # 更新细胞总数
            total_cells = db.query(DigitalCell).count()
            self.awareness_data["total_cells_created"] = total_cells
            
            # 更新性能趋势
            await self._update_performance_trends(db)
            
            db.close()
            
        except Exception as e:
            logger.error("更新系统感知失败", error=str(e))
    
    async def _update_performance_trends(self, db):
        """更新性能趋势"""
        try:
            # 获取最近24小时的评估数据
            since_time = datetime.now() - timedelta(hours=24)
            
            recent_evaluations = db.query(EvaluationLog).filter(
                EvaluationLog.created_at >= since_time
            ).all()
            
            if recent_evaluations:
                avg_fitness = sum(e.fitness_score for e in recent_evaluations) / len(recent_evaluations)
                avg_cost = sum(e.api_cost for e in recent_evaluations) / len(recent_evaluations)
                avg_time = sum(e.execution_time for e in recent_evaluations) / len(recent_evaluations)
                
                trend_data = {
                    "timestamp": datetime.now().isoformat(),
                    "average_fitness": avg_fitness,
                    "average_cost": avg_cost,
                    "average_execution_time": avg_time,
                    "evaluation_count": len(recent_evaluations)
                }
                
                # 保持最近10个数据点
                self.awareness_data["performance_trends"].append(trend_data)
                if len(self.awareness_data["performance_trends"]) > 10:
                    self.awareness_data["performance_trends"].pop(0)
            
        except Exception as e:
            logger.error("更新性能趋势失败", error=str(e))
    
    async def broadcast_consciousness_state(self):
        """广播意识状态"""
        try:
            consciousness_message = {
                "type": "consciousness_update",
                "data": self.awareness_data,
                "timestamp": datetime.now().isoformat()
            }
            
            await self.websocket_manager.broadcast_to_room(
                "evolution",
                consciousness_message
            )
            
        except Exception as e:
            logger.error("广播意识状态失败", error=str(e))
    
    def get_consciousness_state(self) -> Dict[str, Any]:
        """获取当前意识状态"""
        return self.awareness_data.copy()
    
    async def process_external_stimulus(self, stimulus_type: str, data: Dict[str, Any]):
        """处理外部刺激"""
        try:
            if stimulus_type == "evolution_start":
                self.awareness_data["system_state"] = "evolving"
                logger.info("意识感知：进化开始")
                
            elif stimulus_type == "evolution_stop":
                self.awareness_data["system_state"] = "idle"
                logger.info("意识感知：进化停止")
                
            elif stimulus_type == "generation_complete":
                generation_number = data.get("generation_number", 0)
                best_fitness = data.get("best_fitness", 0)
                
                # 立即反思这一代的表现
                await self._reflect_on_generation(generation_number, best_fitness)
                
            elif stimulus_type == "exceptional_performance":
                # 记录异常表现
                insight = {
                    "type": "exceptional_performance",
                    "message": data.get("message", "检测到异常表现"),
                    "details": data,
                    "timestamp": datetime.now().isoformat()
                }
                self.awareness_data["evolution_insights"].append(insight)
                
                # 保持最近20个洞察
                if len(self.awareness_data["evolution_insights"]) > 20:
                    self.awareness_data["evolution_insights"].pop(0)
            
            # 广播更新
            await self.broadcast_consciousness_state()
            
        except Exception as e:
            logger.error("处理外部刺激失败", error=str(e))
    
    async def _reflect_on_generation(self, generation_number: int, best_fitness: float):
        """对特定代数进行反思"""
        try:
            # 与历史最佳比较
            if best_fitness > self.awareness_data["best_fitness_ever"]:
                improvement = best_fitness - self.awareness_data["best_fitness_ever"]
                insight = {
                    "type": "breakthrough",
                    "message": f"第{generation_number}代创造新纪录！适应度提升{improvement:.2f}",
                    "generation": generation_number,
                    "fitness": best_fitness,
                    "timestamp": datetime.now().isoformat()
                }
                self.awareness_data["evolution_insights"].append(insight)
                logger.info("意识感知：突破性进展", generation=generation_number, fitness=best_fitness)
            
        except Exception as e:
            logger.error("代数反思失败", error=str(e))