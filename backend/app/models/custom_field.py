from typing import Dict, Any, List
from pydantic import BaseModel

class CustomFieldDefinition(BaseModel):
    """
    自定义字段定义
    """
    id: int
    name: str
    field_format: str=""
    possible_values: List[str] = []
    is_required: bool = False
    is_filter: bool = False
    searchable: bool = False

    @classmethod
    def from_redmine_api(cls, data: Dict[str, Any]) -> 'CustomFieldDefinition':
        return cls(**data)

class PersonnelFieldMapping(BaseModel):
    """
    人员字段->Redmine Custiom Field ID 映射配置
    """
    # 注意: Redmine 中 cf_2=name, cf_6=email 是冗余的自定义字段，
    # 代码中 name 走 Redmine 内置 firstname/lastname，email 走内置 mail，
    # 因此跳过 cf_2 和 cf_6，ID 不连续属于正常情况
    employee_id: str = "cf_1"   # 人员编号
    employee_id_id: int = 1
    name: str = "cf_2"
    name_id: int = 2
    gender: str = "cf_3"        # 性别
    gender_id: int = 3
    age: str = "cf_4"           # 年龄
    age_id: int = 4
    phone: str = "cf_5"         # 手机号
    phone_id: int = 5
    email: str = "cf_11"
    email_id: int = 11
    department: str = "cf_6"    # 部门
    department_id: int = 6
    position: str = "cf_7"      # 职位
    position_id: int = 7
    start_datetime: str = "cf_8"    # 入职日期
    start_datetime_id: int = 8
    create_datetime: str = "cf_9"  # 创建时间
    create_datetime_id: int = 9
    update_datetime: str = "cf_10"  # 更新时间
    update_datetime_id: int = 10

