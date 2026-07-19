"""
Redis 连接管理单元测试
"""
from unittest.mock import AsyncMock, MagicMock, patch
import pytest


class TestInitRedis:
    """测试 init_redis"""

    async def test_redis_disabled_skips_init(self) -> None:
        with patch("backend.app.core.redis_client.settings") as mock_settings:
            mock_settings.REDIS_ENABLE = False
            from backend.app.core.redis_client import init_redis
            await init_redis()

    async def test_redis_connection_failure_no_crash(self) -> None:
        """连接失败不崩溃"""
        with (
            patch("backend.app.core.redis_client.settings") as mock_settings,
            patch("backend.app.core.redis_client.aioredis") as mock_redis,
        ):
            mock_settings.REDIS_ENABLE = True
            mock_settings.REDIS_HOST = "localhost"
            mock_settings.REDIS_PORT = 6370
            mock_settings.REDIS_PASSWORD = ""
            mock_redis.ConnectionPool.side_effect = OSError("Connection refused")

            from backend.app.core.redis_client import init_redis, _pool
            await init_redis()
            assert _pool is None


class TestRedisStringOps:
    """测试 String 操作降级行为"""

    async def test_get_str_redis_down(self) -> None:
        with patch("backend.app.core.redis_client._pool", None), \
             patch("backend.app.core.redis_client.settings") as mock_settings:
            mock_settings.REDIS_ENABLE = False
            from backend.app.core.redis_client import get_str
            assert await get_str("any_key") is None

    async def test_set_str_redis_down(self) -> None:
        with patch("backend.app.core.redis_client._pool", None), \
             patch("backend.app.core.redis_client.settings") as mock_settings:
            mock_settings.REDIS_ENABLE = False
            from backend.app.core.redis_client import set_str
            assert await set_str("key", "value") is False

    async def test_delete_redis_down(self) -> None:
        with patch("backend.app.core.redis_client._pool", None), \
             patch("backend.app.core.redis_client.settings") as mock_settings:
            mock_settings.REDIS_ENABLE = False
            from backend.app.core.redis_client import delete
            assert await delete("key") == 0

    async def test_exists_redis_down(self) -> None:
        with patch("backend.app.core.redis_client._pool", None), \
             patch("backend.app.core.redis_client.settings") as mock_settings:
            mock_settings.REDIS_ENABLE = False
            from backend.app.core.redis_client import exists
            assert await exists("key") is False

    async def test_incr_redis_down(self) -> None:
        with patch("backend.app.core.redis_client._pool", None), \
             patch("backend.app.core.redis_client.settings") as mock_settings:
            mock_settings.REDIS_ENABLE = False
            from backend.app.core.redis_client import incr
            assert await incr("counter", 60) is None

    async def test_ttl_seconds_redis_down(self) -> None:
        with patch("backend.app.core.redis_client._pool", None), \
             patch("backend.app.core.redis_client.settings") as mock_settings:
            mock_settings.REDIS_ENABLE = False
            from backend.app.core.redis_client import ttl_seconds
            assert await ttl_seconds("key") == -2

class TestRedisAvaliablePaths:
    """redis可用时的真实调用路径 配置mock redis连接池使用"""
    async def test_init_redis_success(self):
        """redis可用->pool创建+ping成功"""
        # 连接池配置

        with patch("backend.app.core.redis_client.aioredis") as mock_redis,\
             patch("backend.app.core.redis_client.settings") as mock_settings:
            mock_settings.REDIS_ENABLE = True
            mock_settings.REDIS_HOST = "localhost"
            mock_settings.REDIS_PORT = 6379
            mock_settings.REDIS_PASSWORD = ""

            mock_client = MagicMock()
            mock_client.ping = AsyncMock(return_value=True)
            mock_redis.Redis.return_value = mock_client

            mock_pool = MagicMock()
            mock_pool.disconnect = AsyncMock()  # disconnect 是异步方法
            mock_redis.ConnectionPool.return_value = mock_pool

            import backend.app.core.redis_client as redis_mod  # 引用模块而非直接 import _pool

            await redis_mod.init_redis()
            assert redis_mod._pool is not None  # 通过模块引用读取当前值
            mock_client.ping.assert_called_once()

            await redis_mod.close_redis()

    async def test_close_redis_when_pool_exists(self):
        """
        _pool存在时close_redis->disconnect + None
        """
        from backend.app.core.redis_client import close_redis  # 函数引用

        mock_pool = MagicMock()
        mock_pool.disconnect = AsyncMock()
        with patch("backend.app.core.redis_client._pool", mock_pool), \
             patch("backend.app.core.redis_client.settings") as mock_settings:
            mock_settings.REDIS_ENABLE = True
            await close_redis()
            mock_pool.disconnect.assert_called_once()  # disconnect被调用

    async def test_incr_counter_success(self):
        """incr成功->返回计数，首次调用设置TTL"""
        from backend.app.core.redis_client import incr  # 函数引用

        with patch("backend.app.core.redis_client._pool", MagicMock()), \
             patch("backend.app.core.redis_client.settings") as mock_settings, \
             patch("backend.app.core.redis_client.aioredis.Redis") as mock_redis_cls:
            mock_settings.REDIS_ENABLE = True
            mock_client = AsyncMock()
            mock_client.incr = AsyncMock(return_value=1)  # 首次incr返回1
            mock_redis_cls.return_value = mock_client
            result = await incr("rate:test", 60)
            assert result == 1
            mock_client.expire.assert_called_once_with("rate:test", 60)  # 首次设置TTL



