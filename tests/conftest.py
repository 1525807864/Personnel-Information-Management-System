"""
测试配置和共享 Fixtures

本文件为所有测试（单元/接口/集成）提供：
  1. RedmineMemoryStore — 内存存储，模拟 Redmine 服务端
  2. httpx.MockTransport — 拦截 RedmineClient 的 HTTP 请求
  3. FastAPI TestClient — 无服务器 HTTP 测试客户端
  4. 认证辅助 fixtures — 预生成 Token 和请求头
  5. UI 测试 fixtures — 登录态 Page Object
"""
import csv
import io
import json
import os
import sys
from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# 确保项目根目录在 Python 路径中
# ---------------------------------------------------------------------------
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

from backend.main import app
from backend.app.core.config import settings


# ═══════════════════════════════════════════════════════════════════════════════
# Windows 事件循环隔离：Playwright UI 测试会创建持久的事件循环，
# 导致后续异步单元测试的 run_until_complete 失败。
# 将 UI 测试排到最后执行，确保异步测试在干净的循环中运行。
# ═══════════════════════════════════════════════════════════════════════════════

def pytest_collection_modifyitems(items):
    """异步单元/API/集成测试先行，UI（Playwright）测试后行"""
    ui_items = []
    non_ui_items = []
    for item in items:
        if "ui" in item.nodeid:
            ui_items.append(item)
        else:
            non_ui_items.append(item)
    items[:] = non_ui_items + ui_items


# ═══════════════════════════════════════════════════════════════════════════════
# RedmineMemoryStore — 模拟 Redmine 服务端的内存存储
# ═══════════════════════════════════════════════════════════════════════════════

class RedmineMemoryStore:
    """模拟 Redmine 服务端，所有数据存内存，响应格式与真实 Redmine API 一致"""

    # cf_id → field_name 映射（与 PersonnelFieldMapping 保持一致）
    CF_ID_TO_NAME = {
        1: "employee_id", 2: "name", 3: "gender", 4: "age",
        5: "phone", 6: "department", 7: "position", 8: "start_datetime",
        9: "create_datetime", 10: "is_deleted", 11: "email",
    }

    def __init__(self):
        self._issues: list[dict] = []
        self._id_counter = 100
        self._users = [
            {
                "id": 1, "login": "admin", "admin": True, "status": 1,
                "firstname": "Test", "lastname": "Admin", "mail": "admin@test.com",
                "custom_fields": [{"id": 1, "name": "部门", "value": "技术部"}],
            }
        ]

    # ── Issue CRUD ─────────────────────────────────────────────

    def create_issue(self, payload: dict) -> dict:
        self._id_counter += 1
        new_issue = {
            "id": self._id_counter,
            "subject": payload.get("issue", {}).get("subject", ""),
            "project": {"id": 427, "name": "人员管理"},
            "tracker": {"id": 1, "name": "任务"},
            "status": {"id": 1, "name": "新建"},
            "created_on": "2024-01-01T00:00:00Z",
            "updated_on": "2024-01-01T00:00:00Z",
            "custom_fields": payload.get("issue", {}).get("custom_fields", []),
        }
        self._issues.append(new_issue)
        return {"issue": new_issue}

    def get_issues(self, params: dict) -> dict:
        """支持 project_id, page, limit, cf_1(cf_1=employee_id) 筛选和分页"""
        page = int(params.get("page", 1))
        limit = int(params.get("limit", 25))
        cf_filter = params.get("cf_1")

        items = self._issues
        if cf_filter:
            items = []
            for iss in self._issues:
                for cf in iss.get("custom_fields", []):
                    if cf.get("id") == 1 and str(cf.get("value")) == cf_filter:
                        items.append(iss)
                        break

        start = (page - 1) * limit
        end = start + limit
        return {
            "issues": items[start:end],
            "total_count": len(items),
            "limit": limit,
            "offset": start,
        }

    def get_issue(self, issue_id: int) -> dict:
        for iss in self._issues:
            if iss["id"] == issue_id:
                return {"issue": iss}
        raise ValueError(f"Issue {issue_id} not found")

    def update_issue(self, issue_id: int, payload: dict) -> dict:
        for iss in self._issues:
            if iss["id"] == issue_id:
                issue_data = payload.get("issue", {})
                if "subject" in issue_data:
                    iss["subject"] = issue_data["subject"]
                new_cfs = issue_data.get("custom_fields", [])
                for new_cf in new_cfs:
                    cf_id = new_cf["id"]
                    cf_name = self.CF_ID_TO_NAME.get(cf_id, f"cf_{cf_id}")
                    # 更新或添加 custom_field（补全 name 字段）
                    found = False
                    for cf in iss.get("custom_fields", []):
                        if cf["id"] == cf_id:
                            cf["value"] = str(new_cf.get("value", ""))
                            cf["name"] = cf_name
                            found = True
                            break
                    if not found:
                        iss.setdefault("custom_fields", []).append({
                            "id": cf_id, "name": cf_name,
                            "value": str(new_cf.get("value", "")),
                        })
                iss["updated_on"] = "2024-06-01T00:00:00Z"
                return {"issue": iss}
        raise ValueError(f"Issue {issue_id} not found")

    # ── User ───────────────────────────────────────────────────

    def get_user(self, user_id: int) -> dict:
        for u in self._users:
            if u["id"] == user_id:
                return {"user": u}
        return {"user": {}}

    def find_users(self, params: dict) -> dict:
        """按 login 搜索用户（用于登录验证）"""
        login = params.get("login", "")
        matched = [u for u in self._users if u.get("login") == login]
        return {"users": matched, "total_count": len(matched)}


# ═══════════════════════════════════════════════════════════════════════════════
# httpx.MockTransport — 拦截 RedmineClient 发出的 HTTP 请求
# ═══════════════════════════════════════════════════════════════════════════════

def _build_redmine_transport(store: RedmineMemoryStore) -> httpx.MockTransport:
    """构建模拟 Redmine API 响应的 MockTransport"""

    BASE = settings.REDMINE_URL.rstrip("/")

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        method = request.method
        headers = dict(request.headers)

        # ── Users API ──────────────────────────────────────────
        if path == "/users/current.json":
            # verify_user_credentials 用 Basic Auth
            auth = headers.get("authorization", "")
            if auth.startswith("Basic "):
                import base64
                try:
                    decoded = base64.b64decode(auth[6:]).decode()
                    login, pwd = decoded.split(":", 1)
                    if login == "admin" and pwd == "admin123":
                        return httpx.Response(200, json={"user": store._users[0]})
                except Exception:
                    pass
            # 其他情况检查 API Key
            if "x-redmine-api-key" in headers:
                return httpx.Response(200, json={"user": store._users[0]})
            return httpx.Response(401, json={"errors": ["Unauthorized"]})

        # ── 其余端点需要 API Key ──────────────────────────────
        if "x-redmine-api-key" not in headers:
            return httpx.Response(401, json={"errors": ["Unauthorized"]})

        if "/users/" in path and ".json" in path and "current" not in path:
            user_id = int(path.split("/users/")[1].split(".")[0])
            return httpx.Response(200, json=store.get_user(user_id))

        if path == "/users.json":
            params = {k: v for k, v in request.url.params.items()}
            result = store.find_users(params)
            return httpx.Response(200, json=result)

        # ── Issues API ─────────────────────────────────────────
        if path == "/issues.json" and method == "POST":
            payload = json.loads(request.content)
            result = store.create_issue(payload)
            return httpx.Response(201, json=result)

        if path == "/issues.json" and method == "GET":
            params = {k: v for k, v in request.url.params.items()}
            result = store.get_issues(params)
            return httpx.Response(200, json=result)

        if "/issues/" in path and ".json" in path:
            issue_id = int(path.split("/issues/")[1].split(".")[0])
            if method == "GET":
                try:
                    return httpx.Response(200, json=store.get_issue(issue_id))
                except ValueError:
                    return httpx.Response(404, json={"errors": ["Not found"]})
            elif method == "PUT":
                payload = json.loads(request.content)
                try:
                    return httpx.Response(200, json=store.update_issue(issue_id, payload))
                except ValueError:
                    return httpx.Response(404, json={"errors": ["Not found"]})

        return httpx.Response(404, json={"errors": ["Unknown endpoint"]})

    return httpx.MockTransport(handler)


# ═══════════════════════════════════════════════════════════════════════════════
# Mock RedmineClient — 核心 Mock Fixture
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def redmine_store() -> RedmineMemoryStore:
    """每次测试独立的 Redmine 内存存储"""
    return RedmineMemoryStore()


@pytest.fixture
def mock_redmine(redmine_store: RedmineMemoryStore):
    """
    用 httpx.MockTransport 拦截 RedmineClient 的 HTTP 层。
    RedmineClient.__init__ 会创建 httpx.AsyncHTTPTransport，
    我们 patch 它返回 MockTransport，这样 RedmineClient 所有
    方法的 HTTP 请求都被拦截，但请求构造/响应解析等真实代码全部执行。
    """
    transport = _build_redmine_transport(redmine_store)

    with (
        patch("httpx.AsyncHTTPTransport", return_value=transport),
        patch("backend.app.api.v1.personnel.get_redmine_client") as mock_personnel_dep,
        patch("backend.app.api.v1.import_api.get_redmine_client") as mock_import_dep,
    ):
        from backend.app.core.redmine_client import RedmineClient

        client = RedmineClient(
            base_url=settings.REDMINE_URL.rstrip("/"),
            api_key=settings.REDMINE_API_KEY,
        )
        mock_personnel_dep.return_value = client
        mock_import_dep.return_value = client

        # 暴露内部存储供测试断言
        client._store = redmine_store
        yield client


# ═══════════════════════════════════════════════════════════════════════════════
# FastAPI TestClient
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def client(mock_redmine):
    return TestClient(app)


# ═══════════════════════════════════════════════════════════════════════════════
# 认证辅助 Fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def login_payload():
    return {"username": "admin", "password": "admin123"}


@pytest.fixture
def auth_token(client, login_payload):
    resp = client.post("/api/v1/auth/login", json=login_payload)
    assert resp.status_code == 200
    return resp.json()["data"]["token"]


@pytest.fixture
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


# ═══════════════════════════════════════════════════════════════════════════════
# 测试数据 Fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def sample_personnel():
    return {
        "employee_id": "EMP001", "name": "张三", "gender": "男", "age": 25,
        "phone": "13800138000", "email": "zhangsan@example.com",
        "department": "技术部", "position": "工程师", "hire_date": "2024-01-01",
    }


@pytest.fixture
def sample_personnel_update():
    return {"name": "张三(已修改)", "position": "高级工程师", "age": 30}


@pytest.fixture
def sample_csv_content():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["人员编号", "姓名", "性别", "年龄", "手机号", "邮箱", "部门", "职位", "入职日期"])
    writer.writerow(["EMP001", "张三", "男", "25", "13800138000", "zhangsan@test.com", "技术部", "工程师", "2024-01-01"])
    writer.writerow(["EMP002", "李四", "女", "30", "13900139000", "lisi@test.com", "产品部", "产品经理", "2023-06-15"])
    return output.getvalue().encode("utf-8-sig")


# ═══════════════════════════════════════════════════════════════════════════════
# UI 测试 Fixtures（仅在 pytest-playwright 可用时加载）
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def app_base_url() -> str:
    return "http://127.0.0.1:8070"


@pytest.fixture(scope="session")
def admin_credentials() -> dict:
    return {"username": "admin", "password": "admin123"}


@pytest.fixture
def new_person_data() -> dict:
    return {
        "employee_id": "UI001", "name": "UI测试用户", "gender": "男", "age": 28,
        "phone": "13812345678", "email": "uitest@test.com",
        "department": "质量保障部", "position": "测试工程师", "hire_date": "2025-01-15",
    }


@pytest.fixture
def logged_in_personnel_form(page, app_base_url: str, admin_credentials: dict):
    """登录后进入新增人员表单页面"""
    from tests.ui.pages.login_page import LoginPage
    from tests.ui.pages.personnel_form_page import PersonnelFormPage

    lp = LoginPage(page)
    lp.open(app_base_url)
    lp.login(admin_credentials["username"], admin_credentials["password"])
    lp.wait_for_dashboard()

    form = PersonnelFormPage(page)
    form.open(app_base_url)
    return form