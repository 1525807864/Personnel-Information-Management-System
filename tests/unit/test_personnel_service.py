"""
人员管理服务单元测试
"""
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.app.core.redmine_client import RedmineClient
from backend.app.models.personnel import Personnel
from backend.app.schemas.personnel import PersonnelCreate
from backend.app.services.personnel_service import PersonnelService


@pytest.fixture
def redmine_mock() -> MagicMock:
    rm = MagicMock(spec=RedmineClient)
    rm.get_issues = AsyncMock()
    rm.create_issue = AsyncMock()
    rm.get_issue = AsyncMock()
    rm.update_issue = AsyncMock()
    return rm


@pytest.fixture
def svc(redmine_mock: MagicMock) -> PersonnelService:
    return PersonnelService(redmine_mock)


@pytest.fixture
def create_data() -> PersonnelCreate:
    return PersonnelCreate(
        employee_id="EMP001", name="张三", gender="男", age=25,
        phone="13800138000", email="zhangsan@example.com",
        department="技术部", position="工程师", hire_date=date(2024, 1, 1),
    )


class TestCheckEmployeeIdExists:
    """测试 _check_employee_id_exists"""

    async def test_id_not_exists(self, svc: PersonnelService, redmine_mock: MagicMock) -> None:
        redmine_mock.get_issues.return_value = {"issues": [], "total_count": 0}
        result = await svc._check_employee_id_exists("EMP999")
        assert result is False

    async def test_id_exists(self, svc: PersonnelService, redmine_mock: MagicMock) -> None:
        redmine_mock.get_issues.return_value = {
            "issues": [{
                "id": 101, "subject": "EMP001-张三",
                "custom_fields": [
                    {"id": 1, "name": "employee_id", "value": "EMP001"},
                ],
            }],
            "total_count": 1,
        }
        result = await svc._check_employee_id_exists("EMP001")
        assert result is True

    async def test_redmine_failure_returns_false(self, svc: PersonnelService, redmine_mock: MagicMock) -> None:
        redmine_mock.get_issues.side_effect = Exception("Redmine API error")
        result = await svc._check_employee_id_exists("EMP001")
        assert result is False


class TestBuildCreatePayload:
    """测试 _build_create_payload"""

    def test_payload_has_required_keys(self, svc: PersonnelService, create_data: PersonnelCreate) -> None:
        payload = svc._build_create_payload(create_data)
        assert "project_id" in payload
        assert "tracker_id" in payload
        assert "subject" in payload
        # PersonnelFieldMapping.build_payload 返回 cf_X 格式的 flat dict
        assert "cf_1" in payload  # employee_id
        assert "cf_2" in payload  # name
        assert create_data.name in payload["subject"]


class TestPersonnelToResponse:
    """测试 Personnel.to_response()"""

    def test_converts_personnel_to_response(self) -> None:
        p = Personnel(
            id=101, employee_id="EMP001", name="张三", gender="男",
            age="25", phone="13800138000", email="zhangsan@example.com",
            department="技术部", position="工程师",
            start_datetime=date(2024, 1, 1),
            create_datetime=None, update_datetime=None,
        )
        resp = p.to_response()
        assert resp.id == 101
        assert resp.employee_id == "EMP001"
        assert resp.name == "张三"
        assert resp.gender == "男"
        assert resp.age == 25
        assert resp.department == "技术部"

    def test_non_digit_age_returns_zero(self) -> None:
        p = Personnel(
            id=102, employee_id="E2", name="李四", gender="女",
            age="abc", phone="139", email="e@t.com",
            department="部", position="职",
            start_datetime=None, create_datetime=None, update_datetime=None,
        )
        resp = p.to_response()
        assert resp.age == 0


# ═══════════════════════════════════════════════════════════════════════════════
# 内存过滤逻辑测试
# ═══════════════════════════════════════════════════════════════════════════════

def _make_issue(issue_id: int, emp_id: str, name: str, gender: str = "男",
                age: str = "25", dept: str = "技术部", pos: str = "工程师",
                start_dt: str = "2024-01-01") -> dict:
    """构造模拟 Redmine Issue 数据"""
    return {
        "id": issue_id,
        "subject": f"{emp_id} - {name}",
        "created_on": "2024-01-01T00:00:00Z",
        "updated_on": "2024-01-01T00:00:00Z",
        "custom_fields": [
            {"id": 1, "name": "employee_id", "value": emp_id},
            {"id": 2, "name": "name", "value": name},
            {"id": 3, "name": "gender", "value": gender},
            {"id": 4, "name": "age", "value": age},
            {"id": 5, "name": "phone", "value": "13800138000"},
            {"id": 6, "name": "department", "value": dept},
            {"id": 7, "name": "position", "value": pos},
            {"id": 8, "name": "start_datetime", "value": start_dt},
            {"id": 11, "name": "email", "value": f"{emp_id.lower()}@test.com"},
        ],
    }


class TestGetPersonnelListFiltering:
    """测试 get_personnel_list 内存过滤逻辑"""

    @pytest.fixture
    def mock_issues_response(self):
        """返回包含多条人员数据的模拟响应"""
        return {
            "issues": [
                _make_issue(1, "EMP001", "张三", dept="技术部", pos="工程师", start_dt="2024-01-01"),
                _make_issue(2, "EMP002", "李四", dept="产品部", pos="产品经理", start_dt="2024-03-15"),
                _make_issue(3, "EMP003", "王五", dept="技术部", pos="架构师", start_dt="2023-06-01"),
            ],
            "total_count": 3,
        }

    async def test_filter_by_department(self, svc: PersonnelService, redmine_mock):
        """按部门过滤：只返回技术部的人员（由 Redmine 服务端过滤）"""
        filtered = {
            "issues": [
                _make_issue(1, "EMP001", "张三", dept="技术部", pos="工程师", start_dt="2024-01-01"),
                _make_issue(3, "EMP003", "王五", dept="技术部", pos="架构师", start_dt="2023-06-01"),
            ],
            "total_count": 2,
        }
        redmine_mock.get_issues.return_value = filtered
        result = await svc.get_personnel_list(department="技术部")
        assert result["total"] == 2
        assert len(result["items"]) == 2
        for item in result["items"]:
            assert item.department == "技术部"

    async def test_filter_by_position(self, svc: PersonnelService, redmine_mock):
        """按职位过滤：只返回工程师（由 Redmine 服务端过滤）"""
        filtered = {
            "issues": [
                _make_issue(1, "EMP001", "张三", dept="技术部", pos="工程师", start_dt="2024-01-01"),
            ],
            "total_count": 1,
        }
        redmine_mock.get_issues.return_value = filtered
        result = await svc.get_personnel_list(position="工程师")
        assert len(result["items"]) == 1
        assert result["items"][0].name == "张三"

    async def test_filter_by_date_range(self, svc: PersonnelService, redmine_mock, mock_issues_response):
        """按入职日期范围过滤（内存过滤）"""
        redmine_mock.get_issues.return_value = mock_issues_response
        result = await svc.get_personnel_list(
            start_date="2024-01-01", end_date="2024-12-31"
        )
        # 只有 EMP001(2024-01-01) 和 EMP002(2024-03-15) 在范围内
        assert len(result["items"]) == 2

    async def test_filter_by_keyword_name(self, svc: PersonnelService, redmine_mock, mock_issues_response):
        """按关键词过滤（匹配姓名，内存过滤）"""
        redmine_mock.get_issues.return_value = mock_issues_response
        result = await svc.get_personnel_list(keyword="张")
        assert len(result["items"]) == 1
        assert result["items"][0].name == "张三"

    async def test_filter_by_keyword_employee_id(self, svc: PersonnelService, redmine_mock, mock_issues_response):
        """按关键词过滤（匹配人员编号，内存过滤）"""
        redmine_mock.get_issues.return_value = mock_issues_response
        result = await svc.get_personnel_list(keyword="emp002")
        assert len(result["items"]) == 1
        assert result["items"][0].employee_id == "EMP002"

    async def test_filter_no_match_returns_empty(self, svc: PersonnelService, redmine_mock):
        """过滤条件无匹配时返回空列表（Redmine 服务端过滤）"""
        redmine_mock.get_issues.return_value = {"issues": [], "total_count": 0}
        result = await svc.get_personnel_list(department="不存在的部门")
        assert len(result["items"]) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# 排序逻辑测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetPersonnelListSorting:
    """测试 get_personnel_list 排序逻辑"""

    async def test_sort_by_age_desc(self, svc: PersonnelService, redmine_mock):
        """按年龄降序排序"""
        redmine_mock.get_issues.return_value = {
            "issues": [
                _make_issue(1, "E1", "A", age="25"),
                _make_issue(2, "E2", "B", age="30"),
                _make_issue(3, "E3", "C", age="20"),
            ],
            "total_count": 3,
        }
        result = await svc.get_personnel_list(sort_by="age", sort_order="desc")
        ages = [item.age for item in result["items"]]
        assert ages == [30, 25, 20]

    async def test_sort_by_age_non_numeric_treated_as_zero(self, svc: PersonnelService, redmine_mock):
        """年龄为非数字时按 0 处理参与排序"""
        redmine_mock.get_issues.return_value = {
            "issues": [
                _make_issue(1, "E1", "A", age="abc"),  # 非数字 → 0
                _make_issue(2, "E2", "B", age="30"),
                _make_issue(3, "E3", "C", age=""),     # 空 → 0
            ],
            "total_count": 3,
        }
        result = await svc.get_personnel_list(sort_by="age", sort_order="desc")
        ages = [item.age for item in result["items"]]
        # 30 排最前，非数字的按0排在后面
        assert ages[0] == 30

    async def test_sort_by_hire_date_with_none_dates(self, svc: PersonnelService, redmine_mock):
        """入职日期为 None 的记录排在最后"""
        redmine_mock.get_issues.return_value = {
            "issues": [
                _make_issue(1, "E1", "A", start_dt="2024-06-01"),
                _make_issue(2, "E2", "B", start_dt=""),  # 空日期 → None
                _make_issue(3, "E3", "C", start_dt="2024-01-01"),
            ],
            "total_count": 3,
        }
        result = await svc.get_personnel_list(sort_by="hire_date", sort_order="desc")
        items = result["items"]
        # 有效日期降序排列，None 排最后
        assert items[0].employee_id == "E1"  # 2024-06-01 最新
        assert items[1].employee_id == "E3"  # 2024-01-01
        assert items[2].employee_id == "E2"  # None 排最后

    async def test_sort_by_name_asc(self, svc: PersonnelService, redmine_mock):
        """按姓名升序排序"""
        redmine_mock.get_issues.return_value = {
            "issues": [
                _make_issue(1, "E1", "王五"),
                _make_issue(2, "E2", "张三"),
                _make_issue(3, "E3", "李四"),
            ],
            "total_count": 3,
        }
        result = await svc.get_personnel_list(sort_by="name", sort_order="asc")
        names = [item.name for item in result["items"]]
        assert names == sorted(names)


# ═══════════════════════════════════════════════════════════════════════════════
# get_departments / get_positions 测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetDepartments:
    """测试 get_departments 去重和排序"""

    async def test_returns_sorted_unique_departments(self, svc: PersonnelService, redmine_mock):
        """返回去重且排序的部门列表"""
        redmine_mock.get_issues.return_value = {
            "issues": [
                _make_issue(1, "E1", "A", dept="产品部"),
                _make_issue(2, "E2", "B", dept="技术部"),
                _make_issue(3, "E3", "C", dept="技术部"),  # 重复
                _make_issue(4, "E4", "D", dept="人事部"),
            ],
            "total_count": 4,
        }
        result = await svc.get_departments()
        assert result == ["产品部", "人事部", "技术部"]  # 按 Unicode 码点排序

    async def test_empty_department_excluded(self, svc: PersonnelService, redmine_mock):
        """空部门不被包含在结果中"""
        redmine_mock.get_issues.return_value = {
            "issues": [
                _make_issue(1, "E1", "A", dept="技术部"),
                _make_issue(2, "E2", "B", dept=""),  # 空部门
            ],
            "total_count": 2,
        }
        result = await svc.get_departments()
        assert result == ["技术部"]

    async def test_redmine_error_returns_empty_list(self, svc: PersonnelService, redmine_mock):
        """Redmine 查询失败时返回空列表"""
        redmine_mock.get_issues.side_effect = Exception("Connection error")
        result = await svc.get_departments()
        assert result == []


class TestGetPositions:
    """测试 get_positions 去重和排序"""

    async def test_returns_sorted_unique_positions(self, svc: PersonnelService, redmine_mock):
        """返回去重且排序的职位列表"""
        redmine_mock.get_issues.return_value = {
            "issues": [
                _make_issue(1, "E1", "A", pos="架构师"),
                _make_issue(2, "E2", "B", pos="工程师"),
                _make_issue(3, "E3", "C", pos="工程师"),  # 重复
                _make_issue(4, "E4", "D", pos="产品经理"),
            ],
            "total_count": 4,
        }
        result = await svc.get_positions()
        assert result == ["产品经理", "工程师", "架构师"]  # 按 Unicode 码点排序

    async def test_redmine_error_returns_empty_list(self, svc: PersonnelService, redmine_mock):
        """Redmine 查询失败时返回空列表"""
        redmine_mock.get_issues.side_effect = Exception("Timeout")
        result = await svc.get_positions()
        assert result == []


# ═══════════════════════════════════════════════════════════════════════════════
# batch_delete 部分失败测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestBatchDelete:
    """测试 batch_delete 部分失败场景"""

    async def test_all_success(self, svc: PersonnelService, redmine_mock):
        """全部删除成功"""
        redmine_mock.update_issue.return_value = {"issue": {"id": 1}}
        deleted = await svc.batch_delete([1, 2, 3])
        assert deleted == 3
        assert redmine_mock.update_issue.call_count == 3

    async def test_partial_failure(self, svc: PersonnelService, redmine_mock):
        """部分删除失败：只统计成功数"""
        redmine_mock.update_issue.side_effect = [
            {"issue": {"id": 1}},           # 成功
            Exception("Redmine 500"),       # 失败
            {"issue": {"id": 3}},           # 成功
        ]
        deleted = await svc.batch_delete([1, 2, 3])
        assert deleted == 2  # 只有2条成功

    async def test_all_failure(self, svc: PersonnelService, redmine_mock):
        """全部删除失败：返回 0"""
        redmine_mock.update_issue.side_effect = Exception("Network error")
        deleted = await svc.batch_delete([1, 2])
        assert deleted == 0

    async def test_empty_ids_list(self, svc: PersonnelService, redmine_mock):
        """空 ID 列表：返回 0"""
        deleted = await svc.batch_delete([])
        assert deleted == 0
        redmine_mock.update_issue.assert_not_called()
