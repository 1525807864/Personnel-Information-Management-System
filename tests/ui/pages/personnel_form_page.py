"""
人员表单 Page Object
封装新增/编辑人员的表单元素和操作
"""
from tests.ui.pages.base_page import BasePage


class PersonnelFormPage(BasePage):
    """人员表单页面（新增 / 编辑共用）"""

    # ── CSS 选择器 ──────────────────────────────────────────
    PAGE_TITLE = "#form-page-title"

    # 表单字段（id 格式：form-{field_name}）
    FIELD_EMPLOYEE_ID = "#form-employee_id"
    FIELD_NAME = "#form-name"
    FIELD_GENDER = "#form-gender"
    FIELD_AGE = "#form-age"
    FIELD_PHONE = "#form-phone"
    FIELD_EMAIL = "#form-email"
    FIELD_DEPARTMENT = "#form-department"
    FIELD_POSITION = "#form-position"
    FIELD_HIRE_DATE = "#form-hire_date"

    # 按钮
    SUBMIT_BTN = "#form-submit-btn"
    RESET_BTN = "#form-reset-btn"
    BACK_BTN = "text=返回列表"

    # 提示
    ALERT_DIV = "#form-alert"

    # 隐藏字段
    EDIT_ID_STORE = "#form-edit-id"

    # ── 导航 ────────────────────────────────────────────────

    def open(self, base_url: str) -> "PersonnelFormPage":
        """打开新增人员页面"""
        self.goto(f"{base_url}/add")
        self.wait_for_load_state("networkidle")
        return self

    # ── 页面状态 ────────────────────────────────────────────

    def get_page_title(self) -> str:
        return self.get_text(self.PAGE_TITLE)

    def is_add_mode(self) -> bool:
        """是否处于新增模式"""
        return "新增" in self.get_page_title()

    def is_edit_mode(self) -> bool:
        """是否处于编辑模式"""
        return "编辑" in self.get_page_title()

    def wait_for_edit_form_load(self, timeout: int = 10_000) -> None:
        """等待编辑表单加载完成（标题变为'编辑人员'或字段被填充）"""
        try:
            self.page.wait_for_selector(
                f"{self.PAGE_TITLE}",
                timeout=timeout,
                state="attached",
            )
            self.page.wait_for_function(
                f"document.querySelector('{self.PAGE_TITLE}')?.innerText?.includes('编辑')",
                timeout=timeout,
            )
        except Exception:
            pass

    # ── 表单填写 ────────────────────────────────────────────

    def fill_employee_id(self, value: str) -> "PersonnelFormPage":
        self.fill(self.FIELD_EMPLOYEE_ID, value)
        return self

    def fill_name(self, value: str) -> "PersonnelFormPage":
        self.fill(self.FIELD_NAME, value)
        return self

    def select_gender(self, gender: str) -> "PersonnelFormPage":
        """选择性别：男/女"""
        self.click(self.FIELD_GENDER)
        self.page.locator(f"text={gender}").click()
        return self

    def fill_age(self, value: int) -> "PersonnelFormPage":
        self.fill(self.FIELD_AGE, str(value))
        return self

    def fill_phone(self, value: str) -> "PersonnelFormPage":
        self.fill(self.FIELD_PHONE, value)
        return self

    def fill_email(self, value: str) -> "PersonnelFormPage":
        self.fill(self.FIELD_EMAIL, value)
        return self

    def fill_department(self, value: str) -> "PersonnelFormPage":
        self.fill(self.FIELD_DEPARTMENT, value)
        return self

    def fill_position(self, value: str) -> "PersonnelFormPage":
        self.fill(self.FIELD_POSITION, value)
        return self

    def fill_hire_date(self, value: str) -> "PersonnelFormPage":
        """填写入职日期，格式 YYYY-MM-DD"""
        self.fill(self.FIELD_HIRE_DATE, value)
        return self

    # ── 组合操作 ────────────────────────────────────────────

    def fill_all_fields(self, data: dict) -> "PersonnelFormPage":
        """一键填写所有字段"""
        self.fill_employee_id(data["employee_id"])
        self.fill_name(data["name"])
        self.select_gender(data["gender"])
        self.fill_age(data["age"])
        self.fill_phone(data["phone"])
        self.fill_email(data["email"])
        self.fill_department(data["department"])
        self.fill_position(data["position"])
        self.fill_hire_date(data["hire_date"])
        return self

    def submit(self) -> "PersonnelFormPage":
        self.click(self.SUBMIT_BTN)
        try:
            self.page.wait_for_selector(f"{self.ALERT_DIV} .alert", timeout=10_000)
        except Exception:
            pass
        return self

    def reset(self) -> "PersonnelFormPage":
        self.click(self.RESET_BTN)
        return self

    def go_back(self) -> "PersonnelListPage":
        from tests.ui.pages.personnel_list_page import PersonnelListPage
        self.click_text("返回列表")
        self.wait_for_url("**/personnel")
        return PersonnelListPage(self.page)

    # ── 结果读取 ────────────────────────────────────────────

    def get_alert_text(self) -> str:
        """获取提示信息"""
        return self.get_text(self.ALERT_DIV)

    def is_success_alert(self) -> bool:
        """是否显示成功提示"""
        try:
            self.page.wait_for_selector(
                f"{self.ALERT_DIV} .alert-success", timeout=5_000
            )
            return True
        except Exception:
            return False

    def is_error_alert(self) -> bool:
        """是否显示错误提示"""
        try:
            self.page.wait_for_selector(
                f"{self.ALERT_DIV} .alert-danger", timeout=5_000
            )
            return True
        except Exception:
            return False

    # ── 读取当前值 ──────────────────────────────────────────

    def get_employee_id_value(self) -> str:
        return self.get_input_value(self.FIELD_EMPLOYEE_ID)

    def get_name_value(self) -> str:
        return self.get_input_value(self.FIELD_NAME)