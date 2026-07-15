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
    Person_Number: str = "cf_1"  # 人员编号
    Person_Number_id: int = 1
    gender: str = "cf_2"  # 性别
    gender_id: int = 2
    age: str = "cf_3"  # 年龄
    age_id: int = 3
    phone: str = "cf_4"  # 手机号
    phone_id: int = 4
    department: str = "cf_5"  # 部门
    department_id: int = 5
    position: str = "cf_6"  # 职位
    position_id: int = 6
    start_datetime: str = "cf_7"  # 入职日期
    start_datetime_id: int = 7
    create_datetime: str = "cf_8" #创建时间
    create_datetime_id: int = 8
    update_datetime: str = "cf_9" #更新时间
    update_datetime_id: int = 9

