"""虚拟世界模块 - 实现复杂的环境交互和任务系统

本模块实现了虚拟世界的核心机制:
- VirtualWorld: 虚拟世界环境，提供复杂的交互场景
- TaskEnvironment: 任务环境，定义各种挑战和目标
- ResourceManager: 资源管理器，处理资源分配和竞争
- EnvironmentDynamics: 环境动力学，模拟环境变化
- InteractionEngine: 交互引擎，处理实体间的交互
- WorldState: 世界状态，维护环境的完整状态
"""

import logging
import random
import time
import json
import math
import copy
from typing import Dict, List, Any, Optional, Tuple, Callable, Union, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import uuid
import numpy as np
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

class EnvironmentType(Enum):
    """环境类型枚举"""
    MAZE = "maze"  # 迷宫环境
    RESOURCE_FIELD = "resource_field"  # 资源场地
    COMPETITIVE_ARENA = "competitive_arena"  # 竞技场
    COLLABORATIVE_SPACE = "collaborative_space"  # 协作空间
    DYNAMIC_LANDSCAPE = "dynamic_landscape"  # 动态地形
    PUZZLE_CHAMBER = "puzzle_chamber"  # 谜题房间
    SURVIVAL_ZONE = "survival_zone"  # 生存区域
    LEARNING_LAB = "learning_lab"  # 学习实验室

class TaskType(Enum):
    """任务类型枚举"""
    PATHFINDING = "pathfinding"  # 寻路任务
    RESOURCE_COLLECTION = "resource_collection"  # 资源收集
    PUZZLE_SOLVING = "puzzle_solving"  # 谜题解决
    OPTIMIZATION = "optimization"  # 优化任务
    SURVIVAL = "survival"  # 生存任务
    COOPERATION = "cooperation"  # 合作任务
    COMPETITION = "competition"  # 竞争任务
    EXPLORATION = "exploration"  # 探索任务
    LEARNING = "learning"  # 学习任务
    ADAPTATION = "adaptation"  # 适应任务

class ResourceType(Enum):
    """资源类型枚举"""
    ENERGY = "energy"  # 能量
    INFORMATION = "information"  # 信息
    TOOLS = "tools"  # 工具
    MATERIALS = "materials"  # 材料
    TIME = "time"  # 时间
    SPACE = "space"  # 空间
    KNOWLEDGE = "knowledge"  # 知识
    CONNECTIONS = "connections"  # 连接

class InteractionType(Enum):
    """交互类型枚举"""
    COOPERATION = "cooperation"  # 合作
    COMPETITION = "competition"  # 竞争
    COMMUNICATION = "communication"  # 沟通
    TRADE = "trade"  # 交易
    CONFLICT = "conflict"  # 冲突
    LEARNING = "learning"  # 学习
    TEACHING = "teaching"  # 教学
    OBSERVATION = "observation"  # 观察

@dataclass
class Position:
    """位置信息"""
    x: float
    y: float
    z: float = 0.0
    
    def distance_to(self, other: 'Position') -> float:
        """计算到另一个位置的距离"""
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2 + (self.z - other.z)**2)
    
    def move_towards(self, target: 'Position', distance: float) -> 'Position':
        """向目标位置移动指定距离"""
        current_distance = self.distance_to(target)
        if current_distance <= distance:
            return Position(target.x, target.y, target.z)
        
        ratio = distance / current_distance
        new_x = self.x + (target.x - self.x) * ratio
        new_y = self.y + (target.y - self.y) * ratio
        new_z = self.z + (target.z - self.z) * ratio
        
        return Position(new_x, new_y, new_z)

@dataclass
class Resource:
    """资源定义"""
    id: str
    resource_type: ResourceType
    amount: float
    quality: float = 1.0
    position: Optional[Position] = None
    owner: Optional[str] = None
    renewable: bool = False
    regeneration_rate: float = 0.0
    max_amount: float = 100.0
    
    def consume(self, amount: float) -> float:
        """消耗资源"""
        consumed = min(amount, self.amount)
        self.amount -= consumed
        return consumed
    
    def regenerate(self, time_delta: float):
        """资源再生"""
        if self.renewable and self.amount < self.max_amount:
            regenerated = self.regeneration_rate * time_delta
            self.amount = min(self.max_amount, self.amount + regenerated)

@dataclass
class Entity:
    """实体定义"""
    id: str
    entity_type: str
    position: Position
    properties: Dict[str, Any] = field(default_factory=dict)
    resources: Dict[str, Resource] = field(default_factory=dict)
    capabilities: List[str] = field(default_factory=list)
    state: Dict[str, Any] = field(default_factory=dict)
    
    def can_interact_with(self, other: 'Entity', interaction_type: InteractionType) -> bool:
        """检查是否可以与另一个实体交互"""
        # 基础距离检查
        distance = self.position.distance_to(other.position)
        max_interaction_distance = self.properties.get('interaction_range', 5.0)
        
        if distance > max_interaction_distance:
            return False
        
        # 能力检查
        required_capability = f"interact_{interaction_type.value}"
        if required_capability not in self.capabilities:
            return False
        
        return True
    
    def move_to(self, target_position: Position, speed: float = 1.0) -> Position:
        """移动到目标位置"""
        max_distance = speed * self.properties.get('movement_speed', 1.0)
        new_position = self.position.move_towards(target_position, max_distance)
        self.position = new_position
        return new_position

@dataclass
class Task:
    """任务定义"""
    id: str
    task_type: TaskType
    description: str
    objectives: List[Dict[str, Any]]
    constraints: Dict[str, Any] = field(default_factory=dict)
    rewards: Dict[str, float] = field(default_factory=dict)
    penalties: Dict[str, float] = field(default_factory=dict)
    time_limit: Optional[float] = None
    difficulty: float = 0.5
    prerequisites: List[str] = field(default_factory=list)
    
    def evaluate_completion(self, world_state: Dict[str, Any]) -> Dict[str, Any]:
        """评估任务完成情况"""
        completion_result = {
            'completed': False,
            'progress': 0.0,
            'objective_status': {},
            'rewards_earned': {},
            'penalties_incurred': {}
        }
        
        completed_objectives = 0
        total_objectives = len(self.objectives)
        
        for objective in self.objectives:
            objective_id = objective.get('id', 'unknown')
            objective_type = objective.get('type', 'unknown')
            target_value = objective.get('target_value', 0)
            
            current_value = self._get_objective_current_value(objective, world_state)
            objective_completed = self._check_objective_completion(objective, current_value)
            
            completion_result['objective_status'][objective_id] = {
                'completed': objective_completed,
                'current_value': current_value,
                'target_value': target_value,
                'progress': min(1.0, current_value / max(target_value, 0.001))
            }
            
            if objective_completed:
                completed_objectives += 1
        
        # 计算总体进度
        completion_result['progress'] = completed_objectives / max(total_objectives, 1)
        completion_result['completed'] = completed_objectives == total_objectives
        
        # 计算奖励和惩罚
        if completion_result['completed']:
            completion_result['rewards_earned'] = copy.deepcopy(self.rewards)
        
        # 检查时间限制惩罚
        if self.time_limit and world_state.get('elapsed_time', 0) > self.time_limit:
            completion_result['penalties_incurred'].update(self.penalties)
        
        return completion_result
    
    def _get_objective_current_value(self, objective: Dict[str, Any], world_state: Dict[str, Any]) -> float:
        """获取目标的当前值"""
        objective_type = objective.get('type', 'unknown')
        metric_name = objective.get('metric', 'unknown')
        
        if objective_type == 'position':
            # 位置目标
            target_pos = objective.get('target_position', {'x': 0, 'y': 0})
            current_pos = world_state.get('agent_position', {'x': 0, 'y': 0})
            distance = math.sqrt((current_pos['x'] - target_pos['x'])**2 + (current_pos['y'] - target_pos['y'])**2)
            return max(0, objective.get('max_distance', 10) - distance)
        
        elif objective_type == 'collection':
            # 收集目标
            collected_items = world_state.get('collected_items', {})
            item_type = objective.get('item_type', 'unknown')
            return collected_items.get(item_type, 0)
        
        elif objective_type == 'metric':
            # 指标目标
            return world_state.get(metric_name, 0)
        
        else:
            return 0.0
    
    def _check_objective_completion(self, objective: Dict[str, Any], current_value: float) -> bool:
        """检查目标是否完成"""
        target_value = objective.get('target_value', 0)
        comparison = objective.get('comparison', 'gte')  # gte, lte, eq
        
        if comparison == 'gte':
            return current_value >= target_value
        elif comparison == 'lte':
            return current_value <= target_value
        elif comparison == 'eq':
            tolerance = objective.get('tolerance', 0.1)
            return abs(current_value - target_value) <= tolerance
        
        return False

class ResourceManager:
    """资源管理器
    
    处理资源的分配、竞争和再生。
    """
    
    def __init__(self):
        """初始化资源管理器"""
        self.resources: Dict[str, Resource] = {}
        self.resource_history: List[Dict[str, Any]] = []
        self.allocation_rules: Dict[str, Callable] = {}
        
        logger.debug(f"[RESOURCE_DEBUG] 初始化资源管理器")
    
    def add_resource(self, resource: Resource):
        """添加资源"""
        self.resources[resource.id] = resource
        logger.debug(f"[RESOURCE_DEBUG] 添加资源: {resource.id} ({resource.resource_type.value})")
    
    def allocate_resource(self, resource_id: str, requester_id: str, 
                         amount: float) -> Dict[str, Any]:
        """分配资源"""
        if resource_id not in self.resources:
            return {
                'success': False,
                'reason': f'资源 {resource_id} 不存在',
                'allocated_amount': 0.0
            }
        
        resource = self.resources[resource_id]
        
        # 检查资源所有权
        if resource.owner and resource.owner != requester_id:
            return {
                'success': False,
                'reason': f'资源 {resource_id} 已被 {resource.owner} 拥有',
                'allocated_amount': 0.0
            }
        
        # 分配资源
        allocated_amount = resource.consume(amount)
        
        # 记录分配历史
        allocation_record = {
            'timestamp': datetime.now().isoformat(),
            'resource_id': resource_id,
            'requester_id': requester_id,
            'requested_amount': amount,
            'allocated_amount': allocated_amount,
            'remaining_amount': resource.amount
        }
        
        self.resource_history.append(allocation_record)
        
        logger.debug(f"[RESOURCE_DEBUG] 分配资源: {allocated_amount}/{amount} 给 {requester_id}")
        
        return {
            'success': allocated_amount > 0,
            'allocated_amount': allocated_amount,
            'remaining_amount': resource.amount
        }
    
    def compete_for_resource(self, resource_id: str, 
                           competitors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """资源竞争"""
        if resource_id not in self.resources:
            return {'winner': None, 'reason': '资源不存在'}
        
        resource = self.resources[resource_id]
        
        if not competitors:
            return {'winner': None, 'reason': '无竞争者'}
        
        # 计算竞争力
        competitor_scores = []
        for competitor in competitors:
            competitor_id = competitor.get('id', 'unknown')
            
            # 基础竞争力计算
            base_strength = competitor.get('strength', 0.5)
            resource_need = competitor.get('resource_need', 0.5)
            distance_factor = 1.0 / max(competitor.get('distance', 1.0), 0.1)
            
            # 综合竞争力
            total_score = base_strength * 0.4 + resource_need * 0.3 + distance_factor * 0.3
            
            competitor_scores.append((competitor_id, total_score))
        
        # 选择获胜者
        competitor_scores.sort(key=lambda x: x[1], reverse=True)
        winner_id, winner_score = competitor_scores[0]
        
        # 分配资源给获胜者
        winner_competitor = next(c for c in competitors if c.get('id') == winner_id)
        requested_amount = winner_competitor.get('requested_amount', resource.amount)
        
        allocation_result = self.allocate_resource(resource_id, winner_id, requested_amount)
        
        logger.debug(f"[RESOURCE_DEBUG] 竞争结果: {winner_id} 获胜 (分数: {winner_score:.3f})")
        
        return {
            'winner': winner_id,
            'winner_score': winner_score,
            'allocation_result': allocation_result,
            'all_scores': competitor_scores
        }
    
    def update_resources(self, time_delta: float):
        """更新资源状态"""
        for resource in self.resources.values():
            resource.regenerate(time_delta)
    
    def get_resource_summary(self) -> Dict[str, Any]:
        """获取资源摘要"""
        summary = {
            'total_resources': len(self.resources),
            'resource_types': {},
            'total_allocations': len(self.resource_history),
            'resource_status': {}
        }
        
        # 统计资源类型
        for resource in self.resources.values():
            resource_type = resource.resource_type.value
            if resource_type not in summary['resource_types']:
                summary['resource_types'][resource_type] = 0
            summary['resource_types'][resource_type] += 1
        
        # 资源状态
        for resource_id, resource in self.resources.items():
            summary['resource_status'][resource_id] = {
                'type': resource.resource_type.value,
                'amount': resource.amount,
                'max_amount': resource.max_amount,
                'utilization': resource.amount / resource.max_amount,
                'owner': resource.owner,
                'renewable': resource.renewable
            }
        
        return summary

class EnvironmentDynamics:
    """环境动力学
    
    模拟环境的动态变化和演化。
    """
    
    def __init__(self):
        """初始化环境动力学"""
        self.change_rules: List[Dict[str, Any]] = []
        self.environmental_factors: Dict[str, float] = {
            'temperature': 0.5,
            'humidity': 0.5,
            'pressure': 0.5,
            'complexity': 0.5,
            'stability': 0.8,
            'resource_abundance': 0.6
        }
        self.change_history: List[Dict[str, Any]] = []
        
        # 初始化默认变化规则
        self._initialize_default_rules()
        
        logger.debug(f"[ENVIRONMENT_DEBUG] 初始化环境动力学")
    
    def _initialize_default_rules(self):
        """初始化默认变化规则"""
        default_rules = [
            {
                'name': 'temperature_fluctuation',
                'description': '温度波动',
                'trigger_condition': lambda state: True,
                'change_function': lambda state, dt: {
                    'temperature': state.get('temperature', 0.5) + random.gauss(0, 0.05) * dt
                }
            },
            {
                'name': 'complexity_evolution',
                'description': '复杂度演化',
                'trigger_condition': lambda state: state.get('entity_count', 0) > 5,
                'change_function': lambda state, dt: {
                    'complexity': min(1.0, state.get('complexity', 0.5) + 0.01 * dt)
                }
            },
            {
                'name': 'resource_depletion',
                'description': '资源枯竭',
                'trigger_condition': lambda state: state.get('resource_usage_rate', 0) > 0.8,
                'change_function': lambda state, dt: {
                    'resource_abundance': max(0.1, state.get('resource_abundance', 0.6) - 0.02 * dt)
                }
            }
        ]
        
        self.change_rules.extend(default_rules)
    
    def add_change_rule(self, rule: Dict[str, Any]):
        """添加变化规则"""
        required_keys = ['name', 'trigger_condition', 'change_function']
        if all(key in rule for key in required_keys):
            self.change_rules.append(rule)
            logger.debug(f"[ENVIRONMENT_DEBUG] 添加变化规则: {rule['name']}")
        else:
            logger.warning(f"[ENVIRONMENT_DEBUG] 变化规则缺少必要字段: {rule}")
    
    def update_environment(self, world_state: Dict[str, Any], time_delta: float) -> Dict[str, Any]:
        """更新环境状态"""
        changes = {}
        applied_rules = []
        
        # 应用变化规则
        for rule in self.change_rules:
            try:
                if rule['trigger_condition'](world_state):
                    rule_changes = rule['change_function'](self.environmental_factors, time_delta)
                    
                    for factor, new_value in rule_changes.items():
                        # 限制值在合理范围内
                        clamped_value = max(0.0, min(1.0, new_value))
                        self.environmental_factors[factor] = clamped_value
                        changes[factor] = clamped_value
                    
                    applied_rules.append(rule['name'])
            
            except Exception as e:
                logger.error(f"[ENVIRONMENT_DEBUG] 规则 {rule['name']} 执行失败: {e}")
        
        # 记录变化历史
        if changes:
            change_record = {
                'timestamp': datetime.now().isoformat(),
                'changes': changes,
                'applied_rules': applied_rules,
                'environmental_factors': copy.deepcopy(self.environmental_factors)
            }
            
            self.change_history.append(change_record)
            
            # 保持历史记录在合理范围内
            if len(self.change_history) > 1000:
                self.change_history = self.change_history[-1000:]
        
        logger.debug(f"[ENVIRONMENT_DEBUG] 环境更新完成，应用规则: {applied_rules}")
        
        return {
            'changes': changes,
            'applied_rules': applied_rules,
            'current_factors': copy.deepcopy(self.environmental_factors)
        }
    
    def get_environmental_pressure(self, entity_type: str) -> float:
        """获取环境压力"""
        # 基础环境压力计算
        base_pressure = 1.0 - self.environmental_factors.get('stability', 0.8)
        
        # 复杂度压力
        complexity_pressure = self.environmental_factors.get('complexity', 0.5) * 0.3
        
        # 资源稀缺压力
        resource_pressure = (1.0 - self.environmental_factors.get('resource_abundance', 0.6)) * 0.4
        
        # 温度压力
        temperature = self.environmental_factors.get('temperature', 0.5)
        temperature_pressure = abs(temperature - 0.5) * 0.3  # 偏离适宜温度的压力
        
        total_pressure = base_pressure + complexity_pressure + resource_pressure + temperature_pressure
        
        return min(1.0, total_pressure)
    
    def predict_future_state(self, time_horizon: float, steps: int = 10) -> List[Dict[str, Any]]:
        """预测未来环境状态"""
        predictions = []
        current_factors = copy.deepcopy(self.environmental_factors)
        step_size = time_horizon / steps
        
        for step in range(steps):
            # 简化的预测模型
            predicted_factors = {}
            
            for factor, current_value in current_factors.items():
                # 基于历史趋势预测
                if len(self.change_history) > 5:
                    recent_changes = []
                    for record in self.change_history[-5:]:
                        if factor in record['changes']:
                            recent_changes.append(record['changes'][factor] - record['environmental_factors'].get(factor, current_value))
                    
                    if recent_changes:
                        avg_change_rate = sum(recent_changes) / len(recent_changes)
                        predicted_value = current_value + avg_change_rate * step_size
                    else:
                        predicted_value = current_value
                else:
                    # 无历史数据时的简单预测
                    predicted_value = current_value + random.gauss(0, 0.01) * step_size
                
                predicted_factors[factor] = max(0.0, min(1.0, predicted_value))
            
            predictions.append({
                'time_offset': (step + 1) * step_size,
                'predicted_factors': predicted_factors
            })
            
            current_factors = predicted_factors
        
        return predictions

class InteractionEngine:
    """交互引擎
    
    处理实体间的各种交互。
    """
    
    def __init__(self, resource_manager: ResourceManager):
        """初始化交互引擎"""
        self.resource_manager = resource_manager
        self.interaction_history: List[Dict[str, Any]] = []
        self.interaction_rules: Dict[InteractionType, Callable] = {}
        
        # 初始化默认交互规则
        self._initialize_default_interactions()
        
        logger.debug(f"[INTERACTION_DEBUG] 初始化交互引擎")
    
    def _initialize_default_interactions(self):
        """初始化默认交互规则"""
        self.interaction_rules[InteractionType.COOPERATION] = self._handle_cooperation
        self.interaction_rules[InteractionType.COMPETITION] = self._handle_competition
        self.interaction_rules[InteractionType.TRADE] = self._handle_trade
        self.interaction_rules[InteractionType.COMMUNICATION] = self._handle_communication
        self.interaction_rules[InteractionType.LEARNING] = self._handle_learning
    
    def process_interaction(self, entity1: Entity, entity2: Entity, 
                          interaction_type: InteractionType, 
                          parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """处理实体间交互"""
        if parameters is None:
            parameters = {}
        
        logger.debug(f"[INTERACTION_DEBUG] 处理交互: {entity1.id} <-> {entity2.id} ({interaction_type.value})")
        
        # 检查交互可行性
        if not entity1.can_interact_with(entity2, interaction_type):
            return {
                'success': False,
                'reason': '交互条件不满足',
                'interaction_type': interaction_type.value
            }
        
        # 执行交互
        if interaction_type in self.interaction_rules:
            result = self.interaction_rules[interaction_type](entity1, entity2, parameters)
        else:
            result = self._handle_generic_interaction(entity1, entity2, interaction_type, parameters)
        
        # 记录交互历史
        interaction_record = {
            'timestamp': datetime.now().isoformat(),
            'entity1_id': entity1.id,
            'entity2_id': entity2.id,
            'interaction_type': interaction_type.value,
            'parameters': parameters,
            'result': result
        }
        
        self.interaction_history.append(interaction_record)
        
        logger.debug(f"[INTERACTION_DEBUG] 交互完成: {result.get('success', False)}")
        return result
    
    def _handle_cooperation(self, entity1: Entity, entity2: Entity, 
                          parameters: Dict[str, Any]) -> Dict[str, Any]:
        """处理合作交互"""
        cooperation_type = parameters.get('cooperation_type', 'resource_sharing')
        
        if cooperation_type == 'resource_sharing':
            # 资源共享合作
            shared_resources = []
            
            for resource_id, resource in entity1.resources.items():
                if resource.amount > 0.5:  # 有足够资源时分享
                    share_amount = resource.amount * 0.2  # 分享20%
                    shared_amount = resource.consume(share_amount)
                    
                    # 给entity2添加资源
                    if resource_id not in entity2.resources:
                        entity2.resources[resource_id] = Resource(
                            id=f"{resource_id}_shared",
                            resource_type=resource.resource_type,
                            amount=0
                        )
                    
                    entity2.resources[resource_id].amount += shared_amount
                    shared_resources.append({
                        'resource_id': resource_id,
                        'amount': shared_amount
                    })
            
            return {
                'success': len(shared_resources) > 0,
                'cooperation_type': cooperation_type,
                'shared_resources': shared_resources,
                'mutual_benefit': len(shared_resources) * 0.1
            }
        
        elif cooperation_type == 'knowledge_sharing':
            # 知识共享合作
            entity1_knowledge = entity1.state.get('knowledge', set())
            entity2_knowledge = entity2.state.get('knowledge', set())
            
            # 交换知识
            if 'knowledge' not in entity1.state:
                entity1.state['knowledge'] = set()
            if 'knowledge' not in entity2.state:
                entity2.state['knowledge'] = set()
            
            shared_knowledge = entity1_knowledge.union(entity2_knowledge)
            entity1.state['knowledge'] = shared_knowledge
            entity2.state['knowledge'] = shared_knowledge
            
            return {
                'success': True,
                'cooperation_type': cooperation_type,
                'knowledge_gained': len(shared_knowledge) - max(len(entity1_knowledge), len(entity2_knowledge))
            }
        
        return {'success': False, 'reason': '未知的合作类型'}
    
    def _handle_competition(self, entity1: Entity, entity2: Entity, 
                          parameters: Dict[str, Any]) -> Dict[str, Any]:
        """处理竞争交互"""
        competition_type = parameters.get('competition_type', 'resource_competition')
        
        if competition_type == 'resource_competition':
            resource_id = parameters.get('resource_id')
            if not resource_id:
                return {'success': False, 'reason': '未指定竞争资源'}
            
            # 准备竞争者信息
            competitors = [
                {
                    'id': entity1.id,
                    'strength': entity1.properties.get('strength', 0.5),
                    'resource_need': entity1.state.get('resource_need', 0.5),
                    'distance': 0.0,  # 假设都在资源旁边
                    'requested_amount': parameters.get('entity1_request', 10.0)
                },
                {
                    'id': entity2.id,
                    'strength': entity2.properties.get('strength', 0.5),
                    'resource_need': entity2.state.get('resource_need', 0.5),
                    'distance': 0.0,
                    'requested_amount': parameters.get('entity2_request', 10.0)
                }
            ]
            
            # 进行资源竞争
            competition_result = self.resource_manager.compete_for_resource(resource_id, competitors)
            
            return {
                'success': True,
                'competition_type': competition_type,
                'winner': competition_result.get('winner'),
                'competition_result': competition_result
            }
        
        return {'success': False, 'reason': '未知的竞争类型'}
    
    def _handle_trade(self, entity1: Entity, entity2: Entity, 
                     parameters: Dict[str, Any]) -> Dict[str, Any]:
        """处理交易交互"""
        offer = parameters.get('offer', {})
        request = parameters.get('request', {})
        
        # 检查entity1是否有提供的资源
        offer_resource_id = offer.get('resource_id')
        offer_amount = offer.get('amount', 0)
        
        if offer_resource_id not in entity1.resources:
            return {'success': False, 'reason': 'entity1没有提供的资源'}
        
        if entity1.resources[offer_resource_id].amount < offer_amount:
            return {'success': False, 'reason': 'entity1资源数量不足'}
        
        # 检查entity2是否有请求的资源
        request_resource_id = request.get('resource_id')
        request_amount = request.get('amount', 0)
        
        if request_resource_id not in entity2.resources:
            return {'success': False, 'reason': 'entity2没有请求的资源'}
        
        if entity2.resources[request_resource_id].amount < request_amount:
            return {'success': False, 'reason': 'entity2资源数量不足'}
        
        # 执行交易
        entity1.resources[offer_resource_id].consume(offer_amount)
        entity2.resources[request_resource_id].consume(request_amount)
        
        # 添加交换的资源
        if offer_resource_id not in entity2.resources:
            entity2.resources[offer_resource_id] = Resource(
                id=f"{offer_resource_id}_traded",
                resource_type=entity1.resources[offer_resource_id].resource_type,
                amount=0
            )
        
        if request_resource_id not in entity1.resources:
            entity1.resources[request_resource_id] = Resource(
                id=f"{request_resource_id}_traded",
                resource_type=entity2.resources[request_resource_id].resource_type,
                amount=0
            )
        
        entity2.resources[offer_resource_id].amount += offer_amount
        entity1.resources[request_resource_id].amount += request_amount
        
        return {
            'success': True,
            'trade_completed': True,
            'offer_fulfilled': offer,
            'request_fulfilled': request
        }
    
    def _handle_communication(self, entity1: Entity, entity2: Entity, 
                            parameters: Dict[str, Any]) -> Dict[str, Any]:
        """处理沟通交互"""
        message = parameters.get('message', '')
        communication_type = parameters.get('communication_type', 'information')
        
        # 简单的信息传递
        if 'received_messages' not in entity2.state:
            entity2.state['received_messages'] = []
        
        entity2.state['received_messages'].append({
            'sender': entity1.id,
            'message': message,
            'type': communication_type,
            'timestamp': datetime.now().isoformat()
        })
        
        # 保持消息历史在合理范围内
        if len(entity2.state['received_messages']) > 50:
            entity2.state['received_messages'] = entity2.state['received_messages'][-50:]
        
        return {
            'success': True,
            'message_delivered': True,
            'communication_type': communication_type
        }
    
    def _handle_learning(self, entity1: Entity, entity2: Entity, 
                        parameters: Dict[str, Any]) -> Dict[str, Any]:
        """处理学习交互"""
        learning_type = parameters.get('learning_type', 'observation')
        
        if learning_type == 'observation':
            # 观察学习
            observed_capabilities = entity2.capabilities.copy()
            learned_capabilities = []
            
            for capability in observed_capabilities:
                if capability not in entity1.capabilities:
                    # 有一定概率学会新能力
                    if random.random() < 0.3:  # 30%概率
                        entity1.capabilities.append(capability)
                        learned_capabilities.append(capability)
            
            return {
                'success': len(learned_capabilities) > 0,
                'learning_type': learning_type,
                'learned_capabilities': learned_capabilities
            }
        
        elif learning_type == 'imitation':
            # 模仿学习
            if 'behavior_patterns' in entity2.state:
                patterns = entity2.state['behavior_patterns']
                if 'behavior_patterns' not in entity1.state:
                    entity1.state['behavior_patterns'] = []
                
                # 学习一些行为模式
                learned_patterns = []
                for pattern in patterns[:3]:  # 最多学习3个模式
                    if pattern not in entity1.state['behavior_patterns']:
                        entity1.state['behavior_patterns'].append(pattern)
                        learned_patterns.append(pattern)
                
                return {
                    'success': len(learned_patterns) > 0,
                    'learning_type': learning_type,
                    'learned_patterns': learned_patterns
                }
        
        return {'success': False, 'reason': '未知的学习类型'}
    
    def _handle_generic_interaction(self, entity1: Entity, entity2: Entity, 
                                  interaction_type: InteractionType, 
                                  parameters: Dict[str, Any]) -> Dict[str, Any]:
        """处理通用交互"""
        return {
            'success': True,
            'interaction_type': interaction_type.value,
            'message': f'{entity1.id} 与 {entity2.id} 进行了 {interaction_type.value} 交互'
        }
    
    def get_interaction_summary(self) -> Dict[str, Any]:
        """获取交互摘要"""
        summary = {
            'total_interactions': len(self.interaction_history),
            'interaction_types': {},
            'successful_interactions': 0,
            'recent_interactions': []
        }
        
        # 统计交互类型
        for record in self.interaction_history:
            interaction_type = record['interaction_type']
            if interaction_type not in summary['interaction_types']:
                summary['interaction_types'][interaction_type] = 0
            summary['interaction_types'][interaction_type] += 1
            
            if record['result'].get('success', False):
                summary['successful_interactions'] += 1
        
        # 最近的交互
        summary['recent_interactions'] = self.interaction_history[-10:]
        
        return summary

class VirtualWorld:
    """虚拟世界 - 整合所有环境功能
    
    这是虚拟世界的核心类，整合了资源管理、环境动力学、交互引擎等功能。
    """
    
    def __init__(self, world_type: EnvironmentType = EnvironmentType.DYNAMIC_LANDSCAPE):
        """初始化虚拟世界"""
        self.world_type = world_type
        self.world_id = str(uuid.uuid4())
        
        # 初始化子系统
        self.resource_manager = ResourceManager()
        self.environment_dynamics = EnvironmentDynamics()
        self.interaction_engine = InteractionEngine(self.resource_manager)
        
        # 世界状态
        self.entities: Dict[str, Entity] = {}
        self.tasks: Dict[str, Task] = {}
        self.world_state = {
            'elapsed_time': 0.0,
            'entity_count': 0,
            'active_tasks': 0,
            'world_events': []
        }
        
        # 初始化世界
        self._initialize_world()
        
        logger.debug(f"[VIRTUAL_WORLD_DEBUG] 初始化虚拟世界: {world_type.value}")
    
    def _initialize_world(self):
        """初始化世界内容"""
        if self.world_type == EnvironmentType.MAZE:
            self._create_maze_environment()
        elif self.world_type == EnvironmentType.RESOURCE_FIELD:
            self._create_resource_field()
        elif self.world_type == EnvironmentType.COMPETITIVE_ARENA:
            self._create_competitive_arena()
        elif self.world_type == EnvironmentType.LEARNING_LAB:
            self._create_learning_lab()
        else:
            self._create_dynamic_landscape()
    
    def _create_maze_environment(self):
        """创建迷宫环境"""
        # 添加迷宫相关资源
        self.resource_manager.add_resource(Resource(
            id="maze_key",
            resource_type=ResourceType.TOOLS,
            amount=1.0,
            position=Position(random.uniform(0, 100), random.uniform(0, 100))
        ))
        
        # 添加寻路任务
        pathfinding_task = Task(
            id="maze_navigation",
            task_type=TaskType.PATHFINDING,
            description="在迷宫中找到出口",
            objectives=[
                {
                    'id': 'reach_exit',
                    'type': 'position',
                    'target_position': {'x': 90, 'y': 90},
                    'max_distance': 5.0,
                    'target_value': 5.0,
                    'comparison': 'gte'
                }
            ],
            rewards={'completion_reward': 100.0},
            time_limit=300.0
        )
        
        self.tasks[pathfinding_task.id] = pathfinding_task
    
    def _create_resource_field(self):
        """创建资源场地"""
        # 添加多种资源
        resource_types = [ResourceType.ENERGY, ResourceType.MATERIALS, ResourceType.INFORMATION]
        
        for i, resource_type in enumerate(resource_types):
            for j in range(3):  # 每种资源3个
                resource = Resource(
                    id=f"{resource_type.value}_{i}_{j}",
                    resource_type=resource_type,
                    amount=random.uniform(50, 100),
                    position=Position(random.uniform(0, 100), random.uniform(0, 100)),
                    renewable=True,
                    regeneration_rate=random.uniform(1, 5)
                )
                self.resource_manager.add_resource(resource)
        
        # 添加收集任务
        collection_task = Task(
            id="resource_collection",
            task_type=TaskType.RESOURCE_COLLECTION,
            description="收集足够的资源",
            objectives=[
                {
                    'id': 'collect_energy',
                    'type': 'collection',
                    'item_type': 'energy',
                    'target_value': 50.0,
                    'comparison': 'gte'
                },
                {
                    'id': 'collect_materials',
                    'type': 'collection',
                    'item_type': 'materials',
                    'target_value': 30.0,
                    'comparison': 'gte'
                }
            ],
            rewards={'completion_reward': 200.0}
        )
        
        self.tasks[collection_task.id] = collection_task
    
    def _create_competitive_arena(self):
        """创建竞技场"""
        # 添加竞争资源
        prize_resource = Resource(
            id="arena_prize",
            resource_type=ResourceType.ENERGY,
            amount=1000.0,
            position=Position(50, 50)
        )
        
        self.resource_manager.add_resource(prize_resource)
        
        # 添加竞争任务
        competition_task = Task(
            id="arena_competition",
            task_type=TaskType.COMPETITION,
            description="在竞技场中获胜",
            objectives=[
                {
                    'id': 'win_competition',
                    'type': 'metric',
                    'metric': 'competition_score',
                    'target_value': 100.0,
                    'comparison': 'gte'
                }
            ],
            rewards={'victory_reward': 500.0},
            time_limit=600.0
        )
        
        self.tasks[competition_task.id] = competition_task
    
    def _create_learning_lab(self):
        """创建学习实验室"""
        # 添加知识资源
        knowledge_resource = Resource(
            id="knowledge_base",
            resource_type=ResourceType.KNOWLEDGE,
            amount=100.0,
            renewable=True,
            regeneration_rate=2.0
        )
        
        self.resource_manager.add_resource(knowledge_resource)
        
        # 添加学习任务
        learning_task = Task(
            id="knowledge_acquisition",
            task_type=TaskType.LEARNING,
            description="获取足够的知识",
            objectives=[
                {
                    'id': 'acquire_knowledge',
                    'type': 'metric',
                    'metric': 'knowledge_level',
                    'target_value': 80.0,
                    'comparison': 'gte'
                }
            ],
            rewards={'learning_reward': 150.0}
        )
        
        self.tasks[learning_task.id] = learning_task
    
    def _create_dynamic_landscape(self):
        """创建动态地形"""
        # 添加多样化资源
        all_resource_types = list(ResourceType)
        
        for resource_type in all_resource_types:
            resource = Resource(
                id=f"dynamic_{resource_type.value}",
                resource_type=resource_type,
                amount=random.uniform(20, 80),
                position=Position(random.uniform(0, 100), random.uniform(0, 100)),
                renewable=random.choice([True, False]),
                regeneration_rate=random.uniform(0.5, 3.0) if random.choice([True, False]) else 0.0
            )
            self.resource_manager.add_resource(resource)
        
        # 添加适应任务
        adaptation_task = Task(
            id="environment_adaptation",
            task_type=TaskType.ADAPTATION,
            description="适应动态变化的环境",
            objectives=[
                {
                    'id': 'maintain_stability',
                    'type': 'metric',
                    'metric': 'stability_score',
                    'target_value': 70.0,
                    'comparison': 'gte'
                },
                {
                    'id': 'resource_efficiency',
                    'type': 'metric',
                    'metric': 'resource_efficiency',
                    'target_value': 60.0,
                    'comparison': 'gte'
                }
            ],
            rewards={'adaptation_reward': 300.0}
        )
        
        self.tasks[adaptation_task.id] = adaptation_task
    
    def add_entity(self, entity: Entity):
        """添加实体到世界"""
        self.entities[entity.id] = entity
        self.world_state['entity_count'] = len(self.entities)
        
        logger.debug(f"[VIRTUAL_WORLD_DEBUG] 添加实体: {entity.id}")
    
    def remove_entity(self, entity_id: str):
        """从世界移除实体"""
        if entity_id in self.entities:
            del self.entities[entity_id]
            self.world_state['entity_count'] = len(self.entities)
            logger.debug(f"[VIRTUAL_WORLD_DEBUG] 移除实体: {entity_id}")
    
    def add_task(self, task: Task):
        """添加任务"""
        self.tasks[task.id] = task
        self.world_state['active_tasks'] = len(self.tasks)
        
        logger.debug(f"[VIRTUAL_WORLD_DEBUG] 添加任务: {task.id}")
    
    def update_world(self, time_delta: float) -> Dict[str, Any]:
        """更新世界状态"""
        update_result = {
            'time_delta': time_delta,
            'environment_changes': {},
            'task_updates': {},
            'entity_updates': {},
            'world_events': []
        }
        
        # 更新时间
        self.world_state['elapsed_time'] += time_delta
        
        # 更新环境动力学
        env_update = self.environment_dynamics.update_environment(self.world_state, time_delta)
        update_result['environment_changes'] = env_update
        
        # 更新资源
        self.resource_manager.update_resources(time_delta)
        
        # 更新任务状态
        for task_id, task in self.tasks.items():
            task_completion = task.evaluate_completion(self.world_state)
            update_result['task_updates'][task_id] = task_completion
            
            if task_completion['completed']:
                update_result['world_events'].append({
                    'type': 'task_completed',
                    'task_id': task_id,
                    'completion_time': self.world_state['elapsed_time']
                })
        
        # 更新实体状态（简化）
        for entity_id, entity in self.entities.items():
            # 简单的实体状态更新
            if 'last_update' not in entity.state:
                entity.state['last_update'] = 0.0
            
            entity.state['last_update'] = self.world_state['elapsed_time']
            update_result['entity_updates'][entity_id] = {
                'position': {'x': entity.position.x, 'y': entity.position.y, 'z': entity.position.z},
                'resource_count': len(entity.resources)
            }
        
        # 记录世界事件
        self.world_state['world_events'].extend(update_result['world_events'])
        
        # 保持事件历史在合理范围内
        if len(self.world_state['world_events']) > 1000:
            self.world_state['world_events'] = self.world_state['world_events'][-1000:]
        
        logger.debug(f"[VIRTUAL_WORLD_DEBUG] 世界更新完成，时间: {self.world_state['elapsed_time']:.2f}")
        
        return update_result
    
    def simulate_entity_interaction(self, entity1_id: str, entity2_id: str, 
                                  interaction_type: InteractionType, 
                                  parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """模拟实体交互"""
        if entity1_id not in self.entities or entity2_id not in self.entities:
            return {'success': False, 'reason': '实体不存在'}
        
        entity1 = self.entities[entity1_id]
        entity2 = self.entities[entity2_id]
        
        return self.interaction_engine.process_interaction(entity1, entity2, interaction_type, parameters)
    
    def get_world_summary(self) -> Dict[str, Any]:
        """获取世界摘要"""
        return {
            'world_id': self.world_id,
            'world_type': self.world_type.value,
            'world_state': copy.deepcopy(self.world_state),
            'entity_count': len(self.entities),
            'task_count': len(self.tasks),
            'resource_summary': self.resource_manager.get_resource_summary(),
            'interaction_summary': self.interaction_engine.get_interaction_summary(),
            'environmental_factors': copy.deepcopy(self.environment_dynamics.environmental_factors)
        }
    
    def get_entity_view(self, entity_id: str, view_range: float = 10.0) -> Dict[str, Any]:
        """获取实体的环境视图"""
        if entity_id not in self.entities:
            return {'error': '实体不存在'}
        
        entity = self.entities[entity_id]
        entity_view = {
            'entity_position': {'x': entity.position.x, 'y': entity.position.y, 'z': entity.position.z},
            'nearby_entities': [],
            'nearby_resources': [],
            'environmental_factors': copy.deepcopy(self.environment_dynamics.environmental_factors),
            'available_tasks': []
        }
        
        # 查找附近的实体
        for other_id, other_entity in self.entities.items():
            if other_id != entity_id:
                distance = entity.position.distance_to(other_entity.position)
                if distance <= view_range:
                    entity_view['nearby_entities'].append({
                        'id': other_id,
                        'type': other_entity.entity_type,
                        'distance': distance,
                        'position': {'x': other_entity.position.x, 'y': other_entity.position.y, 'z': other_entity.position.z}
                    })
        
        # 查找附近的资源
        for resource_id, resource in self.resource_manager.resources.items():
            if resource.position:
                distance = entity.position.distance_to(resource.position)
                if distance <= view_range:
                    entity_view['nearby_resources'].append({
                        'id': resource_id,
                        'type': resource.resource_type.value,
                        'amount': resource.amount,
                        'distance': distance,
                        'position': {'x': resource.position.x, 'y': resource.position.y, 'z': resource.position.z}
                    })
        
        # 可用任务
        for task_id, task in self.tasks.items():
            task_completion = task.evaluate_completion(self.world_state)
            if not task_completion['completed']:
                entity_view['available_tasks'].append({
                    'id': task_id,
                    'type': task.task_type.value,
                    'description': task.description,
                    'progress': task_completion['progress'],
                    'difficulty': task.difficulty
                })
        
        return entity_view