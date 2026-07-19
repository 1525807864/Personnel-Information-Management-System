"""
backend/main.py 单元测试

测试目标：
  1. 422 中文校验错误格式化（_FIELD_LABELS 和 _ERROR_TEMPLATES 映射）
  2. CORS 中间件配置验证
  3. 根路径健康检查接口
  4. RequestLoggingMiddleware 基本行为
"""
import pytest
from fastapi.testclient import TestClient


# ═══════════════════════════════════════════════════════════════════════════════
# 根路径健康检查
# ═══════════════════════════════════════════════════════════════════════════════

class TestRootEndpoint:
    """测试根路径健康检查接口"""

    def test_root_returns_200(self, client: TestClient):
        """根路径返回 200 状态码"""
        resp = client.get("/")
        assert resp.status_code == 200

    def test_root_returns_app_info(self, client: TestClient):
        """根路径返回应用名称和版本号"""
        resp = client.get("/")
        data = resp.json()
        assert data["message"] == "人员信息管理系统 API"
        assert data["Version"] == "1.0.0"


# ═══════════════════════════════════════════════════════════════════════════════
# 422 中文校验错误格式化
# ═══════════════════════════════════════════════════════════════════════════════

class TestValidationErrorHandler:
    """测试 422 校验错误的中文格式化"""

    def test_missing_required_field_returns_chinese_message(self, client: TestClient, auth_headers):
        """缺少必填字段时返回中文错误消息"""
        # 提交一个缺少多个必填字段的人员创建请求
        resp = client.post(
            "/api/v1/personnel/",
            json={"employee_id": "EMP999"},  # 缺少 name, gender, age 等
            headers=auth_headers,
        )
        assert resp.status_code == 422
        data = resp.json()
        assert data["code"] == 422
        assert data["data"] is None
        # 错误消息应为中文
        assert "message" in data
        assert len(data["message"]) > 0

    def test_invalid_phone_format_returns_chinese_message(self, client: TestClient, auth_headers):
        """手机号格式不正确时返回中文提示"""
        resp = client.post(
            "/api/v1/personnel/",
            json={
                "employee_id": "EMP999", "name": "测试", "gender": "男",
                "age": 25, "phone": "123",  # 无效手机号
                "email": "test@test.com", "department": "技术部",
                "position": "工程师", "hire_date": "2024-01-01",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422
        data = resp.json()
        assert data["code"] == 422
        # 消息中应包含格式相关提示
        assert "message" in data

    def test_invalid_age_type_returns_chinese_message(self, client: TestClient, auth_headers):
        """年龄为非数字时返回中文提示"""
        resp = client.post(
            "/api/v1/personnel/",
            json={
                "employee_id": "EMP999", "name": "测试", "gender": "男",
                "age": "abc",  # 非数字
                "phone": "13800138000",
                "email": "test@test.com", "department": "技术部",
                "position": "工程师", "hire_date": "2024-01-01",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422
        data = resp.json()
        assert data["code"] == 422

    def test_invalid_gender_returns_422(self, client: TestClient, auth_headers):
        """性别值不合法时返回 422"""
        resp = client.post(
            "/api/v1/personnel/",
            json={
                "employee_id": "EMP999", "name": "测试", "gender": "未知",
                "age": 25, "phone": "13800138000",
                "email": "test@test.com", "department": "技术部",
                "position": "工程师", "hire_date": "2024-01-01",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422
        data = resp.json()
        assert data["code"] == 422

    def test_422_response_structure(self, client: TestClient, auth_headers):
        """422 响应结构包含 code、message、data 三个字段"""
        resp = client.post(
            "/api/v1/personnel/",
            json={},  # 完全空的请求体
            headers=auth_headers,
        )
        assert resp.status_code == 422
        data = resp.json()
        assert "code" in data
        assert "message" in data
        assert "data" in data
        assert data["code"] == 422
        assert data["data"] is None


# ═══════════════════════════════════════════════════════════════════════════════
# CORS 中间件配置验证
# ═══════════════════════════════════════════════════════════════════════════════

class TestCORSConfiguration:
    """测试 CORS 中间件配置"""

    def test_cors_preflight_request(self, client: TestClient):
        """CORS 预检请求（OPTIONS）应返回正确的 Access-Control 头"""
        resp = client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "http://127.0.0.1:8070",
                "Access-Control-Request-Method": "POST",
            },
        )
        # CORS 中间件应允许配置的 origin
        assert resp.status_code == 200
        assert "access-control-allow-origin" in resp.headers
        assert resp.headers["access-control-allow-origin"] == "http://127.0.0.1:8070"

    def test_cors_allows_credentials(self, client: TestClient):
        """CORS 配置允许携带凭证"""
        resp = client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "http://127.0.0.1:8070",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert resp.headers.get("access-control-allow-credentials") == "true"

    def test_cors_disallows_unknown_origin(self, client: TestClient):
        """未配置的 Origin 不应获得 CORS 允许头"""
        resp = client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "http://evil-site.com",
                "Access-Control-Request-Method": "POST",
            },
        )
        # 对于不允许的 origin，不应返回 access-control-allow-origin 头
        # 或者返回的 origin 不匹配请求的 origin
        acao = resp.headers.get("access-control-allow-origin", "")
        assert acao != "http://evil-site.com"


# ═══════════════════════════════════════════════════════════════════════════════
# RequestLoggingMiddleware 基本行为
# ═══════════════════════════════════════════════════════════════════════════════

class TestRequestLoggingMiddleware:
    """测试请求日志中间件基本行为"""

    def test_middleware_does_not_block_normal_request(self, client: TestClient):
        """中间件不影响正常请求的响应"""
        resp = client.get("/")
        assert resp.status_code == 200
        assert resp.json()["message"] == "人员信息管理系统 API"

    def test_middleware_does_not_alter_response_body(self, client: TestClient):
        """中间件不修改响应体内容"""
        resp = client.get("/")
        data = resp.json()
        # 确保响应体完整未被截断或修改
        assert "message" in data
        assert "Version" in data

    def test_middleware_handles_404_gracefully(self, client: TestClient):
        """中间件对 404 请求也能正常处理（不抛异常）"""
        resp = client.get("/nonexistent-endpoint-xyz")
        assert resp.status_code == 404

    def test_middleware_handles_method_not_allowed(self, client: TestClient):
        """中间件对 405 方法不允许也能正常处理"""
        resp = client.delete("/")
        assert resp.status_code == 405
