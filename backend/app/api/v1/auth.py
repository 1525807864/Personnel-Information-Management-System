from datetime import datetime, UTC

from fastapi import APIRouter, Depends, HTTPException, status, Request

from ...schemas.auth import LoginRequest, LoginResponseData
from ...services.auth_service import AuthService
from ...schemas.common import ApiResponse
from ...core.dependencies import get_redmine_client, get_current_user
from ...core.redmine_client import RedmineClient
from ...core.rate_limiter import check_login_rate_limit
from ...core.security import decode_access_token, blacklist_token
from ...utils.logger import get_logger

logger = get_logger(__name__)


router = APIRouter(prefix="/api/v1/auth", tags=["认证"])


@router.post("/login", response_model=ApiResponse[LoginResponseData])
async def login(
    request: LoginRequest,
    http_request: Request,
    redmine: RedmineClient = Depends(get_redmine_client),
):
    """用户登录 — 含登录限流保护。"""
    await check_login_rate_limit(http_request)

    logger.info("收到登录请求|username=%s", request.username)
    auth_service = AuthService(redmine)
    success, message, user_data = await auth_service.authenticate(request)
    if not success:
        logger.warning("登录失败|username=%s|原因=%s", request.username, message)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 401, "message": message, "data": None},
        )

    token_data = auth_service.generate_token(user_data)
    logger.info("登录成功 | username=%s | role=%s | token_prefix=%s...",
                token_data.username, token_data.role,
                token_data.token[:20])
    return ApiResponse(code=200, message=message, data=token_data)


@router.get("/verify")
async def verify_token(
    current_user: dict = Depends(get_current_user),
):
    """验证 Token 是否有效（含黑名单检查）。"""
    return ApiResponse(
        code=200,
        message="Token有效",
        data={
            "username": current_user["username"],
            "role": current_user["role"],
        },
    )


@router.post("/logout")
async def logout(
    http_request: Request,
    current_user: dict = Depends(get_current_user),
):
    """退出登录 — 将当前 token 的 jti 写入 Redis 黑名单，使其立即失效。"""
    auth_header = http_request.headers.get("Authorization", "")
    token = auth_header.removeprefix("Bearer ").strip()

    payload = decode_access_token(token)
    if payload:
        jti = payload.get("jti")
        if jti:
            exp = payload.get("exp", 0)
            now_ts = int(datetime.now(UTC).timestamp())
            remaining = max(exp - now_ts, 1)
            await blacklist_token(jti, remaining)
            logger.info("Token 已加入黑名单 | sub=%s | jti=%s | ttl=%ds",
                        payload.get("sub"), jti, remaining)

    return ApiResponse(
        code=200,
        message="已退出登录",
        data=None,
    )
