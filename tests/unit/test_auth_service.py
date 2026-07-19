"""
认证服务单元测试

测试目标：
  1. authenticate — 各种凭证验证场景
  2. generate_token — Token 生成
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.app.schemas.auth import LoginRequest
from backend.app.services.auth_service import AuthService


class TestAuthenticate:
    """测试 authenticate 方法"""

    @pytest.fixture
    def redmine_mock(self) -> MagicMock:
        rm = MagicMock()
        rm.verify_user_credentials = AsyncMock()
        rm.get_user_with_api_key = AsyncMock()
        return rm

    @pytest.fixture
    def login_request(self) -> LoginRequest:
        return LoginRequest(username="admin", password="admin123")

    async def test_valid_credentials_admin(
        self, redmine_mock: MagicMock, login_request: LoginRequest
    ) -> None:
        """admin 凭证有效 → 登录成功，角色为 admin"""
        redmine_mock.verify_user_credentials.return_value = {
            "user": {"id": 1, "login": "admin", "admin": True, "status": 1,
                     "firstname": "Test", "lastname": "Admin", "mail": "admin@test.com",
                     "custom_fields": []}
        }
        redmine_mock.get_user_with_api_key.return_value = None

        svc = AuthService(redmine_mock)
        success, msg, data = await svc.authenticate(login_request)

        assert success is True
        assert msg == "登录成功"
        assert data["role"] == "admin"
        assert data["user_id"] == 1

    async def test_valid_credentials_non_admin(
        self, redmine_mock: MagicMock
    ) -> None:
        """非 admin 用户 → 角色为 user"""
        redmine_mock.verify_user_credentials.return_value = {
            "user": {"id": 2, "login": "user1", "admin": False, "status": 1,
                     "firstname": "Normal", "lastname": "User", "mail": "user@test.com",
                     "custom_fields": []}
        }
        redmine_mock.get_user_with_api_key.return_value = None

        req = LoginRequest(username="user1", password="pass")
        svc = AuthService(redmine_mock)
        success, msg, data = await svc.authenticate(req)

        assert success is True
        assert data["role"] == "user"

    async def test_wrong_password(
        self, redmine_mock: MagicMock, login_request: LoginRequest
    ) -> None:
        """错误密码 → 登录失败"""
        redmine_mock.verify_user_credentials.return_value = None

        svc = AuthService(redmine_mock)
        success, msg, data = await svc.authenticate(login_request)

        assert success is False
        assert "用户名或密码错误" in msg
        assert data is None

    async def test_account_locked(
        self, redmine_mock: MagicMock, login_request: LoginRequest
    ) -> None:
        """账号状态为 3（锁定） → 拒绝登录"""
        redmine_mock.verify_user_credentials.return_value = {
            "user": {"id": 3, "login": "locked", "admin": False, "status": 3}
        }

        svc = AuthService(redmine_mock)
        success, msg, data = await svc.authenticate(login_request)

        assert success is False
        assert "锁定" in msg

    async def test_account_status_abnormal(
        self, redmine_mock: MagicMock
    ) -> None:
        """账号状态异常（非 1/2/3） → 拒绝登录"""
        redmine_mock.verify_user_credentials.return_value = {
            "user": {"id": 4, "login": "weird", "admin": False, "status": 99}
        }

        req = LoginRequest(username="weird", password="pass")
        svc = AuthService(redmine_mock)
        success, msg, data = await svc.authenticate(req)

        assert success is False
        assert "状态异常" in msg

    async def test_full_user_info_merged(
        self, redmine_mock: MagicMock
    ) -> None:
        """get_user_with_api_key 返回完整用户信息时应合并 custom_fields"""
        redmine_mock.verify_user_credentials.return_value = {
            "user": {"id": 5, "login": "full", "admin": True, "status": 1,
                     "firstname": "F", "lastname": "L", "mail": "f@test.com"}
        }
        redmine_mock.get_user_with_api_key.return_value = {
            "user": {
                "id": 5, "login": "full", "admin": True, "status": 1,
                "custom_fields": [
                    {"id": 1, "name": "部门", "value": "技术部"},
                ]
            }
        }

        req = LoginRequest(username="full", password="pass")
        svc = AuthService(redmine_mock)
        success, msg, data = await svc.authenticate(req)

        assert success is True
        assert len(data["custom_fields"]) == 1


class TestGenerateToken:
    """测试 generate_token 方法"""

    def test_token_structure(self) -> None:
        """生成的 token 包含正确字段"""
        svc = AuthService(MagicMock())
        user_data = {"user_id": 1, "login": "admin", "role": "admin"}
        result = svc.generate_token(user_data)

        assert result.username == "admin"
        assert result.role == "admin"
        assert result.user_id == 1
        assert len(result.token) > 50
        assert result.token.count(".") == 2  # JWT 三段式
