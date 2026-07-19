"""
高级搜索 Page Object
封装搜索表单、结果表格、分页等
"""
from tests.ui.pages.base_page import BasePage


class SearchPage(BasePage):
    """高级搜索页面"""

    # ── CSS 选择器 ──────────────────────────────────────────
    KEYWORD_INPUT = "#sr-keyword"
    DEPARTMENT_DROPDOWN = "#sr-department"
    POSITION_DROPDOWN = "#sr-position"
    START_DATE_INPUT = "#sr-start-date"
    END_DATE_INPUT = "#sr-end-date"
    SORT_BY_DROPDOWN = "#sr-sort-by"
    SORT_ORDER_DROPDOWN = "#sr-sort-order"

    SEARCH_BTN = "#sr-search-btn"
    RESET_BTN = "#sr-reset-btn"

    RESULT_INFO = "#sr-result-info"
    RESULT_TABLE = "#sr-results"
    PAGINATION = "#sr-pagination"
    PAGINATOR = "#sr-paginator"

    # ── 导航 ────────────────────────────────────────────────

    def open(self, base_url: str) -> "SearchPage":
        self.goto(f"{base_url}/search")
        self.wait_for_selector(self.SEARCH_BTN, timeout=15_000)
        return self

    # ── 搜索表单 ────────────────────────────────────────────

    def fill_keyword(self, keyword: str) -> "SearchPage":
        self.fill(self.KEYWORD_INPUT, keyword)
        return self

    def select_department(self, dept: str) -> "SearchPage":
        self.page.select_option(self.DEPARTMENT_DROPDOWN, label=dept)
        return self

    def select_position(self, pos: str) -> "SearchPage":
        self.page.select_option(self.POSITION_DROPDOWN, label=pos)
        return self

    def fill_start_date(self, date_str: str) -> "SearchPage":
        self.fill(self.START_DATE_INPUT, date_str)
        return self

    def fill_end_date(self, date_str: str) -> "SearchPage":
        self.fill(self.END_DATE_INPUT, date_str)
        return self

    def select_sort_by(self, value: str) -> "SearchPage":
        self.page.select_option(self.SORT_BY_DROPDOWN, value=value)
        return self

    def select_sort_order(self, order: str) -> "SearchPage":
        self.page.select_option(self.SORT_ORDER_DROPDOWN, value=order)
        return self

    # ── 操作 ────────────────────────────────────────────────

    def click_search(self) -> "SearchPage":
        self.click(self.SEARCH_BTN)
        # 等待搜索结果加载（回调 + API 请求）
        try:
            self.page.wait_for_selector(
                f"{self.RESULT_INFO}, text=未找到匹配的记录",
                timeout=15_000,
            )
        except Exception:
            pass
        return self

    def click_reset(self) -> "SearchPage":
        self.click(self.RESET_BTN)
        return self

    def search_by_keyword(self, keyword: str) -> "SearchPage":
        """快捷搜索：输入关键词 → 搜索"""
        self.fill_keyword(keyword)
        self.click_search()
        return self

    # ── 结果 ────────────────────────────────────────────────

    def get_result_info(self) -> str:
        """获取 "共找到 X 条记录" 文本"""
        if self.page.locator(self.RESULT_INFO).count() == 0:
            return ""
        return self.get_text(self.RESULT_INFO)

    def get_result_count(self) -> int:
        """获取搜索结果数量（从 info 文本解析）"""
        info = self.get_result_info()
        import re
        match = re.search(r"(\d+)", info)
        return int(match.group(1)) if match else 0

    def has_results(self) -> bool:
        """是否有搜索结果"""
        return self.get_result_count() > 0

    def is_no_result_displayed(self) -> bool:
        """是否显示 '未找到匹配的记录'"""
        return self.is_visible("text=未找到匹配的记录", timeout=3_000)

    def get_result_table_data(self) -> list[dict]:
        """获取结果表格中的所有行数据"""
        rows = self.page.locator(f"{self.RESULT_TABLE} tbody tr")
        count = rows.count()
        result = []
        for i in range(count):
            cells = rows.nth(i).locator("td")
            cell_count = cells.count()
            row_data = {}
            for j in range(cell_count):
                # 从表头获取列名
                header = self.page.locator(
                    f"{self.RESULT_TABLE} thead th:nth-child({j + 1})"
                )
                col_name = header.inner_text() if header.count() > 0 else f"col_{j}"
                row_data[col_name] = cells.nth(j).inner_text()
            result.append(row_data)
        return result

    # ── 分页 ────────────────────────────────────────────────

    def go_to_page(self, page_num: int) -> "SearchPage":
        self.click(f"{self.PAGINATOR} >> text={page_num}")
        self.wait_for_timeout(1000)
        return self