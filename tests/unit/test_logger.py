"""
日志管理器单元测试
"""
import logging
import os

import pytest

from backend.app.utils.logger import LoggerManager, get_logger


def _close_all_handlers() -> None:
    """关闭并移除 root logger 的所有 handler（释放 Windows 文件锁）"""
    for h in list(logging.root.handlers):
        h.close()
    logging.root.handlers.clear()


@pytest.fixture(autouse=True)
def _reset_logger_manager() -> None:
    LoggerManager._initialized = False
    LoggerManager._config = {}
    _close_all_handlers()
    yield
    LoggerManager._initialized = False
    _close_all_handlers()


class TestLoggerManagerSetup:
    """测试 LoggerManager.setup()"""

    def test_setup_is_idempotent(self, tmp_path) -> None:
        LoggerManager.setup(log_dir=str(tmp_path), log_level="DEBUG")
        first_handlers = len(logging.root.handlers)
        LoggerManager.setup(log_dir=str(tmp_path), log_level="DEBUG")
        assert len(logging.root.handlers) == first_handlers

    def test_setup_creates_log_dir(self, tmp_path) -> None:
        log_dir = str(tmp_path / "nested" / "logs")
        LoggerManager.setup(log_dir=log_dir)
        assert os.path.isdir(log_dir)

    def test_uvicorn_config_is_dict(self, tmp_path) -> None:
        LoggerManager.setup(log_dir=str(tmp_path))
        config = LoggerManager.get_uvicorn_config()
        assert "version" in config
        assert config["disable_existing_loggers"] is False
        assert "console" in config["handlers"]
        assert "file" in config["handlers"]

    def test_root_logger_has_handlers(self, tmp_path) -> None:
        LoggerManager.setup(log_dir=str(tmp_path))
        assert len(logging.root.handlers) >= 2


class TestGetLogger:
    """测试 get_logger()"""

    def test_returns_logger_instance(self) -> None:
        logger = get_logger("test.module")
        assert isinstance(logger, logging.Logger)

    def test_same_name_returns_same_logger(self) -> None:
        assert get_logger("my.module") is get_logger("my.module")

    def test_none_name_returns_root_logger(self) -> None:
        assert get_logger() is logging.root
