"""
人员领域模型 — 基于 Redmine Issue 存储
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime, date, timedelta, timezone

from ..core.config import settings


class Personnel(BaseModel):
    """人员领域模型，每条人员记录对应 Redmine 项目中的一个 Issue"""

    id: int
    employee_id: str
    name: str
    gender: str
    age: str
    phone: str
    email: str
    department: str
    position: str
    start_datetime: Optional[date] = None
    create_datetime: Optional[datetime] = None
    update_datetime: Optional[datetime] = None

    @classmethod
    def from_redmine_issue(cls, issue: Dict[str, Any]) -> "Personnel":
        """
        将 Redmine Issue JSON 映射为 Personnel 对象

        Issue 数据结构示例：
        {
          "id": 1, "subject": "EMP001 - 张三",
          "created_on": "2024-01-01T00:00:00Z",
          "updated_on": "2024-01-01T00:00:00Z",
          "custom_fields": [
            {"id": 1, "name": "employee_id", "value": "EMP001"},
            {"id": 2, "name": "name",        "value": "张三"},
            {"id": 3, "name": "gender",      "value": "男"},
            ...
          ]
        }
        """
        cf_map = {}
        for cf in issue.get("custom_fields", []):
            name = cf.get("name", "")
            value = cf.get("value", "")
            cf_map[name] = value

        # 解析日期字段
        start_dt = None
        raw_start = cf_map.get("start_datetime")
        _BEIJING = timezone(timedelta(hours=8))
        if raw_start:
            try:
                start_dt = datetime.fromisoformat(raw_start.replace("Z","+00:00")).astimezone(_BEIJING).replace(tzinfo=None)
            except (ValueError, TypeError):
                pass
        created = None
        raw_created = issue.get("created_on")
        if raw_created:
            try:
                created = datetime.fromisoformat(
                    raw_created.replace("Z", "+00:00")
                ).astimezone(_BEIJING).replace(tzinfo=None)
            except (ValueError, TypeError):
                pass

        updated = None
        raw_updated = issue.get("updated_on")
        if raw_updated:
            try:
                updated = datetime.fromisoformat(
                    raw_updated.replace("Z", "+00:00")
                ).astimezone(_BEIJING).replace(tzinfo=None)
            except (ValueError, TypeError):
                pass

        return cls(
            id=issue["id"],
            employee_id=cf_map.get("employee_id", ""),
            name=cf_map.get("name", ""),
            gender=cf_map.get("gender", ""),
            age=cf_map.get("age", ""),
            phone=cf_map.get("phone", ""),
            email=cf_map.get("email", ""),
            department=cf_map.get("department", ""),
            position=cf_map.get("position", ""),
            start_datetime=start_dt,
            create_datetime=created,
            update_datetime=updated,
        )

    def to_redmine_payload(self) -> dict:
        """将 Personnel 转为 Redmine Issue 创建/更新所需的扁平 dict。"""
        from .custom_field import PersonnelFieldMapping

        return PersonnelFieldMapping.build_payload(
            {
                "employee_id": self.employee_id,
                "name": self.name,
                "gender": self.gender,
                "age": self.age,
                "phone": self.phone,
                "email": self.email,
                "department": self.department,
                "position": self.position,
                "start_datetime": str(self.start_datetime) if self.start_datetime else "",
                "create_datetime": str(self.create_datetime) if self.create_datetime else "",
                "update_datetime": str(self.update_datetime) if self.update_datetime else "",
            },
            project_id=settings.REDMINE_PROJECT_ID,
        )