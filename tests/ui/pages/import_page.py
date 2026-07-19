"""
数据导入 Page Object
封装文件上传、策略选择、导入执行、结果读取
"""
import os
from tests.ui.pages.base_page import BasePage


class ImportPage(BasePage):
    """数据导入页面"""

    # ── CSS 选择器 ──────────────────────────────────────────
    UPLOAD_COMPONENT = "#import-upload"
    UPLOAD_INPUT = "#import-upload input[type='file']"
    FILE_NAME_DISPLAY = "#import-filename"

    STRATEGY_RADIO = "#import-strategy"
    STRATEGY_SKIP = "text=跳过重复数据"
    STRATEGY_OVERWRITE = "text=覆盖已有数据"
    STRATEGY_TERMINATE = "text=遇到重复终止"

    IMPORT_BTN = "#import-btn"
    PROGRESS_DIV = "#import-progress"
    RESULT_DIV = "#import-result"

    # ── 导航 ────────────────────────────────────────────────

    def open(self, base_url: str) -> "ImportPage":
        self.goto(f"{base_url}/import")
        self.wait_for_selector(self.UPLOAD_COMPONENT, timeout=15_000)
        return self

    # ── 文件上传 ────────────────────────────────────────────

    def upload_file(self, file_path: str) -> "ImportPage":
        """上传文件（通过 <input type='file'> 直接设置文件路径）"""
        self.page.locator(self.UPLOAD_INPUT).set_input_files(file_path)
        self.wait_for_timeout(500)
        return self

    def get_uploaded_filename(self) -> str:
        """获取已选择文件的显示文本"""
        try:
            self.page.wait_for_selector(self.FILE_NAME_DISPLAY, timeout=5_000, state="visible")
            return self.get_text(self.FILE_NAME_DISPLAY)
        except Exception:
            return ""

    def is_file_selected(self) -> bool:
        """是否已选择文件"""
        text = self.get_uploaded_filename()
        return "已选择文件" in text or len(text) > 0

    # ── 策略选择 ────────────────────────────────────────────

    def select_strategy_skip(self) -> "ImportPage":
        self.click(self.STRATEGY_SKIP)
        return self

    def select_strategy_overwrite(self) -> "ImportPage":
        self.click(self.STRATEGY_OVERWRITE)
        return self

    def select_strategy_terminate(self) -> "ImportPage":
        self.click(self.STRATEGY_TERMINATE)
        return self

    # ── 导入操作 ────────────────────────────────────────────

    def click_import(self) -> "ImportPage":
        """点击开始导入按钮"""
        self.click(self.IMPORT_BTN)
        self.wait_for_timeout(3000)  # 等待后端处理
        return self

    def is_import_button_enabled(self) -> bool:
        """导入按钮是否可点击"""
        btn = self.page.locator(self.IMPORT_BTN)
        return not btn.is_disabled()

    # ── 结果读取 ────────────────────────────────────────────

    def get_result_stat(self, label: str) -> str:
        """获取统计卡片中的数值（label: '总计行数', '成功导入', '导入失败', '重复数据'）"""
        card = self.page.locator(f"text={label}")
        if card.count() > 0:
            parent = card.locator("..")
            heading = parent.locator("h5")
            if heading.count() > 0:
                return heading.inner_text()
        return "0"

    def get_total_rows(self) -> int:
        text = self.get_result_stat("总计行数")
        return self._parse_number(text)

    def get_success_count(self) -> int:
        text = self.get_result_stat("成功导入")
        return self._parse_number(text)

    def get_failed_count(self) -> int:
        text = self.get_result_stat("导入失败")
        return self._parse_number(text)

    def get_duplicate_count(self) -> int:
        text = self.get_result_stat("重复数据")
        return self._parse_number(text)

    def is_import_success_displayed(self) -> bool:
        """导入结果区域是否已显示"""
        return self.is_visible(self.RESULT_DIV, timeout=5_000)

    def get_error_messages(self) -> list[str]:
        """获取错误详情列表"""
        errors = self.page.locator(f"{self.RESULT_DIV} ul li")
        if errors.count() == 0:
            return []
        return errors.all_inner_texts()

    # ── 内部 ────────────────────────────────────────────────

    @staticmethod
    def _parse_number(text: str) -> int:
        import re
        match = re.search(r"\d+", text)
        return int(match.group()) if match else 0

    # ── 测试数据生成 ────────────────────────────────────────

    @staticmethod
    def create_test_csv(file_path: str, rows: list[dict] = None) -> str:
        """创建测试用的 CSV 文件"""
        import csv
        if rows is None:
            rows = [
                {"人员编号": "TEST001", "姓名": "测试一", "性别": "男", "年龄": "25",
                 "手机号": "13800138001", "邮箱": "test1@test.com",
                 "部门": "技术部", "职位": "工程师", "入职日期": "2024-01-01"},
            ]
        os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)
        with open(file_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        return file_path