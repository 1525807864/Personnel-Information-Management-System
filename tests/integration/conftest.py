"""
集成测试专用 Fixtures

与根 conftest.py 的区别：
  - 集成测试需要更真实的 mock 数据（多页数据、多状态等）
  - 需要模拟完整的 Redmine API 交互链路
  - 需要测试数据清理机制
"""
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_redmine_integration():
    """
    为集成测试提供更丰富的 Redmine Mock

    与单元测试的 mock_redmine 不同，此 fixture 模拟：
      - 多页数据（验证分页逻辑）
      - 重复检查的完整流程
      - 创建→更新→删除的完整链路
    """
    client = MagicMock()

    # --- 认证相关 ---
    client.verify_user_credentials = AsyncMock(return_value={
        "user": {
            "id": 1, "login": "admin", "admin": True,
            "firstname": "Admin", "lastname": "User",
            "mail": "admin@test.com", "status": 1,
            "custom_fields": [],
        }
    })
    client.get_user_with_api_key = AsyncMock(return_value={
        "user": {"id": 1, "login": "admin", "admin": True, "status": 1,
                 "custom_fields": [], "memberships": []}
    })

    # --- Issue 相关（集成测试需要更完整的模拟） ---

    _id_counter = 100

    async def _create_issue(issue_data):
        nonlocal _id_counter
        _id_counter += 1
        return {
            "issue": {
                "id": _id_counter,
                "subject": issue_data.get("subject", ""),
                "project": {"id": 427},
                "status": {"id": 1, "name": "新建"},
                "created_on": "2024-01-01T00:00:00Z",
                "updated_on": "2024-01-01T00:00:00Z",
                "custom_fields": [],
            }
        }
    client.create_issue = AsyncMock(side_effect=_create_issue)

    # 模拟：get_issues 返回分页数据
    _stored_issues = []

    async def _get_issues(project_id, page=1, limit=25, filters=None):
        start = (page - 1) * limit
        end = start + limit
        page_items = _stored_issues[start:end]
        return {
            "issues": page_items,
            "total_count": len(_stored_issues),
            "limit": limit,
            "offset": start,
        }
    client.get_issues = AsyncMock(side_effect=_get_issues)

    # 模拟：get_issue 取单条记录
    async def _get_issue(issue_id):
        for iss in _stored_issues:
            if iss["id"] == issue_id:
                return {"issue": iss}
        raise ValueError(f"Issue {issue_id} not found")
    client.get_issue = AsyncMock(side_effect=_get_issue)

    # 模拟：update_issue
    async def _update_issue(issue_id, issue_data):
        for iss in _stored_issues:
            if iss["id"] == issue_id:
                if "subject" in issue_data:
                    iss["subject"] = issue_data["subject"]
                for new_cf in issue_data.get("custom_fields", []):
                    cf_id = new_cf.get("id") if isinstance(new_cf, dict) else new_cf
                    cf_value = new_cf.get("value", "") if isinstance(new_cf, dict) else ""
                    for cf in iss.get("custom_fields", []):
                        if cf["id"] == cf_id:
                            cf["value"] = cf_value
                            break
                return {"issue": iss}
        raise ValueError(f"Issue {issue_id} not found")
    client.update_issue = AsyncMock(side_effect=_update_issue)

    # 存储引用，方便测试中添加预置数据
    client._stored_issues = _stored_issues

    return client
