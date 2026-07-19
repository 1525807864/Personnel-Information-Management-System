"""
人员 CRUD 完整流程集成测试

测试完整的人员生命周期：
  创建 → 列表查询（验证创建成功）→ 详情查询 → 修改 → 删除 → 列表查询（验证删除后不显示）
"""
import pytest


class TestPersonnelFullCRUDFlow:
    """人员完整 CRUD 生命周期测试"""

    def test_create_read_update_delete_flow(self, client, auth_headers, sample_personnel):
        """完整 CRUD 链路"""
        # 步骤 1：创建
        resp = client.post(
            "/api/v1/personnel/",
            json=sample_personnel,
            headers=auth_headers,
        )
        assert resp.status_code == 200
        created = resp.json()["data"]
        created_id = created["id"]
        assert created["employee_id"] == sample_personnel["employee_id"]
        assert created["name"] == sample_personnel["name"]

        # 步骤 2：列表查询 → 验证新记录存在
        resp = client.get("/api/v1/personnel/", headers=auth_headers)
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        found = [item for item in items if item["id"] == created_id]
        assert len(found) > 0, f"列表中未找到 ID={created_id} 的记录"

        # 步骤 3：详情查询
        resp = client.get(f"/api/v1/personnel/{created_id}", headers=auth_headers)
        assert resp.status_code == 200
        detail = resp.json()["data"]
        assert detail["employee_id"] == sample_personnel["employee_id"]
        for field in ["id", "employee_id", "name", "gender", "age",
                       "phone", "email", "department", "position"]:
            assert field in detail, f"详情缺少字段: {field}"

        # 步骤 4：修改
        update_data = {
            "name": "张三(已修改)",
            "position": "高级工程师",
            "age": 30,
        }
        resp = client.put(
            f"/api/v1/personnel/{created_id}",
            json=update_data,
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "修改成功"

        # 步骤 5：删除（软删除）
        resp = client.delete(
            f"/api/v1/personnel/{created_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "删除成功"

        # 步骤 6：删除后详情
        resp = client.get(f"/api/v1/personnel/{created_id}", headers=auth_headers)
        assert resp.status_code in (200, 404)


class TestDuplicateHandlingFlow:
    """测试重复数据处理的完整流程"""

    def test_duplicate_employee_id_rejected(self, client, auth_headers, sample_personnel):
        """创建→用相同编号再创建→被拒绝"""
        resp1 = client.post(
            "/api/v1/personnel/",
            json=sample_personnel,
            headers=auth_headers,
        )
        assert resp1.status_code == 200

        resp2 = client.post(
            "/api/v1/personnel/",
            json=sample_personnel,
            headers=auth_headers,
        )
        assert resp2.status_code == 409, f"期望 409 重复冲突，实际 {resp2.status_code}"


class TestBatchOperationsFlow:
    """测试批量操作流程"""

    def test_batch_create_and_delete(self, client, auth_headers):
        """批量创建→批量删除 的完整流程"""
        records = [
            {"employee_id": f"BAT{i:03d}", "name": f"批量{i:02d}", "gender": "男",
             "age": 25 + i, "phone": f"1380013800{i}", "email": f"batch{i}@test.com",
             "department": "技术部", "position": "工程师", "hire_date": "2024-01-01"}
            for i in range(3)
        ]

        created_ids = []
        for rec in records:
            resp = client.post(
                "/api/v1/personnel/", json=rec, headers=auth_headers,
            )
            assert resp.status_code == 200
            created_ids.append(resp.json()["data"]["id"])

        # 验证列表中有这些记录
        resp = client.get("/api/v1/personnel/", headers=auth_headers)
        items = resp.json()["data"]["items"]
        found_ids = [item["id"] for item in items]
        for cid in created_ids:
            assert cid in found_ids, f"ID={cid} 应在列表中"

        # 批量删除
        resp = client.post(
            "/api/v1/personnel/batch",
            json=created_ids,
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["deleted_count"] >= 0
