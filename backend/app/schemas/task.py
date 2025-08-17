#!/usr/bin/env python3
"""
任务相关的Pydantic schemas
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class TaskBase(BaseModel):
    """任务基础模型"""
    name: str = Field(min_length=1, max_length=255, description="任务名称")
    description: str = Field(min_length=1, description="任务描述")
    priority: int = Field(default=0, ge=0, le=100, description="优先级")
    category: str = Field(description="任务类别")
    template: Optional[str] = Field(default=None, description="任务模板")
    is_active: bool = Field(default=True, description="是否激活")

class TaskCreate(TaskBase):
    """创建任务请求"""
    pass

class TaskUpdate(BaseModel):
    """更新任务请求"""
    name: Optional[str] = Field(default=None, min_length=1, max_length=255, description="任务名称")
    description: Optional[str] = Field(default=None, min_length=1, description="任务描述")
    priority: Optional[int] = Field(default=None, ge=0, le=100, description="优先级")
    category: Optional[str] = Field(default=None, description="任务类别")
    template: Optional[str] = Field(default=None, description="任务模板")
    is_active: Optional[bool] = Field(default=None, description="是否激活")

class TaskResponse(TaskBase):
    """任务响应"""
    id: str = Field(description="任务ID")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")
    
    class Config:
        from_attributes = True

class TaskReorderRequest(BaseModel):
    """任务重排序请求"""
    task_ids: list[str] = Field(description="任务ID列表（按新顺序排列）")

class TaskBatchRequest(BaseModel):
    """批量任务操作请求"""
    task_ids: list[str] = Field(description="任务ID列表")
    action: str = Field(description="操作类型: activate, deactivate, delete")