"""
认证接口测试

测试端点：
  POST /api/v1/auth/login  — 用户登录
  GET  /api/v1/auth/verify — Token 验证
  POST /api/v1/auth/logout — 退出登录
"""
import pytest


class TestAuthLogin:
    """测试登录接口 POST /api/v1/auth/login"""

    def test_login_success(self, client, login_payload):
        """正确用户名密码登录成功"""
        resp = client.post("/api/v1/auth/login", json=login_payload)
        assert resp.status_code == 200, f"期望 200，实际 {resp.status_code}: {resp.text}"

        data = resp.json()
        assert data["code"] == 200
        assert "token" in data["data"], "响应应包含 token 字段"
        assert data["data"]["username"] == "admin"
        assert data["data"]["role"] == "admin"

        token = data["data"]["token"]
        assert len(token) > 50, f"Token 太短: {len(token)} 字符"

    def test_login_wrong_password(self, client):
        """错误密码登录失败 — 返回 401"""
        resp = client.post("/api/v1/auth/login", json={
            "username": "admin", "password": "wrong_password",
        })
        assert resp.status_code == 401

    def test_login_empty_password(self, client):
        """空密码 — 返回 422（Pydantic 校验失败）"""
        resp = client.post("/api/v1/auth/login", json={
            "username": "admin", "password": "",
        })
        assert resp.status_code == 422

    def test_login_empty_username(self, client):
        """空用户名 — 返回 422"""
        resp = client.post("/api/v1/auth/login", json={
            "username": "", "password": "admin123",
        })
        assert resp.status_code == 422

    def test_login_missing_fields(self, client):
        """缺少必填字段 — 返回 422"""
        resp = client.post("/api/v1/auth/login", json={"username": "admin"})
        assert resp.status_code == 422

    def test_login_username_too_short(self, client):
        """用户名太短（< 3 位）— 返回 422"""
        resp = client.post("/api/v1/auth/login", json={
            "username": "ab", "password": "admin123",
        })
        assert resp.status_code == 422

    def test_login_username_too_long(self, client):
        """用户名太长（> 20 位）— 返回 422"""
        resp = client.post("/api/v1/auth/login", json={
            "username": "a" * 21, "password": "admin123",
        })
        assert resp.status_code == 422


class TestAuthVerify:
    """测试 Token 验证接口 GET /api/v1/auth/verify"""

    def test_verify_token_valid(self, client, auth_headers):
        """有效 Token 验证成功"""
        resp = client.get("/api/v1/auth/verify", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "Token有效"
        assert data["data"]["username"] == "admin"
        assert data["data"]["role"] == "admin"

    def test_verify_no_token(self, client):
        """无 Token 时返回 401"""
        resp = client.get("/api/v1/auth/verify")
        assert resp.status_code == 401

    def test_verify_invalid_token(self, client):
        """无效 Token（随机字符串）返回 401"""
        resp = client.get(
            "/api/v1/auth/verify",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert resp.status_code == 401

    def test_verify_malformed_token(self, client):
        """格式错误的 Token（非三段式）"""
        resp = client.get(
            "/api/v1/auth/verify",
            headers={"Authorization": "Bearer just_one_segment"},
        )
        assert resp.status_code == 401


class TestAuthLogout:
    """测试退出登录接口 POST /api/v1/auth/logout"""

    def test_logout_success(self, client, auth_headers):
        """携带有效 Token 退出应成功"""
        resp = client.post("/api/v1/auth/logout", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "已退出登录"

    def test_logout_no_token(self, client):
        """无 Token 退出应返回 401"""
        resp = client.post("/api/v1/auth/logout")
        assert resp.status_code == 401
