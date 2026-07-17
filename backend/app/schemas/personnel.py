import re
from datetime import date, datetime
from typing import Optional, List

from pydantic import BaseModel, Field, EmailStr, validator

# =============================================================================
# 常量定义
# =============================================================================

PHONE_PATTERN = re.compile(r"^1[3-9]\d{9}$")
EMPLOYEE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,20}$")
SAFE_TEXT_PATTERN = re.compile(r"^[\u4e00-\u9fa5a-zA-Z0-9_\-()\s]{1,50}$")


# =============================================================================
# 新增人员
# =============================================================================

class PersonnelCreate(BaseModel):
    """新增人员 — 请求体 Schema"""

    employee_id: str = Field(
        ...,
        min_length=1,
        max_length=20,
        pattern=EMPLOYEE_ID_PATTERN.pattern,
        description="人员编号，1-20个字符，必须唯一",
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=50,
        pattern=SAFE_TEXT_PATTERN.pattern,
        description="姓名，1-50个字符",
    )
    gender: str = Field(..., description="性别，必须为'男'或'女'")
    age: int = Field(..., ge=18, le=65, description="年龄，范围18-65")
    phone: str = Field(..., pattern=PHONE_PATTERN.pattern, description="手机号，11位")
    email: EmailStr = Field(..., description="邮箱地址")
    department: str = Field(
        ...,
        min_length=1,
        max_length=50,
        pattern=SAFE_TEXT_PATTERN.pattern,
        description="部门名称，1-50个字符",
    )
    position: str = Field(
        ...,
        min_length=1,
        max_length=50,
        pattern=SAFE_TEXT_PATTERN.pattern,
        description="职位名称，1-50个字符",
    )
    hire_date: date = Field(..., description="入职日期，格式 YYYY-MM-DD")

    @validator("gender")
    def validate_gender(cls, v: str) -> str:
        """校验性别：必须为'男'或'女'"""
        v = v.strip()
        if v not in ("男", "女"):
            raise ValueError("性别必须为'男'或'女'")
        return v

    @validator("hire_date")
    def validate_hire_date(cls, v: date) -> date:
        """校验入职日期：不能晚于今天"""
        if v > date.today():
            raise ValueError("入职日期不能晚于今天")
        return v

    @validator("name")
    def validate_name_not_empty(cls, v: str) -> str:
        """校验姓名：去除前后空格后不能为空"""
        v = v.strip()
        if not v:
            raise ValueError("姓名不能为空")
        return v


# =============================================================================
# 修改人员
# =============================================================================

class PersonnelUpdate(BaseModel):
    """修改人员 — 请求体 Schema（所有字段可选，只更新传入的字段）"""

    name: Optional[str] = Field(None, min_length=1, max_length=50, description="姓名")
    gender: Optional[str] = Field(None, description="性别：男/女")
    age: Optional[int] = Field(None, ge=18, le=65, description="年龄")
    phone: Optional[str] = Field(None, pattern=PHONE_PATTERN.pattern, description="手机号")
    email: Optional[EmailStr] = Field(None, description="邮箱")
    department: Optional[str] = Field(None, min_length=1, max_length=50, description="部门")
    position: Optional[str] = Field(None, min_length=1, max_length=50, description="职位")
    hire_date: Optional[date] = Field(None, description="入职日期")

    @validator("gender")
    def validate_gender_optional(cls, v: Optional[str]) -> Optional[str]:
        """性别校验：仅在传入时校验"""
        if v is not None:
            v = v.strip()
            if v not in ("男", "女"):
                raise ValueError("性别必须为'男'或'女'")
        return v

    @validator("hire_date")
    def validate_hire_date_optional(cls, v: Optional[date]) -> Optional[date]:
        """入职日期校验：仅在传入时校验"""
        if v is not None and v > date.today():
            raise ValueError("入职日期不能晚于今天")
        return v

    @validator("name")
    def validate_name_optional(cls, v: Optional[str]) -> Optional[str]:
        """姓名校验：仅在传入时，去除前后空格后不能为空"""
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("姓名不能为空")
        return v


# =============================================================================
# 响应 Schema
# =============================================================================

class PersonnelResponse(BaseModel):
    """
    人员信息 — 响应 Schema

    字段映射：
      Personnel.start_datetime  → hire_date
      Personnel.create_datetime → created_at
      Personnel.update_datetime → updated_at
    """

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

    class Config:
        orm_mode = True


class PersonnelListResponse(BaseModel):
    """人员列表 — 响应 Schema"""

    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    size: int = Field(..., description="每页数量")
    items: List[PersonnelResponse] = Field(default=[], description="人员列表")


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

    @validator("sort_by")
    def validate_sort_by(cls, v: str) -> str:
        """校验排序字段白名单"""
        allowed = {
            "employee_id", "name", "gender", "age",
            "department", "position", "hire_date", "created_at",
        }
        if v not in allowed:
            return "created_at"
        return v

    @validator("sort_order")
    def validate_sort_order(cls, v: str) -> str:
        """校验排序方式：仅允许 asc 或 desc"""
        v = v.lower()
        if v not in ("asc", "desc"):
            return "desc"
        return v


# =============================================================================
# 批量删除
# =============================================================================

class BatchDeleteRequest(BaseModel):
    """批量删除 — 请求体 Schema，示例：[1, 2, 3, 4, 5]"""

    ids: List[int] = Field(..., min_items=1, description="要删除的人员ID列表，至少包含1个ID")


class BatchDeleteResponse(BaseModel):
    """批量删除 — 响应数据"""

    deleted_count: int = Field(..., description="成功删除的记录数")
