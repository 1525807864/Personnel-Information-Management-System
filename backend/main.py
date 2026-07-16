"""人员信息管理系统 — 后端入口"""
import logging
import logging.config
import os
import sys
import time
from contextlib import asynccontextmanager

# 确保项目根目录在 sys.path 中（支持 python backend/main.py 和 python -m backend.main 两种启动方式）
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.api.v1 import auth as auth_router
from backend.app.api.v1 import personnel as personnel_router
from backend.app.core.redis_client import init_redis, close_redis


# ═══════════════════════════════════════════════════════════════
# 日志配置
# ═══════════════════════════════════════════════════════════════

def _build_log_config() -> dict:
    """构建统一的 logging dictConfig，融合应用自定义配置与 uvicorn 默认配置。

    将其传递给 uvicorn.run(log_config=...) 可防止 uvicorn 内部调用
    dictConfig() 时覆盖掉自定义的 handler/formatter。
    """
    log_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        settings.LOG_DIR,
    )
    os.makedirs(log_dir, exist_ok=True)

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": "uvicorn.logging.DefaultFormatter",
                "fmt": "%(levelprefix)s %(message)s",
                "use_colors": None,
            },
            "access": {
                "()": "uvicorn.logging.AccessFormatter",
                "fmt": '%(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s',
            },
            "custom": {
                "()": "logging.Formatter",
                "fmt": "%(asctime)s | %(levelname)-7s | %(name)s:%(lineno)d | %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr",
            },
            "access": {
                "formatter": "access",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
            "console": {
                "formatter": "custom",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "level": settings.LOG_LEVEL.upper(),
            },
            "file": {
                "formatter": "custom",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": os.path.join(log_dir, "app.log"),
                "maxBytes": settings.LOG_MAX_BYTES,
                "backupCount": settings.LOG_BACKUP_COUNT,
                "encoding": "utf-8",
                "level": "DEBUG",
            },
        },
        "loggers": {
            "uvicorn": {"handlers": ["default"], "level": "INFO", "propagate": False},
            "uvicorn.error": {"level": "INFO"},
            "uvicorn.access": {"handlers": ["access"], "level": "INFO", "propagate": False},
            "httpx": {"level": "WARNING"},
            "httpcore": {"level": "WARNING"},
            "urllib3": {"level": "WARNING"},
            "watchfiles": {"level": "WARNING"},
        },
        "root": {
            "level": "DEBUG",
            "handlers": ["console", "file"],
        },
    }


# 模块导入时立即配置日志（确保 uvicorn 启动前的日志也能输出）
# uvicorn.run() 会重新应用同一份配置，不会有副作用
logging.config.dictConfig(_build_log_config())

logger = logging.getLogger("backend.main")


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

# 注册路由
app.include_router(auth_router.router)
app.include_router(personnel_router.router)


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
        log_config=_build_log_config(),
    )