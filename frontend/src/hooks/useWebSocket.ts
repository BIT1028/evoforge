import { useState, useEffect, useRef, useCallback } from 'react';

export interface WebSocketMessage {
  type: string;
  data: any;
  timestamp: string;
}

export interface UseWebSocketOptions {
  reconnectAttempts?: number;
  reconnectDelay?: number;
  autoConnect?: boolean;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: any) => void;
  onMessage?: (message: WebSocketMessage) => void;
}

export interface UseWebSocketReturn {
  socket: WebSocket | null;
  isConnected: boolean;
  isConnecting: boolean;
  lastMessage: WebSocketMessage | null;
  connectionError: string | null;
  connect: () => void;
  disconnect: () => void;
  sendMessage: (type: string, data: any) => void;
  joinRoom: (room: string) => void;
  leaveRoom: (room: string) => void;
}

export const useWebSocket = (
  url: string,
  options: UseWebSocketOptions = {}
): UseWebSocketReturn => {
  const {
    reconnectAttempts = 5,
    reconnectDelay = 1000,
    autoConnect = true,
    onConnect,
    onDisconnect,
    onError,
    onMessage
  } = options;

  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  
  const reconnectCount = useRef(0);
  const reconnectTimer = useRef<NodeJS.Timeout | null>(null);
  const shouldReconnect = useRef(true);

  // 连接WebSocket
  const connect = useCallback(() => {
    if (socket?.readyState === WebSocket.OPEN) {
      console.log('WebSocket已连接，跳过重复连接');
      return;
    }

    setIsConnecting(true);
    setConnectionError(null);

    try {
      // 创建原生WebSocket连接
      const newSocket = new WebSocket(url);

      // 连接成功
      newSocket.onopen = () => {
        console.log('WebSocket连接成功');
        setIsConnected(true);
        setIsConnecting(false);
        setConnectionError(null);
        reconnectCount.current = 0;
        onConnect?.();
      };

      // 连接断开
      newSocket.onclose = (event) => {
        console.log('WebSocket连接断开:', event.code, event.reason);
        setIsConnected(false);
        setIsConnecting(false);
        onDisconnect?.();

        // 自动重连
        if (shouldReconnect.current && reconnectCount.current < reconnectAttempts) {
          scheduleReconnect();
        }
      };

      // 连接错误
      newSocket.onerror = (error) => {
        console.error('WebSocket连接错误:', error);
        setIsConnecting(false);
        setConnectionError('连接失败');
        onError?.(error);

        // 自动重连
        if (shouldReconnect.current && reconnectCount.current < reconnectAttempts) {
          scheduleReconnect();
        }
      };

      // 接收消息
      newSocket.onmessage = (event) => {
        try {
          const parsedData = JSON.parse(event.data);
          const message: WebSocketMessage = {
            type: parsedData.type || 'message',
            data: parsedData.data || parsedData,
            timestamp: new Date().toISOString()
          };
          
          console.log('收到WebSocket消息:', message);
          setLastMessage(message);
          onMessage?.(message);
        } catch (error) {
          console.error('解析WebSocket消息失败:', error);
          // 如果解析失败，创建一个原始消息
          const message: WebSocketMessage = {
            type: 'raw',
            data: event.data,
            timestamp: new Date().toISOString()
          };
          setLastMessage(message);
          onMessage?.(message);
        }
      };

      setSocket(newSocket);
    } catch (error) {
      console.error('创建WebSocket连接失败:', error);
      setIsConnecting(false);
      setConnectionError('创建连接失败');
      onError?.(error);
    }
  }, [url, onConnect, onDisconnect, onError, onMessage, reconnectAttempts]);

  // 断开连接
  const disconnect = useCallback(() => {
    shouldReconnect.current = false;
    
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current);
      reconnectTimer.current = null;
    }

    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.close();
    }
    setSocket(null);
    
    setIsConnected(false);
    setIsConnecting(false);
  }, [socket]);

  // 计划重连
  const scheduleReconnect = useCallback(() => {
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current);
    }

    const delay = reconnectDelay * Math.pow(2, reconnectCount.current); // 指数退避
    
    console.log(`计划在${delay}ms后重连 (第${reconnectCount.current + 1}次尝试)`);
    
    reconnectTimer.current = setTimeout(() => {
      reconnectCount.current++;
      connect();
    }, delay);
  }, [connect, reconnectDelay]);

  // 发送消息
  const sendMessage = useCallback((type: string, data: any) => {
    if (socket?.readyState === WebSocket.OPEN) {
      const message = {
        type,
        data,
        timestamp: new Date().toISOString()
      };
      socket.send(JSON.stringify(message));
      console.log('发送WebSocket消息:', message);
    } else {
      console.warn('WebSocket未连接，无法发送消息');
    }
  }, [socket]);

  // 加入房间
  const joinRoom = useCallback((room: string) => {
    if (socket?.readyState === WebSocket.OPEN) {
      const message = {
        type: 'join_room',
        data: { room },
        timestamp: new Date().toISOString()
      };
      socket.send(JSON.stringify(message));
      console.log('加入房间:', room);
    }
  }, [socket]);

  // 离开房间
  const leaveRoom = useCallback((room: string) => {
    if (socket?.readyState === WebSocket.OPEN) {
      const message = {
        type: 'leave_room',
        data: { room },
        timestamp: new Date().toISOString()
      };
      socket.send(JSON.stringify(message));
      console.log('离开房间:', room);
    }
  }, [socket]);

  // 自动连接
  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [autoConnect, connect, disconnect]);

  // 清理定时器
  useEffect(() => {
    return () => {
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current);
      }
    };
  }, []);

  return {
    socket,
    isConnected,
    isConnecting,
    lastMessage,
    connectionError,
    connect,
    disconnect,
    sendMessage,
    joinRoom,
    leaveRoom
  };
};

// 简化版WebSocket钩子（仅用于接收消息）
export const useWebSocketSimple = (url: string) => {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<any>(null);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // 创建WebSocket连接
    const ws = new WebSocket(url);
    socketRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket连接成功');
      setIsConnected(true);
    };

    ws.onclose = () => {
      console.log('WebSocket连接关闭');
      setIsConnected(false);
    };

    ws.onerror = (error) => {
      console.error('WebSocket错误:', error);
      setIsConnected(false);
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        setLastMessage(message);
      } catch (error) {
        console.error('解析WebSocket消息失败:', error);
      }
    };

    return () => {
      ws.close();
    };
  }, [url]);

  const sendMessage = useCallback((message: any) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(message));
    }
  }, []);

  return {
    isConnected,
    lastMessage,
    sendMessage
  };
};

// 进化专用WebSocket钩子
export const useEvolutionWebSocket = () => {
  // 构建正确的WebSocket URL
  const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  const wsUrl = baseUrl.replace('http://', 'ws://').replace('https://', 'wss://');
  
  return useWebSocket(`${wsUrl}/ws`, {
    reconnectAttempts: 10,
    reconnectDelay: 2000,
    autoConnect: true,
    onConnect: () => {
      console.log('进化WebSocket连接成功');
    },
    onDisconnect: () => {
      console.log('进化WebSocket连接断开');
    },
    onError: (error) => {
      console.error('进化WebSocket错误:', error);
    },
    onMessage: (message) => {
      console.log('收到进化消息:', message);
    }
  });
};