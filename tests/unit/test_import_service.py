"""
导入服务单元测试

测试目标：
  1. 文件格式解析（CSV/Excel）
  2. 列名映射逻辑（中文→英文）
  3. 逐行 Pydantic 校验逻辑
  4. 重复数据处理策略逻辑
  5. Redmine payload 构建逻辑
"""
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pandas as pd
import pytest

from backend.app.services.import_service import (
    ImportService,
    COLUMN_MAPPING,
    REQUIRED_FIELDS,
)
from backend.app.schemas.import_schemas import ImportErrorDetail
from backend.app.utils.exceptions import FileImportException


# ═══════════════════════════════════════════════════════════════════════════════
# CSV 内容生成辅助函数
# ═══════════════════════════════════════════════════════════════════════════════

def _make_csv_content(rows: list[str]) -> bytes:
    """将字符串列表组装为 UTF-8 BOM CSV 的 bytes"""
    return ("\n".join(rows)).encode("utf-8-sig")


# ═══════════════════════════════════════════════════════════════════════════════
# 获取无 Redmine 依赖的 ImportService 实例
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def svc():
    """创建一个 ImportService 实例，提供假的 RedmineClient"""
    mock_redmine = MagicMock()
    return ImportService(mock_redmine)


# ═══════════════════════════════════════════════════════════════════════════════
# 文件解析测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestParseFile:
    """测试 _parse_file()"""

    def test_parse_csv(self, svc):
        """解析 CSV 文件"""
        content = _make_csv_content([
            "人员编号,姓名,性别,年龄",
            "EMP001,张三,男,25",
        ])
        df = svc._parse_file(content, "test.csv")
        assert len(df) == 1
        assert df.iloc[0]["人员编号"] == "EMP001"
        assert df.iloc[0]["姓名"] == "张三"

    def test_parse_csv_empty(self, svc):
        """只有表头没有数据的 CSV"""
        content = _make_csv_content(["人员编号,姓名,性别,年龄"])
        df = svc._parse_file(content, "test.csv")
        assert len(df) == 0

    def test_parse_unsupported_format(self, svc):
        """不支持的格式抛出 FileImportException"""
        with pytest.raises(FileImportException, match="不支持的文件格式"):
            svc._parse_file(b"fake content", "test.prows")

    def test_parse_corrupted_file(self, svc):
        """损坏的文件抛出 FileImportException"""
        with pytest.raises(FileImportException, match="文件解析失败"):
            svc._parse_file(b"\x00\x01\x02\x03", "test.xlsx")


# ═══════════════════════════════════════════════════════════════════════════════
# 列名映射测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestMapColumns:
    """测试 _map_columns()"""

    def test_chinese_columns_mapping(self, svc):
        """中文列名应正确映射为英文字段名"""
        df = pd.DataFrame([{
            "人员编号": "EMP001", "姓名": "张三", "性别": "男",
            "年龄": 25, "手机号": "13800138000", "邮箱": "z@t.com",
            "部门": "技术部", "职位": "工程师", "入职日期": "2024-01-01",
        }])
        result = svc._map_columns(df)
        assert "employee_id" in result.columns
        assert "name" in result.columns
        assert "gender" in result.columns
        assert "age" in result.columns
        assert "phone" in result.columns
        assert "email" in result.columns
        assert "department" in result.columns
        assert "position" in result.columns
        assert "hire_date" in result.columns
        assert "人员编号" not in result.columns
        assert "姓名" not in result.columns

    def test_missing_columns_filled(self, svc):
        """缺失的必填列应自动补充为空字符串列"""
        df = pd.DataFrame([{"人员编号": "EMP001", "姓名": "张三"}])
        result = svc._map_columns(df)
        for field in REQUIRED_FIELDS:
            assert field in result.columns, f"缺少列: {field}"
        assert result.iloc[0]["email"] == ""

    def test_empty_rows_removed(self, svc):
        """全空的行应被删除"""
        df = pd.DataFrame([
            {"人员编号": "EMP001", "姓名": "张三", "性别": "男",
             "年龄": 25, "手机号": "13800138000", "邮箱": "z@t.com",
             "部门": "技术部", "职位": "工程师", "入职日期": "2024-01-01"},
            {"人员编号": None, "姓名": None, "性别": None,
             "年龄": None, "手机号": None, "邮箱": None,
             "部门": None, "职位": None, "入职日期": None},
        ])
        result = svc._map_columns(df)
        assert len(result) == 1

    def test_all_empty_raises(self, svc):
        """所有行都为空时抛出 FileImportException"""
        df = pd.DataFrame([{"人员编号": None}])
        with pytest.raises(FileImportException, match="文件映射后没有有效数据"):
            svc._map_columns(df)

    def test_extra_columns_preserved(self, svc):
        """多余的列名保留原样"""
        df = pd.DataFrame([{
            "人员编号": "EMP001", "姓名": "张三", "备注": "这是多余列"
        }])
        result = svc._map_columns(df)
        assert "备注" in result.columns
        assert result.iloc[0]["备注"] == "这是多余列"


# ═══════════════════════════════════════════════════════════════════════════════
# 逐行校验测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestValidateRows:
    """测试 _validate_rows()"""

    def test_all_valid_rows(self, svc):
        """全部行都通过校验"""
        df = pd.DataFrame([
            {
                "employee_id": "EMP001", "name": "张三", "gender": "男",
                "age": 25, "phone": "13800138000", "email": "z1@t.com",
                "department": "技术部", "position": "工程师", "hire_date": "2024-01-01",
            },
            {
                "employee_id": "EMP002", "name": "李四", "gender": "女",
                "age": 30, "phone": "13900139000", "email": "z2@t.com",
                "department": "产品部", "position": "产品经理", "hire_date": "2023-06-15",
            },
        ])
        valid, errors = svc._validate_rows(df)
        assert len(valid) == 2
        assert len(errors) == 0

    def test_mixed_valid_and_invalid(self, svc):
        """混合有效和无效行的校验"""
        df = pd.DataFrame([
            {
                "employee_id": "EMP001", "name": "张三", "gender": "男",
                "age": 25, "phone": "13800138000", "email": "z1@t.com",
                "department": "技术部", "position": "工程师", "hire_date": "2024-01-01",
            },
            {
                "employee_id": "EMP002", "name": "王五", "gender": "未知",
                "age": 16, "phone": "12345", "email": "bad-email",
                "department": "技术部", "position": "工程师", "hire_date": "2024-01-01",
            },
        ])
        valid, errors = svc._validate_rows(df)
        assert len(valid) == 1
        assert len(errors) == 1
        assert errors[0].row == 2
        assert errors[0].employee_id == "EMP002"

    def test_phone_int_to_str_conversion(self, svc):
        """手机号 int → str 强制转换"""
        df = pd.DataFrame([{
            "employee_id": "EMP001", "name": "张三", "gender": "男",
            "age": 25,
            "phone": 13800138000,
            "email": "z1@t.com",
            "department": "技术部", "position": "工程师",
            "hire_date": "2024-01-01",
        }])
        valid, errors = svc._validate_rows(df)
        assert len(valid) == 1, f"校验应通过，但失败了: {errors}"
        assert len(errors) == 0

    def test_employee_id_int_conversion(self, svc):
        """纯数字的员工编号也应被转为字符串"""
        df = pd.DataFrame([{
            "employee_id": 12345,
            "name": "张三", "gender": "男",
            "age": 25, "phone": "13800138000", "email": "z1@t.com",
            "department": "技术部", "position": "工程师",
            "hire_date": "2024-01-01",
        }])
        valid, errors = svc._validate_rows(df)
        assert len(valid) == 1, f"应通过但失败了: {[e.reason for e in errors]}"

    def test_all_rows_invalid(self, svc):
        """全部行校验失败时，valid_rows 为空"""
        df = pd.DataFrame([
            {
                "employee_id": "EMP001", "name": "", "gender": "男",
                "age": 25, "phone": "13800138000", "email": "z1@t.com",
                "department": "技术部", "position": "工程师", "hire_date": "2024-01-01",
            },
        ])
        valid, errors = svc._validate_rows(df)
        assert len(valid) == 0
        assert len(errors) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# Payload 构建测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestBuildPayloads:
    """测试 _build_payload()"""

    def test_create_payload_fields(self, svc):
        """创建 payload 应包含所有必要字段"""
        row = {
            "employee_id": "EMP001", "name": "张三", "gender": "男",
            "age": 25, "phone": "13800138000", "email": "z@t.com",
            "department": "技术部", "position": "工程师", "hire_date": date(2024, 1, 1),
        }
        payload = svc._build_payload(row)
        assert payload["subject"] == "EMP001 - 张三"
        assert "project_id" in payload
        assert payload["tracker_id"] == 1
        assert payload["status_id"] == 1
        assert payload["cf_1"] == "EMP001"
        assert payload["cf_2"] == "张三"
        assert payload["cf_3"] == "男"
        assert payload["cf_4"] == "25"
        assert payload["cf_5"] == "13800138000"
        assert payload["cf_6"] == "技术部"
        assert payload["cf_7"] == "工程师"
        assert payload["cf_8"] == "2024-01-01"
        assert payload["cf_11"] == "z@t.com"

    def test_update_payload_no_project_id(self, svc):
        """更新 payload 不应包含 project_id"""
        row = {
            "employee_id": "EMP001", "name": "张三", "gender": "男",
            "age": 30, "phone": "13800138000", "email": "z@t.com",
            "department": "技术部", "position": "高级工程师",
            "hire_date": date(2024, 1, 1),
        }
        payload = svc._build_payload(row, for_update=True)
        assert "project_id" not in payload
        assert "tracker_id" not in payload
        assert payload["cf_7"] == "高级工程师"
        assert payload["subject"] == "EMP001 - 张三"


# ═══════════════════════════════════════════════════════════════════════════════
# 导入结果构建测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestBuildResult:
    """测试 _build_result()"""

    def test_basic_result(self, svc):
        """基本的结果统计"""
        result = svc._build_result(
            total_rows=40, success_count=25, failed_count=10,
            duplicate_count=5, skipped_count=5, overwritten_count=0,
            error_details=[
                ImportErrorDetail(row=26, employee_id="ERR001", reason="性别错误"),
            ],
        )
        assert result.total_rows == 40
        assert result.success_count == 25
        assert result.failed_count == 10
        assert result.error_messages == ["第 26 行（编号: ERR001）: 性别错误"]

    def test_empty_result(self, svc):
        """空结果"""
        result = svc._build_result(0, 0, 0, 0, 0, 0, [])
        assert result.total_rows == 0
        assert result.error_messages == []
        assert result.error_details == []


class TestProcessRowsStrategies:
    """_process_rows 三种策略完整覆盖"""

    @pytest.fixture
    def svc(self):
        """创建带 mock redmine 的 ImportService"""
        from unittest.mock import AsyncMock, MagicMock
        mock = MagicMock()
        mock.create_issue = AsyncMock()
        mock.update_issue = AsyncMock()
        svc = ImportService(mock)
        return svc

    def _make_rows(self, rows: list[dict]) -> list[dict]:
        """构造测试用行数据列表（模拟 _validate_rows 返回的 List[dict]）"""
        return rows

    def _valid_row(self, idx: int) -> dict:
        """生成一条合法的导入行（列名为英文字段名）"""
        return {
            "employee_id": f"E{idx:03d}",  # 人员编号
            "name": f"用户{idx}",  # 姓名
            "gender": "男",  # 性别
            "age": "25",  # 年龄
            "phone": f"1380013800{idx}",  # 手机号
            "email": f"u{idx}@test.com",  # 邮箱
            "department": "技术部",  # 部门
            "position": "工程师",  # 职位
            "hire_date": "2024-01-01",  # 入职日期
        }

    async def test_skip_strategy_duplicate_skipped(self, svc):
        """skip 策略：重复数据被跳过"""
        rows = self._make_rows([self._valid_row(1)])
        existing = {"E001": 1}  # E001 已存在于 Redmine

        result = await svc._process_rows(
            valid_rows=rows,
            error_details=[],           # 必需参数
            existing_map=existing,
            strategy="skip",
            total_rows=len(rows),         # 总行数
        )
        assert result.duplicate_count == 1  # 1 条重复
        assert result.success_count == 0  # 0 条成功
        svc.redmine.create_issue.assert_not_called()  # 未调用创建

    async def test_overwrite_strategy_updates_existing(self, svc):
        """overwrite 策略：已存在记录被更新"""
        from unittest.mock import AsyncMock  # 异步 mock

        rows = self._make_rows([self._valid_row(1)])
        existing = {"E001": 1}

        svc.redmine.update_issue = AsyncMock(return_value={"issue": {"id": 1}})

        result = await svc._process_rows(
            valid_rows=rows,
            error_details=[],
            existing_map=existing,
            strategy="overwrite",
            total_rows=len(rows),
        )
        assert result.duplicate_count == 1  # 1 条重复
        assert result.success_count == 1  # 覆盖成功算 success
        svc.redmine.update_issue.assert_called_once()  # 调用更新
        svc.redmine.create_issue.assert_not_called()  # 未调用创建

    async def test_terminate_strategy_stops_on_duplicate(self, svc):
        """terminate 策略：遇到重复立即停止"""
        rows = self._make_rows([self._valid_row(1), self._valid_row(2)])
        existing = {"E001": 1}  # 第一行就重复

        result = await svc._process_rows(
            valid_rows=rows,
            error_details=[],
            existing_map=existing,
            strategy="terminate",
            total_rows=len(rows),
        )
        assert result.success_count == 0  # 未处理任何行
        svc.redmine.create_issue.assert_not_called()

    async def test_new_records_created(self, svc):
        """无重复 → 新记录被创建"""
        from unittest.mock import AsyncMock  # 异步 mock

        rows = self._make_rows([self._valid_row(1), self._valid_row(2)])
        existing_map = {}  # 空映射，无重复

        svc.redmine.create_issue = AsyncMock(side_effect=[
            {"issue": {"id": 201}},  # 第一条
            {"issue": {"id": 202}},  # 第二条
        ])

        result = await svc._process_rows(
            valid_rows=rows,
            error_details=[],
            existing_map=existing_map,
            strategy="skip",
            total_rows=len(rows),
        )
        assert result.success_count == 2  # 2 条成功
        assert svc.redmine.create_issue.call_count == 2

    async def test_create_failure_counted_as_error(self, svc):
        """创建 Redmine 失败 → 计入 failed_count"""
        from unittest.mock import AsyncMock  # 异步 mock

        rows = self._make_rows([self._valid_row(1)])
        existing = {}  # 无重复

        svc.redmine.create_issue = AsyncMock(
            side_effect=Exception("Redmine API 500")  # 模拟 Redmine 故障
        )

        result = await svc._process_rows(
            valid_rows=rows,
            error_details=[],
            existing_map=existing,
            strategy="skip",
            total_rows=len(rows),          # 总行数
        )
        assert result.failed_count == 1  # 1 条失败
        assert result.success_count == 0  # 0 条成功


class TestExportErrorRows:
    """export_error_rows 静态方法"""

    def test_empty_error_list(self):
        """空错误行列表 → 抛出 FileImportException"""
        from backend.app.services.import_service import ImportService
        from backend.app.utils.exceptions import FileImportException

        with pytest.raises(FileImportException):
            ImportService.export_error_rows(
                file_content=b"col1,col2\nv1,v2\n",
                filename="test.csv",
                error_rows=[],                        # 空列表应抛异常
            )

    def test_valid_error_rows(self):
        """有效错误行号 → 返回对应行的 CSV"""
        from backend.app.services.import_service import ImportService

        csv_bytes = ImportService.export_error_rows(
            file_content=b"col1,col2\nv1,v2\nv2,v2\nv3,v4\n",  # 表头 + 3行数据
            filename="data.csv",
            error_rows=[2],                                    # 第2行（1-based）
        )
        assert len(csv_bytes) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# _fetch_existing_employee_ids 分页循环测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestFetchExistingEmployeeIds:
    """测试 _fetch_existing_employee_ids 分页循环逻辑"""

    @pytest.fixture
    def svc_with_mock(self):
        """创建带 AsyncMock redmine 的 ImportService"""
        from unittest.mock import AsyncMock, MagicMock
        mock = MagicMock()
        mock.get_issues = AsyncMock()
        return ImportService(mock)

    async def test_single_page(self, svc_with_mock):
        """单页数据（少于100条）直接返回"""
        svc_with_mock.redmine.get_issues.return_value = {
            "issues": [
                {"id": 101, "custom_fields": [{"id": 1, "value": "EMP001"}]},
                {"id": 102, "custom_fields": [{"id": 1, "value": "EMP002"}]},
            ],
            "total_count": 2,
        }
        result = await svc_with_mock._fetch_existing_employee_ids()
        assert result == {"EMP001": 101, "EMP002": 102}
        # 只调用一次（少于100条不继续分页）
        svc_with_mock.redmine.get_issues.assert_called_once()

    async def test_multi_page_pagination(self, svc_with_mock):
        """多页数据正确分页循环"""
        # 第一页返回100条，第二页返回50条
        page1_issues = [
            {"id": i, "custom_fields": [{"id": 1, "value": f"EMP{i:03d}"}]}
            for i in range(1, 101)
        ]
        page2_issues = [
            {"id": i, "custom_fields": [{"id": 1, "value": f"EMP{i:03d}"}]}
            for i in range(101, 151)
        ]
        svc_with_mock.redmine.get_issues.side_effect = [
            {"issues": page1_issues, "total_count": 150},
            {"issues": page2_issues, "total_count": 150},
        ]
        result = await svc_with_mock._fetch_existing_employee_ids()
        assert len(result) == 150
        assert result["EMP001"] == 1
        assert result["EMP150"] == 150
        # 调用了两次（分页）
        assert svc_with_mock.redmine.get_issues.call_count == 2

    async def test_empty_response_stops_loop(self, svc_with_mock):
        """空响应立即停止循环"""
        svc_with_mock.redmine.get_issues.return_value = {
            "issues": [], "total_count": 0
        }
        result = await svc_with_mock._fetch_existing_employee_ids()
        assert result == {}
        svc_with_mock.redmine.get_issues.assert_called_once()

    async def test_redmine_error_returns_empty_map(self, svc_with_mock):
        """Redmine 查询失败时返回空映射表（降级）"""
        svc_with_mock.redmine.get_issues.side_effect = Exception("Connection timeout")
        result = await svc_with_mock._fetch_existing_employee_ids()
        assert result == {}

    async def test_issue_without_cf1_skipped(self, svc_with_mock):
        """没有 cf_1 字段的 Issue 被跳过"""
        svc_with_mock.redmine.get_issues.return_value = {
            "issues": [
                {"id": 1, "custom_fields": [{"id": 2, "value": "张三"}]},  # 无 cf_1
                {"id": 2, "custom_fields": [{"id": 1, "value": "EMP002"}]},
            ],
            "total_count": 2,
        }
        result = await svc_with_mock._fetch_existing_employee_ids()
        assert result == {"EMP002": 2}


# ═══════════════════════════════════════════════════════════════════════════════
# import_file 完整端到端流程测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestImportFileEndToEnd:
    """测试 import_file 完整端到端流程"""

    @pytest.fixture
    def svc_e2e(self):
        """创建带完整 mock 的 ImportService"""
        from unittest.mock import AsyncMock, MagicMock
        mock = MagicMock()
        mock.get_issues = AsyncMock(return_value={"issues": [], "total_count": 0})
        mock.create_issue = AsyncMock(return_value={"issue": {"id": 999}})
        mock.update_issue = AsyncMock(return_value={"issue": {"id": 999}})
        return ImportService(mock)

    def _make_valid_csv(self, count: int = 2) -> bytes:
        """生成包含 count 条有效数据的 CSV"""
        lines = ["人员编号,姓名,性别,年龄,手机号,邮箱,部门,职位,入职日期"]
        for i in range(1, count + 1):
            lines.append(
                f"EMP{i:03d},用户{i},男,25,1380013800{i},u{i}@test.com,技术部,工程师,2024-01-01"
            )
        return "\n".join(lines).encode("utf-8-sig")

    async def test_import_all_new_records_skip_strategy(self, svc_e2e):
        """skip 策略：全部为新记录，全部成功创建"""
        content = self._make_valid_csv(3)
        result = await svc_e2e.import_file(content, "data.csv", strategy="skip")
        assert result.total_rows == 3
        assert result.success_count == 3
        assert result.failed_count == 0
        assert result.duplicate_count == 0
        assert svc_e2e.redmine.create_issue.call_count == 3

    async def test_import_with_duplicates_skip_strategy(self, svc_e2e):
        """skip 策略：存在重复记录时跳过"""
        # 模拟 EMP001 已存在
        svc_e2e.redmine.get_issues.return_value = {
            "issues": [{"id": 100, "custom_fields": [{"id": 1, "value": "EMP001"}]}],
            "total_count": 1,
        }
        content = self._make_valid_csv(2)  # EMP001, EMP002
        result = await svc_e2e.import_file(content, "data.csv", strategy="skip")
        assert result.duplicate_count == 1
        assert result.skipped_count == 1
        assert result.success_count == 1  # 只有 EMP002 成功

    async def test_import_with_duplicates_overwrite_strategy(self, svc_e2e):
        """overwrite 策略：重复记录被覆盖更新"""
        svc_e2e.redmine.get_issues.return_value = {
            "issues": [{"id": 100, "custom_fields": [{"id": 1, "value": "EMP001"}]}],
            "total_count": 1,
        }
        content = self._make_valid_csv(2)
        result = await svc_e2e.import_file(content, "data.csv", strategy="overwrite")
        assert result.duplicate_count == 1
        assert result.overwritten_count == 1
        assert result.success_count == 2  # 覆盖+新建都算成功
        svc_e2e.redmine.update_issue.assert_called_once()

    async def test_import_with_duplicates_terminate_strategy(self, svc_e2e):
        """terminate 策略：遇到重复立即终止"""
        svc_e2e.redmine.get_issues.return_value = {
            "issues": [{"id": 100, "custom_fields": [{"id": 1, "value": "EMP001"}]}],
            "total_count": 1,
        }
        content = self._make_valid_csv(3)  # EMP001, EMP002, EMP003
        result = await svc_e2e.import_file(content, "data.csv", strategy="terminate")
        # 第一条就重复，立即终止
        assert result.duplicate_count == 1
        assert result.success_count == 0

    async def test_import_invalid_strategy_fallback_to_skip(self, svc_e2e):
        """非法策略自动降级为 skip"""
        content = self._make_valid_csv(1)
        result = await svc_e2e.import_file(content, "data.csv", strategy="invalid_strategy")
        # 不报错，正常执行
        assert result.total_rows == 1
        assert result.success_count == 1

    async def test_import_empty_file_raises(self, svc_e2e):
        """空文件抛出 FileImportException"""
        content = _make_csv_content(["人员编号,姓名,性别,年龄,手机号,邮箱,部门,职位,入职日期"])
        with pytest.raises(FileImportException, match="没有可读取的数据行"):
            await svc_e2e.import_file(content, "empty.csv")

    async def test_import_unsupported_format_raises(self, svc_e2e):
        """不支持的文件格式抛出 FileImportException"""
        with pytest.raises(FileImportException, match="不支持的文件格式"):
            await svc_e2e.import_file(b"fake", "data.txt")

    async def test_import_mixed_valid_invalid_rows(self, svc_e2e):
        """混合有效和无效行：无效行计入 failed_count"""
        lines = [
            "人员编号,姓名,性别,年龄,手机号,邮箱,部门,职位,入职日期",
            "EMP001,张三,男,25,13800138001,z1@test.com,技术部,工程师,2024-01-01",
            "EMP002,李四,未知,16,123,bad-email,技术部,工程师,2024-01-01",  # 无效行
        ]
        content = "\n".join(lines).encode("utf-8-sig")
        result = await svc_e2e.import_file(content, "mixed.csv", strategy="skip")
        assert result.total_rows == 2
        assert result.success_count == 1
        assert result.failed_count == 1


# ═══════════════════════════════════════════════════════════════════════════════
# export_error_rows 补充测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestExportErrorRowsExtended:
    """export_error_rows 补充测试"""

    def test_export_multiple_error_rows(self):
        """导出多行错误数据"""
        from backend.app.services.import_service import ImportService

        csv_content = "编号,姓名\nE1,张三\nE2,李四\nE3,王五\n"
        result = ImportService.export_error_rows(
            file_content=csv_content.encode("utf-8-sig"),
            filename="data.csv",
            error_rows=[2, 3],  # 第2行和第3行（源码条件 1<=r-1<=max_idx 排除第1行）
        )
        # 结果应包含表头 + 2行数据
        decoded = result.decode("utf-8-sig")
        lines = [l for l in decoded.strip().splitlines() if l.strip()]
        assert len(lines) == 3  # 表头 + 2行

    def test_export_out_of_range_rows_filtered(self):
        """超出范围的行号被过滤"""
        from backend.app.services.import_service import ImportService

        csv_content = "编号,姓名\nE1,张三\nE2,李四\n"
        result = ImportService.export_error_rows(
            file_content=csv_content.encode("utf-8-sig"),
            filename="data.csv",
            error_rows=[2, 99],  # 第2行有效，99 超出范围
        )
        decoded = result.decode("utf-8-sig")
        lines = [l for l in decoded.strip().splitlines() if l.strip()]
        assert len(lines) == 2  # 表头 + 1行（只有第2行有效）

    def test_export_unsupported_format_raises(self):
        """不支持的文件格式抛出 FileImportException"""
        from backend.app.services.import_service import ImportService
        from backend.app.utils.exceptions import FileImportException

        with pytest.raises(FileImportException, match="不支持的文件格式"):
            ImportService.export_error_rows(
                file_content=b"fake",
                filename="data.pdf",
                error_rows=[1],
            )

    def test_export_all_rows_out_of_range_raises(self):
        """所有行号都超出范围时抛出异常"""
        from backend.app.services.import_service import ImportService
        from backend.app.utils.exceptions import FileImportException

        csv_content = "编号,姓名\nE1,张三\n"
        with pytest.raises(FileImportException, match="没有有效的错误行"):
            ImportService.export_error_rows(
                file_content=csv_content.encode("utf-8-sig"),
                filename="data.csv",
                error_rows=[99, 100],  # 全部超出范围
            )

    def test_export_result_has_bom(self):
        """导出结果包含 UTF-8 BOM 头（确保 Excel 正确识别中文）"""
        from backend.app.services.import_service import ImportService

        csv_content = "编号,姓名\nE1,张三\nE2,李四\n"
        result = ImportService.export_error_rows(
            file_content=csv_content.encode("utf-8-sig"),
            filename="data.csv",
            error_rows=[2],  # 第2行（源码条件排除第1行）
        )
        # UTF-8 BOM: \xef\xbb\xbf
        assert result[:3] == b"\xef\xbb\xbf"