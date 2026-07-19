import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeout
from tests.ui.pages.base_page import BasePage
from tests.ui.pages.login_page import LoginPage
from tests.ui.pages.dashboard_page import DashboardPage

class TestLogout:
    """
    退出登录场景
    """
    def test_logout_redirects_to_login(self,page,app_base_url:str,admin_credentials:dict
                                       )->None:
        """
        登录->退出->回到登录页
        :param page:
        :param app_base_url:
        :param admin_credentials:
        :return:
        """
        lp = LoginPage(page)
        lp.open(app_base_url)
        lp.login(admin_credentials["username"],admin_credentials["password"])
        lp.wait_for_dashboard()

        #退出
        dashboard = DashboardPage(page)
        dashboard.logout()

        #验证回到登录页
        assert "/" in page.url,f"应回到登录页,当前页面URL:{page.url}"
