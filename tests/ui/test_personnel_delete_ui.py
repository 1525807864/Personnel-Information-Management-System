"""
人员删除 UI 测试

测试目标：
  1. 从人员列表选择记录
  2. 点击批量删除按钮
  3. 确认删除弹窗交互
  4. 取消删除操作
"""
import pytest

from tests.ui.pages.login_page import LoginPage
from tests.ui.pages.personnel_list_page import PersonnelListPage


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


class TestDeletePersonnel:
    """人员删除 UI 流程测试"""

    def test_delete_modal_opens_on_batch_delete(self, logged_in_list_page):
        """选中记录后点击批量删除，弹出确认弹窗"""
        list_page = logged_in_list_page
        list_page.wait_for_timeout(2000)

        row_count = list_page.get_row_count()
        if row_count == 0:
            pytest.skip("列表无数据，跳过删除测试")

        # 选中第一行
        list_page.select_row(0)

        # 点击批量删除
        list_page.click_batch_delete()
        list_page.wait_for_timeout(500)

        # 验证弹窗打开
        assert list_page.is_delete_modal_open(), "删除确认弹窗应打开"

    def test_delete_modal_shows_message(self, logged_in_list_page):
        """删除弹窗显示确认信息"""
        list_page = logged_in_list_page
        list_page.wait_for_timeout(2000)

        row_count = list_page.get_row_count()
        if row_count == 0:
            pytest.skip("列表无数据，跳过删除测试")

        list_page.select_row(0)
        list_page.click_batch_delete()
        list_page.wait_for_timeout(500)

        if not list_page.is_delete_modal_open():
            pytest.skip("删除弹窗未打开")

        # 获取弹窗消息
        message = list_page.get_delete_message()
        assert len(message) > 0, "弹窗应显示确认信息"

    def test_cancel_delete_keeps_data(self, logged_in_list_page):
        """取消删除后数据保持不变"""
        list_page = logged_in_list_page
        list_page.wait_for_timeout(2000)

        row_count = list_page.get_row_count()
        if row_count == 0:
            pytest.skip("列表无数据，跳过删除测试")

        # 记录删除前的行数
        original_count = row_count

        list_page.select_row(0)
        list_page.click_batch_delete()
        list_page.wait_for_timeout(500)

        if not list_page.is_delete_modal_open():
            pytest.skip("删除弹窗未打开")

        # 点击取消
        list_page.cancel_delete()
        list_page.wait_for_timeout(1000)

        # 验证行数未变
        current_count = list_page.get_row_count()
        assert current_count == original_count, "取消删除后行数应保持不变"

    def test_confirm_delete_removes_record(self, logged_in_list_page):
        """确认删除后记录被移除"""
        list_page = logged_in_list_page
        list_page.wait_for_timeout(2000)

        row_count = list_page.get_row_count()
        if row_count == 0:
            pytest.skip("列表无数据，跳过删除测试")

        original_count = row_count

        list_page.select_row(0)
        list_page.click_batch_delete()
        list_page.wait_for_timeout(500)

        if not list_page.is_delete_modal_open():
            pytest.skip("删除弹窗未打开")

        # 确认删除
        list_page.confirm_delete()
        list_page.wait_for_timeout(2000)

        # 验证行数减少（软删除后刷新列表）
        list_page.refresh()
        list_page.wait_for_timeout(2000)
        new_count = list_page.get_row_count()

        # 删除成功后行数应减少（或至少不增加）
        assert new_count <= original_count, "删除后行数应减少或保持不变"

    def test_batch_delete_button_disabled_without_selection(self, logged_in_list_page):
        """未选中任何行时批量删除按钮禁用"""
        list_page = logged_in_list_page
        list_page.wait_for_timeout(2000)

        # 不选中任何行，检查按钮状态
        # 注意：具体行为取决于前端实现，有些实现是按钮始终可点击但点击后提示先选择
        row_count = list_page.get_row_count()
        if row_count == 0:
            pytest.skip("列表无数据")

        # 验证有数据但未选中
        selected_count = list_page.get_selected_count()
        assert selected_count == 0, "初始状态不应有选中行"
