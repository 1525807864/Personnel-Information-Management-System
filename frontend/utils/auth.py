"""前端认证工具-Token管理"""
import json
from typing import Optional, Dict, Any
from dash import dcc
TOKEN_KEY = "auth-token"
USER_KEY = "auth-user"
_cache_token: Optional[str] = None
_cache_user: Optional[Dict[str,Any]] = None

def set_cache_from_store(token_data:Optional[str],user_data:Optional[str])->None:
    global _cache_token, _cache_user
    _cache_token = token_data
    _cache_user = json.loads(user_data) if user_data else None

def save_token(token:str)->str:
    global _cache_token
    _cache_token = token
    return token

def get_token() -> Optional[str]:
    return _cache_token
def save_user_info(username: str, role: str) -> str:
    global _cache_user
    _cache_user = {"username": username, "role": role}
    return json.dumps(_cache_user, ensure_ascii=False)
def get_user_info() -> Optional[Dict[str,Any]]:
    return _cache_user
def clear_auth() -> tuple:
    global _cache_token,_cache_user
    _cache_token = None
    _cache_user = None
    return None,None
