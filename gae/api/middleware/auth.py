# -*- coding: utf-8 -*-
"""
认证中间件

提供JWT令牌验证、用户认证和权限控制功能。
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

import jwt
from fastapi import HTTPException, Request, Response, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

class AuthMiddleware(BaseHTTPMiddleware):
    """
    认证中间件
    
    处理JWT令牌验证和用户认证
    """
    
    def __init__(self, app, config: Dict[str, Any]):
        super().__init__(app)
        self.config = config
        self.secret_key = config.get('secret_key', 'default-secret-key')
        self.algorithm = config.get('algorithm', 'HS256')
        self.token_expire_minutes = config.get('access_token_expire_minutes', 30)
        
        # 不需要认证的路径
        self.public_paths = {
            '/docs', '/redoc', '/openapi.json',
            '/health', '/metrics',
            '/api/v1/auth/login', '/api/v1/auth/register',
            '/api/v1/system/health', '/api/v1/system/info'
        }
        
        # WebSocket路径（单独处理）
        self.websocket_paths = {'/ws'}
        
        logger.info("Auth middleware initialized")
    
    async def dispatch(self, request: Request, call_next):
        """
        处理请求认证
        
        Args:
            request: HTTP请求
            call_next: 下一个中间件或路由处理器
            
        Returns:
            Response: HTTP响应
        """
        start_time = time.time()
        
        try:
            # 检查是否为公开路径
            if self._is_public_path(request.url.path):
                response = await call_next(request)
                return response
            
            # 检查是否为WebSocket连接
            if self._is_websocket_path(request.url.path):
                # WebSocket认证在连接时处理
                response = await call_next(request)
                return response
            
            # 验证认证令牌
            user_info = await self._authenticate_request(request)
            if not user_info:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "status": "error",
                        "message": "Authentication required",
                        "error_code": "AUTH_REQUIRED"
                    }
                )
            
            # 将用户信息添加到请求状态
            request.state.user = user_info
            
            # 继续处理请求
            response = await call_next(request)
            
            # 记录认证成功
            process_time = time.time() - start_time
            logger.debug(
                f"Auth successful for user {user_info.get('user_id')} "
                f"on {request.method} {request.url.path} in {process_time:.3f}s"
            )
            
            return response
            
        except HTTPException as e:
            logger.warning(f"Auth failed for {request.url.path}: {str(e)}")
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "status": "error",
                    "message": e.detail,
                    "error_code": "AUTH_FAILED"
                }
            )
        except Exception as e:
            logger.error(f"Auth middleware error: {str(e)}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": "error",
                    "message": "Internal authentication error",
                    "error_code": "AUTH_ERROR"
                }
            )
    
    def _is_public_path(self, path: str) -> bool:
        """
        检查是否为公开路径
        
        Args:
            path: 请求路径
            
        Returns:
            bool: 是否为公开路径
        """
        # 精确匹配
        if path in self.public_paths:
            return True
        
        # 前缀匹配
        for public_path in self.public_paths:
            if path.startswith(public_path):
                return True
        
        return False
    
    def _is_websocket_path(self, path: str) -> bool:
        """
        检查是否为WebSocket路径
        
        Args:
            path: 请求路径
            
        Returns:
            bool: 是否为WebSocket路径
        """
        return path in self.websocket_paths or path.startswith('/ws')
    
    async def _authenticate_request(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        验证请求认证
        
        Args:
            request: HTTP请求
            
        Returns:
            Optional[Dict]: 用户信息，如果认证失败返回None
        """
        try:
            # 获取Authorization头
            authorization = request.headers.get('Authorization')
            if not authorization:
                return None
            
            # 解析Bearer令牌
            if not authorization.startswith('Bearer '):
                return None
            
            token = authorization[7:]  # 移除'Bearer '前缀
            
            # 验证JWT令牌
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            
            # 检查令牌是否过期
            exp = payload.get('exp')
            if exp and datetime.utcnow().timestamp() > exp:
                logger.warning("Token expired")
                return None
            
            # 提取用户信息
            user_info = {
                'user_id': payload.get('sub'),
                'username': payload.get('username'),
                'email': payload.get('email'),
                'roles': payload.get('roles', []),
                'permissions': payload.get('permissions', []),
                'exp': exp,
                'iat': payload.get('iat')
            }
            
            return user_info
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Token validation error: {str(e)}")
            return None

# JWT工具函数
def create_access_token(data: Dict[str, Any], secret_key: str, 
                       expires_delta: Optional[timedelta] = None) -> str:
    """
    创建访问令牌
    
    Args:
        data: 令牌数据
        secret_key: 密钥
        expires_delta: 过期时间增量
        
    Returns:
        str: JWT令牌
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=30)
    
    to_encode.update({
        'exp': expire.timestamp(),
        'iat': datetime.utcnow().timestamp()
    })
    
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm='HS256')
    return encoded_jwt

def verify_token(token: str, secret_key: str) -> Optional[Dict[str, Any]]:
    """
    验证令牌
    
    Args:
        token: JWT令牌
        secret_key: 密钥
        
    Returns:
        Optional[Dict]: 令牌载荷，如果验证失败返回None
    """
    try:
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Token verification error: {str(e)}")
        return None

# FastAPI依赖项
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = security) -> Dict[str, Any]:
    """
    获取当前用户（FastAPI依赖项）
    
    Args:
        credentials: HTTP认证凭据
        
    Returns:
        Dict: 用户信息
        
    Raises:
        HTTPException: 认证失败
    """
    # 这里需要从配置中获取密钥
    # 暂时使用默认密钥
    secret_key = 'default-secret-key'
    
    payload = verify_token(credentials.credentials, secret_key)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_info = {
        'user_id': payload.get('sub'),
        'username': payload.get('username'),
        'email': payload.get('email'),
        'roles': payload.get('roles', []),
        'permissions': payload.get('permissions', [])
    }
    
    return user_info

def require_auth(user: Dict[str, Any] = get_current_user) -> Dict[str, Any]:
    """
    要求认证的依赖项
    
    Args:
        user: 当前用户
        
    Returns:
        Dict: 用户信息
    """
    return user

def require_roles(required_roles: List[str]):
    """
    要求特定角色的依赖项工厂
    
    Args:
        required_roles: 必需的角色列表
        
    Returns:
        function: 依赖项函数
    """
    async def check_roles(user: Dict[str, Any] = get_current_user) -> Dict[str, Any]:
        user_roles = user.get('roles', [])
        
        if not any(role in user_roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required roles: {required_roles}"
            )
        
        return user
    
    return check_roles

def require_permissions(required_permissions: List[str]):
    """
    要求特定权限的依赖项工厂
    
    Args:
        required_permissions: 必需的权限列表
        
    Returns:
        function: 依赖项函数
    """
    async def check_permissions(user: Dict[str, Any] = get_current_user) -> Dict[str, Any]:
        user_permissions = user.get('permissions', [])
        
        if not all(perm in user_permissions for perm in required_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required permissions: {required_permissions}"
            )
        
        return user
    
    return check_permissions

# WebSocket认证
async def authenticate_websocket(websocket, token: str) -> Optional[Dict[str, Any]]:
    """
    WebSocket连接认证
    
    Args:
        websocket: WebSocket连接
        token: 认证令牌
        
    Returns:
        Optional[Dict]: 用户信息，如果认证失败返回None
    """
    try:
        # 这里需要从配置中获取密钥
        secret_key = 'default-secret-key'
        
        payload = verify_token(token, secret_key)
        if not payload:
            return None
        
        user_info = {
            'user_id': payload.get('sub'),
            'username': payload.get('username'),
            'email': payload.get('email'),
            'roles': payload.get('roles', []),
            'permissions': payload.get('permissions', [])
        }
        
        return user_info
        
    except Exception as e:
        logger.error(f"WebSocket authentication error: {str(e)}")
        return None