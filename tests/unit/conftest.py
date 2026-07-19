"""
单元测试专用 conftest

处理库兼容性问题（如 bcrypt 5.x 与 passlib 1.7.4 不兼容）
"""
import pytest


def _check_passlib_bcrypt_compat():
    """检测 passlib 的 bcrypt 后端是否能正常工作"""
    try:
        from passlib.context import CryptContext
        ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
        ctx.hash("test")
        return True
    except Exception:
        return False


_PASSLIB_BCRYPT_OK = _check_passlib_bcrypt_compat()
