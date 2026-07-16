"""
author :LiShaoPeng
date: 2026/07/15
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from jose import jwt, JWTError
from passlib.context import CryptContext
import logging

from backend.app.core.config import settings

logger = logging.getLogger(__name__)
#密码上下文，用于本地管理员账号的备用方案
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = settings.JWT_ALGORITHM
SECRET_KEY = settings.SECRET_KEY
EXPIRE_HOURS = settings.JWT_EXPIRE_HOURS

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """生成 JWT access token，自动附加 jti（JWT ID）用于撤销。"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=EXPIRE_HOURS))
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "jti": uuid.uuid4().hex,
    })
    logger.debug("创建 JWT | sub=%s | jti=%s | expire_at=%s",
                 data.get("sub"), to_encode["jti"], expire.isoformat())
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """解码并验证 JWT token，验证失败返回 None。"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        logger.debug("JWT 解码成功 | sub=%s | jti=%s | username=%s",
                     payload.get("sub"), payload.get("jti"), payload.get("username"))
        return payload
    except JWTError:
        return None


async def is_token_blacklisted(jti: str) -> bool:
    """检查 token 是否在 Redis 黑名单中（已登出）。

    Redis 不可用时返回 False（降级放行）。
    """
    from backend.app.core.redis_client import exists
    return await exists(f"blacklist:{jti}")


async def blacklist_token(jti: str, ttl: int) -> bool:
    """将 token 加入 Redis 黑名单（登出时调用）。

    ttl 应为 token 剩余有效秒数。
    """
    from backend.app.core.redis_client import set_str
    return await set_str(f"blacklist:{jti}", "1", ttl=ttl)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码（用于本地管理员账户，非Redmine验证）
    :param plain_password: 明文
    :param hashed_password:  密文
    :return:
    """
    return pwd_context.verify(plain_password, hashed_password)
def hash_password(password:str)->str:
    """
    哈希密码
    :param password: 哈希密码
    :return: 加密后的密码
    """
    return pwd_context.hash(password)