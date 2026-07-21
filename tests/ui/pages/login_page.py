from ..pages.base_page import BasePage


class LoginPage(BasePage):
    """登录页面"""

    # ── CSS 选择器 ──────────────────────────────────────────
    USERNAME_INPUT = "#login-username"
    PASSWORD_INPUT = "#login-password"
    SUBMIT_BTN = "#login-btn"
    ERROR_DIV = "#login-error"

    # ── 导航 ────────────────────────────────────────────────

    def open(self, base_url: str) -> "LoginPage":
        """打开登录页面"""
        self.goto(f"{base_url}/login")
        self.wait_for_selector(self.USERNAME_INPUT, timeout=15_000)
        return self

    # ── 元素操作 ────────────────────────────────────────────

    def fill_username(self, username: str) -> "LoginPage":
        self.fill(self.USERNAME_INPUT, username)
        return self

    def fill_password(self, password: str) -> "LoginPage":
        self.fill(self.PASSWORD_INPUT, password)
        return self

    def click_submit(self) -> "LoginPage":
        self.click(self.SUBMIT_BTN)
        return self

    # ── 组合操作（业务流程）──────────────────────────────────

    def login(self, username: str, password: str) -> "LoginPage":
        """完整登录流程：填写 → 提交"""
        self.fill_username(username)
        self.fill_password(password)
        self.click_submit()
        return self

    # ── 结果读取 ────────────────────────────────────────────

    def get_error_text(self) -> str:
        """获取登录错误提示文本"""
        try:
            return self.get_text(self.ERROR_DIV)
        except Exception:
            return ""

    def is_error_visible(self) -> bool:
        """错误提示是否可见"""
        return self.is_visible(self.ERROR_DIV, timeout=3_000)

    # ── 等待 ────────────────────────────────────────────────

    def wait_for_dashboard(self, timeout: int = 30_000) -> None:
        """等待登录成功后跳转到仪表盘"""
        try:
            self.wait_for_text("欢迎使用人员信息管理系统", timeout=timeout)
        except Exception:
            raise AssertionError("登录超时，未跳转到仪表盘")

    def wait_for_url_dashboard(self, timeout: int = 15_000) -> None:
        """等待 URL 变为 /dashboard"""
        self.wait_for_url("**/dashboard", timeout=timeout)


