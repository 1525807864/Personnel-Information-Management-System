from pydantic import BaseModel, Field
from typing import Generic, TypeVar, Optional
from datetime import datetime

T=TypeVar("T")
class ApiResponse(BaseModel,Generic[T]):
    """统一响应格式"""
    code: int=200
    message: str="success"
    data: Optional[T]=None
    timestamp: datetime = Field(default_factory=datetime.now)
class PaginationData(BaseModel,Generic[T]):
    """分页响应数据"""
    total: int
    page: int
    size: int
    items: list[T]