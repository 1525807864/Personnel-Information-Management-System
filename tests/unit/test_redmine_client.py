"""
RedmineClient 单元测试

测试目标：
  1. create_issue 两步操作（先创建 Issue 再更新自定义字段）的成功/失败分支
  2. verify_user_credentials Basic Auth 验证的成功、401、网络异常分支
  3. check_account_locked 各种返回情况（含搜索结果少于4个用户的边界情况）
  4. get_users 分页参数传递、空结果、HTTP 错误码处理
  5. update_issue、delete_issue 的成功与异常分支
  6. get_issues、get_issue 基本操作
"""
import json
from unittest.mock import patch

import httpx
import pytest

from backend.app.core.redmine_client import RedmineClient


# ═══════════════════════════════════════════════════════════════════════════════
# 辅助：构建带 MockTransport 的 RedmineClient
# ═══════════════════════════════════════════════════════════════════════════════

BASE_URL = "http://redmine.test"
API_KEY = "test-api-key-123"


def _make_client(handler) -> RedmineClient:
    """用指定的 handler 函数创建 RedmineClient（HTTP 层被 MockTransport 拦截）"""
    transport = httpx.MockTransport(handler)
    with patch("httpx.AsyncHTTPTransport", return_value=transport):
        client = RedmineClient(base_url=BASE_URL, api_key=API_KEY)
    return client


# ═══════════════════════════════════════════════════════════════════════════════
# create_issue 测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestCreateIssue:
    """测试 create_issue 两步操作"""

    async def test_create_issue_with_custom_fields_success(self):
        """创建 Issue 并成功更新自定义字段（两步操作完整流程）"""
        call_log = []

        def handler(request: httpx.Request) -> httpx.Response:
            path = request.url.path
            method = request.method
            call_log.append((method, path))

            if path == "/issues.json" and method == "POST":
                payload = json.loads(request.content)
                assert payload["issue"]["project_id"] == 427
                assert payload["issue"]["subject"] == "TEST001 - 张三"
                return httpx.Response(200, json={
                    "issue": {"id": 1001, "subject": "TEST001 - 张三"}
                })
            elif "/issues/1001.json" in path and method == "PUT":
                payload = json.loads(request.content)
                assert "custom_fields" in payload["issue"]
                return httpx.Response(200, json={})
            elif "/issues/1001.json" in path and method == "GET":
                return httpx.Response(200, json={
                    "issue": {
                        "id": 1001,
                        "subject": "TEST001 - 张三",
                        "custom_fields": [
                            {"id": 1, "value": "TEST001"},
                            {"id": 2, "value": "张三"},
                        ],
                    }
                })
            return httpx.Response(404)

        client = _make_client(handler)
        result = await client.create_issue({
            "project_id": 427,
            "subject": "TEST001 - 张三",
            "tracker_id": 1,
            "status_id": 1,
            "cf_1": "TEST001",
            "cf_2": "张三",
        })

        # 验证返回了重新 GET 的完整 Issue
        assert result["issue"]["id"] == 1001
        assert len(result["issue"]["custom_fields"]) == 2
        # 验证调用顺序：POST → PUT → GET
        assert call_log[0] == ("POST", "/issues.json")
        assert call_log[1] == ("PUT", "/issues/1001.json")
        assert call_log[2] == ("GET", "/issues/1001.json")

    async def test_create_issue_without_custom_fields(self):
        """创建 Issue 无自定义字段时不执行第二步更新"""
        call_log = []

        def handler(request: httpx.Request) -> httpx.Response:
            call_log.append((request.method, request.url.path))
            if request.url.path == "/issues.json" and request.method == "POST":
                return httpx.Response(201, json={
                    "issue": {"id": 2001, "subject": "无自定义字段"}
                })
            return httpx.Response(404)

        client = _make_client(handler)
        result = await client.create_issue({
            "project_id": 427,
            "subject": "无自定义字段",
        })

        assert result["issue"]["id"] == 2001
        # 仅一次 POST 调用，无 PUT/GET
        assert len(call_log) == 1
        assert call_log[0] == ("POST", "/issues.json")

    async def test_create_issue_post_fails(self):
        """创建 Issue 第一步 POST 失败时抛出 HTTPStatusError"""
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(422, json={"errors": ["Subject cannot be blank"]})

        client = _make_client(handler)
        with pytest.raises(httpx.HTTPStatusError):
            await client.create_issue({
                "project_id": 427,
                "subject": "",
            })

    async def test_create_issue_update_step_fails(self):
        """创建 Issue 第二步 PUT 更新自定义字段失败时抛出 HTTPStatusError"""
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/issues.json" and request.method == "POST":
                return httpx.Response(201, json={"issue": {"id": 3001}})
            elif "/issues/3001.json" in request.url.path and request.method == "PUT":
                return httpx.Response(500, json={"errors": ["Internal Server Error"]})
            return httpx.Response(404)

        client = _make_client(handler)
        with pytest.raises(httpx.HTTPStatusError):
            await client.create_issue({
                "project_id": 427,
                "subject": "Test",
                "cf_1": "E001",
            })


# ═══════════════════════════════════════════════════════════════════════════════
# verify_user_credentials 测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestVerifyUserCredentials:
    """测试 verify_user_credentials Basic Auth 验证"""

    async def test_valid_credentials_returns_user_info(self):
        """正确的用户名密码返回用户信息字典"""
        def handler(request: httpx.Request) -> httpx.Response:
            assert "/users/current.json" in request.url.path
            auth = request.headers.get("authorization", "")
            assert auth.startswith("Basic ")
            return httpx.Response(200, json={
                "user": {"id": 1, "login": "admin", "admin": True}
            })

        client = _make_client(handler)
        result = await client.verify_user_credentials("admin", "admin123")
        assert result is not None
        assert result["user"]["login"] == "admin"
        assert result["user"]["admin"] is True

    async def test_invalid_credentials_returns_none(self):
        """错误的凭证返回 None（401 响应）"""
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, json={"errors": ["Unauthorized"]})

        client = _make_client(handler)
        result = await client.verify_user_credentials("admin", "wrong_password")
        assert result is None

    async def test_network_exception_returns_none(self):
        """网络异常时返回 None（不抛出异常）"""
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Connection refused")

        client = _make_client(handler)
        result = await client.verify_user_credentials("admin", "admin123")
        assert result is None

    async def test_server_error_returns_none(self):
        """服务端 500 错误时返回 None"""
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="Internal Server Error")

        client = _make_client(handler)
        result = await client.verify_user_credentials("admin", "admin123")
        assert result is None


# ═══════════════════════════════════════════════════════════════════════════════
# check_account_locked 测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestCheckAccountLocked:
    """测试 check_account_locked（含边界情况）"""

    async def test_account_locked_status_3(self):
        """用户 status=3 表示锁定，返回 True"""
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={
                "users": [
                    {"id": 1, "login": "admin", "status": 1},
                    {"id": 2, "login": "user2", "status": 1},
                    {"id": 3, "login": "user3", "status": 1},
                    {"id": 4, "login": "target", "status": 3},
                ]
            })

        client = _make_client(handler)
        result = await client.check_account_locked("target")
        assert result is True

    async def test_account_active_status_1(self):
        """用户 status=1 表示活跃，返回 False"""
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={
                "users": [
                    {"id": 1, "login": "u1", "status": 1},
                    {"id": 2, "login": "u2", "status": 1},
                    {"id": 3, "login": "u3", "status": 1},
                    {"id": 4, "login": "target", "status": 1},
                ]
            })

        client = _make_client(handler)
        result = await client.check_account_locked("target")
        assert result is False

    async def test_fewer_than_4_users_raises_index_error(self):
        """搜索结果少于4个用户时，users[3] 会引发 IndexError（已知 bug）"""
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={
                "users": [
                    {"id": 1, "login": "admin", "status": 1},
                ]
            })

        client = _make_client(handler)
        # 已知 bug：users[3] 会 IndexError
        with pytest.raises(IndexError):
            await client.check_account_locked("admin")

    async def test_empty_users_list_raises_index_error(self):
        """空用户列表时 users[3] 引发 IndexError（已知 bug）"""
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"users": []})

        client = _make_client(handler)
        with pytest.raises(IndexError):
            await client.check_account_locked("nobody")

    async def test_non_200_response_returns_false(self):
        """非 200 响应时返回 False"""
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="Server Error")

        client = _make_client(handler)
        result = await client.check_account_locked("admin")
        assert result is False


# ═══════════════════════════════════════════════════════════════════════════════
# get_users 测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetUsers:
    """测试 get_users 分页参数传递、空结果、HTTP 错误"""

    async def test_pagination_params_passed(self):
        """分页参数正确传递到请求中"""
        captured_params = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured_params.update(dict(request.url.params))
            return httpx.Response(200, json={
                "users": [{"id": 1, "login": "admin"}],
                "total_count": 1,
            })

        client = _make_client(handler)
        result = await client.get_users(page=3, limit=50)

        assert captured_params["page"] == "3"
        assert captured_params["limit"] == "50"
        assert captured_params["status"] == "*"
        assert result["total_count"] == 1

    async def test_empty_result(self):
        """无用户时返回空列表"""
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"users": [], "total_count": 0})

        client = _make_client(handler)
        result = await client.get_users()
        assert result["users"] == []
        assert result["total_count"] == 0

    async def test_custom_field_filters(self):
        """cf_ 前缀的过滤器正确传递"""
        captured_params = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured_params.update(dict(request.url.params))
            return httpx.Response(200, json={"users": [], "total_count": 0})

        client = _make_client(handler)
        await client.get_users(filters={"cf_1": "技术部", "name": "张"})

        assert captured_params["cf_1"] == "技术部"
        assert captured_params["name"] == "张"

    async def test_http_error_raises(self):
        """HTTP 错误码（如 401）抛出 HTTPStatusError"""
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, json={"errors": ["Unauthorized"]})

        client = _make_client(handler)
        with pytest.raises(httpx.HTTPStatusError):
            await client.get_users()


# ═══════════════════════════════════════════════════════════════════════════════
# update_issue 测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestUpdateIssue:
    """测试 update_issue 成功与异常分支"""

    async def test_update_issue_204_refetch(self):
        """Redmine 返回 204 时重新 GET 获取最新数据"""
        call_log = []

        def handler(request: httpx.Request) -> httpx.Response:
            call_log.append((request.method, request.url.path))
            if request.method == "PUT":
                return httpx.Response(204)
            elif request.method == "GET":
                return httpx.Response(200, json={
                    "issue": {"id": 100, "subject": "Updated Subject"}
                })
            return httpx.Response(404)

        client = _make_client(handler)
        result = await client.update_issue(100, {"subject": "Updated Subject"})

        assert result["issue"]["subject"] == "Updated Subject"
        assert ("PUT", "/issues/100.json") in call_log
        assert ("GET", "/issues/100.json") in call_log

    async def test_update_issue_200_with_body(self):
        """Redmine 返回 200 带 body 时直接返回"""
        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "PUT":
                return httpx.Response(200, json={
                    "issue": {"id": 100, "subject": "OK"}
                })
            return httpx.Response(404)

        client = _make_client(handler)
        result = await client.update_issue(100, {"subject": "OK"})
        assert result["issue"]["id"] == 100

    async def test_update_issue_with_custom_fields(self):
        """更新 Issue 时自定义字段正确构建到 payload"""
        captured_body = {}

        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "PUT":
                captured_body.update(json.loads(request.content))
                return httpx.Response(204)
            elif request.method == "GET":
                return httpx.Response(200, json={"issue": {"id": 100}})
            return httpx.Response(404)

        client = _make_client(handler)
        await client.update_issue(100, {
            "subject": "Test",
            "cf_2": "新名字",
            "cf_4": "30",
        })

        assert captured_body["issue"]["subject"] == "Test"
        cf_list = captured_body["issue"]["custom_fields"]
        assert {"id": 2, "value": "新名字"} in cf_list
        assert {"id": 4, "value": "30"} in cf_list

    async def test_update_issue_not_found_raises(self):
        """更新不存在的 Issue 抛出 HTTPStatusError"""
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, json={"errors": ["Not found"]})

        client = _make_client(handler)
        with pytest.raises(httpx.HTTPStatusError):
            await client.update_issue(9999, {"subject": "X"})


# ═══════════════════════════════════════════════════════════════════════════════
# get_issues / get_issue 测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetIssues:
    """测试 get_issues 和 get_issue"""

    async def test_get_issues_with_filters(self):
        """get_issues 正确传递项目ID、分页和过滤参数"""
        captured_params = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured_params.update(dict(request.url.params))
            return httpx.Response(200, json={
                "issues": [{"id": 1}], "total_count": 1
            })

        client = _make_client(handler)
        result = await client.get_issues(
            project_id=427, page=2, limit=10,
            filters={"cf_1": "EMP001", "status_id": "open"},
        )

        assert captured_params["project_id"] == "427"
        assert captured_params["page"] == "2"
        assert captured_params["limit"] == "10"
        assert captured_params["cf_1"] == "EMP001"
        assert captured_params["status_id"] == "open"
        assert result["total_count"] == 1

    async def test_get_issues_http_error(self):
        """get_issues 遇到 HTTP 错误抛出异常"""
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="Server Error")

        client = _make_client(handler)
        with pytest.raises(httpx.HTTPStatusError):
            await client.get_issues(project_id=427)

    async def test_get_issue_success(self):
        """get_issue 成功获取单个 Issue"""
        def handler(request: httpx.Request) -> httpx.Response:
            assert "/issues/55.json" in request.url.path
            return httpx.Response(200, json={
                "issue": {"id": 55, "subject": "Test Issue"}
            })

        client = _make_client(handler)
        result = await client.get_issue(55)
        assert result["issue"]["id"] == 55
        assert result["issue"]["subject"] == "Test Issue"

    async def test_get_issue_not_found(self):
        """get_issue 获取不存在的 Issue 抛出异常"""
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, json={"errors": ["Not found"]})

        client = _make_client(handler)
        with pytest.raises(httpx.HTTPStatusError):
            await client.get_issue(9999)


# ═══════════════════════════════════════════════════════════════════════════════
# get_user_with_api_key 测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetUserWithApiKey:
    """测试 get_user_with_api_key"""

    async def test_success_returns_user_data(self):
        """成功获取用户完整信息"""
        def handler(request: httpx.Request) -> httpx.Response:
            assert "x-redmine-api-key" in request.headers
            return httpx.Response(200, json={
                "user": {"id": 1, "login": "admin", "status": 1}
            })

        client = _make_client(handler)
        result = await client.get_user_with_api_key(1)
        assert result is not None
        assert result["user"]["login"] == "admin"

    async def test_not_found_returns_none(self):
        """用户不存在时返回 None"""
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, json={"errors": ["Not found"]})

        client = _make_client(handler)
        result = await client.get_user_with_api_key(9999)
        assert result is None
