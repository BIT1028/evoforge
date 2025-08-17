#!/usr/bin/env python3
"""
配置管理模块
"""
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field
import os

class Settings(BaseSettings):
    """应用配置"""
    
    # 基础配置
    DEBUG: bool = Field(default=True, description="调试模式")
    SECRET_KEY: str = Field(default="chimera-secret-key-change-in-production", description="应用密钥")
    ALLOWED_HOSTS: List[str] = Field(default=["*"], description="允许的主机")
    
    # 数据库配置
    DATABASE_URL: str = Field(
        default="sqlite:///./chimera.db",
        description="数据库连接URL"
    )
    
    # Redis配置
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis连接URL"
    )
    
    # SiliconFlow API配置
    SILICONFLOW_API_KEY: str = Field(
        default="",
        description="SiliconFlow API密钥"
    )
    SILICONFLOW_BASE_URL: str = Field(
        default="https://api.siliconflow.cn/v1",
        description="SiliconFlow API基础URL"
    )
    SILICONFLOW_MODEL: str = Field(
        default="Qwen/Qwen2-72B-Instruct",
        description="默认使用的模型"
    )
    
    # Docker沙箱配置
    SANDBOX_IMAGE: str = Field(
        default="python:3.11-slim",
        description="沙箱Docker镜像"
    )
    SANDBOX_MEMORY_LIMIT: str = Field(
        default="128m",
        description="沙箱内存限制"
    )
    SANDBOX_CPU_LIMIT: float = Field(
        default=0.5,
        description="沙箱CPU限制"
    )
    SANDBOX_TIMEOUT: int = Field(
        default=30,
        description="沙箱执行超时时间（秒）"
    )
    
    # 进化算法参数
    POPULATION_SIZE: int = Field(
        default=50,
        description="种群大小"
    )
    MUTATION_RATE: float = Field(
        default=0.1,
        description="变异率"
    )
    CROSSOVER_RATE: float = Field(
        default=0.8,
        description="交叉率"
    )
    ELITE_SIZE: int = Field(
        default=5,
        description="精英个体数量"
    )
    
    # 服务器配置
    HOST: str = Field(default="0.0.0.0", description="服务器主机")
    PORT: int = Field(default=8000, description="服务器端口")
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"

# 全局配置实例
settings = Settings()