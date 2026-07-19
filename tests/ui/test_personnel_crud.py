"""
人员管理crud模块测试
"""
import pytest


class TestCreatePersonnel:
    """
    新增人员
    """
    def test_create_personnel(self,logged_in_personnel_form,new_person_data:dict)->None:
        """
        填写表单->提交->验证成功
        :param logged_in_personnel_form:
        :param new_person_data:
        :return:
        """
        form_page = logged_in_personnel_form
        assert form_page.is_add_mode(),"应处于新增模式"
        form_page.fill_all_fields(new_person_data)
        form_page.submit()
