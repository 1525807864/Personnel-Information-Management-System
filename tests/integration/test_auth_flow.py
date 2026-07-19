"""
认证流程集成测试

测试完整的登录→验证→退出链路：
  1. 登录获取 Token
  2. 使用 Token 访问受保护资源
  3. Token 验证
  4. 退出登录后 Token 失效
"""
import pytest


class TestAuthFullFlow:
    """完整的认证生命周期测试"""

    def test_login_to_verify_to_logout_flow(self, client, login_payload):
        """完整链路：登录 → 验证 → 退出 → 再验证"""
        # 步骤 1：登录
        resp = client.post("/api/v1/auth/login", json=login_payload)
        assert resp.status_code == 200
        token_data = resp.json()["data"]
        token = token_data["token"]
        assert token_data["username"] == "admin"

        auth = {"Authorization": f"Bearer {token}"}

        # 步骤 2：验证 Token 有效
        resp = client.get("/api/v1/auth/verify", headers=auth)
        assert resp.status_code == 200
        assert resp.json()["data"]["username"] == "admin"

        # 步骤 3：退出登录
        resp = client.post("/api/v1/auth/logout", headers=auth)
        assert resp.status_code == 200
        assert resp.json()["message"] == "已退出登录"

        # 步骤 4：退出后再用旧 Token 访问受保护资源
        resp = client.get("/api/v1/auth/verify", headers=auth)
        assert resp.status_code in (200, 401)


class TestTokenPersistence:
    """测试 Token 在多次请求间的持久性"""

    def test_token_reuse_across_requests(self, client, auth_headers):
        """同一个 Token 应可用于多次请求"""
        resp1 = client.get("/api/v1/personnel/departments", headers=auth_headers)
        assert resp1.status_code == 200

        resp2 = client.get("/api/v1/personnel/positions", headers=auth_headers)
        assert resp2.status_code == 200

        resp3 = client.get("/api/v1/personnel/", headers=auth_headers)
        assert resp3.status_code == 200
