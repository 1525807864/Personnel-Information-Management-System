from typing import Optional,Tuple,Any,List,Dict
from ..core.security import create_access_token
from ..core.redmine_client import RedmineClient
from ..core.config import settings
from ..schemas.auth import LoginRequest,LoginResponseData
from ..utils.logger import get_logger
from ..models.user import RedmineUser
logger = get_logger(__name__)


class AuthService:
    def __init__(self,redmine_client: RedmineClient):
        self.redmine = redmine_client

    async def authenticate(self,request: LoginRequest) -> Tuple[bool,str,Optional[Dict[str,Any]]]:
        """
        验证用户凭证
        流程：
        1. 用用户凭证向 Redmine 发起 Basic Auth 验证
        2. 如果凭证无效 → 返回失败
        3. 如果账户被锁定 → 返回失败
        4. 如果凭证有效 → 用 Admin API Key 获取用户完整信息（含 custom_fields）
        5. 返回用户信息
        :param request:
        :return:
        """
        logger.info("正在向Redmine验证凭证|login=%s",request.username)
        user_info = await self.redmine.verify_user_credentials(login=request.username,password=request.password)
        if user_info is None:
            logger.warning("Redmine 凭证验证失败|login=%s",request.username)
            return False,"用户名或密码错误",None
        redmine_user = RedmineUser.from_redmine_api(user_info)

        logger.info("账号状态: %s | login=%s", redmine_user.status, request.username)
        if redmine_user.status == 3:
            logger.warning("账号已被锁定 | login=%s | status=%s",
                           request.username, redmine_user.status)
            return False,"账号被锁定，请联系管理员",None
        if redmine_user.status not in (1,2):
            logger.warning("账号状态异常 | login=%s | status=%s",
                           request.username, redmine_user.status)
            return False,"账号状态异常，登录失败",None
        full_user = await self.redmine.get_user_with_api_key(redmine_user.id)
        if full_user:
            redmine_user = RedmineUser.from_redmine_api(full_user)
            logger.info("获取到用户完整信息 | user_id=%s | custom_fields_count=%s",
                        redmine_user.id, len(redmine_user.custom_fields))

        role = "admin" if redmine_user.admin else "user"
        return True,"登录成功",{
            "user_id":redmine_user.id,
            "login":redmine_user.login,
            "name":f"{redmine_user.lastname}{redmine_user.firstname}",
            "email":redmine_user.email,
            "role":role,
            "status":redmine_user.status,
            "admin":redmine_user.admin,
            "custom_fields":redmine_user.custom_fields,

        }
    #为已验证的用户生成jwt token
    def generate_token(self,user_data:Dict[str,Any]) -> LoginResponseData:
        token_payload = {
            "sub":str(user_data["user_id"]),
            "username":str(user_data["login"]),
            "role":str(user_data["role"]),
        }
        logger.debug("签发 JWT Token | sub=%s | username=%s | expire_hours=%s",
                     token_payload["sub"], token_payload["username"],
                     settings.JWT_EXPIRE_HOURS)
        token = create_access_token(token_payload)
        logger.info("Token 签发完成 | username=%s | token_length=%s",
                    user_data["login"], len(token))
        return LoginResponseData(token=token,username=user_data["login"],role=user_data["role"],user_id=user_data["user_id"])
