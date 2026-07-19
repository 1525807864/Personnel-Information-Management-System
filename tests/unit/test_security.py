"""
安全模块单元测试

测试目标：
  1. JWT Token 创建和解码
  2. 密码加密和验证（bcrypt）
  3. Token 过期逻辑
  4. JWT 载荷结构完整性
"""
from datetime import timedelta

import pytest

from tests.unit.conftest import _PASSLIB_BCRYPT_OK

from backend.app.core.security import (
    create_access_token,
    decode_access_token,
    verify_password,
    hash_password,
)


class TestJWTToken:
    """JWT（JSON Web Token）相关测试"""

    def test_create_token_structure(self):
        """测试 JWT 三段式结构"""
        token = create_access_token({"sub": "1", "username": "admin", "role": "admin"})
        parts = token.split(".")
        assert len(parts) == 3, f"JWT 应为三段式，实际为 {len(parts)} 段"

    def test_create_token_contains_claims(self):
        """测试 Token 包含所有必要声明（claims）"""
        data = {"sub": "99", "username": "testuser", "role": "user"}
        token = create_access_token(data)
        decoded = decode_access_token(token)

        assert decoded is not None, "解码失败"
        assert decoded.get("sub") == "99"
        assert decoded.get("username") == "testuser"
        assert decoded.get("role") == "user"

        assert "exp" in decoded, "缺少过期时间声明(exp)"
        assert "iat" in decoded, "缺少签发时间声明(iat)"
        assert "jti" in decoded, "缺少JWT ID声明(jti)"

        assert decoded["exp"] > decoded["iat"]

    def test_token_expiration(self):
        """测试 Token 过期逻辑

        使用负的 expires_delta 创建已过期的 Token。
        注意：不能使用 timedelta(seconds=0)，因为 Python 中 timedelta(0) 是 falsy 值，
        create_access_token 中的 `expires_delta or timedelta(hours=EXPIRE_HOURS)`
        会回退到默认 24 小时过期时间。
        """
        token = create_access_token(
            {"sub": "1"},
            expires_delta=timedelta(seconds=-1),
        )
        decoded = decode_access_token(token)
        assert decoded is None, "过期 Token 应解码失败返回 None"

    def test_token_future_expiry(self):
        """测试远期过期 Token"""
        token = create_access_token(
            {"sub": "1"},
            expires_delta=timedelta(hours=24),
        )
        decoded = decode_access_token(token)
        assert decoded is not None
        assert decoded["sub"] == "1"

    def test_invalid_token(self):
        """测试篡改的 Token 解码失败"""
        assert decode_access_token("not.a.valid.token") is None
        assert decode_access_token("") is None
        assert decode_access_token("abc") is None

    def test_token_jti_unique(self):
        """测试每次生成的 jti（JWT ID）是唯一的"""
        tokens = [
            create_access_token({"sub": "1"}) for _ in range(10)
        ]
        jtis = {decode_access_token(t)["jti"] for t in tokens}
        assert len(jtis) == 10, f"jti 应唯一，但只有 {len(jtis)} 个不同值"


class TestPasswordHashing:
    """密码加密和验证测试"""

    @pytest.mark.skipif(
        "not _PASSLIB_BCRYPT_OK",
        reason="当前环境 bcrypt 5.x 与 passlib 1.7.4 不兼容，跳过密码哈希测试"
    )
    def test_hash_and_verify(self):
        """测试：哈希 -> 验证 闭环"""
        plain = "mySecret123"
        hashed = hash_password(plain)
        assert hashed != plain
        assert verify_password(plain, hashed) is True
        assert verify_password("wrongPassword", hashed) is False

    @pytest.mark.skipif(
        "not _PASSLIB_BCRYPT_OK",
        reason="当前环境 bcrypt 5.x 与 passlib 1.7.4 不兼容，跳过密码哈希测试"
    )
    def test_same_password_different_hash(self):
        """测试 bcrypt 加盐机制：相同密码每次哈希结果不同"""
        plain = "samePassword"
        hash1 = hash_password(plain)
        hash2 = hash_password(plain)
        assert hash1 != hash2, "bcrypt 应自动加盐，相同密码产生不同哈希"
        assert verify_password(plain, hash1)
        assert verify_password(plain, hash2)

    @pytest.mark.skipif(
        "not _PASSLIB_BCRYPT_OK",
        reason="当前环境 bcrypt 5.x 与 passlib 1.7.4 不兼容，跳过密码哈希测试"
    )
    def test_empty_password(self):
        """测试空密码处理"""
        hashed = hash_password("")


class TestTokenBlacklist:
    """Token 黑名单测试 — 验证函数可正常调用不崩溃"""

    async def test_blacklist_token_callable(self) -> None:
        """blacklist_token 可正常调用"""
        import uuid
        from backend.app.core.security import blacklist_token
        jti = uuid.uuid4().hex
        result = await blacklist_token(jti, 60)
        # 无论 Redis 是否可用，都不应抛异常
        assert result is True or result is False

    async def test_is_blacklisted_callable(self) -> None:
        """is_token_blacklisted 可正常调用"""
        import uuid
        from backend.app.core.security import is_token_blacklisted
        jti = f"definitely-not-blacklisted-{uuid.uuid4().hex}"
        result = await is_token_blacklisted(jti)
        # 无论 Redis 是否可用，都不应抛异常
        assert result is True or result is False
