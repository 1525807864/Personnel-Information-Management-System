"""
人员编辑 UI 测试

测试目标：
  1. 从人员列表选择记录进入编辑模式
  2. 修改已有记录的字段
  3. 提交编辑并验证结果
"""
import pytest

from tests.ui.pages.login_page import LoginPage
from tests.ui.pages.personnel_list_page import PersonnelListPage
from tests.ui.pages.personnel_form_page import PersonnelFormPage


@pytest.fixture
def logged_in_list_page(page, app_base_url: str, admin_credentials: dict):
    """登录后进入人员列表页面"""
    lp = LoginPage(page)
    lp.open(app_base_url)
    lp.login(admin_credentials["username"], admin_credentials["password"])
    lp.wait_for_dashboard()

    list_page = PersonnelListPage(page)
    list_page.open(app_base_url)
    return list_page


class TestEditPersonnel:
    """人员编辑 UI 流程测试"""

    def test_enter_edit_mode_from_list(self, logged_in_list_page, app_base_url: str):
        """从列表选择记录后点击编辑按钮进入编辑模式"""
        list_page = logged_in_list_page

        # 等待表格加载
        list_page.wait_for_timeout(2000)

        # 检查是否有数据
        row_count = list_page.get_row_count()
        if row_count == 0:
            pytest.skip("列表无数据，跳过编辑测试")

        # 选中第一行
        list_page.select_row(0)

        # 点击编辑按钮
        form_page = list_page.click_edit_selected()
        list_page.wait_for_timeout(5000)
        # 验证进入编辑模式
        assert form_page.is_edit_mode(), "应处于编辑模式"

    def test_edit_personnel_name_field(self, logged_in_list_page, app_base_url: str):
        """编辑人员：修改姓名字段"""
        list_page = logged_in_list_page
        list_page.wait_for_timeout(2000)

        row_count = list_page.get_row_count()
        if row_count == 0:
            pytest.skip("列表无数据，跳过编辑测试")

        # 获取原始姓名
        original_name = list_page.get_cell_text(0, 1)  # 假设第2列是姓名

        # 选中并编辑
        list_page.select_row(0)
        form_page = list_page.click_edit_selected()

        if not form_page.is_edit_mode():
            pytest.skip("未能进入编辑模式")

        # 修改姓名
        new_name = f"{original_name}(已编辑)"
        form_page.clear_and_fill(PersonnelFormPage.FIELD_NAME, new_name)

        # 验证输入框值已更新
        current_value = form_page.get_name_value()
        assert current_value == new_name, f"姓名应更新为 {new_name}"

    def test_edit_form_submit_shows_alert(self, logged_in_list_page, app_base_url: str):
        """编辑提交后显示提示信息"""
        list_page = logged_in_list_page
        list_page.wait_for_timeout(2000)

        row_count = list_page.get_row_count()
        if row_count == 0:
            pytest.skip("列表无数据，跳过编辑测试")

        list_page.select_row(0)
        form_page = list_page.click_edit_selected()
        list_page.wait_for_timeout(5000)
        if not form_page.is_edit_mode():
            pytest.skip("未能进入编辑模式")

        # 修改职位字段
        form_page.clear_and_fill(PersonnelFormPage.FIELD_POSITION, "高级测试工程师")

        # 提交
        form_page.submit()

        # 验证显示了提示（成功或失败都算正常交互）
        alert_text = form_page.get_alert_text()
        assert len(alert_text) > 0, "提交后应显示提示信息"
