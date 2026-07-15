import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings

# 项目根目录（config.py 向上三级：core → app → backend → 项目根）
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class Settings(BaseSettings):
    # ─── 应用配置 ───
    APP_NAME: str = "人员信息管理系统"
    DEBUG: bool = True
    FASTAPI_HOST: str = "0.0.0.0"
    FASTAPI_PORT: int = 8000

    # ─── JWT 配置 ───
    SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24

    # ─── Redmine 配置 ───
    REDMINE_URL: str
    REDMINE_API_KEY: str
    REDMINE_PROJECT_ID: int = 427

    # ─── Redis 配置 ───
    REDIS_ENABLE: bool = False
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None

    # ─── CORS 配置 ───
    CORS_ALLOWED_ORIGINS: str = "http://localhost:8070"
    # ─── 日志配置 ───
    LOG_LEVEL: str = "INFO"  # DEBUG / INFO / WARNING / ERROR
    LOG_DIR: str = "logs"  # 日志文件目录（相对于项目根目录）
    LOG_MAX_BYTES: int = 10 * 1024 * 1024  # 单个日志文件最大 10MB
    LOG_BACKUP_COUNT: int = 5  # 最多保留 5 个历史日志
    model_config = {
        "env_file": os.path.join(_PROJECT_ROOT, ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }



settings = Settings()
