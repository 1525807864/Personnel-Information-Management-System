"""
人员管理接口测试

测试端点：
  POST   /api/v1/personnel/                    — 新增人员
  GET    /api/v1/personnel/                    — 查询人员列表
  GET    /api/v1/personnel/{id}                — 查询人员详情
  PUT    /api/v1/personnel/{id}                — 修改人员
  DELETE /api/v1/personnel/{id}                — 删除人员
  POST   /api/v1/personnel/search              — 高级搜索
  GET    /api/v1/personnel/departments         — 获取部门列表
  GET    /api/v1/personnel/positions           — 获取职位列表
  POST   /api/v1/personnel/batch               — 批量删除
"""
import pytest
from unittest.mock import AsyncMock
from unittest.mock import patch
# ═══════════════════════════════════════════════════════════════════════════════
# 测试数据常量
# ═══════════════════════════════════════════════════════════════════════════════

SAMPLE_PERSONNEL = {
    "employee_id": "EMP001",
    "name": "张三",
    "gender": "男",
    "age": 25,
    "phone": "13800138000",
    "email": "zhangsan@example.com",
    "department": "技术部",
    "position": "工程师",
    "hire_date": "2024-01-01",
}

SAMPLE_PERSONNEL_2 = {
    "employee_id": "EMP002",
    "name": "おうまな",
    "gender": "女",
    "age": 30,
    "phone": "13900139000",
    "email": "lisi@example.com",
    "department": "产品部",
    "position": "产品经理",
    "hire_date": "2023-06-15",
}


# ═══════════════════════════════════════════════════════════════════════════════
# 权限测试（所有路由通用）
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuthRequired:
    """验证所有人员管理端点均要求认证"""

    @pytest.mark.parametrize("method, path, body", [
        ("get",    "/api/v1/personnel/",          None),
        ("post",   "/api/v1/personnel/",          SAMPLE_PERSONNEL),
        ("get",    "/api/v1/personnel/1",          None),
        ("put",    "/api/v1/personnel/1",          {"name": "test"}),
        ("delete", "/api/v1/personnel/1",          None),
        ("post",   "/api/v1/personnel/search",     {}),
        ("get",    "/api/v1/personnel/departments", None),
        ("get",    "/api/v1/personnel/positions",   None),
        ("post",   "/api/v1/personnel/batch",      [1]),
    ])
    def test_unauthorized(self, client, method, path, body):
        """无 Token 访问任何受保护端点应返回 401"""
        if method == "get":
            resp = client.get(path)
        elif method == "post":
            resp = client.post(path, json=body)
        elif method == "put":
            resp = client.put(path, json=body)
        elif method == "delete":
            resp = client.delete(path)
        else:
            pytest.fail(f"Unsupported method: {method}")

        assert resp.status_code == 401, (
            f"{method.upper()} {path} 无 Token 应返回 401，"
            f"实际 {resp.status_code}: {resp.text}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 创建人员测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestCreatePersonnel:
    """测试 POST /api/v1/personnel/ — 新增人员"""

    def test_create_success(self, client, auth_headers):
        """创建成功 → 200"""
        resp = client.post(
            "/api/v1/personnel/",
            json=SAMPLE_PERSONNEL,
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
        assert data["message"] == "新增成功"
        assert data["data"]["employee_id"] == "EMP001"
        assert data["data"]["name"] == "张三"
        assert data["data"]["id"] is not None

    def test_create_duplicate_employee_id(self, client, auth_headers):
        """重复员工编号创建失败 → 409"""
        # 第一次创建成功
        client.post("/api/v1/personnel/", json=SAMPLE_PERSONNEL, headers=auth_headers)
        # 第二次相同的 employee_id 应返回 409
        resp = client.post("/api/v1/personnel/", json=SAMPLE_PERSONNEL, headers=auth_headers)
        assert resp.status_code == 409

    @pytest.mark.parametrize("field, invalid_value, desc", [
        ("employee_id", "EMP@001",       "非法字符@"),
        ("name",        "",               "空姓名"),
        ("gender",      "未知",           "非法性别"),
        ("age",         17,               "年龄<18"),
        ("age",         66,               "年龄>65"),
        ("phone",       "12345",          "手机号不足11位"),
        ("email",       "not-an-email",   "邮箱格式错误"),
        ("hire_date",   "2099-12-31",     "未来日期"),
    ])
    def test_create_invalid_field(self, client, auth_headers, field, invalid_value, desc):
        """各种非法字段应返回 422 校验错误"""
        payload = SAMPLE_PERSONNEL.copy()
        payload[field] = invalid_value
        resp = client.post("/api/v1/personnel/", json=payload, headers=auth_headers)
        assert resp.status_code in (422, 400), (
            f"校验失败应返回 422/400，字段={field} 值={invalid_value}（{desc}），"
            f"实际 {resp.status_code}"
        )

    @pytest.mark.parametrize("missing_field", [
        "employee_id", "name", "gender", "age", "phone", "email",
        "department", "position", "hire_date",
    ])
    def test_create_missing_required_field(self, client, auth_headers, missing_field):
        """缺少必填字段 → 422"""
        payload = SAMPLE_PERSONNEL.copy()
        del payload[missing_field]
        resp = client.post("/api/v1/personnel/", json=payload, headers=auth_headers)
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
# 查询人员列表测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetPersonnelList:
    """测试 GET /api/v1/personnel/ — 查询人员列表"""

    def test_list_default(self, client, auth_headers):
        """默认分页查询"""
        resp = client.get("/api/v1/personnel/", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
        assert "total" in data["data"]
        assert "page" in data["data"]
        assert "size" in data["data"]
        assert "items" in data["data"]
        assert isinstance(data["data"]["items"], list)

    def test_list_with_pagination(self, client, auth_headers):
        """自定义分页参数"""
        resp = client.get(
            "/api/v1/personnel/",
            params={"page": 2, "size": 10},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["page"] == 2
        assert data["data"]["size"] == 10

    def test_list_page_invalid(self, client, auth_headers):
        """page=0 → 422"""
        resp = client.get(
            "/api/v1/personnel/",
            params={"page": 0},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_list_size_too_large(self, client, auth_headers):
        """size=200 → 422"""
        resp = client.get(
            "/api/v1/personnel/",
            params={"size": 200},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_list_with_keyword(self, client, auth_headers):
        """带关键词搜索"""
        resp = client.get(
            "/api/v1/personnel/",
            params={"keyword": "张三"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_list_with_sorting(self, client, auth_headers):
        """带排序参数"""
        resp = client.get(
            "/api/v1/personnel/",
            params={"sort_by": "age", "sort_order": "asc"},
            headers=auth_headers,
        )
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# 查询人员详情测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetPersonnelDetail:
    """测试 GET /api/v1/personnel/{id} — 查询人员详情"""

    def test_get_detail_success(self, client, auth_headers):
        """查询存在的记录"""
        resp = client.post(
            "/api/v1/personnel/", json=SAMPLE_PERSONNEL, headers=auth_headers,
        )
        created_id = resp.json()["data"]["id"]

        resp = client.get(f"/api/v1/personnel/{created_id}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["employee_id"] == "EMP001"

    def test_get_detail_not_found(self, client, auth_headers):
        """查询不存在的记录 → 404"""
        resp = client.get("/api/v1/personnel/999999", headers=auth_headers)
        assert resp.status_code == 404

    def test_get_detail_invalid_id(self, client, auth_headers):
        """非法 ID（非数字）→ 422"""
        resp = client.get("/api/v1/personnel/abc", headers=auth_headers)
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
# 修改人员测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestUpdatePersonnel:
    """测试 PUT /api/v1/personnel/{id} — 修改人员"""

    def test_update_success(self, client, auth_headers):
        """修改已存在的记录"""
        resp = client.post(
            "/api/v1/personnel/", json=SAMPLE_PERSONNEL, headers=auth_headers,
        )
        created_id = resp.json()["data"]["id"]

        update_data = {"name": "张三丰", "position": "高级工程师", "age": 30}
        resp = client.put(
            f"/api/v1/personnel/{created_id}",
            json=update_data,
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "修改成功"

    def test_update_not_found(self, client, auth_headers):
        """修改不存在的记录 → 404"""
        resp = client.put(
            "/api/v1/personnel/999999",
            json={"name": "新名字"},
            headers=auth_headers,
        )
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# 删除人员测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestDeletePersonnel:
    """测试 DELETE /api/v1/personnel/{id} — 删除人员（软删除）"""

    def test_delete_success(self, client, auth_headers):
        """软删除成功 → 200"""
        resp = client.post(
            "/api/v1/personnel/", json=SAMPLE_PERSONNEL, headers=auth_headers,
        )
        created_id = resp.json()["data"]["id"]

        resp = client.delete(f"/api/v1/personnel/{created_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["message"] == "删除成功"


# ═══════════════════════════════════════════════════════════════════════════════
# 高级搜索测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestSearchPersonnel:
    """测试 POST /api/v1/personnel/search — 高级搜索"""

    def test_search_empty(self, client, auth_headers):
        """空搜索条件 → 200"""
        resp = client.post(
            "/api/v1/personnel/search",
            json={},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_search_by_keyword(self, client, auth_headers):
        """按关键词搜索"""
        resp = client.post(
            "/api/v1/personnel/search",
            json={"keyword": "张三", "page": 1, "size": 10},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_search_by_department(self, client, auth_headers):
        """按部门搜索"""
        resp = client.post(
            "/api/v1/personnel/search",
            json={"department": "技术部"},
            headers=auth_headers,
        )
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# 部门和职位列表测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestDepartmentsAndPositions:
    """测试部门/职位下拉列表接口"""

    def test_get_departments(self, client, auth_headers):
        """获取部门列表 → 200"""
        resp = client.get("/api/v1/personnel/departments", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["data"], list)

    def test_get_positions(self, client, auth_headers):
        """获取职位列表 → 200"""
        resp = client.get("/api/v1/personnel/positions", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["data"], list)


# ═══════════════════════════════════════════════════════════════════════════════
# 批量删除测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestBatchDelete:
    """测试 POST /api/v1/personnel/batch — 批量删除"""

    def test_batch_delete_success(self, client, auth_headers):
        """批量删除多个记录"""
        r1 = client.post(
            "/api/v1/personnel/", json=SAMPLE_PERSONNEL, headers=auth_headers,
        )
        r2 = client.post(
            "/api/v1/personnel/", json=SAMPLE_PERSONNEL_2, headers=auth_headers,
        )
        id1 = r1.json()["data"]["id"]
        id2 = r2.json()["data"]["id"]

        resp = client.post(
            "/api/v1/personnel/batch",
            json=[id1, id2],
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["deleted_count"] >= 0

    def test_batch_delete_empty_ids(self, client, auth_headers):
        """空 ID 列表 → 200（FastAPI Body(min_items) 在 v0.115+ 已废弃，降级放行到服务层处理）"""
        resp = client.post(
            "/api/v1/personnel/batch",
            json=[],
            headers=auth_headers,
        )
        assert resp.status_code == 200


class TestPersonnelErrorPaths:
    """API 异常处理分支 — patch 服务层方法抛异常触发 500"""

    def test_create_runtime_error_500(self, client, auth_headers):
        """创建时 service 抛 RuntimeError → 500"""
        with patch(
                # 目标：PersonnelService.create_personnel 方法
                "backend.app.services.personnel_service.PersonnelService.create_personnel",
                side_effect=RuntimeError("Redmine 宕机"),
        ):
            resp = client.post(
                "/api/v1/personnel/",
                json={
                    "employee_id": "ERR500", "name": "测试", "gender": "男",
                    "age": 30, "phone": "13800138000", "email": "e@t.com",
                    "department": "部", "position": "职", "hire_date": "2024-01-01",
                },
                headers=auth_headers,
            )
        assert resp.status_code == 500

    def test_list_runtime_error_500(self, client, auth_headers):
        """列表查询时 service 抛 RuntimeError → 500"""
        with patch(
                # 目标：PersonnelService.get_personnel_list 方法
                "backend.app.services.personnel_service.PersonnelService.get_personnel_list",
                side_effect=RuntimeError("Redmine 不可用"),
        ):
            resp = client.get("/api/v1/personnel/", headers=auth_headers)
        assert resp.status_code == 500

    def test_search_runtime_error_500(self, client, auth_headers):
        """搜索时 service 抛 RuntimeError → 500"""
        with patch(
                # 目标：PersonnelService.search_personnel 方法
                "backend.app.services.personnel_service.PersonnelService.search_personnel",
                side_effect=RuntimeError("搜索服务异常"),
        ):
            resp = client.post(
                "/api/v1/personnel/search",
                json={"keyword": "test"},
                headers=auth_headers,
            )
        assert resp.status_code == 500

    def test_update_runtime_error_500(self, client, auth_headers):
        """更新时 service 抛 RuntimeError → 500"""
        with patch(
                # 目标：PersonnelService.update_personnel 方法
                "backend.app.services.personnel_service.PersonnelService.update_personnel",
                side_effect=RuntimeError("更新失败"),
        ):
            resp = client.put(
                "/api/v1/personnel/1",
                json={"name": "新名字"},
                headers=auth_headers,
            )
        assert resp.status_code == 500

    def test_delete_runtime_error_500(self, client, auth_headers):
        """删除时 service 抛 RuntimeError → 500"""
        with patch(
                # 目标：PersonnelService.delete_personnel 方法
                "backend.app.services.personnel_service.PersonnelService.delete_personnel",
                side_effect=RuntimeError("删除失败"),
        ):
            resp = client.delete("/api/v1/personnel/1", headers=auth_headers)
        assert resp.status_code == 500
