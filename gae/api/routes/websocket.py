# -*- coding: utf-8 -*-
"""
WebSocket实时通信路由

提供WebSocket连接管理和实时数据推送：
- 进化状态实时推送
- 任务更新通知
- 系统监控数据流
- 评估结果推送
- 错误和警告通知
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from typing import Dict, List, Set, Optional, Any
import json
import logging
import asyncio
from datetime import datetime
from enum import Enum
import uuid

from ..models.requests import WebSocketSubscribeRequest, WebSocketUnsubscribeRequest
from ..models.responses import WebSocketMessageResponse
from ..models.dtos import (
    IndividualDTO,
    ExperimentDTO,
    TaskDTO,
    EvaluationDTO,
    SystemStatusDTO
)
from ...config.config_manager import ConfigManager
from ...core.error_handler import EvoForgeError, ErrorType
from ...core.module_coordinator import ModuleCoordinator
from ...database.database_manager import DatabaseManager

# 创建路由器
router = APIRouter()
logger = logging.getLogger(__name__)

class MessageType(str, Enum):
    """WebSocket消息类型"""
    EVOLUTION_STATUS = "evolution_status"
    TASK_UPDATE = "task_update"
    EVALUATION_RESULT = "evaluation_result"
    SYSTEM_STATUS = "system_status"
    ERROR_NOTIFICATION = "error_notification"
    WARNING_NOTIFICATION = "warning_notification"
    INFO_NOTIFICATION = "info_notification"
    EXPERIMENT_UPDATE = "experiment_update"
    INDIVIDUAL_UPDATE = "individual_update"
    HEARTBEAT = "heartbeat"
    SUBSCRIPTION_CONFIRMED = "subscription_confirmed"
    SUBSCRIPTION_CANCELLED = "subscription_cancelled"

class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        # 活跃连接：{connection_id: websocket}
        self.active_connections: Dict[str, WebSocket] = {}
        # 订阅关系：{connection_id: {message_types}}
        self.subscriptions: Dict[str, Set[str]] = {}
        # 实验订阅：{experiment_id: {connection_ids}}
        self.experiment_subscriptions: Dict[str, Set[str]] = {}
        # 任务订阅：{task_id: {connection_ids}}
        self.task_subscriptions: Dict[str, Set[str]] = {}
        # 连接元数据：{connection_id: metadata}
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, connection_id: str = None) -> str:
        """建立WebSocket连接"""
        if connection_id is None:
            connection_id = str(uuid.uuid4())
        
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        self.subscriptions[connection_id] = set()
        self.connection_metadata[connection_id] = {
            'connected_at': datetime.utcnow().isoformat(),
            'last_heartbeat': datetime.utcnow().isoformat(),
            'client_info': {}
        }
        
        logger.info(f"WebSocket connection established: {connection_id}")
        
        # 发送连接确认消息
        await self.send_personal_message(
            connection_id,
            {
                'type': MessageType.INFO_NOTIFICATION,
                'data': {
                    'connection_id': connection_id,
                    'message': 'WebSocket connection established'
                },
                'timestamp': datetime.utcnow().isoformat()
            }
        )
        
        return connection_id
    
    def disconnect(self, connection_id: str):
        """断开WebSocket连接"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        
        if connection_id in self.subscriptions:
            del self.subscriptions[connection_id]
        
        if connection_id in self.connection_metadata:
            del self.connection_metadata[connection_id]
        
        # 清理实验订阅
        for experiment_id, subscribers in self.experiment_subscriptions.items():
            subscribers.discard(connection_id)
        
        # 清理任务订阅
        for task_id, subscribers in self.task_subscriptions.items():
            subscribers.discard(connection_id)
        
        logger.info(f"WebSocket connection disconnected: {connection_id}")
    
    async def send_personal_message(self, connection_id: str, message: dict):
        """发送个人消息"""
        if connection_id in self.active_connections:
            try:
                websocket = self.active_connections[connection_id]
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message to {connection_id}: {str(e)}")
                self.disconnect(connection_id)
    
    async def broadcast_message(self, message: dict, message_type: str = None):
        """广播消息给所有订阅者"""
        disconnected_connections = []
        
        for connection_id, websocket in self.active_connections.items():
            # 检查是否订阅了该消息类型
            if message_type and message_type not in self.subscriptions.get(connection_id, set()):
                continue
            
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error broadcasting to {connection_id}: {str(e)}")
                disconnected_connections.append(connection_id)
        
        # 清理断开的连接
        for connection_id in disconnected_connections:
            self.disconnect(connection_id)
    
    async def broadcast_to_experiment_subscribers(self, experiment_id: str, message: dict):
        """向实验订阅者广播消息"""
        if experiment_id not in self.experiment_subscriptions:
            return
        
        subscribers = self.experiment_subscriptions[experiment_id].copy()
        disconnected_connections = []
        
        for connection_id in subscribers:
            if connection_id in self.active_connections:
                try:
                    websocket = self.active_connections[connection_id]
                    await websocket.send_text(json.dumps(message))
                except Exception as e:
                    logger.error(f"Error sending to experiment subscriber {connection_id}: {str(e)}")
                    disconnected_connections.append(connection_id)
        
        # 清理断开的连接
        for connection_id in disconnected_connections:
            self.disconnect(connection_id)
    
    async def broadcast_to_task_subscribers(self, task_id: str, message: dict):
        """向任务订阅者广播消息"""
        if task_id not in self.task_subscriptions:
            return
        
        subscribers = self.task_subscriptions[task_id].copy()
        disconnected_connections = []
        
        for connection_id in subscribers:
            if connection_id in self.active_connections:
                try:
                    websocket = self.active_connections[connection_id]
                    await websocket.send_text(json.dumps(message))
                except Exception as e:
                    logger.error(f"Error sending to task subscriber {connection_id}: {str(e)}")
                    disconnected_connections.append(connection_id)
        
        # 清理断开的连接
        for connection_id in disconnected_connections:
            self.disconnect(connection_id)
    
    def subscribe(self, connection_id: str, message_types: List[str]):
        """订阅消息类型"""
        if connection_id in self.subscriptions:
            self.subscriptions[connection_id].update(message_types)
            logger.info(f"Connection {connection_id} subscribed to: {message_types}")
    
    def unsubscribe(self, connection_id: str, message_types: List[str]):
        """取消订阅消息类型"""
        if connection_id in self.subscriptions:
            self.subscriptions[connection_id].difference_update(message_types)
            logger.info(f"Connection {connection_id} unsubscribed from: {message_types}")
    
    def subscribe_to_experiment(self, connection_id: str, experiment_id: str):
        """订阅实验更新"""
        if experiment_id not in self.experiment_subscriptions:
            self.experiment_subscriptions[experiment_id] = set()
        self.experiment_subscriptions[experiment_id].add(connection_id)
        logger.info(f"Connection {connection_id} subscribed to experiment: {experiment_id}")
    
    def unsubscribe_from_experiment(self, connection_id: str, experiment_id: str):
        """取消订阅实验更新"""
        if experiment_id in self.experiment_subscriptions:
            self.experiment_subscriptions[experiment_id].discard(connection_id)
            logger.info(f"Connection {connection_id} unsubscribed from experiment: {experiment_id}")
    
    def subscribe_to_task(self, connection_id: str, task_id: str):
        """订阅任务更新"""
        if task_id not in self.task_subscriptions:
            self.task_subscriptions[task_id] = set()
        self.task_subscriptions[task_id].add(connection_id)
        logger.info(f"Connection {connection_id} subscribed to task: {task_id}")
    
    def unsubscribe_from_task(self, connection_id: str, task_id: str):
        """取消订阅任务更新"""
        if task_id in self.task_subscriptions:
            self.task_subscriptions[task_id].discard(connection_id)
            logger.info(f"Connection {connection_id} unsubscribed from task: {task_id}")
    
    def get_connection_count(self) -> int:
        """获取活跃连接数"""
        return len(self.active_connections)
    
    def get_subscription_stats(self) -> Dict[str, Any]:
        """获取订阅统计信息"""
        return {
            'total_connections': len(self.active_connections),
            'total_subscriptions': sum(len(subs) for subs in self.subscriptions.values()),
            'experiment_subscriptions': len(self.experiment_subscriptions),
            'task_subscriptions': len(self.task_subscriptions),
            'subscription_breakdown': {
                msg_type: sum(1 for subs in self.subscriptions.values() if msg_type in subs)
                for msg_type in MessageType
            }
        }

# 全局连接管理器
connection_manager = ConnectionManager()

# 依赖注入
async def get_config_manager() -> ConfigManager:
    """获取配置管理器"""
    # 这里应该从应用状态中获取
    return None

async def get_module_coordinator() -> ModuleCoordinator:
    """获取模块协调器"""
    # 这里应该从应用状态中获取
    return None

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    connection_id: Optional[str] = Query(None, description="连接ID"),
    client_info: Optional[str] = Query(None, description="客户端信息")
):
    """
    WebSocket连接端点
    
    Args:
        websocket: WebSocket连接
        connection_id: 可选的连接ID
        client_info: 客户端信息
    """
    actual_connection_id = await connection_manager.connect(websocket, connection_id)
    
    # 更新客户端信息
    if client_info:
        try:
            client_data = json.loads(client_info)
            connection_manager.connection_metadata[actual_connection_id]['client_info'] = client_data
        except json.JSONDecodeError:
            logger.warning(f"Invalid client_info JSON: {client_info}")
    
    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                await handle_websocket_message(actual_connection_id, message)
            except json.JSONDecodeError:
                await connection_manager.send_personal_message(
                    actual_connection_id,
                    {
                        'type': MessageType.ERROR_NOTIFICATION,
                        'data': {
                            'error': 'Invalid JSON format',
                            'received_data': data
                        },
                        'timestamp': datetime.utcnow().isoformat()
                    }
                )
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {str(e)}")
                await connection_manager.send_personal_message(
                    actual_connection_id,
                    {
                        'type': MessageType.ERROR_NOTIFICATION,
                        'data': {
                            'error': 'Message processing failed',
                            'details': str(e)
                        },
                        'timestamp': datetime.utcnow().isoformat()
                    }
                )
    
    except WebSocketDisconnect:
        connection_manager.disconnect(actual_connection_id)
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        connection_manager.disconnect(actual_connection_id)

async def handle_websocket_message(connection_id: str, message: dict):
    """
    处理WebSocket消息
    
    Args:
        connection_id: 连接ID
        message: 消息内容
    """
    message_type = message.get('type')
    data = message.get('data', {})
    
    if message_type == 'subscribe':
        # 订阅消息类型
        message_types = data.get('message_types', [])
        connection_manager.subscribe(connection_id, message_types)
        
        await connection_manager.send_personal_message(
            connection_id,
            {
                'type': MessageType.SUBSCRIPTION_CONFIRMED,
                'data': {
                    'subscribed_types': message_types
                },
                'timestamp': datetime.utcnow().isoformat()
            }
        )
    
    elif message_type == 'unsubscribe':
        # 取消订阅消息类型
        message_types = data.get('message_types', [])
        connection_manager.unsubscribe(connection_id, message_types)
        
        await connection_manager.send_personal_message(
            connection_id,
            {
                'type': MessageType.SUBSCRIPTION_CANCELLED,
                'data': {
                    'unsubscribed_types': message_types
                },
                'timestamp': datetime.utcnow().isoformat()
            }
        )
    
    elif message_type == 'subscribe_experiment':
        # 订阅实验更新
        experiment_id = data.get('experiment_id')
        if experiment_id:
            connection_manager.subscribe_to_experiment(connection_id, experiment_id)
            
            await connection_manager.send_personal_message(
                connection_id,
                {
                    'type': MessageType.SUBSCRIPTION_CONFIRMED,
                    'data': {
                        'experiment_id': experiment_id,
                        'message': 'Subscribed to experiment updates'
                    },
                    'timestamp': datetime.utcnow().isoformat()
                }
            )
    
    elif message_type == 'unsubscribe_experiment':
        # 取消订阅实验更新
        experiment_id = data.get('experiment_id')
        if experiment_id:
            connection_manager.unsubscribe_from_experiment(connection_id, experiment_id)
            
            await connection_manager.send_personal_message(
                connection_id,
                {
                    'type': MessageType.SUBSCRIPTION_CANCELLED,
                    'data': {
                        'experiment_id': experiment_id,
                        'message': 'Unsubscribed from experiment updates'
                    },
                    'timestamp': datetime.utcnow().isoformat()
                }
            )
    
    elif message_type == 'subscribe_task':
        # 订阅任务更新
        task_id = data.get('task_id')
        if task_id:
            connection_manager.subscribe_to_task(connection_id, task_id)
            
            await connection_manager.send_personal_message(
                connection_id,
                {
                    'type': MessageType.SUBSCRIPTION_CONFIRMED,
                    'data': {
                        'task_id': task_id,
                        'message': 'Subscribed to task updates'
                    },
                    'timestamp': datetime.utcnow().isoformat()
                }
            )
    
    elif message_type == 'unsubscribe_task':
        # 取消订阅任务更新
        task_id = data.get('task_id')
        if task_id:
            connection_manager.unsubscribe_from_task(connection_id, task_id)
            
            await connection_manager.send_personal_message(
                connection_id,
                {
                    'type': MessageType.SUBSCRIPTION_CANCELLED,
                    'data': {
                        'task_id': task_id,
                        'message': 'Unsubscribed from task updates'
                    },
                    'timestamp': datetime.utcnow().isoformat()
                }
            )
    
    elif message_type == 'heartbeat':
        # 心跳消息
        connection_manager.connection_metadata[connection_id]['last_heartbeat'] = datetime.utcnow().isoformat()
        
        await connection_manager.send_personal_message(
            connection_id,
            {
                'type': MessageType.HEARTBEAT,
                'data': {
                    'server_time': datetime.utcnow().isoformat()
                },
                'timestamp': datetime.utcnow().isoformat()
            }
        )
    
    elif message_type == 'get_status':
        # 获取连接状态
        stats = connection_manager.get_subscription_stats()
        metadata = connection_manager.connection_metadata.get(connection_id, {})
        
        await connection_manager.send_personal_message(
            connection_id,
            {
                'type': MessageType.INFO_NOTIFICATION,
                'data': {
                    'connection_id': connection_id,
                    'metadata': metadata,
                    'subscriptions': list(connection_manager.subscriptions.get(connection_id, set())),
                    'server_stats': stats
                },
                'timestamp': datetime.utcnow().isoformat()
            }
        )
    
    else:
        # 未知消息类型
        await connection_manager.send_personal_message(
            connection_id,
            {
                'type': MessageType.ERROR_NOTIFICATION,
                'data': {
                    'error': f'Unknown message type: {message_type}',
                    'supported_types': [
                        'subscribe', 'unsubscribe', 'subscribe_experiment',
                        'unsubscribe_experiment', 'subscribe_task', 'unsubscribe_task',
                        'heartbeat', 'get_status'
                    ]
                },
                'timestamp': datetime.utcnow().isoformat()
            }
        )

# WebSocket消息推送函数（供其他模块调用）

async def push_evolution_status(experiment_id: str, status_data: dict):
    """推送进化状态更新"""
    message = {
        'type': MessageType.EVOLUTION_STATUS,
        'data': {
            'experiment_id': experiment_id,
            'status': status_data
        },
        'timestamp': datetime.utcnow().isoformat()
    }
    
    # 广播给订阅进化状态的连接
    await connection_manager.broadcast_message(message, MessageType.EVOLUTION_STATUS)
    
    # 广播给订阅该实验的连接
    await connection_manager.broadcast_to_experiment_subscribers(experiment_id, message)

async def push_task_update(task_id: str, task_data: TaskDTO):
    """推送任务更新"""
    message = {
        'type': MessageType.TASK_UPDATE,
        'data': {
            'task_id': task_id,
            'task': task_data.dict()
        },
        'timestamp': datetime.utcnow().isoformat()
    }
    
    # 广播给订阅任务更新的连接
    await connection_manager.broadcast_message(message, MessageType.TASK_UPDATE)
    
    # 广播给订阅该任务的连接
    await connection_manager.broadcast_to_task_subscribers(task_id, message)

async def push_evaluation_result(evaluation_data: EvaluationDTO):
    """推送评估结果"""
    message = {
        'type': MessageType.EVALUATION_RESULT,
        'data': {
            'evaluation': evaluation_data.dict()
        },
        'timestamp': datetime.utcnow().isoformat()
    }
    
    # 广播给订阅评估结果的连接
    await connection_manager.broadcast_message(message, MessageType.EVALUATION_RESULT)
    
    # 如果有实验ID，也广播给实验订阅者
    if evaluation_data.experiment_id:
        await connection_manager.broadcast_to_experiment_subscribers(
            evaluation_data.experiment_id, message
        )

async def push_system_status(status_data: SystemStatusDTO):
    """推送系统状态更新"""
    message = {
        'type': MessageType.SYSTEM_STATUS,
        'data': {
            'system_status': status_data.dict()
        },
        'timestamp': datetime.utcnow().isoformat()
    }
    
    # 广播给订阅系统状态的连接
    await connection_manager.broadcast_message(message, MessageType.SYSTEM_STATUS)

async def push_error_notification(error: EvoForgeError, context: dict = None):
    """推送错误通知"""
    message = {
        'type': MessageType.ERROR_NOTIFICATION,
        'data': {
            'error_type': error.error_type.value,
            'error_code': error.error_code,
            'message': error.message,
            'details': error.details,
            'context': context or {}
        },
        'timestamp': datetime.utcnow().isoformat()
    }
    
    # 广播给所有连接
    await connection_manager.broadcast_message(message, MessageType.ERROR_NOTIFICATION)

async def push_warning_notification(message_text: str, details: dict = None):
    """推送警告通知"""
    message = {
        'type': MessageType.WARNING_NOTIFICATION,
        'data': {
            'message': message_text,
            'details': details or {}
        },
        'timestamp': datetime.utcnow().isoformat()
    }
    
    # 广播给订阅警告通知的连接
    await connection_manager.broadcast_message(message, MessageType.WARNING_NOTIFICATION)

async def push_info_notification(message_text: str, details: dict = None):
    """推送信息通知"""
    message = {
        'type': MessageType.INFO_NOTIFICATION,
        'data': {
            'message': message_text,
            'details': details or {}
        },
        'timestamp': datetime.utcnow().isoformat()
    }
    
    # 广播给订阅信息通知的连接
    await connection_manager.broadcast_message(message, MessageType.INFO_NOTIFICATION)

async def push_experiment_update(experiment_data: ExperimentDTO):
    """推送实验更新"""
    message = {
        'type': MessageType.EXPERIMENT_UPDATE,
        'data': {
            'experiment': experiment_data.dict()
        },
        'timestamp': datetime.utcnow().isoformat()
    }
    
    # 广播给订阅实验更新的连接
    await connection_manager.broadcast_message(message, MessageType.EXPERIMENT_UPDATE)
    
    # 广播给订阅该实验的连接
    await connection_manager.broadcast_to_experiment_subscribers(
        experiment_data.experiment_id, message
    )

async def push_individual_update(individual_data: IndividualDTO):
    """推送个体更新"""
    message = {
        'type': MessageType.INDIVIDUAL_UPDATE,
        'data': {
            'individual': individual_data.dict()
        },
        'timestamp': datetime.utcnow().isoformat()
    }
    
    # 广播给订阅个体更新的连接
    await connection_manager.broadcast_message(message, MessageType.INDIVIDUAL_UPDATE)
    
    # 如果有实验ID，也广播给实验订阅者
    if individual_data.experiment_id:
        await connection_manager.broadcast_to_experiment_subscribers(
            individual_data.experiment_id, message
        )

# 获取连接管理器状态的API端点
@router.get("/stats")
async def get_websocket_stats():
    """获取WebSocket连接统计信息"""
    return connection_manager.get_subscription_stats()

# 心跳检查任务
async def heartbeat_check_task():
    """定期检查连接心跳"""
    while True:
        try:
            current_time = datetime.utcnow()
            timeout_threshold = current_time - timedelta(minutes=5)  # 5分钟超时
            
            disconnected_connections = []
            
            for connection_id, metadata in connection_manager.connection_metadata.items():
                last_heartbeat_str = metadata.get('last_heartbeat')
                if last_heartbeat_str:
                    last_heartbeat = datetime.fromisoformat(last_heartbeat_str.replace('Z', '+00:00'))
                    if last_heartbeat < timeout_threshold:
                        disconnected_connections.append(connection_id)
            
            # 断开超时连接
            for connection_id in disconnected_connections:
                logger.info(f"Disconnecting inactive connection: {connection_id}")
                connection_manager.disconnect(connection_id)
            
            # 等待30秒后再次检查
            await asyncio.sleep(30)
            
        except Exception as e:
            logger.error(f"Error in heartbeat check task: {str(e)}")
            await asyncio.sleep(30)

# 启动心跳检查任务
asyncio.create_task(heartbeat_check_task())