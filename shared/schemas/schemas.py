"""
共享数据模式
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field, field_validator


# 用户相关模式
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool = True


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None


class User(UserBase):
    id: int
    is_superuser: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# 任务相关模式
class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    priority: str = Field("medium", pattern="^(low|medium|high)$")
    task_type: str = Field(..., pattern="^(prediction|segmentation|analysis)$")
    input_data: Optional[Dict[str, Any]] = None


class TaskCreate(TaskBase):
    user_id: int


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(pending|processing|completed|failed)$")
    priority: Optional[str] = Field(None, pattern="^(low|medium|high)$")
    progress: Optional[float] = Field(None, ge=0, le=100)
    result_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class Task(TaskBase):
    id: int
    user_id: int
    status: str
    progress: float
    result_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: datetime

    class Config:
        from_attributes = True


# 模型相关模式
class ModelBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    version: str = Field(..., min_length=1, max_length=20)
    model_type: str = Field(..., pattern="^(classification|segmentation|detection)$")
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    is_active: bool = True


class ModelCreate(ModelBase):
    file_path: str


class ModelUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    version: Optional[str] = Field(None, min_length=1, max_length=20)
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class Model(ModelBase):
    id: int
    file_path: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# 通知相关模式
class NotificationBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1)
    notification_type: str = Field("info", pattern="^(info|warning|error|success)$")


class NotificationCreate(NotificationBase):
    user_id: int
    task_id: Optional[int] = None


class Notification(NotificationBase):
    id: int
    user_id: int
    task_id: Optional[int] = None
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


# API密钥相关模式
class APIKeyBase(BaseModel):
    key_name: str = Field(..., min_length=1, max_length=100)
    expires_at: Optional[datetime] = None


class APIKeyCreate(APIKeyBase):
    pass


class APIKey(APIKeyBase):
    id: int
    user_id: int
    api_key: str
    is_active: bool
    last_used_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# 预测相关模式
class PredictionRequest(BaseModel):
    image_url: str
    model_id: Optional[int] = None
    model_name: Optional[str] = None
    confidence_threshold: Optional[float] = Field(0.5, ge=0, le=1)


class PredictionResult(BaseModel):
    task_id: int
    predictions: List[Dict[str, Any]]
    processing_time: float
    model_info: Dict[str, Any]


# 分割相关模式
class SegmentationRequest(BaseModel):
    image_url: str
    model_id: Optional[int] = None
    model_name: Optional[str] = None


class SegmentationResult(BaseModel):
    task_id: int
    mask_url: str
    segmented_image_url: str
    processing_time: float
    model_info: Dict[str, Any]


# 系统日志相关模式
class SystemLogBase(BaseModel):
    service_name: str
    level: str = Field(..., pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    message: str
    details: Optional[Dict[str, Any]] = None
    user_id: Optional[int] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class SystemLogCreate(SystemLogBase):
    pass


class SystemLog(SystemLogBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Token相关模式
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


# 响应模式
class ResponseBase(BaseModel):
    success: bool = True
    message: str = "操作成功"


class SuccessResponse(ResponseBase):
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


# 分页模式
class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=100)

    @field_validator("size")
    def validate_size(cls, v):
        if v > 100:
            raise ValueError("每页大小不能超过100")
        return v


class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    size: int
    pages: int


# 健康检查模式
class HealthCheck(BaseModel):
    status: str
    timestamp: datetime
    service: str
    version: str
    dependencies: Dict[str, str]