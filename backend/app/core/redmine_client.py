"""
author:Lishaopeng
date:2026/7/14
redmine_client客户端
"""
import time

import httpx
from typing import Dict,Any,List,Optional
from datetime import datetime
import logging
logger = logging.getLogger(__name__)
class RedmineClient:
    def __init__(self,base_url:str,api_key:str):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {'X-Redmine-API-Key': api_key,'Content-Type': 'application/json'}
    async def get_user(self,user_id:int)->Dict[str,Any]:
        """获取单个用户信息"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/users/{user_id}.json", headers=self.headers)
            response.raise_for_status()
            return response.json()
    async def get_users(self,page:int=1,limit:int=20,filters:Optional[Dict]=None)->Dict[str,Any]:
        """
        获取用户列表支持分页和过滤
        :param page:页数
        :param limit: 每页显示的数量
        :param filters:
        :return:
        """
        params = {
            'page': page,
            'limit': limit,
            'status':'*',#所有状态
        }
        #添加自定义的字段过滤
        if filters:
            for key,value in filters.items():
                if key.startswith("cf_"):
                    params[f'cf_{key[3:]}'] = value
                else:
                    params[key] = value
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/users.json", params=params, headers=self.headers)
            response.raise_for_status()
            return response.json()

    async def create_user(self,user_data:Dict[str,Any])->Dict[str,Any]:
        """
        创建用户
        :param user_data:用户数据
        :return: 返回一个字典数据
        准备发送给redmine的数据
        """
        payload = {
            'user':{
                'login':user_data['login'],
                'password':user_data['password'],
                'firstname':user_data.get('firstname'),
                'lastname':user_data.get('lastname'),
                'email':user_data.get('email'),
                'status':user_data.get('status',1),
            }
        }
        # 添加自定义字段
        custom_fields = []
        for key, value in user_data.items():
            if key.startswith("cf_"):
                custom_fields.append({
                    'id': int(key[3:]),
                    'value': value,
                })
        if custom_fields:
            payload['user']['custom_fields'] = custom_fields

        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.base_url}/users.json", json=payload, headers=self.headers)
            response.raise_for_status()
            return response.json()

    async def update_user(self, user_id: int, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新用户"""
        payload = {'user': {}}

        # 只包含需要更新的字段
        updatable_fields = ['login', 'firstname', 'lastname', 'mail', 'status']
        for field in updatable_fields:
            if field in user_data:
                payload['user'][field] = user_data[field]

        # 更新自定义字段
        custom_fields = []
        for key, value in user_data.items():
            if key.startswith('cf_'):
                custom_fields.append({
                    'id': int(key[3:]),
                    'value': value
                })
        if custom_fields:
            payload['user']['custom_fields'] = custom_fields

        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{self.base_url}/users/{user_id}.json",
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()

    async def delete_user(self, user_id: int):
        """删除用户"""
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.base_url}/users/{user_id}.json",
                headers=self.headers
            )
            response.raise_for_status()
            return True

    async def verify_user_credentials(self,login:str,password:str)->Optional[Dict[str,Any]]:
        """
        用HTTP basic Auth向redmine验证用户凭证
        :param login: Redmine用户名
        :param password: Redmine密码
        :return: 凭证有效时返回用户信息字典，无效时返回None
        """
        import base64
        credentials = base64.b64encode(f"{login}:{password}".encode()).decode()
        auth_headers = {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient() as client:
            t0 = time.perf_counter()
            try:
                response = await client.get(
                    f"{self.base_url}/users/current.json",
                    headers=auth_headers,
                )
            except Exception as e:
                elapsed = (time.perf_counter() - t0) * 1000
                logger.error("Redmine API 请求异常 | login=%s | error=%s | 耗时=%.1fms", login, str(e), elapsed)
                return None
            elapsed = (time.perf_counter() - t0) * 1000
            if response.status_code == 200:
                logger.debug("Redmine Basic Auth 验证成功 | login=%s | 耗时=%.1fms", login, elapsed)
                return response.json()
            logger.warning("Redmine Basic Auth 验证失败 | login=%s | status=%s | body=%s | 耗时=%.1fms",
                           login, response.status_code, response.text[:200], elapsed)
            return None
    async def get_user_with_api_key(self,user_id:int)->Optional[Dict[str,Any]]:
        """
        用Admin API Key获取用户的完整信息，用于verify通过后调用，获取用户的角色、状态、自定义字段等
        :param user_id:
        :return: 用户完整的字典数据
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/users/{user_id}.json",
                headers=self.headers,
                params={'include': "memberships"},
            )
            if response.status_code == 200:
                return response.json()
            return None
    """
    检查账户是否被锁定
    通过redmine用户的status来判断啊
    1=活跃 2=已注册 3=已锁定 5=待激活
    """
    async def check_account_locked(self,login:str)->bool:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/users.json",
                headers=self.headers,
                params={"name": login, "status": "*", "limit": 1}
            )
            if response.status_code == 200:
                data = response.json()
                users = data.get("users","")
                return users[3].get("status") == 3 #status==3表示锁定
            return False
