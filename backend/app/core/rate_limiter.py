"""登录限流 — 基于 Redis INCR 的滑动窗口计数器。

Redis 不可用时降级放行，不阻塞正常登录流程。
"""

from fastapi import HTTPException, status, Request

from . import redis_client
from ..utils.logger import get_logger

logger = get_logger(__name__)

_LOGIN_MAX_ATTEMPTS = 5
_LOGIN_WINDOW_SECONDS = 60


async def check_login_rate_limit(request: Request) -> None:
    """检查当前 IP 的登录频率。

    同一 IP 在 60 秒内最多 5 次 POST /login，超过则返回 HTTP 429。
    Redis 不可用时直接放行。
    """
    client_ip = request.client.host if request.client else "unknown"

    count = await redis_client.incr(
        f"rate_limit:login:{client_ip}",
        _LOGIN_WINDOW_SECONDS,
    )

    if count is None:
        return  # Redis 不可用，降级放行

    if count > _LOGIN_MAX_ATTEMPTS:
        logger.warning("登录限流触发 | ip=%s | attempts=%d", client_ip, count)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": 429,
                "message": f"登录尝试过于频繁，请 {_LOGIN_WINDOW_SECONDS} 秒后再试",
                "data": None,
            },
        )
