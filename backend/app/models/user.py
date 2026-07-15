from typing import Optional,List,Dict,Any
from datetime import datetime
from pydantic import BaseModel,Field

#redmine模型层
class RedmineUser(BaseModel):
    id: int
    login: str
    firstname: str = ""
    lastname: str = ""
    email: str = ""
    admin: bool = False
    status: int = 1
    created_on: Optional[datetime] = None
    updated_on: Optional[datetime] = None
    last_login_on: Optional[datetime] = None
    custom_fields: Dict[str, Any] = Field(default_factory=dict)

    @property
    def full_name(self)->str:
        return f"{self.lastname}{self.firstname}"
    @classmethod
    def from_redmine_api(cls,data:Dict[str,Any])->'RedmineUser':
        """
        从redmine API响应创建用户对象
        :param api_response:
        :return:
        """
        user_data = data.get("user",data)
        cf_map = {}
        for cf in user_data.get("custom_fields",[]):
            if cf.get("firstname"):
                cf_map[cf["firstname"]] = cf.get("value")
        user_data["custom_fields"] = cf_map
        return cls(**user_data)

    def to_dict(self)->Dict[str,Any]:
        """
        转换为字段，用于API响应
        :return:
        """
        return {
            'id':self.id,
            'login':self.login,
            'firstname':self.firstname,
            'lastname':self.lastname,
            'email':self.email,
            'admin':self.admin,
            'status':self.status,
            'created_on':self.created_on,
            'updated_on':self.updated_on,
            'last_login_on':self.last_login_on,
            'custom_fields':self.custom_fields
        }

