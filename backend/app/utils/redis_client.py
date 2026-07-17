import logging
from http.client import HTTPException
from typing import Optional
import redis.asyncio as aioredis
from redis.asyncio import ConnectionPool

from backend.app.core.config import settings

logger = logging.getLogger(__name__)
_pool: Optional[ConnectionPool] = None

async def init_redis()->None:
    """初始化redis连接池"""
    global _pool
    if not settings.REDIS_ENABLE:
        logger.info("Redis未启动,跳过连接")
        return
    try:
        _pool = aioredis.ConnectionPool(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            maxsize=settings.REDIS_MAXSIZE,
            decode_responses = True,
        )
        client = aioredis.Redis(connection_pool=_pool)
        await client.ping()
        logger.info("Redis 连接成功 | host=%s | port=%s", settings.REDIS_HOST, settings.REDIS_PORT)
    except Exception as e:
        logger.warning(f"连接Redis失败{e}")
        _pool = None

async def close_redis() -> None:
    """关闭redis连接"""
    global _pool
    if _pool:
        await _pool.disconnect()
        _pool = None
        logger.info("Redis连接已经关闭")

def _get_client()->Optional[aioredis.Redis]:
    """获取Redis客户端实例（内部使用）"""
    if not _pool or not settings.REDIS_ENABLE:
        return None
    return aioredis.Redis(connection_pool=_pool)

async def _safe(coro):
    """执行Redis操作，失败返回None"""
    client = _get_client()
    if client is None:
        return None
    try:
        return await coro(client)
    except Exception as e:
        logger.warning("Redis操作失败 | error%s",e)
        return None

# ─── 通用 String 操作 ───

async def get_str(key: str) -> Optional[str]:
    """读取字符串值。"""
    return await _safe(lambda c: c.get(key))


async def set_str(key: str, value: str, ttl: Optional[int] = None) -> bool:
    """写入字符串值，可选 TTL（秒）。"""
    result = await _safe(lambda c: c.set(key, value, ex=ttl) if ttl else c.set(key, value))
    return result is not None


async def delete(*keys: str) -> int:
    """删除一个或多个 Key，返回删除数量。"""
    result = await _safe(lambda c: c.delete(*keys))
    return result if result is not None else 0


async def exists(key: str) -> bool:
    """检查 Key 是否存在。"""
    result = await _safe(lambda c: c.exists(key))
    return bool(result)


async def incr(key: str, ttl: int) -> Optional[int]:
    """原子递增计数器并设置 TTL（用于限流）。"""
    async def _incr(client):
        value = await client.incr(key)
        if value == 1:
            await client.expire(key, ttl)
        return value

    return await _safe(_incr)


async def ttl_seconds(key: str) -> int:
    """获取 Key 剩余 TTL（秒）。返回 -2 表示不存在，-1 表示无过期时间。"""
    result = await _safe(lambda c: c.ttl(key))
    return result if result is not None else -2