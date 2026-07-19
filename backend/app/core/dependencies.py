from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .security import decode_access_token, is_token_blacklisted
from .redmine_client import RedmineClient
from .config import settings

# HTTP Bearer 认证方案
security_scheme = HTTPBearer(auto_error=False)


def get_redmine_client() -> RedmineClient:
    """获取 Redmine 客户端实例（作为 FastAPI 依赖）"""
    return RedmineClient(
        base_url=settings.REDMINE_URL.rstrip("/"),
        api_key=settings.REDMINE_API_KEY,
    )


async def get_current_user(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> dict:
    """
    从请求头的 Bearer Token 中解析当前用户信息

    用法：在 API 路由参数中添加
        current_user: dict = Depends(get_current_user)
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 401, "message": "请先登录", "data": None},
        )

    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 401, "message": "Token 无效或已过期，请重新登录", "data": None},
        )

    jti = payload.get("jti")
    if jti and await is_token_blacklisted(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 401, "message": "Token 已注销，请重新登录", "data": None},
        )

    return {
        "user_id": int(payload.get("sub", 0)),
        "username": payload.get("username", ""),
        "role": payload.get("role", "user"),
    }


async def get_current_admin(
        current_user: dict = Depends(get_current_user),
) -> dict:
    """要求当前用户是管理员"""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": 403, "message": "需要管理员权限", "data": None},
        )
    return current_user
