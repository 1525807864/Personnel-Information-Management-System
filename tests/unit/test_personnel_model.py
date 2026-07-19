"""
Personnel 领域模型单元测试

测试目标：
  1. from_redmine_issue() — Redmine JSON → Personnel 对象转换
  2. to_redmine_payload()  — Personnel 对象 → Redmine API payload 转换
  3. 日期字段解析的容错性
  4. 空值/缺失字段的处理
"""
from datetime import date, datetime

import pytest

from backend.app.models.personnel import Personnel


class TestPersonnelFromRedmineIssue:
    """测试 from_redmine_issue() 类方法"""

    def test_full_issue_mapping(self):
        """完整的 Redmine Issue JSON 应正确映射所有字段"""
        issue = {
            "id": 42,
            "subject": "EMP001 - 张三",
            "created_on": "2024-01-15T08:30:00Z",
            "updated_on": "2024-06-20T14:00:00Z",
            "custom_fields": [
                {"id": 1, "name": "employee_id", "value": "EMP001"},
                {"id": 2, "name": "name", "value": "张三"},
                {"id": 3, "name": "gender", "value": "男"},
                {"id": 4, "name": "age", "value": "25"},
                {"id": 5, "name": "phone", "value": "13800138000"},
                {"id": 6, "name": "department", "value": "技术部"},
                {"id": 7, "name": "position", "value": "工程师"},
                {"id": 8, "name": "start_datetime", "value": "2024-01-01"},
                {"id": 11, "name": "email", "value": "zhangsan@test.com"},
            ],
        }

        p = Personnel.from_redmine_issue(issue)

        assert p.id == 42
        assert p.employee_id == "EMP001"
        assert p.name == "张三"
        assert p.gender == "男"
        assert p.age == "25"
        assert p.phone == "13800138000"
        assert p.email == "zhangsan@test.com"
        assert p.department == "技术部"
        assert p.position == "工程师"
        assert p.start_datetime == date(2024, 1, 1)
        assert p.create_datetime is not None
        assert p.update_datetime is not None

    def test_empty_custom_fields(self):
        """custom_fields 为空列表时，所有字段应为默认空值"""
        issue = {
            "id": 1,
            "custom_fields": [],
        }
        p = Personnel.from_redmine_issue(issue)
        assert p.employee_id == ""
        assert p.name == ""
        assert p.gender == ""
        assert p.age == ""
        assert p.phone == ""
        assert p.email == ""
        assert p.department == ""
        assert p.position == ""
        assert p.start_datetime is None

    def test_invalid_date_handling(self):
        """不可解析的日期应被容错处理为 None"""
        issue = {
            "id": 1,
            "custom_fields": [
                {"id": 8, "name": "start_datetime", "value": "not-a-date"},
            ],
        }
        p = Personnel.from_redmine_issue(issue)
        assert p.start_datetime is None

    def test_missing_created_updated(self):
        """缺失 created_on/updated_on 时不抛异常"""
        issue = {"id": 1, "custom_fields": []}
        p = Personnel.from_redmine_issue(issue)
        assert p.create_datetime is None
        assert p.update_datetime is None


class TestPersonnelToRedminePayload:
    """测试 to_redmine_payload() 方法"""

    def test_full_payload(self):
        """完整的 Personnel 对象应序列化为正确的 Redmine payload"""
        p = Personnel(
            id=42,
            employee_id="EMP001",
            name="张三",
            gender="男",
            age="25",
            phone="13800138000",
            email="zhangsan@test.com",
            department="技术部",
            position="工程师",
            start_datetime=date(2024, 1, 1),
            create_datetime=datetime(2024, 1, 1, 12, 0, 0),
            update_datetime=datetime(2024, 6, 1, 12, 0, 0),
        )

        payload = p.to_redmine_payload()

        assert payload["subject"] == "EMP001 - 张三"
        assert "project_id" in payload
        assert payload["cf_1"] == "EMP001"
        assert payload["cf_2"] == "张三"
        assert payload["cf_3"] == "男"
        assert payload["cf_4"] == "25"
        assert payload["cf_5"] == "13800138000"
        assert payload["cf_6"] == "技术部"
        assert payload["cf_7"] == "工程师"
        assert payload["cf_8"] == "2024-01-01"
        assert payload["cf_11"] == "zhangsan@test.com"

    def test_none_dates_handling(self):
        """日期为 None 时应序列化为空字符串而非字符串 'None'"""
        p = Personnel(
            id=1, employee_id="E1", name="测试", gender="男",
            age="30", phone="13800138000", email="test@test.com",
            department="技术部", position="工程师",
            start_datetime=None,
        )
        payload = p.to_redmine_payload()
        assert payload["cf_8"] == ""
        assert payload["cf_9"] == ""
        assert payload["cf_10"] == ""
