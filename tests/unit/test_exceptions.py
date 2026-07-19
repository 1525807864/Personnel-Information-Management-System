"""
自定义异常类单元测试

测试目标：
  1. 各异常类的继承关系
  2. 异常实例的 code 和 message 属性
  3. 异常的可捕获性
"""
import pytest

from backend.app.utils.exceptions import (
    BusinessException,
    DuplicateDataException,
    UnauthorizedException,
    NotFoundException,
    ValidationException,
    FileImportException,
    AccountLockedException,
)


class TestBusinessException:
    """测试异常基类"""

    def test_default_code(self):
        """默认状态码为 400"""
        ex = BusinessException("错误")
        assert ex.code == 400
        assert ex.message == "错误"
        assert str(ex) == "错误"

    def test_custom_code(self):
        """自定义状态码"""
        ex = BusinessException("自定义错误", code=418)
        assert ex.code == 418

    def test_is_exception(self):
        """应继承自 Exception，可被 try/except 捕获"""
        with pytest.raises(BusinessException) as exc_info:
            raise BusinessException("测试异常")
        assert exc_info.value.message == "测试异常"


class TestExceptionHierarchy:
    """测试异常继承关系和各自的状态码"""

    @pytest.mark.parametrize("exc_class, expected_code, default_msg", [
        (DuplicateDataException,  409, "数据已存在"),
        (UnauthorizedException,   401, "未授权访问"),
        (NotFoundException,       404, "资源不存在"),
        (ValidationException,     422, "数据校验失败"),
        (FileImportException,     400, "文件导入失败"),
        (AccountLockedException,  423, "账户已被锁定，请30分钟后重试"),
    ])
    def test_exception_code_and_message(self, exc_class, expected_code, default_msg):
        """各异常类应提供正确的状态码和默认消息"""
        ex = exc_class()
        assert ex.code == expected_code
        assert ex.message == default_msg

        ex = exc_class("自定义")
        assert ex.code == expected_code
        assert ex.message == "自定义"

    @pytest.mark.parametrize("exc_class", [
        DuplicateDataException,
        UnauthorizedException,
        NotFoundException,
        ValidationException,
        FileImportException,
        AccountLockedException,
    ])
    def test_is_business_exception(self, exc_class):
        """所有子类应可被 BusinessException 捕获"""
        with pytest.raises(BusinessException):
            raise exc_class()
