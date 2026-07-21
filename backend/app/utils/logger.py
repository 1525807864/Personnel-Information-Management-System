"""日志工具 — 统一的日志配置与获取。

LoggerManager.setup() 在应用启动时调用一次，配置全局 logging；
get_logger() 供各模块获取已配置好的 logger 实例。
"""
import logging
import logging.config
import logging.handlers
import os
from typing import Optional


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """获取已由 LoggerManager 统一配置的 logger。"""
    return logging.getLogger(name)


class LoggerManager:
    """应用日志管理器 — 封装 logging dictConfig 与 uvicorn 日志配置。"""

    _log_dir: str = ""
    _log_level: str = "INFO"
    _max_bytes: int = 100 * 1024 * 1024
    _backup_count: int = 5

    # ── 公开方法 ──────────────────────────────────────────────

    @classmethod
    def setup(
        cls,
        log_dir: str,
        log_level: str = "INFO",
        max_bytes: int = 100 * 1024 * 1024,
        backup_count: int = 5,
    ) -> None:
        """应用启动时调用：创建日志目录并应用全局 logging 配置。"""
        cls._log_dir = log_dir
        cls._log_level = log_level
        cls._max_bytes = max_bytes
        cls._backup_count = backup_count

        os.makedirs(log_dir, exist_ok=True)
        logging.config.dictConfig(cls._build_config())

    @classmethod
    def get_uvicorn_config(cls) -> dict:
        """返回 uvicorn.run(log_config=...) 所需的字典配置。"""
        if not cls._log_dir:
            raise RuntimeError("LoggerManager 未初始化，请先调用 LoggerManager.setup()")
        return cls._build_config()

    # ── 内部方法 ──────────────────────────────────────────────

    @classmethod
    def _build_config(cls) -> dict:
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
                    "level": cls._log_level.upper(),
                },
                "file": {
                    "formatter": "custom",
                    "class": "logging.handlers.RotatingFileHandler",
                    "filename": os.path.join(cls._log_dir, "app.log"),
                    "maxBytes": cls._max_bytes,
                    "backupCount": cls._backup_count,
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
