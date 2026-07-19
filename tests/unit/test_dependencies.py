"""
dependencies.py 单元测试

测试目标：
  1. get_current_admin 函数的完整测试（当前 4 条语句完全未覆盖）
  2. get_current_user 的补充边界测试
  3. get_redmine_client 基本行为
"""
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from backend.app.core.dependencies import (
    get_current_user,
    get_current_admin,
    get_redmine_client,
)


# ═══════════════════════════════════════════════════════════════════════════════
# get_current_admin 测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetCurrentAdmin:
    """测试 get_current_admin 管理员权限校验"""

    async def test_admin_user_passes(self):
        """管理员用户（role=admin）正常通过"""
        admin_user = {"user_id": 1, "username": "admin", "role": "admin"}
        result = await get_current_admin(current_user=admin_user)
        assert result == admin_user
        assert  result["role"] =="admin"

    async def test_non_admin_user_raises_403(self):
        """非管理员用户（role=user）抛出 403"""
        normal_user = {"user_id": 2, "username": "user1", "role": "user"}
        with pytest.raises(HTTPException) as exc_info:
            await get_current_admin(current_user=normal_user)
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["message"] == "需要管理员权限"
        assert exc_info.value.detail["code"] == 403

    async def test_missing_role_raises_403(self):
        """缺少 role 字段时抛出 403"""
        user_without_role = {"user_id": 3, "username": "norole"}
        with pytest.raises(HTTPException) as exc_info:
            await get_current_admin(current_user=user_without_role)
        assert exc_info.value.status_code == 403

    async def test_empty_role_raises_403(self):
        """role 为空字符串时抛出 403"""
        user_empty_role = {"user_id": 4, "username": "empty", "role": ""}
        with pytest.raises(HTTPException) as exc_info:
            await get_current_admin(current_user=user_empty_role)
        assert exc_info.value.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════════
# get_current_user 补充边界测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetCurrentUserEdgeCases:
    """测试 get_current_user 边界情况"""

    async def test_no_credentials_raises_401(self):
        """无 Authorization 头时抛出 401"""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=None)
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["message"] == "请先登录"

    async def test_invalid_token_raises_401(self):
        """无效 Token 抛出 401"""
        creds = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="invalid.token.here"
        )
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=creds)
        assert exc_info.value.status_code == 401
        assert "无效或已过期" in exc_info.value.detail["message"]

    async def test_valid_token_returns_user_info(self):
        """有效 Token 返回用户信息"""
        from backend.app.core.security import create_access_token

        token = create_access_token({
            "sub": "1",
            "username": "admin",
            "role": "admin",
        })
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with patch("backend.app.core.dependencies.is_token_blacklisted", new_callable=AsyncMock) as mock_bl:
            mock_bl.return_value = False
            result = await get_current_user(credentials=creds)

        assert result["user_id"] == 1
        assert result["username"] == "admin"
        assert result["role"] == "admin"

    async def test_blacklisted_token_raises_401(self):
        """已加入黑名单的 Token 抛出 401"""
        from backend.app.core.security import create_access_token

        token = create_access_token({
            "sub": "1",
            "username": "admin",
            "role": "admin",
        })
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with patch("backend.app.core.dependencies.is_token_blacklisted", new_callable=AsyncMock) as mock_bl:
            mock_bl.return_value = True  # Token 已被注销
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials=creds)
            assert exc_info.value.status_code == 401
            assert "已注销" in exc_info.value.detail["message"]


# ═══════════════════════════════════════════════════════════════════════════════
# get_redmine_client 测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetRedmineClient:
    """测试 get_redmine_client 依赖"""

    def test_returns_redmine_client_instance(self):
        """返回 RedmineClient 实例"""
        from backend.app.core.redmine_client import RedmineClient
        client = get_redmine_client()
        assert isinstance(client, RedmineClient)

    def test_client_uses_settings_url(self):
        """客户端使用配置文件中的 Redmine URL"""
        from backend.app.core.config import settings
        client = get_redmine_client()
        assert client.base_url == settings.REDMINE_URL.rstrip("/")

    def test_client_uses_settings_api_key(self):
        """客户端使用配置文件中的 API Key"""
        from backend.app.core.config import settings
        client = get_redmine_client()
        assert client.api_key == settings.REDMINE_API_KEY
