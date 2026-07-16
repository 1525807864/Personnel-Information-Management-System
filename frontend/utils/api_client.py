"""API调用封装"""
import requests
from typing import Optional,Any
API_BASE = "http://localhost:8002"

def set_api_base(url: str) -> None:
    global API_BASE
    API_BASE = url.strip("/")
def _headers()->dict:
    token = _get_token()
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}
#获取token的get函数
def _get_token()->Optional[str]:
    try:
        from frontend.utils.auth import get_token
        return get_token()
    except Exception as e:
        raise Exception(f"获取token错误：{e}")

def get(path: str, params: Optional[dict] = None) -> dict:
    resp = requests.get(f"{API_BASE}{path}", headers=_headers(), params=params, timeout=15)
    return _handle_response(resp)


def post(path: str, json_data: Optional[dict] = None) -> dict:
    resp = requests.post(f"{API_BASE}{path}", headers=_headers(), json=json_data, timeout=15)
    return _handle_response(resp)


def put(path: str, json_data: Optional[dict] = None) -> dict:
    resp = requests.put(f"{API_BASE}{path}", headers=_headers(), json=json_data, timeout=15)
    return _handle_response(resp)


def delete(path: str) -> dict:
    resp = requests.delete(f"{API_BASE}{path}", headers=_headers(), timeout=15)
    return _handle_response(resp)


def upload_file(path: str, file_content: bytes, filename: str, extra_fields: Optional[dict] = None) -> dict:
    files = {"file": (filename, file_content)}
    data = extra_fields or {}
    resp = requests.post(f"{API_BASE}{path}", headers=_headers(), files=files, data=data, timeout=60)
    return _handle_response(resp)


def _handle_response(resp: requests.Response) -> dict:
    try:
        data = resp.json()
    except Exception:
        return {"code": resp.status_code, "message": resp.text, "data": None}
    if resp.status_code >= 400:
        detail = data.get("detail", {})
        if isinstance(detail, dict):
            msg = detail.get("message") or str(resp.reason)
        else:
            msg = detail or data.get("message") or str(resp.reason)
        return {"code": resp.status_code, "message": msg, "data": None}
    return data
