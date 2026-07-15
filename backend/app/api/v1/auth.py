from fastapi import APIRouter,Depends,HTTPException,status
from backend.app.schemas.auth import  LoginRequest,LoginResponseData

from backend.app.services.auth_service import AuthService
from backend.app.schemas.common import ApiResponse
from backend.app.core.dependencies import get_redmine_client, get_current_user
from backend.app.core.redmine_client import RedmineClient
import logging
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/auth",tags=["认证"])

@router.post("/login",response_model=ApiResponse[LoginResponseData])
async def login(
        request: LoginRequest,
        redmine: RedmineClient = Depends(get_redmine_client),
):
    """
    用户登录
    1、接收login+password
    2、转发到redmine做auth验证
    3、验证通过 签发jwt 返回
    4、验证失败 返回401
    :param request:
    :param redmine:
    :return:
    """
    logger.info("收到登录请求|username=%s",request.username)
    auth_service = AuthService(redmine)
    success,message,user_data = await auth_service.authenticate(request)
    if not success:
        logger.warning("登录失败|username=%s|原因=%s",request.username,message)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail={"code":401,"message":message,"data":None})

    token_data = auth_service.generate_token(user_data)
    logger.info("登录成功 | username=%s | role=%s | token_prefix=%s...",
                token_data.username, token_data.role,
                token_data.token[:20])
    return ApiResponse(code=200,message=message,data=token_data)
@router.get("/verify")
async def verify_token(
        current_user: dict = Depends(get_current_user),
):
    "验证Token是否有效"
    return ApiResponse(
        code=200,
        message="Token有效",
        data={
            "username": current_user["username"],
            "role":current_user["role"],
        },
    )


@router.post("/logout")


async def logout(
        current_user: dict = Depends(get_current_user),
):
    """
    退出登录

    说明：JWT 是无状态的，要真正失效 token 需要配合 Redis 黑名单。
    当前版本仅返回成功，token 在客户端清除即已实现基本退出。
    """
    return ApiResponse(
        code=200,
        message="已退出登录",
        data=None,
    )
