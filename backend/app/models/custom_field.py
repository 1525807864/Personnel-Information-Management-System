from typing import Dict, Any, List

from pydantic import BaseModel


class CustomFieldDefinition(BaseModel):
    """自定义字段定义"""

    id: int
    name: str
    field_format: str = ""
    possible_values: List[str] = []
    is_required: bool = False
    is_filter: bool = False
    searchable: bool = False

    @classmethod
    def from_redmine_api(cls, data: Dict[str, Any]) -> "CustomFieldDefinition":
        return cls(**data)


class PersonnelFieldMapping:
    """人员字段 ↔ Redmine Custom Field ID 双向映射

    项目中所有 Redmine cf_X payload 构建均通过此类完成，避免硬编码散落各处。
    """

    FIELD_TO_CF: Dict[str, str] = {
        "employee_id":      "cf_1",
        "name":             "cf_2",
        "gender":           "cf_3",
        "age":              "cf_4",
        "phone":            "cf_5",
        "department":       "cf_6",
        "position":         "cf_7",
        "start_datetime":   "cf_8",
        "create_datetime":  "cf_9",
        "update_datetime":  "cf_10",
        "email":            "cf_11",
    }

    CF_TO_FIELD: Dict[str, str] = {v: k for k, v in FIELD_TO_CF.items()}

    _STRING_FIELDS = frozenset({"age", "start_datetime", "create_datetime", "update_datetime"})

    @classmethod
    def get_cf_key(cls, field_name: str) -> str:
        return cls.FIELD_TO_CF[field_name]

    @classmethod
    def get_field_name(cls, cf_key: str) -> str:
        return cls.CF_TO_FIELD[cf_key]

    @classmethod
    def build_payload(
        cls, data: dict, *, project_id: int = 0, include_meta: bool = False,
    ) -> dict:
        """将人员数据 dict 转为 Redmine Issue API payload。

        仅包含 data 中存在的字段——data 没有的字段不会被写入 payload，
        避免更新时将未提供的字段覆盖为空。

        Args:
            data: 人员数据，key 为字段名（如 employee_id, name, gender ...）。
            project_id: Redmine 项目 ID，传 0 时不写入 project_id（更新场景）。
            include_meta: True 时附加 tracker_id=1 / status_id=1（创建 Issue 时需要）。

        Returns:
            {"subject": "...", "project_id": 1, "cf_1": "...", ...}
        """
        emp_id = str(data.get("employee_id", "")).strip()
        name = str(data.get("name", "")).strip()

        payload: dict = {"subject": f"{emp_id} - {name}"}
        if project_id:
            payload["project_id"] = project_id
        if include_meta:
            payload["tracker_id"] = 1
            payload["status_id"] = 1

        for field_name, cf_key in cls.FIELD_TO_CF.items():
            if field_name not in data:
                continue
            value = data[field_name]
            if value is None:
                payload[cf_key] = ""
            elif field_name in cls._STRING_FIELDS:
                payload[cf_key] = str(value)
            else:
                payload[cf_key] = value

        return payload
