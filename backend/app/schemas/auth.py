"""
auth: LiShaoPeng
date: 2026/07/14
"""
from typing import Optional,Dict,List,Any
from pydantic import BaseModel,Field

class LoginRequest(BaseModel):
    username: str = Field(...,min_length=3,max_length=20)
    password: str = Field(...,min_length=3,max_length=20)
class RegisterRequest(BaseModel):
    username: str = Field(...,min_length=3,max_length=20)
    password: str = Field(...,min_length=3,max_length=20)
    firstname: str = Field(...,min_length=3,max_length=20)
    lastname: str = Field(...,min_length=3,max_length=20)
    email: str = Field(...,min_length=3,max_length=20)
class LoginResponseData(BaseModel):
    token: str
    username: str
    role: str = "user"
    user_id: int

class TokenVerifyData(BaseModel):
    """
    Token验证返回的数据
    """
    username: str
    role: str
    user_id: int

