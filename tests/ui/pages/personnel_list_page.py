"""
人员列表 Page Object
封装表格、分页、搜索、批量操作、弹窗等
"""
from tests.ui.pages.base_page import BasePage


class PersonnelListPage(BasePage):
    """人员列表页面"""

    # ── CSS 选择器 ──────────────────────────────────────────
    SEARCH_INPUT = "#pl-search-input"
    SEARCH_BTN = "#pl-search-btn"
    ADD_BTN = "#pl-add-btn"
    BATCH_DELETE_BTN = "#pl-batch-delete-btn"
    VIEW_DETAIL_BTN = "#pl-view-detail-btn"
    EDIT_SELECTED_BTN = "#pl-edit-selected-btn"
    DATA_TABLE = "#pl-data-table"
    PAGINATION = "#pl-pagination-component"
    STATUS_DIV = "#pl-status"

    # 删除确认弹窗
    DELETE_MODAL = "#pl-delete-modal"
    DELETE_CONFIRM_BTN = "#pl-delete-confirm"
    DELETE_CANCEL_BTN = "#pl-delete-cancel"
    DELETE_MESSAGE = "#pl-delete-message"

    # 详情弹窗
    DETAIL_MODAL = "#pl-detail-modal"
    DETAIL_BODY = "#pl-detail-body"
    DETAIL_CLOSE_BTN = "#pl-detail-close"

    # ── 导航 ────────────────────────────────────────────────

    def open(self, base_url: str) -> "PersonnelListPage":
        self.goto(f"{base_url}/personnel")
        # 使用 state="attached" 因为 DataTable 在 dbc.Spinner 包裹下
        # 加载期间可能处于 hidden 状态，但 DOM 中已存在即可操作
        self.wait_for_selector(self.DATA_TABLE, timeout=15_000, state="attached")
        return self

    # ── 搜索 ────────────────────────────────────────────────

    def search(self, keyword: str) -> "PersonnelListPage":
        self.fill(self.SEARCH_INPUT, keyword)
        self.click(self.SEARCH_BTN)
        self.wait_for_timeout(1000)  # 等待表格刷新
        return self

    # ── 表格操作 ────────────────────────────────────────────

    _COL_COUNT = 10  # Dash DataTable 列数（含复选框列 + 9 个数据列）

    def get_row_count(self) -> int:
        """获取当前表格数据行数"""
        checkboxes = self.page.locator(
            f"{self.DATA_TABLE} input[type='checkbox']"
        )
        return checkboxes.count()

    def get_cell_text(self, row_index: int, column_index: int) -> str:
        """获取指定数据列单元格文本（0-indexed，不含复选框列）"""
        # Dash DataTable 内部使用 <table><tr><td> 结构，前2行是表头
        # column_index + 1 跳过复选框列
        cells = self.page.locator(f"{self.DATA_TABLE} td")
        idx = (row_index + 2) * self._COL_COUNT + column_index + 1
        target = cells.nth(idx)
        target.wait_for(state="attached", timeout=10_000)
        return target.inner_text()

    def select_row(self, row_index: int) -> "PersonnelListPage":
        """勾选指定行（0-indexed），通过点击 Dash DataTable 行选中复选框"""
        # 使用 force=True 绕过可见性检查（表格可能在虚拟滚动中）
        checkbox = self.page.locator(
            f"{self.DATA_TABLE} input[type='checkbox']"
        ).nth(row_index)
        checkbox.check(force=True)
        self.wait_for_timeout(500)
        return self

    def select_rows(self, *row_indices: int) -> "PersonnelListPage":
        """勾选多行"""
        for idx in row_indices:
            self.select_row(idx)
        return self

    def get_selected_count(self) -> int:
        """获取已选中行数"""
        checkboxes = self.page.locator(
            f"{self.DATA_TABLE} input[type='checkbox']:checked"
        )
        return checkboxes.count()

    def is_row_present(self, text: str) -> bool:
        """表格中是否存在包含指定文本的行"""
        return self.is_visible(f"text={text}", timeout=3_000)

    # ── 分页 ────────────────────────────────────────────────

    def go_to_page(self, page_num: int) -> "PersonnelListPage":
        """点击分页器跳转到指定页"""
        self.click(f"{self.PAGINATION} >> text={page_num}")
        self.wait_for_timeout(1000)
        return self

    def get_current_page(self) -> int:
        """获取当前页码"""
        active = self.page.locator(f"{self.PAGINATION} .active a")
        if active.count() > 0:
            return int(active.inner_text())
        return 1

    # ── 按钮操作 ────────────────────────────────────────────

    def click_add(self) -> "PersonnelFormPage":
        from tests.ui.pages.personnel_form_page import PersonnelFormPage
        self.click(self.ADD_BTN)
        self.wait_for_url("**/add")
        return PersonnelFormPage(self.page)

    def click_batch_delete(self) -> "PersonnelListPage":
        """点击批量删除按钮（需要先勾选行）"""
        self.click(self.BATCH_DELETE_BTN)
        return self

    def click_view_detail(self) -> "PersonnelListPage":
        """点击查看详情按钮"""
        self.click(self.VIEW_DETAIL_BTN)
        return self

    def click_edit_selected(self) -> "PersonnelFormPage":
        """点击编辑选中按钮 → 跳转到编辑表单"""
        from tests.ui.pages.personnel_form_page import PersonnelFormPage
        self.click(self.EDIT_SELECTED_BTN)
        self.wait_for_url("**/add")
        form_page = PersonnelFormPage(self.page)
        form_page.wait_for_edit_form_load()
        return form_page

    # ── 删除弹窗 ────────────────────────────────────────────

    def confirm_delete(self) -> "PersonnelListPage":
        """在删除确认弹窗中点击确认"""
        self.click(self.DELETE_CONFIRM_BTN)
        self.wait_for_timeout(1000)
        return self

    def cancel_delete(self) -> "PersonnelListPage":
        """在删除确认弹窗中点击取消"""
        self.click(self.DELETE_CANCEL_BTN)
        return self

    def get_delete_message(self) -> str:
        return self.get_text(self.DELETE_MESSAGE)

    def is_delete_modal_open(self) -> bool:
        return self.is_visible(self.DELETE_MODAL)

    # ── 详情弹窗 ────────────────────────────────────────────

    def close_detail_modal(self) -> "PersonnelListPage":
        self.click(self.DETAIL_CLOSE_BTN)
        return self

    def get_detail_text(self) -> str:
        return self.get_text(self.DETAIL_BODY)

    # ── 状态提示 ────────────────────────────────────────────

    def get_status_text(self) -> str:
        return self.get_text(self.STATUS_DIV)

    # ── 批量操作按钮状态 ────────────────────────────────────

    def is_batch_delete_enabled(self) -> bool:
        btn = self.page.locator(self.BATCH_DELETE_BTN)
        return not btn.is_disabled()

    def is_edit_button_enabled(self) -> bool:
        btn = self.page.locator(self.EDIT_SELECTED_BTN)
        return not btn.is_disabled()

    def is_view_button_enabled(self) -> bool:
        btn = self.page.locator(self.VIEW_DETAIL_BTN)
        return not btn.is_disabled()