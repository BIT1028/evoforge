#!/usr/bin/env python3
"""
WebSocket连接管理
"""
from typing import Dict, Set
from collections import defaultdict
from fastapi import WebSocket
import structlog
import json

logger = structlog.get_logger()

class WebSocketManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        self.connections: Dict[str, WebSocket] = {}
        self.rooms: Dict[str, Set[str]] = defaultdict(set)
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """建立WebSocket连接"""
        await websocket.accept()
        self.connections[client_id] = websocket
        
        # 默认加入evolution房间
        await self.join_room(client_id, "evolution")
        
        logger.info("WebSocket连接建立", client_id=client_id)
    
    async def disconnect(self, client_id: str):
        """断开WebSocket连接"""
        if client_id in self.connections:
            del self.connections[client_id]
        
        # 从所有房间移除
        for room in self.rooms.values():
            room.discard(client_id)
        
        logger.info("WebSocket连接断开", client_id=client_id)
    
    async def join_room(self, client_id: str, room: str):
        """加入房间"""
        self.rooms[room].add(client_id)
        logger.debug("客户端加入房间", client_id=client_id, room=room)
    
    async def leave_room(self, client_id: str, room: str):
        """离开房间"""
        self.rooms[room].discard(client_id)
        logger.debug("客户端离开房间", client_id=client_id, room=room)
    
    async def send_to_client(self, client_id: str, message: dict):
        """向特定客户端发送消息"""
        if client_id in self.connections:
            try:
                await self.connections[client_id].send_text(json.dumps(message))
                logger.debug("发送消息到客户端", client_id=client_id, message_type=message.get("type"))
            except Exception as e:
                logger.error("发送消息失败", client_id=client_id, error=str(e))
                await self.disconnect(client_id)
    
    async def broadcast_to_room(self, room: str, message: dict):
        """向房间广播消息"""
        if room in self.rooms:
            disconnected_clients = []
            
            for client_id in self.rooms[room]:
                if client_id in self.connections:
                    try:
                        await self.connections[client_id].send_text(json.dumps(message))
                    except Exception as e:
                        logger.error("广播消息失败", client_id=client_id, error=str(e))
                        disconnected_clients.append(client_id)
            
            # 清理断开的连接
            for client_id in disconnected_clients:
                await self.disconnect(client_id)
            
            logger.debug(
                "房间广播完成",
                room=room,
                message_type=message.get("type"),
                client_count=len(self.rooms[room]) - len(disconnected_clients)
            )
    
    async def broadcast_to_all(self, message: dict):
        """向所有连接广播消息"""
        disconnected_clients = []
        
        for client_id, websocket in self.connections.items():
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error("全局广播失败", client_id=client_id, error=str(e))
                disconnected_clients.append(client_id)
        
        # 清理断开的连接
        for client_id in disconnected_clients:
            await self.disconnect(client_id)
        
        logger.debug(
            "全局广播完成",
            message_type=message.get("type"),
            client_count=len(self.connections) - len(disconnected_clients)
        )

# 全局WebSocket管理器实例
websocket_manager = WebSocketManager()