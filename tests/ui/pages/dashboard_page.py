"""
仪表盘Page Object
登录成功后的首页，包含导航卡片
"""
from tests.ui.pages.base_page import BasePage
from tests.ui.pages.login_page import LoginPage
from tests.ui.pages.personnel_form_page import PersonnelFormPage
from tests.ui.pages.personnel_list_page import PersonnelListPage
from tests.ui.pages.search_page import SearchPage
from tests.ui.pages.import_page import ImportPage

class DashboardPage(BasePage):
    """仪表盘首页"""

    # ── 文本标识 ────────────────────────────────────────────
    PAGE_HEADING = "text=欢迎使用人员信息管理系统"
    SIDEBAR = "#sidebar"

    # ── 导航链接（侧边栏）───────────────────────────────────
    NAV_PERSONNEL = "text=人员列表"
    NAV_SEARCH = "text=高级搜索"
    NAV_ADD = "text=新增人员"
    NAV_IMPORT = "text=数据导入"
    NAV_HOME = "text=首页"

    # ── 卡片按钮 ────────────────────────────────────────────
    CARD_PERSONNEL = "text=进入人员列表"
    CARD_SEARCH = "text=进入搜索"
    CARD_IMPORT = "text=进入导入"

    # ── 顶部导航栏 ──────────────────────────────────────────
    LOGOUT_BTN = "#logout-btn"
    USERNAME_DISPLAY = "#username-dash"

    # ── 验证 ────────────────────────────────────────────────

    def is_loaded(self) -> bool:
        """验证仪表盘已加载"""
        return self.is_visible(self.PAGE_HEADING)

    def get_welcome_text(self) -> str:
        return self.get_text(self.PAGE_HEADING)

    def get_displayed_username(self) -> str:
        return self.get_text(self.USERNAME_DISPLAY)

    # ── 侧边栏导航 ──────────────────────────────────────────

    def go_to_personnel_list(self) -> "PersonnelListPage":

        self.click_text("人员列表")
        self.wait_for_timeout(1500)
        return PersonnelListPage(self.page)

    def go_to_search(self) -> "SearchPage":

        self.click_text("高级搜索")
        self.wait_for_timeout(1500)
        return SearchPage(self.page)

    def go_to_add_personnel(self) -> "PersonnelFormPage":

        self.click_text("新增人员")
        self.wait_for_timeout(1500)
        return PersonnelFormPage(self.page)

    def go_to_import(self) -> "ImportPage":

        self.click_text("数据导入")
        self.wait_for_timeout(1500)
        return ImportPage(self.page)

    # ── 卡片快捷入口 ────────────────────────────────────────

    def click_card_personnel(self) -> "PersonnelListPage":

        self.click(self.CARD_PERSONNEL)
        self.wait_for_timeout(1500)
        return PersonnelListPage(self.page)

    def click_card_search(self) -> "SearchPage":

        self.click(self.CARD_SEARCH)
        self.wait_for_timeout(1500)
        return SearchPage(self.page)

    def click_card_import(self) -> "ImportPage":

        self.click(self.CARD_IMPORT)
        self.wait_for_timeout(1500)
        return ImportPage(self.page)

    # ── 退出登录 ────────────────────────────────────────────

    def logout(self) -> "LoginPage":

        self.click(self.LOGOUT_BTN)
        self.wait_for_selector("#logout-btn",timeout=10_000)
        return LoginPage(self.page)
