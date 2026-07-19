"""人员信息管理系统 — 后端入口"""
import os
import sys
import time
from contextlib import asynccontextmanager

# 当脚本被直接运行（python backend/main.py）或被 multiprocessing spawn 时，
# 设置包上下文以支持相对导入。python -m backend.main 和 uvicorn 导入模式
# 下 __package__ 已由 Python 自动设置为 "backend"，此条件不触发。
if __package__ in (None, ""):
    __package__ = "backend"

# 确保项目根目录在 sys.path 中（支持 python backend/main.py 和 python -m backend.main 两种启动方式）
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from .app.core.config import settings
from .app.api.v1 import auth as auth_router
from .app.api.v1 import personnel as personnel_router
from .app.api.v1 import import_api as import_router
from .app.core.redis_client import init_redis, close_redis
from .app.utils.logger import LoggerManager, get_logger


# ═══════════════════════════════════════════════════════════════
# 日志配置
# ═══════════════════════════════════════════════════════════════

LoggerManager.setup(
    log_dir=os.path.join(_PROJECT_ROOT, settings.LOG_DIR),
    log_level=settings.LOG_LEVEL,
    max_bytes=settings.LOG_MAX_BYTES,
    backup_count=settings.LOG_BACKUP_COUNT,
)

logger = get_logger("backend.main")


# ═══════════════════════════════════════════════════════════════
# 请求日志中间件
# ═══════════════════════════════════════════════════════════════

class RequestLoggingMiddleware:
    """记录每个 HTTP 请求的方法、路径、状态码和耗时。"""
    def __init__(self,app):
        """接收下游ASGI APP(Starlette自动注入)"""
        self.app = app
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.perf_counter()
        method = scope.get("method", "UNKNOWN")
        path = scope.get("path", "/")
        client_ip = scope.get("client", ("unknown", 0))[0]
        status_code = 500

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 0)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            status_code = 500
            raise
        finally:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            log_fn = logger.warning if status_code >= 400 else logger.info
            log_fn(
                "%s %s → %d | %.1fms | client=%s",
                method, path, status_code, elapsed_ms, client_ip,
            )

    async def _call_next(self, scope, receive, send):
        raise NotImplementedError("Middleware 未正确初始化")


# ═══════════════════════════════════════════════════════════════
# 应用生命周期
# ═══════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_redis()
    logger.info("=" * 50)
    logger.info("人员信息管理系统 API 启动中...")
    logger.info("Redmine 地址: %s", settings.REDMINE_URL)
    logger.info("Redmine 项目 ID: %s", settings.REDMINE_PROJECT_ID)
    logger.info("Redis 状态: %s", "已启用" if settings.REDIS_ENABLE else "未启用")
    logger.info("=" * 50)
    yield
    await close_redis()
    logger.info("人员信息管理系统 API 正在关闭...")


# ═══════════════════════════════════════════════════════════════
# 创建 FastAPI 应用
# ═══════════════════════════════════════════════════════════════

app = FastAPI(
    title=settings.APP_NAME,
    description="基于 FastAPI + Redmine 的人员信息管理系统",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# 请求日志（在 CORS 之前，确保记录所有请求）
app.add_middleware(RequestLoggingMiddleware)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── 字段名 → 中文标签 ───────────────────────────────────────────────
_FIELD_LABELS = {
    "employee_id": "人员编号", "name": "姓名", "gender": "性别",
    "age": "年龄", "phone": "手机号", "email": "邮箱",
    "department": "部门", "position": "职位", "hire_date": "入职日期",
    "username": "用户名", "password": "密码",
}

# ─── 校验错误 → 中文消息 ──────────────────────────────────────────────
_ERROR_TEMPLATES = {
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


@app.exception_handler(RequestValidationError)
async def _validation_handler(request: Request, exc: RequestValidationError):
    messages = []
    for err in exc.errors():
        loc = err["loc"] if err["loc"] else ["unknown"]
        field = str(loc[-1]) if not isinstance(loc[-1], int) else str(loc[-2]) if len(loc) >= 2 else "未知字段"
        label = _FIELD_LABELS.get(field, field)
        tpl = _ERROR_TEMPLATES.get(err.get("type", ""))
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


# 注册路由
app.include_router(auth_router.router)
app.include_router(personnel_router.router)
app.include_router(import_router.router)


@app.get("/")
async def root():
    logger.debug("根路径被访问")
    return {"message": "人员信息管理系统 API", "Version": "1.0.0"}


# ═══════════════════════════════════════════════════════════════
# 启动入口
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logger.info("启动 uvicorn 服务器 | host=%s | port=%s", settings.FASTAPI_HOST, settings.FASTAPI_PORT)
    uvicorn.run(
        "backend.main:app",
        host=settings.FASTAPI_HOST,
        port=settings.FASTAPI_PORT,
        reload=settings.DEBUG,
        log_config=LoggerManager.get_uvicorn_config(),
    )