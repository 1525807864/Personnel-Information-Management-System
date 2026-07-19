import logging
import os
import time
from typing import Optional, List

from playwright.sync_api import Page, Locator, TimeoutError as PlaywrightTimeout


class BasePage:
    """所有 Page Object 的基类"""

    SCREENSHOT_DIR = "test-results/screenshots"

    def __init__(self, page: Page):
        self.page = page
        self._logger = logging.getLogger(self.__class__.__name__)

    # ── 导航 ───────────────────────────────────────────────

    def goto(self, url: str, wait_until: str = "domcontentloaded") -> None:
        self.page.goto(url, wait_until=wait_until)
        self._logger.info("[NAV] goto %s", url)

    def refresh(self) -> None:
        self.page.reload(wait_until="domcontentloaded")

    def go_back(self) -> None:
        self.page.go_back(wait_until="domcontentloaded")

    # ── 等待 ───────────────────────────────────────────────

    def wait_for_url(self, url_or_pattern: str, timeout: int = 30_000) -> None:
        self.page.wait_for_url(url_or_pattern, timeout=timeout)

    def wait_for_selector(
        self,
        selector: str,
        timeout: int = 10_000,
        state: str = "visible",
    ) -> None:
        self.page.wait_for_selector(selector, timeout=timeout, state=state)

    def wait_for_text(self, text: str, timeout: int = 10_000) -> bool:
        self.page.locator(f"text={text}").first.wait_for(timeout=timeout)
        return True

    def wait_for_load_state(self, state: str = "domcontentloaded") -> None:
        self.page.wait_for_load_state(state)

    def wait_for_timeout(self, ms: int = 1000) -> None:
        """固定等待（用于等待动画/回调执行，谨慎使用）"""
        self.page.wait_for_timeout(ms)

    # ── 点击 ───────────────────────────────────────────────

    def click(self, selector: str, timeout: int = 10_000) -> None:
        self.wait_for_selector(selector, timeout=timeout)
        self.page.click(selector)
        self._logger.info("[CLICK] %s", selector)

    def click_text(self, text: str, timeout: int = 10_000) -> None:
        """点击包含指定文本的元素"""
        self.page.locator(f"text={text}").first.click(timeout=timeout)
        self._logger.info("[CLICK] text=%s", text)

    # ── 输入 ───────────────────────────────────────────────

    def fill(self, selector: str, value: str, timeout: int = 10_000) -> None:
        self.wait_for_selector(selector, timeout=timeout)
        self.page.fill(selector, value)
        self._logger.info("[FILL] %s = %s", selector, repr(value))

    def clear_and_fill(self, selector: str, value: str) -> None:
        self.page.locator(selector).clear()
        self.page.locator(selector).fill(value)

    # ── 下拉框 ─────────────────────────────────────────────

    def select_option(self, selector: str, value: str) -> None:
        self.page.select_option(selector, value)
        self._logger.info("[SELECT] %s = %s", selector, value)

    # ── 勾选 ───────────────────────────────────────────────

    def check(self, selector: str) -> None:
        self.page.check(selector)
        self._logger.info("[CHECK] %s", selector)

    def uncheck(self, selector: str) -> None:
        self.page.uncheck(selector)

    # ── 读取 ───────────────────────────────────────────────

    def get_text(self, selector: str) -> str:
        try:
            self.wait_for_selector(selector, timeout=5_000)
        except Exception:
            pass
        locator = self.page.locator(selector)
        if locator.count() == 0:
            return ""
        return locator.inner_text()

    def get_input_value(self, selector: str) -> str:
        return self.page.locator(selector).input_value()

    def get_texts(self, selector: str) -> List[str]:
        """获取所有匹配元素的文本列表"""
        return self.page.locator(selector).all_inner_texts()

    def is_visible(self, selector: str, timeout: int = 5_000) -> bool:
        try:
            self.page.wait_for_selector(selector, timeout=timeout, state="visible")
            return True
        except PlaywrightTimeout:
            return False

    def is_hidden(self, selector: str, timeout: int = 5_000) -> bool:
        try:
            self.page.wait_for_selector(selector, timeout=timeout, state="hidden")
            return True
        except PlaywrightTimeout:
            return False

    def count(self, selector: str) -> int:
        return self.page.locator(selector).count()

    # ── 截图 ───────────────────────────────────────────────

    def take_screenshot(self, name: str = "screenshot") -> str:
        os.makedirs(self.SCREENSHOT_DIR, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        path = os.path.join(self.SCREENSHOT_DIR, f"{name}_{timestamp}.png")
        self.page.screenshot(path=path, full_page=True)
        self._logger.info("[SCREENSHOT] %s", path)
        return path

    # ── 弹窗/对话框 ────────────────────────────────────────

    def accept_dialog(self) -> None:
        self.page.on("dialog", lambda d: d.accept())

    def get_dialog_message(self) -> Optional[str]:
        msg = None

        def _capture(dialog):
            nonlocal msg
            msg = dialog.message
            dialog.dismiss()

        self.page.on("dialog", _capture)
        return msg

    # ── 滚动 ───────────────────────────────────────────────

    def scroll_to_bottom(self) -> None:
        self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

    def scroll_into_view(self, selector: str) -> None:
        self.page.locator(selector).scroll_into_view_if_needed()