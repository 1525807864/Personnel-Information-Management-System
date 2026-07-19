"""
人员 Schema 数据模型单元测试

测试目标：
  1. PersonnelCreate — 创建请求体的字段校验规则
  2. PersonnelUpdate — 更新请求体的可选字段校验
  3. PersonnelSearchRequest — 搜索请求体的参数校验
  4. BatchDeleteRequest — 批量删除请求体的参数校验
  5. ImportResultData — 导入结果数据模型
"""
from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from backend.app.schemas.personnel import (
    PersonnelCreate,
    PersonnelUpdate,
    PersonnelSearchRequest,
    BatchDeleteRequest,
    PHONE_PATTERN,
    EMPLOYEE_ID_PATTERN,
    SAFE_TEXT_PATTERN,
)
from backend.app.schemas.import_schemas import (
    ImportResultData,
    ImportErrorDetail,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 通用测试数据
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def valid_create_data():
    """标准有效创建数据"""
    return {
        "employee_id": "EMP001",
        "name": "张三",
        "gender": "男",
        "age": 25,
        "phone": "13800138000",
        "email": "zhangsan@example.com",
        "department": "技术部",
        "position": "工程师",
        "hire_date": date(2024, 1, 1),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# PersonnelCreate 校验测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestPersonnelCreateValidation:
    """测试 PersonnelCreate 的 Pydantic 字段级校验规则"""

    # --- employee_id 字段 ---

    def test_employee_id_valid(self, valid_create_data):
        """合法的 employee_id 应通过校验"""
        obj = PersonnelCreate(**valid_create_data)
        assert obj.employee_id == "EMP001"

    @pytest.mark.parametrize("invalid_id, desc", [
        ("",                          "空字符串"),
        ("a" * 21,                    "超过20位"),
        ("EMP 001",                   "含空格"),
        ("EMP@001",                   "含特殊字符@"),
        ("EMP#001",                   "含特殊字符#"),
        ("EMP.001",                   "含点号"),
    ])
    def test_employee_id_invalid(self, valid_create_data, invalid_id, desc):
        """测试各种非法 employee_id 被拒绝"""
        valid_create_data["employee_id"] = invalid_id
        with pytest.raises(ValidationError):
            PersonnelCreate(**valid_create_data)

    def test_employee_id_boundary_1_char(self, valid_create_data):
        """employee_id 最小长度 1 位"""
        valid_create_data["employee_id"] = "A"
        obj = PersonnelCreate(**valid_create_data)
        assert obj.employee_id == "A"

    def test_employee_id_boundary_20_chars(self, valid_create_data):
        """employee_id 最大长度 20 位"""
        valid_create_data["employee_id"] = "A" * 20
        obj = PersonnelCreate(**valid_create_data)
        assert len(obj.employee_id) == 20

    # --- name 字段 ---

    def test_name_valid_chinese(self, valid_create_data):
        """中文姓名应通过校验"""
        obj = PersonnelCreate(**valid_create_data)
        assert obj.name == "张三"

    def test_name_valid_english(self, valid_create_data):
        """英文姓名应通过校验"""
        valid_create_data["name"] = "John-Smith"
        obj = PersonnelCreate(**valid_create_data)
        assert obj.name == "John-Smith"

    def test_name_empty_after_strip(self, valid_create_data):
        """全空格姓名应被拒绝（validator 去空格后为空）"""
        valid_create_data["name"] = "   "
        with pytest.raises(ValidationError):
            PersonnelCreate(**valid_create_data)

    def test_name_too_long(self, valid_create_data):
        """姓名超过 50 位应被拒绝"""
        valid_create_data["name"] = "张" * 51
        with pytest.raises(ValidationError):
            PersonnelCreate(**valid_create_data)

    # --- gender 字段 ---

    @pytest.mark.parametrize("gender", ["男", "女"])
    def test_gender_valid(self, valid_create_data, gender):
        """合法的性别值"""
        valid_create_data["gender"] = gender
        obj = PersonnelCreate(**valid_create_data)
        assert obj.gender == gender

    @pytest.mark.parametrize("invalid_gender", ["未知", "male", "female", "", "  ", "无"])
    def test_gender_invalid(self, valid_create_data, invalid_gender):
        """非法的性别值"""
        valid_create_data["gender"] = invalid_gender
        with pytest.raises(ValidationError):
            PersonnelCreate(**valid_create_data)

    # --- age 字段 ---

    @pytest.mark.parametrize("age", [18, 25, 40, 65])
    def test_age_valid(self, valid_create_data, age):
        """年龄 18-65 范围"""
        valid_create_data["age"] = age
        obj = PersonnelCreate(**valid_create_data)
        assert obj.age == age

    @pytest.mark.parametrize("invalid_age, desc", [
        (17, "小于18"),
        (66, "大于65"),
        (0,  "为0"),
        (-1, "负数"),
    ])
    def test_age_invalid(self, valid_create_data, invalid_age, desc):
        """非法年龄值"""
        valid_create_data["age"] = invalid_age
        with pytest.raises(ValidationError):
            PersonnelCreate(**valid_create_data)

    # --- phone 字段 ---

    def test_phone_valid(self, valid_create_data):
        """合法手机号"""
        obj = PersonnelCreate(**valid_create_data)
        assert obj.phone == "13800138000"

    @pytest.mark.parametrize("invalid_phone, desc", [
        ("1380013800",   "只有10位"),
        ("138001380000", "12位"),
        ("23800138000",  "非1开头"),
        ("1380013800a",  "含字母"),
        ("138-0013-800", "含连字符"),
        ("",             "空字符串"),
    ])
    def test_phone_invalid(self, valid_create_data, invalid_phone, desc):
        """非法手机号"""
        valid_create_data["phone"] = invalid_phone
        with pytest.raises(ValidationError):
            PersonnelCreate(**valid_create_data)

    # --- email 字段 ---

    def test_email_valid(self, valid_create_data):
        """合法邮箱"""
        obj = PersonnelCreate(**valid_create_data)
        assert obj.email == "zhangsan@example.com"

    @pytest.mark.parametrize("invalid_email, desc", [
        ("notanemail",      "无@符号"),
        ("@no-local.com",   "无本地部分"),
        ("no-domain@",      "无域名部分"),
        ("spaces in@x.com", "含空格"),
    ])
    def test_email_invalid(self, valid_create_data, invalid_email, desc):
        """非法邮箱"""
        valid_create_data["email"] = invalid_email
        with pytest.raises(ValidationError):
            PersonnelCreate(**valid_create_data)

    # --- hire_date 字段 ---

    def test_hire_date_valid_past(self, valid_create_data):
        """入职日期为过去日期"""
        valid_create_data["hire_date"] = date(2020, 1, 1)
        obj = PersonnelCreate(**valid_create_data)
        assert obj.hire_date == date(2020, 1, 1)

    def test_hire_date_valid_today(self, valid_create_data):
        """入职日期为今天"""
        valid_create_data["hire_date"] = date.today()
        obj = PersonnelCreate(**valid_create_data)
        assert obj.hire_date == date.today()

    def test_hire_date_future(self, valid_create_data):
        """入职日期为明天（未来）应被拒绝"""
        valid_create_data["hire_date"] = date.today() + timedelta(days=1)
        with pytest.raises(ValidationError):
            PersonnelCreate(**valid_create_data)

    # --- 必填字段缺失 ---

    @pytest.mark.parametrize("missing_field", [
        "employee_id", "name", "gender", "age", "phone", "email",
        "department", "position", "hire_date",
    ])
    def test_missing_required_field(self, valid_create_data, missing_field):
        """缺少必填字段应抛出 ValidationError"""
        del valid_create_data[missing_field]
        with pytest.raises(ValidationError):
            PersonnelCreate(**valid_create_data)


# ═══════════════════════════════════════════════════════════════════════════════
# PersonnelUpdate 校验测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestPersonnelUpdateValidation:
    """测试 PersonnelUpdate 的可选字段校验"""

    def test_update_empty_dict(self):
        """空字典（不传任何字段）应合法"""
        obj = PersonnelUpdate()
        assert obj.model_dump(exclude_unset=True) == {}

    def test_update_partial_fields(self):
        """只更新部分字段"""
        obj = PersonnelUpdate(name="新名字", age=30)
        assert obj.name == "新名字"
        assert obj.age == 30
        dumped = obj.model_dump(exclude_unset=True)
        assert "email" not in dumped
        assert "phone" not in dumped

    def test_update_gender_invalid(self):
        """更新时性别值非法"""
        with pytest.raises(ValidationError):
            PersonnelUpdate(gender="不男不女")

    def test_update_hire_date_future(self):
        """更新时入职日期在未来"""
        with pytest.raises(ValidationError):
            PersonnelUpdate(hire_date=date.today() + timedelta(days=365))

    def test_update_name_empty(self):
        """更新时姓名为空字符串"""
        with pytest.raises(ValidationError):
            PersonnelUpdate(name="")


# ═══════════════════════════════════════════════════════════════════════════════
# PersonnelSearchRequest 校验测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestPersonnelSearchRequest:
    """测试高级搜索请求体的校验规则"""

    def test_default_values(self):
        """默认值应正确设置"""
        req = PersonnelSearchRequest()
        assert req.page == 1
        assert req.size == 20
        assert req.sort_by == "created_at"
        assert req.sort_order == "desc"
        assert req.keyword is None

    def test_valid_sort_fields(self):
        """合法的排序字段"""
        for field in ["employee_id", "name", "gender", "age", "department",
                       "position", "hire_date", "created_at"]:
            req = PersonnelSearchRequest(sort_by=field)
            assert req.sort_by == field

    def test_invalid_sort_by(self):
        """非法的排序字段应回退到默认值 created_at"""
        req = PersonnelSearchRequest(sort_by="hacked_field")
        assert req.sort_by == "created_at"

    def test_invalid_sort_order(self):
        """非法的排序方式应回退到 desc"""
        req = PersonnelSearchRequest(sort_order="random_order")
        assert req.sort_order == "desc"

    def test_page_min_value(self):
        """page 最小值应为 1"""
        with pytest.raises(ValidationError):
            PersonnelSearchRequest(page=0)

    def test_size_max_value(self):
        """size 最大值应为 100"""
        with pytest.raises(ValidationError):
            PersonnelSearchRequest(size=101)


# ═══════════════════════════════════════════════════════════════════════════════
# BatchDeleteRequest 校验测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestBatchDeleteRequest:
    """测试批量删除请求体的校验"""

    def test_valid_ids(self):
        """合法的 ID 列表"""
        req = BatchDeleteRequest(ids=[1, 2, 3])
        assert req.ids == [1, 2, 3]

    def test_empty_ids(self):
        """空 ID 列表应被拒绝（min_items=1）"""
        with pytest.raises(ValidationError):
            BatchDeleteRequest(ids=[])

    def test_single_id(self):
        """单个 ID 应合法"""
        req = BatchDeleteRequest(ids=[1])
        assert req.ids == [1]


# ═══════════════════════════════════════════════════════════════════════════════
# 正则模式测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestRegexPatterns:
    """测试 schema 中定义的三个正则表达式常量"""

    def test_phone_pattern_valid(self):
        """PHONE_PATTERN 验证合法手机号"""
        assert PHONE_PATTERN.match("13800138000")
        assert PHONE_PATTERN.match("15912345678")
        assert PHONE_PATTERN.match("18888888888")
        assert PHONE_PATTERN.match("19900001111")

    def test_phone_pattern_invalid(self):
        """PHONE_PATTERN 拒绝非法手机号"""
        assert not PHONE_PATTERN.match("12345678901")
        assert not PHONE_PATTERN.match("1380013800")
        assert not PHONE_PATTERN.match("138001380000")
        assert not PHONE_PATTERN.match("1380013800a")

    def test_employee_id_pattern_valid(self):
        """EMPLOYEE_ID_PATTERN 验证合法编号"""
        assert EMPLOYEE_ID_PATTERN.match("EMP001")
        assert EMPLOYEE_ID_PATTERN.match("test_user-01")
        assert EMPLOYEE_ID_PATTERN.match("A")

    def test_employee_id_pattern_invalid(self):
        """EMPLOYEE_ID_PATTERN 拒绝非法编号"""
        assert not EMPLOYEE_ID_PATTERN.match("EMP@001")
        assert not EMPLOYEE_ID_PATTERN.match("EMP 001")
        assert not EMPLOYEE_ID_PATTERN.match("")

    def test_safe_text_pattern_valid(self):
        """SAFE_TEXT_PATTERN 验证合法文本"""
        assert SAFE_TEXT_PATTERN.match("张三")
        assert SAFE_TEXT_PATTERN.match("John Doe")
        assert SAFE_TEXT_PATTERN.match("张三(实习)")
        assert SAFE_TEXT_PATTERN.match("Test_User-1")

    def test_safe_text_pattern_invalid(self):
        """SAFE_TEXT_PATTERN 拒绝非法文本"""
        assert not SAFE_TEXT_PATTERN.match("")
        assert not SAFE_TEXT_PATTERN.match("张" * 51)
        assert not SAFE_TEXT_PATTERN.match("abc@def")


# ═══════════════════════════════════════════════════════════════════════════════
# ImportResultData 模型测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestImportResultData:
    """测试导入结果数据模型的字段和默认值"""

    def test_default_values(self):
        """所有计数器默认为 0"""
        result = ImportResultData()
        assert result.total_rows == 0
        assert result.success_count == 0
        assert result.failed_count == 0
        assert result.duplicate_count == 0
        assert result.skipped_count == 0
        assert result.overwritten_count == 0
        assert result.error_messages == []
        assert result.error_details == []

    def test_full_result(self):
        """完整的导入结果"""
        result = ImportResultData(
            total_rows=100,
            success_count=95,
            failed_count=3,
            duplicate_count=2,
            skipped_count=2,
            overwritten_count=0,
            error_messages=["第 5 行: 手机号格式不正确"],
            error_details=[
                ImportErrorDetail(row=5, employee_id="EMP005", reason="手机号格式不正确"),
            ],
        )
        assert result.total_rows == 100
        assert result.error_messages == ["第 5 行: 手机号格式不正确"]
        assert len(result.error_details) == 1
        assert result.error_details[0].row == 5
