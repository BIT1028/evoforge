"""智能行为模块 - 实现程序的智能决策和行为涌现

本模块实现了智能行为的核心机制:
- IntelligentAgent: 智能代理，整合感知、决策、行动
- BehaviorPattern: 行为模式，学习和存储成功的行为序列
- DecisionMaking: 决策系统，基于多因素进行智能决策
- LearningSystem: 学习系统，从经验中学习和改进
- AdaptationEngine: 适应引擎，动态调整行为策略
- EmergentBehavior: 涌现行为，发现新的行为模式
"""

import logging
import random
import time
import json
import math
import copy
from typing import Dict, List, Any, Optional, Tuple, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import uuid
import numpy as np
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

class BehaviorType(Enum):
    """行为类型枚举"""
    EXPLORATION = "exploration"  # 探索行为
    EXPLOITATION = "exploitation"  # 利用行为
    LEARNING = "learning"  # 学习行为
    ADAPTATION = "adaptation"  # 适应行为
    COOPERATION = "cooperation"  # 合作行为
    COMPETITION = "competition"  # 竞争行为
    INNOVATION = "innovation"  # 创新行为
    OPTIMIZATION = "optimization"  # 优化行为
    SURVIVAL = "survival"  # 生存行为
    SOCIAL = "social"  # 社交行为

class DecisionContext(Enum):
    """决策上下文枚举"""
    NORMAL = "normal"  # 正常情况
    CRISIS = "crisis"  # 危机情况
    OPPORTUNITY = "opportunity"  # 机会情况
    UNCERTAINTY = "uncertainty"  # 不确定情况
    RESOURCE_SCARCITY = "resource_scarcity"  # 资源稀缺
    COMPETITION = "competition"  # 竞争环境
    COLLABORATION = "collaboration"  # 合作环境

class LearningMode(Enum):
    """学习模式枚举"""
    SUPERVISED = "supervised"  # 监督学习
    UNSUPERVISED = "unsupervised"  # 无监督学习
    REINFORCEMENT = "reinforcement"  # 强化学习
    IMITATION = "imitation"  # 模仿学习
    DISCOVERY = "discovery"  # 发现学习
    TRANSFER = "transfer"  # 迁移学习

@dataclass
class Action:
    """行动定义
    
    表示智能代理可以执行的具体行动。
    """
    id: str
    action_type: str
    parameters: Dict[str, Any]
    expected_outcome: Dict[str, float]
    cost: float = 0.0
    risk: float = 0.0
    confidence: float = 0.5
    prerequisites: List[str] = field(default_factory=list)
    
    def execute(self, environment: Dict[str, Any]) -> Dict[str, Any]:
        """执行行动"""
        # 检查前提条件
        for prereq in self.prerequisites:
            if not environment.get(prereq, False):
                return {
                    'success': False,
                    'reason': f'前提条件不满足: {prereq}',
                    'outcome': {}
                }
        
        # 模拟行动执行
        success_probability = self.confidence * (1 - self.risk)
        success = random.random() < success_probability
        
        if success:
            # 成功执行，返回预期结果的变体
            actual_outcome = {}
            for key, expected_value in self.expected_outcome.items():
                # 添加一些随机性
                noise = random.gauss(0, 0.1)
                actual_outcome[key] = max(0, expected_value + noise)
            
            return {
                'success': True,
                'outcome': actual_outcome,
                'cost': self.cost
            }
        else:
            # 执行失败
            return {
                'success': False,
                'reason': '行动执行失败',
                'outcome': {},
                'cost': self.cost * 0.5  # 失败时成本减半
            }

@dataclass
class BehaviorPattern:
    """行为模式
    
    表示一系列相关行动的组合，形成特定的行为模式。
    """
    id: str
    pattern_type: BehaviorType
    action_sequence: List[str]  # 行动ID序列
    trigger_conditions: Dict[str, Any]  # 触发条件
    success_rate: float = 0.0
    usage_count: int = 0
    effectiveness_score: float = 0.0
    adaptation_history: List[Dict[str, Any]] = field(default_factory=list)
    creation_time: datetime = field(default_factory=datetime.now)
    
    def matches_context(self, context: Dict[str, Any]) -> float:
        """检查是否匹配当前上下文"""
        match_score = 0.0
        total_conditions = len(self.trigger_conditions)
        
        if total_conditions == 0:
            return 0.5  # 无条件时返回中等匹配度
        
        for condition, expected_value in self.trigger_conditions.items():
            if condition in context:
                actual_value = context[condition]
                
                if isinstance(expected_value, (int, float)):
                    # 数值比较
                    if isinstance(actual_value, (int, float)):
                        diff = abs(actual_value - expected_value)
                        similarity = max(0, 1 - diff)
                        match_score += similarity
                elif isinstance(expected_value, str):
                    # 字符串比较
                    if actual_value == expected_value:
                        match_score += 1.0
                elif isinstance(expected_value, bool):
                    # 布尔比较
                    if actual_value == expected_value:
                        match_score += 1.0
        
        return match_score / total_conditions
    
    def update_effectiveness(self, outcome: Dict[str, Any]):
        """更新效果评分"""
        self.usage_count += 1
        
        # 计算本次效果分数
        if outcome.get('success', False):
            outcome_score = sum(outcome.get('outcome', {}).values()) / max(len(outcome.get('outcome', {})), 1)
            cost_penalty = outcome.get('cost', 0) * 0.1
            current_score = max(0, outcome_score - cost_penalty)
        else:
            current_score = 0.0
        
        # 更新成功率
        if outcome.get('success', False):
            self.success_rate = (self.success_rate * (self.usage_count - 1) + 1.0) / self.usage_count
        else:
            self.success_rate = (self.success_rate * (self.usage_count - 1)) / self.usage_count
        
        # 更新效果评分（指数移动平均）
        alpha = 0.1  # 学习率
        self.effectiveness_score = (1 - alpha) * self.effectiveness_score + alpha * current_score
        
        # 记录适应历史
        self.adaptation_history.append({
            'timestamp': datetime.now().isoformat(),
            'outcome': outcome,
            'effectiveness_score': self.effectiveness_score,
            'success_rate': self.success_rate
        })
        
        # 保持历史记录在合理范围内
        if len(self.adaptation_history) > 100:
            self.adaptation_history = self.adaptation_history[-100:]
        
        logger.debug(f"[BEHAVIOR_DEBUG] 行为模式 {self.id} 效果更新: {self.effectiveness_score:.3f}")

class DecisionMaking:
    """决策系统
    
    基于多因素分析进行智能决策。
    """
    
    def __init__(self):
        """初始化决策系统"""
        self.decision_history: List[Dict[str, Any]] = []
        self.decision_weights = {
            'expected_benefit': 0.3,
            'success_probability': 0.25,
            'cost_efficiency': 0.2,
            'risk_tolerance': 0.15,
            'strategic_alignment': 0.1
        }
        
        logger.debug(f"[DECISION_DEBUG] 初始化决策系统")
    
    def make_decision(self, available_actions: List[Action], 
                     current_context: Dict[str, Any],
                     goals: List[Dict[str, Any]]) -> Optional[Action]:
        """进行决策"""
        if not available_actions:
            return None
        
        logger.debug(f"[DECISION_DEBUG] 开始决策，可选行动数: {len(available_actions)}")
        
        # 评估每个行动
        action_scores = []
        for action in available_actions:
            score = self._evaluate_action(action, current_context, goals)
            action_scores.append((action, score))
        
        # 按分数排序
        action_scores.sort(key=lambda x: x[1], reverse=True)
        
        # 选择最佳行动
        best_action, best_score = action_scores[0]
        
        # 记录决策
        decision_record = {
            'timestamp': datetime.now().isoformat(),
            'context': current_context,
            'available_actions': len(available_actions),
            'selected_action': best_action.id,
            'decision_score': best_score,
            'reasoning': self._generate_decision_reasoning(best_action, current_context, goals)
        }
        
        self.decision_history.append(decision_record)
        
        logger.debug(f"[DECISION_DEBUG] 选择行动: {best_action.id}, 评分: {best_score:.3f}")
        return best_action
    
    def _evaluate_action(self, action: Action, context: Dict[str, Any], 
                        goals: List[Dict[str, Any]]) -> float:
        """评估行动"""
        # 计算预期收益
        expected_benefit = sum(action.expected_outcome.values()) / max(len(action.expected_outcome), 1)
        
        # 计算成功概率
        success_probability = action.confidence * (1 - action.risk)
        
        # 计算成本效率
        cost_efficiency = expected_benefit / max(action.cost, 0.1) if action.cost > 0 else expected_benefit
        
        # 计算风险容忍度
        risk_tolerance = 1 - action.risk
        
        # 计算战略一致性
        strategic_alignment = self._calculate_strategic_alignment(action, goals)
        
        # 加权综合评分
        total_score = (
            expected_benefit * self.decision_weights['expected_benefit'] +
            success_probability * self.decision_weights['success_probability'] +
            cost_efficiency * self.decision_weights['cost_efficiency'] +
            risk_tolerance * self.decision_weights['risk_tolerance'] +
            strategic_alignment * self.decision_weights['strategic_alignment']
        )
        
        return total_score
    
    def _calculate_strategic_alignment(self, action: Action, goals: List[Dict[str, Any]]) -> float:
        """计算战略一致性"""
        if not goals:
            return 0.5
        
        alignment_scores = []
        
        for goal in goals:
            goal_metrics = goal.get('target_metrics', {})
            action_outcomes = action.expected_outcome
            
            # 计算行动结果与目标的匹配度
            matches = 0
            total_metrics = len(goal_metrics)
            
            for metric, target_value in goal_metrics.items():
                if metric in action_outcomes:
                    expected_value = action_outcomes[metric]
                    if target_value > 0:
                        match_score = min(1.0, expected_value / target_value)
                    else:
                        match_score = 1.0 if expected_value <= target_value else 0.0
                    matches += match_score
            
            if total_metrics > 0:
                goal_alignment = matches / total_metrics
                # 根据目标优先级加权
                priority = goal.get('priority', 0.5)
                alignment_scores.append(goal_alignment * priority)
        
        return sum(alignment_scores) / len(alignment_scores) if alignment_scores else 0.5
    
    def _generate_decision_reasoning(self, action: Action, context: Dict[str, Any], 
                                   goals: List[Dict[str, Any]]) -> str:
        """生成决策推理"""
        reasoning_parts = []
        
        # 分析预期收益
        expected_benefit = sum(action.expected_outcome.values()) / max(len(action.expected_outcome), 1)
        if expected_benefit > 0.7:
            reasoning_parts.append("预期收益高")
        elif expected_benefit < 0.3:
            reasoning_parts.append("预期收益较低")
        
        # 分析风险
        if action.risk < 0.2:
            reasoning_parts.append("风险较低")
        elif action.risk > 0.7:
            reasoning_parts.append("风险较高")
        
        # 分析成本
        if action.cost < 0.3:
            reasoning_parts.append("成本较低")
        elif action.cost > 0.7:
            reasoning_parts.append("成本较高")
        
        # 分析战略一致性
        strategic_alignment = self._calculate_strategic_alignment(action, goals)
        if strategic_alignment > 0.7:
            reasoning_parts.append("与目标高度一致")
        elif strategic_alignment < 0.3:
            reasoning_parts.append("与目标一致性较低")
        
        return "; ".join(reasoning_parts) if reasoning_parts else "综合考虑各因素"
    
    def update_decision_weights(self, feedback: Dict[str, float]):
        """根据反馈更新决策权重"""
        # 简单的权重调整机制
        learning_rate = 0.05
        
        for factor, performance in feedback.items():
            if factor in self.decision_weights:
                if performance > 0.7:  # 表现良好，增加权重
                    self.decision_weights[factor] *= (1 + learning_rate)
                elif performance < 0.3:  # 表现不佳，减少权重
                    self.decision_weights[factor] *= (1 - learning_rate)
        
        # 归一化权重
        total_weight = sum(self.decision_weights.values())
        for factor in self.decision_weights:
            self.decision_weights[factor] /= total_weight
        
        logger.debug(f"[DECISION_DEBUG] 决策权重已更新: {self.decision_weights}")

class LearningSystem:
    """学习系统
    
    从经验中学习，改进行为和决策。
    """
    
    def __init__(self):
        """初始化学习系统"""
        self.learning_history: List[Dict[str, Any]] = []
        self.knowledge_base: Dict[str, Any] = {
            'patterns': {},
            'rules': {},
            'associations': defaultdict(list)
        }
        self.learning_rate = 0.1
        
        logger.debug(f"[LEARNING_DEBUG] 初始化学习系统")
    
    def learn_from_experience(self, experience: Dict[str, Any], 
                            learning_mode: LearningMode = LearningMode.REINFORCEMENT) -> Dict[str, Any]:
        """从经验中学习"""
        logger.debug(f"[LEARNING_DEBUG] 开始学习，模式: {learning_mode.value}")
        
        learning_result = {
            'new_knowledge': [],
            'updated_patterns': [],
            'insights': []
        }
        
        if learning_mode == LearningMode.REINFORCEMENT:
            learning_result.update(self._reinforcement_learning(experience))
        elif learning_mode == LearningMode.UNSUPERVISED:
            learning_result.update(self._unsupervised_learning(experience))
        elif learning_mode == LearningMode.IMITATION:
            learning_result.update(self._imitation_learning(experience))
        elif learning_mode == LearningMode.DISCOVERY:
            learning_result.update(self._discovery_learning(experience))
        
        # 记录学习历史
        learning_record = {
            'timestamp': datetime.now().isoformat(),
            'learning_mode': learning_mode.value,
            'experience': experience,
            'learning_result': learning_result
        }
        
        self.learning_history.append(learning_record)
        
        logger.debug(f"[LEARNING_DEBUG] 学习完成，新知识: {len(learning_result['new_knowledge'])}")
        return learning_result
    
    def _reinforcement_learning(self, experience: Dict[str, Any]) -> Dict[str, Any]:
        """强化学习"""
        result = {'new_knowledge': [], 'updated_patterns': [], 'insights': []}
        
        action = experience.get('action')
        outcome = experience.get('outcome', {})
        reward = outcome.get('reward', 0.0)
        
        if action:
            # 更新行动价值
            action_id = action.get('id', 'unknown')
            if action_id not in self.knowledge_base['patterns']:
                self.knowledge_base['patterns'][action_id] = {
                    'value': 0.0,
                    'usage_count': 0,
                    'success_rate': 0.0
                }
            
            pattern = self.knowledge_base['patterns'][action_id]
            
            # 更新价值（Q-learning风格）
            old_value = pattern['value']
            pattern['value'] = old_value + self.learning_rate * (reward - old_value)
            pattern['usage_count'] += 1
            
            # 更新成功率
            if outcome.get('success', False):
                pattern['success_rate'] = (pattern['success_rate'] * (pattern['usage_count'] - 1) + 1.0) / pattern['usage_count']
            else:
                pattern['success_rate'] = (pattern['success_rate'] * (pattern['usage_count'] - 1)) / pattern['usage_count']
            
            result['updated_patterns'].append(action_id)
            
            # 生成洞察
            if pattern['usage_count'] > 10:
                if pattern['success_rate'] > 0.8:
                    result['insights'].append(f"行动 {action_id} 表现优秀，建议优先使用")
                elif pattern['success_rate'] < 0.3:
                    result['insights'].append(f"行动 {action_id} 表现不佳，建议避免使用")
        
        return result
    
    def _unsupervised_learning(self, experience: Dict[str, Any]) -> Dict[str, Any]:
        """无监督学习"""
        result = {'new_knowledge': [], 'updated_patterns': [], 'insights': []}
        
        # 寻找模式和关联
        context = experience.get('context', {})
        outcome = experience.get('outcome', {})
        
        # 发现上下文-结果关联
        for context_key, context_value in context.items():
            for outcome_key, outcome_value in outcome.items():
                association_key = f"{context_key}->{outcome_key}"
                
                self.knowledge_base['associations'][association_key].append({
                    'context_value': context_value,
                    'outcome_value': outcome_value,
                    'timestamp': datetime.now().isoformat()
                })
                
                # 保持关联记录在合理范围内
                if len(self.knowledge_base['associations'][association_key]) > 100:
                    self.knowledge_base['associations'][association_key] = \
                        self.knowledge_base['associations'][association_key][-100:]
                
                result['new_knowledge'].append(association_key)
        
        # 分析关联强度
        for association_key, records in self.knowledge_base['associations'].items():
            if len(records) >= 10:  # 有足够数据时分析
                correlation = self._calculate_correlation(records)
                if abs(correlation) > 0.7:
                    result['insights'].append(f"发现强关联: {association_key} (相关性: {correlation:.3f})")
        
        return result
    
    def _imitation_learning(self, experience: Dict[str, Any]) -> Dict[str, Any]:
        """模仿学习"""
        result = {'new_knowledge': [], 'updated_patterns': [], 'insights': []}
        
        # 从成功案例中学习
        if experience.get('outcome', {}).get('success', False):
            action_sequence = experience.get('action_sequence', [])
            context = experience.get('context', {})
            
            # 记录成功的行动序列
            sequence_key = f"success_sequence_{len(action_sequence)}"
            if sequence_key not in self.knowledge_base['patterns']:
                self.knowledge_base['patterns'][sequence_key] = []
            
            self.knowledge_base['patterns'][sequence_key].append({
                'sequence': action_sequence,
                'context': context,
                'outcome': experience.get('outcome', {}),
                'timestamp': datetime.now().isoformat()
            })
            
            result['new_knowledge'].append(sequence_key)
            result['insights'].append(f"学习到成功的行动序列: {len(action_sequence)} 步")
        
        return result
    
    def _discovery_learning(self, experience: Dict[str, Any]) -> Dict[str, Any]:
        """发现学习"""
        result = {'new_knowledge': [], 'updated_patterns': [], 'insights': []}
        
        # 寻找新的模式和规律
        outcome = experience.get('outcome', {})
        
        # 发现异常结果
        for key, value in outcome.items():
            if isinstance(value, (int, float)):
                # 检查是否是异常值
                historical_values = []
                for record in self.learning_history[-50:]:  # 最近50条记录
                    if key in record.get('experience', {}).get('outcome', {}):
                        historical_values.append(record['experience']['outcome'][key])
                
                if len(historical_values) >= 10:
                    mean_value = sum(historical_values) / len(historical_values)
                    if abs(value - mean_value) > 2 * np.std(historical_values):
                        result['insights'].append(f"发现异常结果: {key} = {value} (平均值: {mean_value:.3f})")
                        result['new_knowledge'].append(f"anomaly_{key}_{value}")
        
        return result
    
    def _calculate_correlation(self, records: List[Dict[str, Any]]) -> float:
        """计算相关性"""
        if len(records) < 2:
            return 0.0
        
        context_values = []
        outcome_values = []
        
        for record in records:
            context_val = record.get('context_value')
            outcome_val = record.get('outcome_value')
            
            if isinstance(context_val, (int, float)) and isinstance(outcome_val, (int, float)):
                context_values.append(context_val)
                outcome_values.append(outcome_val)
        
        if len(context_values) < 2:
            return 0.0
        
        # 计算皮尔逊相关系数
        try:
            correlation = np.corrcoef(context_values, outcome_values)[0, 1]
            return correlation if not np.isnan(correlation) else 0.0
        except:
            return 0.0
    
    def get_learned_patterns(self) -> Dict[str, Any]:
        """获取学习到的模式"""
        return copy.deepcopy(self.knowledge_base['patterns'])
    
    def get_associations(self) -> Dict[str, List[Dict[str, Any]]]:
        """获取发现的关联"""
        return dict(self.knowledge_base['associations'])

class AdaptationEngine:
    """适应引擎
    
    动态调整行为策略以适应环境变化。
    """
    
    def __init__(self, learning_system: LearningSystem):
        """初始化适应引擎"""
        self.learning_system = learning_system
        self.adaptation_history: List[Dict[str, Any]] = []
        self.current_strategy: Dict[str, Any] = {
            'exploration_rate': 0.3,
            'risk_tolerance': 0.5,
            'learning_rate': 0.1,
            'cooperation_tendency': 0.5
        }
        
        logger.debug(f"[ADAPTATION_DEBUG] 初始化适应引擎")
    
    def adapt_to_environment(self, environment_state: Dict[str, Any], 
                           performance_feedback: Dict[str, float]) -> Dict[str, Any]:
        """适应环境变化"""
        logger.debug(f"[ADAPTATION_DEBUG] 开始环境适应")
        
        adaptation_result = {
            'strategy_changes': {},
            'new_behaviors': [],
            'adaptation_insights': []
        }
        
        # 分析环境变化
        environment_analysis = self._analyze_environment_change(environment_state)
        
        # 分析性能反馈
        performance_analysis = self._analyze_performance_feedback(performance_feedback)
        
        # 调整策略
        strategy_changes = self._adjust_strategy(environment_analysis, performance_analysis)
        adaptation_result['strategy_changes'] = strategy_changes
        
        # 生成新行为
        new_behaviors = self._generate_adaptive_behaviors(environment_analysis)
        adaptation_result['new_behaviors'] = new_behaviors
        
        # 生成适应洞察
        insights = self._generate_adaptation_insights(environment_analysis, performance_analysis)
        adaptation_result['adaptation_insights'] = insights
        
        # 记录适应历史
        adaptation_record = {
            'timestamp': datetime.now().isoformat(),
            'environment_state': environment_state,
            'performance_feedback': performance_feedback,
            'adaptation_result': adaptation_result,
            'strategy_before': copy.deepcopy(self.current_strategy)
        }
        
        # 应用策略变化
        for key, value in strategy_changes.items():
            self.current_strategy[key] = value
        
        adaptation_record['strategy_after'] = copy.deepcopy(self.current_strategy)
        self.adaptation_history.append(adaptation_record)
        
        logger.debug(f"[ADAPTATION_DEBUG] 适应完成，策略变化: {len(strategy_changes)}")
        return adaptation_result
    
    def _analyze_environment_change(self, environment_state: Dict[str, Any]) -> Dict[str, Any]:
        """分析环境变化"""
        analysis = {
            'complexity_change': 0.0,
            'resource_change': 0.0,
            'competition_change': 0.0,
            'stability': 0.5
        }
        
        # 与历史环境状态比较
        if len(self.adaptation_history) > 0:
            last_environment = self.adaptation_history[-1]['environment_state']
            
            # 分析复杂度变化
            current_complexity = environment_state.get('complexity', 0.5)
            last_complexity = last_environment.get('complexity', 0.5)
            analysis['complexity_change'] = current_complexity - last_complexity
            
            # 分析资源变化
            current_resources = len(environment_state.get('available_resources', []))
            last_resources = len(last_environment.get('available_resources', []))
            if last_resources > 0:
                analysis['resource_change'] = (current_resources - last_resources) / last_resources
            
            # 分析竞争变化
            current_competition = environment_state.get('competition_level', 0.5)
            last_competition = last_environment.get('competition_level', 0.5)
            analysis['competition_change'] = current_competition - last_competition
            
            # 计算稳定性
            total_change = abs(analysis['complexity_change']) + abs(analysis['resource_change']) + abs(analysis['competition_change'])
            analysis['stability'] = max(0, 1 - total_change)
        
        return analysis
    
    def _analyze_performance_feedback(self, performance_feedback: Dict[str, float]) -> Dict[str, Any]:
        """分析性能反馈"""
        analysis = {
            'overall_performance': 0.0,
            'performance_trend': 0.0,
            'weak_areas': [],
            'strong_areas': []
        }
        
        if performance_feedback:
            # 计算整体性能
            analysis['overall_performance'] = sum(performance_feedback.values()) / len(performance_feedback)
            
            # 识别强弱项
            for metric, value in performance_feedback.items():
                if value > 0.7:
                    analysis['strong_areas'].append(metric)
                elif value < 0.4:
                    analysis['weak_areas'].append(metric)
            
            # 分析性能趋势
            if len(self.adaptation_history) > 0:
                last_feedback = self.adaptation_history[-1]['performance_feedback']
                if last_feedback:
                    last_performance = sum(last_feedback.values()) / len(last_feedback)
                    analysis['performance_trend'] = analysis['overall_performance'] - last_performance
        
        return analysis
    
    def _adjust_strategy(self, environment_analysis: Dict[str, Any], 
                       performance_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """调整策略"""
        strategy_changes = {}
        
        # 根据环境复杂度调整探索率
        complexity_change = environment_analysis.get('complexity_change', 0)
        if complexity_change > 0.2:  # 环境变复杂
            new_exploration_rate = min(0.8, self.current_strategy['exploration_rate'] + 0.1)
            strategy_changes['exploration_rate'] = new_exploration_rate
        elif complexity_change < -0.2:  # 环境变简单
            new_exploration_rate = max(0.1, self.current_strategy['exploration_rate'] - 0.1)
            strategy_changes['exploration_rate'] = new_exploration_rate
        
        # 根据性能调整学习率
        performance_trend = performance_analysis.get('performance_trend', 0)
        if performance_trend < -0.1:  # 性能下降
            new_learning_rate = min(0.3, self.current_strategy['learning_rate'] + 0.05)
            strategy_changes['learning_rate'] = new_learning_rate
        elif performance_trend > 0.1:  # 性能提升
            new_learning_rate = max(0.05, self.current_strategy['learning_rate'] - 0.02)
            strategy_changes['learning_rate'] = new_learning_rate
        
        # 根据竞争水平调整风险容忍度
        competition_change = environment_analysis.get('competition_change', 0)
        if competition_change > 0.2:  # 竞争加剧
            new_risk_tolerance = max(0.2, self.current_strategy['risk_tolerance'] - 0.1)
            strategy_changes['risk_tolerance'] = new_risk_tolerance
        elif competition_change < -0.2:  # 竞争减少
            new_risk_tolerance = min(0.8, self.current_strategy['risk_tolerance'] + 0.1)
            strategy_changes['risk_tolerance'] = new_risk_tolerance
        
        # 根据资源变化调整合作倾向
        resource_change = environment_analysis.get('resource_change', 0)
        if resource_change < -0.3:  # 资源减少
            new_cooperation = min(0.8, self.current_strategy['cooperation_tendency'] + 0.15)
            strategy_changes['cooperation_tendency'] = new_cooperation
        elif resource_change > 0.3:  # 资源增加
            new_cooperation = max(0.2, self.current_strategy['cooperation_tendency'] - 0.1)
            strategy_changes['cooperation_tendency'] = new_cooperation
        
        return strategy_changes
    
    def _generate_adaptive_behaviors(self, environment_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成适应性行为"""
        new_behaviors = []
        
        # 根据环境变化生成新行为
        if environment_analysis.get('complexity_change', 0) > 0.3:
            new_behaviors.append({
                'type': 'complexity_adaptation',
                'description': '增强复杂环境适应能力',
                'parameters': {
                    'analysis_depth': 'deep',
                    'decision_time': 'extended',
                    'backup_plans': 3
                }
            })
        
        if environment_analysis.get('resource_change', 0) < -0.2:
            new_behaviors.append({
                'type': 'resource_conservation',
                'description': '启动资源保护模式',
                'parameters': {
                    'efficiency_focus': True,
                    'waste_reduction': 0.8,
                    'sharing_enabled': True
                }
            })
        
        if environment_analysis.get('stability', 0.5) < 0.3:
            new_behaviors.append({
                'type': 'stability_seeking',
                'description': '寻求稳定性策略',
                'parameters': {
                    'conservative_actions': True,
                    'risk_avoidance': 0.8,
                    'predictable_patterns': True
                }
            })
        
        return new_behaviors
    
    def _generate_adaptation_insights(self, environment_analysis: Dict[str, Any], 
                                    performance_analysis: Dict[str, Any]) -> List[str]:
        """生成适应洞察"""
        insights = []
        
        # 环境洞察
        if environment_analysis.get('complexity_change', 0) > 0.2:
            insights.append("环境复杂度显著增加，需要提高适应能力")
        
        if environment_analysis.get('stability', 0.5) < 0.4:
            insights.append("环境不稳定，建议采用更保守的策略")
        
        # 性能洞察
        if performance_analysis.get('performance_trend', 0) < -0.1:
            insights.append("性能出现下降趋势，需要调整策略")
        
        weak_areas = performance_analysis.get('weak_areas', [])
        if len(weak_areas) > 2:
            insights.append(f"发现多个弱项领域: {', '.join(weak_areas)}")
        
        strong_areas = performance_analysis.get('strong_areas', [])
        if len(strong_areas) > 0:
            insights.append(f"保持优势领域: {', '.join(strong_areas)}")
        
        return insights
    
    def get_current_strategy(self) -> Dict[str, Any]:
        """获取当前策略"""
        return copy.deepcopy(self.current_strategy)

class IntelligentAgent:
    """智能代理 - 整合所有智能行为功能
    
    这是智能行为的核心代理，整合了决策、学习、适应等功能。
    """
    
    def __init__(self):
        """初始化智能代理"""
        self.learning_system = LearningSystem()
        self.decision_making = DecisionMaking()
        self.adaptation_engine = AdaptationEngine(self.learning_system)
        
        self.behavior_patterns: Dict[str, BehaviorPattern] = {}
        self.available_actions: Dict[str, Action] = {}
        self.agent_state = {
            'energy': 1.0,
            'knowledge_level': 0.0,
            'experience_count': 0,
            'adaptation_count': 0
        }
        
        # 初始化基础行为模式
        self._initialize_base_behaviors()
        
        # 初始化基础行动
        self._initialize_base_actions()
        
        logger.debug(f"[INTELLIGENT_AGENT_DEBUG] 初始化智能代理")
    
    def _initialize_base_behaviors(self):
        """初始化基础行为模式"""
        base_behaviors = [
            {
                'id': 'exploration_behavior',
                'type': BehaviorType.EXPLORATION,
                'actions': ['explore_environment', 'try_new_approach'],
                'triggers': {'curiosity_level': 0.7, 'knowledge_gap': True}
            },
            {
                'id': 'optimization_behavior',
                'type': BehaviorType.OPTIMIZATION,
                'actions': ['optimize_parameters', 'refine_strategy'],
                'triggers': {'performance_stable': True, 'improvement_potential': 0.3}
            },
            {
                'id': 'learning_behavior',
                'type': BehaviorType.LEARNING,
                'actions': ['analyze_experience', 'update_knowledge'],
                'triggers': {'new_experience': True, 'learning_opportunity': 0.5}
            },
            {
                'id': 'adaptation_behavior',
                'type': BehaviorType.ADAPTATION,
                'actions': ['adjust_strategy', 'modify_approach'],
                'triggers': {'environment_change': 0.3, 'performance_decline': True}
            }
        ]
        
        for behavior_def in base_behaviors:
            behavior = BehaviorPattern(
                id=behavior_def['id'],
                pattern_type=behavior_def['type'],
                action_sequence=behavior_def['actions'],
                trigger_conditions=behavior_def['triggers']
            )
            self.behavior_patterns[behavior.id] = behavior
    
    def _initialize_base_actions(self):
        """初始化基础行动"""
        base_actions = [
            {
                'id': 'explore_environment',
                'type': 'exploration',
                'params': {'scope': 'wide', 'depth': 'shallow'},
                'outcome': {'knowledge_gain': 0.3, 'discovery_chance': 0.2},
                'cost': 0.2,
                'risk': 0.1
            },
            {
                'id': 'try_new_approach',
                'type': 'innovation',
                'params': {'creativity': 0.8, 'risk_level': 'medium'},
                'outcome': {'innovation_score': 0.6, 'learning_value': 0.4},
                'cost': 0.3,
                'risk': 0.4
            },
            {
                'id': 'optimize_parameters',
                'type': 'optimization',
                'params': {'precision': 'high', 'scope': 'local'},
                'outcome': {'efficiency_gain': 0.4, 'performance_boost': 0.3},
                'cost': 0.15,
                'risk': 0.05
            },
            {
                'id': 'analyze_experience',
                'type': 'learning',
                'params': {'depth': 'deep', 'pattern_recognition': True},
                'outcome': {'insight_gain': 0.5, 'pattern_discovery': 0.3},
                'cost': 0.1,
                'risk': 0.0
            }
        ]
        
        for action_def in base_actions:
            action = Action(
                id=action_def['id'],
                action_type=action_def['type'],
                parameters=action_def['params'],
                expected_outcome=action_def['outcome'],
                cost=action_def['cost'],
                risk=action_def['risk'],
                confidence=0.7
            )
            self.available_actions[action.id] = action
    
    def perceive_and_act(self, environment: Dict[str, Any], 
                        goals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """感知环境并采取行动
        
        这是智能代理的主要行为循环。
        """
        logger.debug(f"[INTELLIGENT_AGENT_DEBUG] 开始感知和行动循环")
        
        # 感知环境
        perception = self._perceive_environment(environment)
        
        # 选择行为模式
        selected_pattern = self._select_behavior_pattern(perception, goals)
        
        # 决策行动
        selected_action = None
        if selected_pattern:
            available_actions = [self.available_actions[action_id] 
                               for action_id in selected_pattern.action_sequence 
                               if action_id in self.available_actions]
            
            if available_actions:
                selected_action = self.decision_making.make_decision(available_actions, perception, goals)
        
        # 执行行动
        action_result = None
        if selected_action:
            action_result = selected_action.execute(environment)
            
            # 学习经验
            experience = {
                'context': perception,
                'action': {
                    'id': selected_action.id,
                    'type': selected_action.action_type,
                    'parameters': selected_action.parameters
                },
                'outcome': action_result,
                'goals': goals
            }
            
            learning_result = self.learning_system.learn_from_experience(experience)
            
            # 更新行为模式效果
            if selected_pattern:
                selected_pattern.update_effectiveness(action_result)
            
            # 更新代理状态
            self._update_agent_state(action_result, learning_result)
        
        # 适应环境
        if self.agent_state['experience_count'] % 10 == 0:  # 每10次经验进行一次适应
            performance_feedback = self._calculate_performance_feedback()
            adaptation_result = self.adaptation_engine.adapt_to_environment(environment, performance_feedback)
            self.agent_state['adaptation_count'] += 1
        
        # 构建返回结果
        result = {
            'perception': perception,
            'selected_pattern': selected_pattern.id if selected_pattern else None,
            'selected_action': selected_action.id if selected_action else None,
            'action_result': action_result,
            'agent_state': copy.deepcopy(self.agent_state),
            'behavior_insights': self._generate_behavior_insights()
        }
        
        logger.debug(f"[INTELLIGENT_AGENT_DEBUG] 行为循环完成")
        return result
    
    def _perceive_environment(self, environment: Dict[str, Any]) -> Dict[str, Any]:
        """感知环境"""
        perception = {
            'environment_complexity': environment.get('complexity', 0.5),
            'available_resources': environment.get('available_resources', []),
            'challenges': environment.get('challenges', []),
            'opportunities': environment.get('opportunities', []),
            'competition_level': environment.get('competition_level', 0.5),
            'change_rate': environment.get('change_rate', 0.0),
            'resource_abundance': len(environment.get('available_resources', [])) / 10.0,
            'threat_level': len(environment.get('threats', [])) / 5.0
        }
        
        # 添加内部状态感知
        perception.update({
            'internal_energy': self.agent_state['energy'],
            'knowledge_level': self.agent_state['knowledge_level'],
            'experience_count': self.agent_state['experience_count']
        })
        
        return perception
    
    def _select_behavior_pattern(self, perception: Dict[str, Any], 
                               goals: List[Dict[str, Any]]) -> Optional[BehaviorPattern]:
        """选择行为模式"""
        pattern_scores = []
        
        for pattern in self.behavior_patterns.values():
            # 计算上下文匹配度
            context_match = pattern.matches_context(perception)
            
            # 计算目标一致性
            goal_alignment = self._calculate_pattern_goal_alignment(pattern, goals)
            
            # 计算历史效果
            effectiveness = pattern.effectiveness_score
            
            # 综合评分
            total_score = (context_match * 0.4 + 
                         goal_alignment * 0.3 + 
                         effectiveness * 0.3)
            
            pattern_scores.append((pattern, total_score))
        
        if pattern_scores:
            # 按分数排序并选择最佳模式
            pattern_scores.sort(key=lambda x: x[1], reverse=True)
            best_pattern, best_score = pattern_scores[0]
            
            # 只有当分数足够高时才选择
            if best_score > 0.3:
                return best_pattern
        
        return None
    
    def _calculate_pattern_goal_alignment(self, pattern: BehaviorPattern, 
                                        goals: List[Dict[str, Any]]) -> float:
        """计算模式与目标的一致性"""
        if not goals:
            return 0.5
        
        alignment_scores = []
        
        for goal in goals:
            goal_type = goal.get('goal_type', '')
            
            # 根据行为类型和目标类型计算匹配度
            if pattern.pattern_type == BehaviorType.EXPLORATION and 'exploration' in goal_type:
                alignment_scores.append(0.9)
            elif pattern.pattern_type == BehaviorType.OPTIMIZATION and 'optimization' in goal_type:
                alignment_scores.append(0.9)
            elif pattern.pattern_type == BehaviorType.LEARNING and 'learning' in goal_type:
                alignment_scores.append(0.9)
            elif pattern.pattern_type == BehaviorType.ADAPTATION and 'adaptation' in goal_type:
                alignment_scores.append(0.9)
            else:
                alignment_scores.append(0.3)  # 基础匹配度
        
        return sum(alignment_scores) / len(alignment_scores) if alignment_scores else 0.5
    
    def _update_agent_state(self, action_result: Dict[str, Any], 
                          learning_result: Dict[str, Any]):
        """更新代理状态"""
        # 更新经验计数
        self.agent_state['experience_count'] += 1
        
        # 更新能量
        energy_cost = action_result.get('cost', 0)
        energy_gain = 0.1 if action_result.get('success', False) else 0.05
        self.agent_state['energy'] = max(0, min(1, self.agent_state['energy'] - energy_cost + energy_gain))
        
        # 更新知识水平
        knowledge_gain = len(learning_result.get('new_knowledge', [])) * 0.01
        self.agent_state['knowledge_level'] = min(1, self.agent_state['knowledge_level'] + knowledge_gain)
    
    def _calculate_performance_feedback(self) -> Dict[str, float]:
        """计算性能反馈"""
        feedback = {
            'overall_effectiveness': 0.0,
            'learning_efficiency': 0.0,
            'adaptation_success': 0.0,
            'goal_achievement': 0.0
        }
        
        # 计算整体效果
        if self.behavior_patterns:
            avg_effectiveness = sum(p.effectiveness_score for p in self.behavior_patterns.values()) / len(self.behavior_patterns)
            feedback['overall_effectiveness'] = avg_effectiveness
        
        # 计算学习效率
        if self.learning_system.learning_history:
            recent_learning = self.learning_system.learning_history[-10:]  # 最近10次学习
            avg_new_knowledge = sum(len(l['learning_result'].get('new_knowledge', [])) for l in recent_learning) / len(recent_learning)
            feedback['learning_efficiency'] = min(1.0, avg_new_knowledge / 5.0)  # 归一化到0-1
        
        # 计算适应成功率
        if self.adaptation_engine.adaptation_history:
            recent_adaptations = self.adaptation_engine.adaptation_history[-5:]  # 最近5次适应
            avg_changes = sum(len(a['adaptation_result'].get('strategy_changes', {})) for a in recent_adaptations) / len(recent_adaptations)
            feedback['adaptation_success'] = min(1.0, avg_changes / 3.0)  # 归一化到0-1
        
        # 目标达成率（简化计算）
        feedback['goal_achievement'] = self.agent_state['knowledge_level'] * 0.7 + self.agent_state['energy'] * 0.3
        
        return feedback
    
    def _generate_behavior_insights(self) -> List[str]:
        """生成行为洞察"""
        insights = []
        
        # 分析行为模式效果
        if self.behavior_patterns:
            best_pattern = max(self.behavior_patterns.values(), key=lambda p: p.effectiveness_score)
            worst_pattern = min(self.behavior_patterns.values(), key=lambda p: p.effectiveness_score)
            
            if best_pattern.effectiveness_score > 0.7:
                insights.append(f"行为模式 '{best_pattern.id}' 表现优秀")
            
            if worst_pattern.effectiveness_score < 0.3:
                insights.append(f"行为模式 '{worst_pattern.id}' 需要改进")
        
        # 分析代理状态
        if self.agent_state['energy'] < 0.3:
            insights.append("能量水平较低，建议休息或降低活动强度")
        
        if self.agent_state['knowledge_level'] > 0.8:
            insights.append("知识水平较高，可以尝试更复杂的任务")
        
        # 分析学习效果
        if self.learning_system.learning_history:
            recent_insights = []
            for record in self.learning_system.learning_history[-5:]:
                recent_insights.extend(record['learning_result'].get('insights', []))
            
            if len(recent_insights) > 3:
                insights.append("最近学习效果良好，发现了多个新洞察")
        
        return insights
    
    def get_agent_summary(self) -> Dict[str, Any]:
        """获取代理摘要"""
        return {
            'agent_state': copy.deepcopy(self.agent_state),
            'behavior_patterns': {
                pattern_id: {
                    'type': pattern.pattern_type.value,
                    'effectiveness': pattern.effectiveness_score,
                    'usage_count': pattern.usage_count,
                    'success_rate': pattern.success_rate
                }
                for pattern_id, pattern in self.behavior_patterns.items()
            },
            'learning_summary': {
                'total_experiences': len(self.learning_system.learning_history),
                'knowledge_patterns': len(self.learning_system.knowledge_base['patterns']),
                'associations': len(self.learning_system.knowledge_base['associations'])
            },
            'adaptation_summary': {
                'adaptation_count': self.agent_state['adaptation_count'],
                'current_strategy': self.adaptation_engine.get_current_strategy()
            }
        }