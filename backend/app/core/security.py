"""
author :LiShaoPeng
date: 2026/07/15
"""
from datetime import datetime,timedelta
from typing import Optional,Dict,Any
from jose import jwt,JWTError
from passlib.context import CryptContext
import logging
from backend.app.core.config import settings
logger = logging.getLogger(__name__)
#密码上下文，用于本地管理员账号的备用方案
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = settings.JWT_ALGORITHM
SECRET_KEY = settings.SECRET_KEY
EXPIRE_HOURS = settings.JWT_EXPIRE_HOURS

def create_access_token(data: Dict[str,Any],expires_delta: Optional[timedelta] = None)->str:
    """
    生成jwt access token
    :param data: 要编码到token中的数据
    :param expires_delta: 过期时间增量，默认是24小时
    :return: 编码后的jwt字符串
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=EXPIRE_HOURS))
    logger.debug("创建 JWT | subject=%s | expire_at=%s", data.get("sub"),
                 expire.isoformat())
    to_encode.update({"exp": expire,"iat":datetime.utcnow()})
    return jwt.encode(to_encode,SECRET_KEY,algorithm=ALGORITHM)


def decode_access_token(token:str)->Optional[Dict[str,Any]]:
    """
    解码并验证JWT token
    :param token: JWT token
    :return: 解码后的payload字典，验证失败返回None
    """
    try:
        payload = jwt.decode(token,SECRET_KEY,algorithms=[ALGORITHM])
        logger.debug("JWT 解码成功 | sub=%s | username=%s",
                     payload.get("sub"), payload.get("username"))
        return payload
    except JWTError:
        return None

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