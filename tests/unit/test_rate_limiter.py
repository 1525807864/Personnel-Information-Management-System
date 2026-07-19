"""
登录限流模块单元测试

测试目标：
  1. 正常登录不超过阈值 → 放行
  2. 超过阈值 → 抛出 HTTP 429
  3. Redis 不可用 → 降级放行
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from backend.app.core import rate_limiter


class TestCheckLoginRateLimit:
    """测试 check_login_rate_limit 函数"""

    @pytest.fixture
    def mock_request(self) -> MagicMock:
        req = MagicMock()
        req.client.host = "192.168.1.1"
        return req

    async def test_normal_request_passes(self, mock_request: MagicMock) -> None:
        """正常频率的登录请求 → 放行"""
        with patch.object(rate_limiter.redis_client, "incr", new_callable=AsyncMock) as mock_incr:
            mock_incr.return_value = 3  # 低于阈值 5

            await rate_limiter.check_login_rate_limit(mock_request)
            # 不抛异常即通过

    async def test_rate_limit_triggered(self, mock_request: MagicMock) -> None:
        """超过阈值 → 抛出 429 Too Many Requests"""
        with patch.object(rate_limiter.redis_client, "incr", new_callable=AsyncMock) as mock_incr:
            mock_incr.return_value = 5001  # 超过阈值 5000

            with pytest.raises(HTTPException) as exc_info:
                await rate_limiter.check_login_rate_limit(mock_request)

            assert exc_info.value.status_code == 429
            detail = exc_info.value.detail
            assert detail["code"] == 429
            assert "频繁" in detail["message"]

    async def test_redis_down_bypasses_limit(self, mock_request: MagicMock) -> None:
        """Redis 不可用时 → 降级放行"""
        with patch.object(rate_limiter.redis_client, "incr", new_callable=AsyncMock) as mock_incr:
            mock_incr.return_value = None  # Redis 不可用

            await rate_limiter.check_login_rate_limit(mock_request)
            # 不抛异常即放行

    async def test_exactly_at_threshold_passes(self, mock_request: MagicMock) -> None:
        """恰好等于阈值时 → 应放行（只有超过才拦截）"""
        with patch.object(rate_limiter.redis_client, "incr", new_callable=AsyncMock) as mock_incr:
            mock_incr.return_value = 5000  # 等于阈值

            await rate_limiter.check_login_rate_limit(mock_request)

    async def test_missing_client_ip(self) -> None:
        """request.client 为 None → 使用 'unknown' 作为 key"""
        req = MagicMock()
        req.client = None

        with patch.object(rate_limiter.redis_client, "incr", new_callable=AsyncMock) as mock_incr:
            mock_incr.return_value = 1

            await rate_limiter.check_login_rate_limit(req)

            mock_incr.assert_called_once_with(
                "rate_limit:login:unknown", rate_limiter._LOGIN_WINDOW_SECONDS
            )
