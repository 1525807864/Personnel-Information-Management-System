"""Redis 连接管理与基础操作封装。

Redis 不可用时所有操作降级返回安全默认值（None / False），不会崩溃。
"""

from typing import Optional

import redis.asyncio as aioredis
from redis.asyncio import ConnectionPool

from .config import settings
from ..utils.logger import get_logger

logger = get_logger(__name__)

_pool: Optional[ConnectionPool] = None


async def init_redis() -> None:
    """初始化 Redis 连接池（应用启动时调用）。"""
    global _pool
    if not settings.REDIS_ENABLE:
        logger.info("Redis 未启用（REDIS_ENABLE=False），跳过连接")
        return
    try:
        _pool = aioredis.ConnectionPool(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD or None,
            max_connections=10,
            decode_responses=True,
        )
        client = aioredis.Redis(connection_pool=_pool)
        await client.ping()
        logger.info("Redis 连接成功 | host=%s | port=%s", settings.REDIS_HOST, settings.REDIS_PORT)
    except Exception as e:
        logger.warning("Redis 连接失败，应用将降级运行 | error=%s", e)
        _pool = None


async def close_redis() -> None:
    """关闭 Redis 连接池（应用关闭时调用）。"""
    global _pool
    if _pool:
        await _pool.disconnect()
        _pool = None
        logger.info("Redis 连接池已关闭")


def _get_client() -> Optional[aioredis.Redis]:
    """获取 Redis 客户端实例（内部使用）。"""
    if not _pool or not settings.REDIS_ENABLE:
        return None
    return aioredis.Redis(connection_pool=_pool)


async def _safe(coro):
    """执行 Redis 操作，失败时返回 None。"""
    client = _get_client()
    if client is None:
        return None
    try:
        return await coro(client)
    except Exception as e:
        logger.warning("Redis 操作失败 | error=%s", e)
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


async def set_nx(key: str, value: str = "1", ttl: int = 10) -> bool:
    """原子设置 Key（仅当不存在时），用于分布式锁。

    返回 True 表示设置成功（获得锁），False 表示 Key 已存在（锁被占用）。
    Redis 不可用时降级返回 True（不阻塞业务）。
    """
    async def _set_nx(client):
        return await client.set(key, value, nx=True, ex=ttl)

    result = await _safe(_set_nx)
    if result is None:
        return True
    return bool(result)
