import re
from datetime import date, datetime
from typing import Optional, List, Annotated

from pydantic import BaseModel, Field, EmailStr, field_validator, ConfigDict

# =============================================================================
# 正则常量
# =============================================================================

PHONE_PATTERN = re.compile(r"^1[3-9]\d{9}$")
EMPLOYEE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,20}$")
SAFE_TEXT_PATTERN = re.compile(r"^[一-龥a-zA-Z0-9_\-()\s]{1,50}$")

# =============================================================================
# 共享字段类型
# =============================================================================

EmpIdStr = Annotated[
    str,
    Field(min_length=1, max_length=20, pattern=EMPLOYEE_ID_PATTERN.pattern,
          description="人员编号，1-20个字符，必须唯一"),
]
NameStr = Annotated[
    str,
    Field(min_length=1, max_length=50, pattern=SAFE_TEXT_PATTERN.pattern,
          description="姓名，1-50个字符"),
]
GenderStr = Annotated[str, Field(description="性别，必须为'男'或'女'")]
AgeInt = Annotated[int, Field(ge=18, le=65, description="年龄，范围18-65")]
PhoneStr = Annotated[str, Field(pattern=PHONE_PATTERN.pattern, description="手机号，11位")]
DeptStr = Annotated[
    str,
    Field(min_length=1, max_length=50, pattern=SAFE_TEXT_PATTERN.pattern,
          description="部门名称，1-50个字符"),
]
PosStr = Annotated[
    str,
    Field(min_length=1, max_length=50, pattern=SAFE_TEXT_PATTERN.pattern,
          description="职位名称，1-50个字符"),
]
HireDateField = Annotated[date, Field(description="入职日期，格式 YYYY-MM-DD")]

# =============================================================================
# 共享验证器 — 消除 PersonnelCreate / PersonnelUpdate 验证逻辑重复
# =============================================================================


def _validate_gender(v: str) -> str:
    v = v.strip()
    if v not in ("男", "女"):
        raise ValueError("性别必须为'男'或'女'")
    return v


def _validate_hire_date_not_future(v: date) -> date:
    if v > date.today():
        raise ValueError("入职日期不能晚于今天")
    return v


def _validate_name_not_empty(v: str) -> str:
    v = v.strip()
    if not v:
        raise ValueError("姓名不能为空")
    return v


def _validate_gender_optional(v: Optional[str]) -> Optional[str]:
    if v is not None:
        return _validate_gender(v)
    return v


def _validate_hire_date_optional(v: Optional[date]) -> Optional[date]:
    if v is not None:
        return _validate_hire_date_not_future(v)
    return v


def _validate_name_optional(v: Optional[str]) -> Optional[str]:
    if v is not None:
        return _validate_name_not_empty(v)
    return v


# =============================================================================
# 新增人员
# =============================================================================


class PersonnelCreate(BaseModel):
    """新增人员 — 请求体 Schema"""

    employee_id: EmpIdStr
    name: NameStr
    gender: GenderStr
    age: AgeInt
    phone: PhoneStr
    email: EmailStr = Field(..., description="邮箱地址")
    department: DeptStr
    position: PosStr
    hire_date: HireDateField

    _v_gender = field_validator("gender")(_validate_gender)
    _v_hire_date = field_validator("hire_date")(_validate_hire_date_not_future)
    _v_name = field_validator("name")(_validate_name_not_empty)


# =============================================================================
# 修改人员
# =============================================================================


class PersonnelUpdate(BaseModel):
    """修改人员 — 请求体 Schema（所有字段可选，只更新传入的字段）"""

    name: Optional[NameStr] = None
    gender: Optional[GenderStr] = None
    age: Optional[AgeInt] = None
    phone: Optional[PhoneStr] = None
    email: Optional[EmailStr] = None
    department: Optional[DeptStr] = None
    position: Optional[PosStr] = None
    hire_date: Optional[HireDateField] = None

    _v_gender = field_validator("gender")(_validate_gender_optional)
    _v_hire_date = field_validator("hire_date")(_validate_hire_date_optional)
    _v_name = field_validator("name")(_validate_name_optional)


# =============================================================================
# 响应 Schema
# =============================================================================


class PersonnelResponse(BaseModel):
    """人员信息 — 响应 Schema"""

    id: int
    employee_id: str
    name: str
    gender: str
    age: int
    phone: str
    email: str
    department: str
    position: str
    hire_date: Optional[date] = None
    is_deleted: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# 高级搜索
# =============================================================================


class PersonnelSearchRequest(BaseModel):
    """高级搜索 — 请求体 Schema"""

    keyword: Optional[str] = Field(None, description="搜索关键词，模糊匹配姓名或编号")
    department: Optional[str] = Field(None, description="部门精确筛选")
    position: Optional[str] = Field(None, description="职位精确筛选")
    start_date: Optional[date] = Field(None, description="入职开始日期（含）")
    end_date: Optional[date] = Field(None, description="入职结束日期（含）")
    page: int = Field(1, ge=1, description="页码，从1开始")
    size: int = Field(20, ge=1, le=100, description="每页数量，最大100")
    sort_by: str = Field(
        "created_at",
        description="排序字段：employee_id / name / gender / age / department / position / hire_date / created_at",
    )
    sort_order: str = Field("desc", description="排序方式：asc 升序 / desc 降序")

    @field_validator("sort_by")
    @classmethod
    def validate_sort_by(cls, v: str) -> str:
        allowed = {
            "employee_id", "name", "gender", "age",
            "department", "position", "hire_date", "created_at",
        }
        return v if v in allowed else "created_at"

    @field_validator("sort_order")
    @classmethod
    def validate_sort_order(cls, v: str) -> str:
        v = v.lower()
        return v if v in ("asc", "desc") else "desc"


# =============================================================================
# 批量删除
# =============================================================================


class BatchDeleteRequest(BaseModel):
    """批量删除 — 请求体 Schema"""

    ids: List[int] = Field(..., min_length=1, description="要删除的人员ID列表，至少包含1个ID")


class BatchDeleteResponse(BaseModel):
    """批量删除 — 响应数据"""

    deleted_count: int = Field(..., description="成功删除的记录数")
