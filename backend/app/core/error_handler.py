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
    "missing": "{field}不能为空",
    "int_parsing": "{field}必须为数字",
    "string_too_short": "{field}长度不能少于{min_length}位",
    "string_too_long": "{field}长度不能超过{max_length}位",
    "greater_than_equal": "{field}不能小于{ge}",
    "less_than_equal": "{field}不能大于{le}",
    "value_error.email": "邮箱格式不正确",
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
            msg = err.get("msg", f"{label}校验失败")
            if err.get("type") == "value_error":
                msg = msg.removeprefix("Value error, ")
            messages.append(msg)
    logger.warning("请求校验失败 | %s", "；".join(messages))
    return JSONResponse(
        status_code=422,
        content={"code": 422, "message": "；".join(messages), "data": None},
    )