"""
请求校验错误处理

将 Pydantic ValidationError 转换为中文的 JSON 响应，
同时提供字段名标签和错误消息模板供其他模块复用。
"""
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from ..utils.logger import get_logger

logger = get_logger(__name__)

# ─── 字段名 → 中文标签 ───────────────────────────────────────────────

FIELD_LABELS = {
    "employee_id": "人员编号", "name": "姓名", "gender": "性别",
    "age": "年龄", "phone": "手机号", "email": "邮箱",
    "department": "部门", "position": "职位", "hire_date": "入职日期",
    "username": "用户名", "password": "密码",
}

# ─── 校验错误 → 中文消息 ──────────────────────────────────────────────

ERROR_TEMPLATES = {
    "string_pattern_mismatch": "{field}格式不正确",
    "value_error.missing": "{field}不能为空",
    "type_error.integer": "{field}必须为数字",
    "value_error.email": "邮箱格式不正确",
    "value_error.number.not_ge": "{field}不能小于{min_value}",
    "value_error.number.not_le": "{field}不能大于{max_value}",
    "value_error.any_str.min_length": "{field}长度不能少于{min_length}位",
    "value_error.any_str.max_length": "{field}长度不能超过{max_length}位",
    "value_error.date": "入职日期格式不正确",
}


async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """将 Pydantic 校验错误转为中文 JSON 响应"""
    messages = []
    for err in exc.errors():
        loc = err["loc"] if err["loc"] else ["unknown"]
        field = str(loc[-1]) if not isinstance(loc[-1], int) else str(loc[-2]) if len(loc) >= 2 else "未知字段"
        label = FIELD_LABELS.get(field, field)
        tpl = ERROR_TEMPLATES.get(err.get("type", ""))
        if tpl:
            ctx = {k: v for k, v in (err.get("ctx") or {}).items()}
            ctx["field"] = label
            messages.append(tpl.format(**ctx))
        else:
            messages.append(err.get("msg", f"{label}校验失败"))
    logger.warning("请求校验失败 | %s", "；".join(messages))
    return JSONResponse(
        status_code=422,
        content={"code": 422, "message": "；".join(messages), "data": None},
    )