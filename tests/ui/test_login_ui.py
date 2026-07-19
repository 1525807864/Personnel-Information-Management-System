"""
登录页面UI测试
使用playwright来进行前端的UI测试
测试场景:
    1、进入登录页面
    2、输入正确的用户名和密码
    3、点击登录按钮
    4、验证跳转到仪表盘页面
"""

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeout
from backend.app.utils.logger import get_logger
from tests.ui.pages.login_page import LoginPage

logger = get_logger(__name__)



@pytest.fixture
def login_page(app_base_url: str, page) -> LoginPage:
    return LoginPage(page).open(app_base_url)


class TestLoginSuccess:
    @pytest.mark.parametrize("username,password", [("admin", "admin123")])
    def test_login_submit(self, login_page: LoginPage, username, password):
        login_page.fill_username(username)
        login_page.fill_password(password)
        login_page.click_submit()

        # 等待登录结果：成功 → 跳转 /dashboard，失败 → 显示错误
        try:
            login_page.wait_for_dashboard(timeout=25_000)
            logger.info("登录成功，已跳转到 /dashboard")
        except PlaywrightTimeout:
            error_text = login_page.get_error_text()
            login_page.take_screenshot("login_failure")
            pytest.fail(
                f"登录失败，未能跳转到 /dashboard\n"
                f"当前URL: {login_page.page.url}\n"
                f"错误信息: {error_text or '无'}"
            )

        # 二次确认：仪表盘页面核心元素可见
        login_page.wait_for_dashboard(timeout=10_000)

class TestLoginFailure:
    """
    登录失败场景测试
    """
    def test_wrong_password(self, login_page: LoginPage)->None:
        """
        错误密码->显示错误,不跳转
        :param login_page:
        :return:
        """
        login_page.fill_username("admin")
        login_page.fill_password("admin123456789")
        login_page.click_submit()
        login_page.wait_for_timeout(2000)

        assert login_page.is_error_visible(),"应显示错误提示"



