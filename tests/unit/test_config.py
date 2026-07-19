"""
应用配置模块单元测试

测试目标：
  1. Settings 类可正常实例化
  2. 基本字段类型正确
  3. JWT 默认值
"""
import os
from unittest.mock import patch

import pytest


class TestSettingsBasics:
    """测试 Settings 基本功能"""

    def test_can_instantiate_with_env(self) -> None:
        """用 .env 覆盖可正常实例化"""
        env_override = {
            "SECRET_KEY": "test-secret-for-unit-test",
            "REDMINE_URL": "https://redmine.example.com",
            "REDMINE_API_KEY": "test-api-key",
        }
        with patch.dict(os.environ, env_override, clear=True):
            from backend.app.core.config import Settings
            s = Settings()

            assert s.APP_NAME == "人员信息管理系统"
            assert s.SECRET_KEY == "test-secret-for-unit-test"
            assert s.REDMINE_URL == "https://redmine.example.com"
            assert s.REDMINE_API_KEY == "test-api-key"

    def test_jwt_defaults(self) -> None:
        """JWT 默认值"""
        env_override = {
            "SECRET_KEY": "test-secret",
            "REDMINE_URL": "https://redmine.example.com",
            "REDMINE_API_KEY": "key",
        }
        with patch.dict(os.environ, env_override, clear=True):
            from backend.app.core.config import Settings
            s = Settings()

            assert s.JWT_ALGORITHM == "HS256"
            assert s.JWT_EXPIRE_HOURS == 24

    def test_cors_allowed_origins(self) -> None:
        """CORS origins 应可逗号分隔"""
        env_override = {
            "SECRET_KEY": "test-secret",
            "REDMINE_URL": "https://redmine.example.com",
            "REDMINE_API_KEY": "key",
            "CORS_ALLOWED_ORIGINS": "http://a.com,http://b.com",
        }
        with patch.dict(os.environ, env_override, clear=True):
            from backend.app.core.config import Settings
            s = Settings()

            assert s.CORS_ALLOWED_ORIGINS == "http://a.com,http://b.com"

    def test_log_settings_have_sensible_defaults(self) -> None:
        """日志相关设置应有合理的默认值"""
        env_override = {
            "SECRET_KEY": "test-secret",
            "REDMINE_URL": "https://redmine.example.com",
            "REDMINE_API_KEY": "key",
        }
        with patch.dict(os.environ, env_override, clear=True):
            from backend.app.core.config import Settings
            s = Settings()

            assert s.LOG_LEVEL in ("DEBUG", "INFO", "WARNING", "ERROR")
            assert isinstance(s.LOG_MAX_BYTES, int) and s.LOG_MAX_BYTES > 0
            assert isinstance(s.LOG_BACKUP_COUNT, int) and s.LOG_BACKUP_COUNT > 0
