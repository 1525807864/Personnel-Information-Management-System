"""
RedmineUser 模型单元测试
"""
from backend.app.models.user import RedmineUser


class TestRedmineUserFromApi:
    """测试 from_redmine_api 类方法"""

    def test_parses_top_level_user_key(self) -> None:
        raw = {
            "user": {
                "id": 1, "login": "admin",
                "firstname": "Test", "lastname": "Admin",
                "mail": "admin@test.com", "admin": True, "status": 1,
                "custom_fields": [],
            }
        }
        user = RedmineUser.from_redmine_api(raw)
        assert user.id == 1
        assert user.login == "admin"
        assert user.admin is True

    def test_parses_flat_data(self) -> None:
        raw = {
            "id": 2, "login": "user1",
            "firstname": "Normal", "lastname": "User",
            "custom_fields": [],
        }
        user = RedmineUser.from_redmine_api(raw)
        assert user.id == 2

    def test_custom_fields_with_firstname_key(self) -> None:
        """模型使用 cf["firstname"] 作为映射 key"""
        raw = {
            "user": {
                "id": 3, "login": "test",
                "custom_fields": [
                    {"id": 1, "firstname": "部门", "value": "技术部"},
                    {"id": 2, "firstname": "职位", "value": "工程师"},
                ],
            }
        }
        user = RedmineUser.from_redmine_api(raw)
        assert user.custom_fields == {"部门": "技术部", "职位": "工程师"}

    def test_empty_custom_fields(self) -> None:
        raw = {"user": {"id": 4, "login": "test", "custom_fields": []}}
        user = RedmineUser.from_redmine_api(raw)
        assert user.custom_fields == {}


class TestRedmineUserFullName:
    """测试 full_name 属性"""

    def test_chinese_name(self) -> None:
        user = RedmineUser(id=1, login="u", lastname="李", firstname="四")
        assert user.full_name == "李四"

    def test_english_name(self) -> None:
        user = RedmineUser(id=1, login="u", lastname="Smith", firstname="John")
        assert user.full_name == "SmithJohn"

    def test_empty_name(self) -> None:
        user = RedmineUser(id=1, login="u")
        assert user.full_name == ""


class TestRedmineUserToDict:
    """测试 to_dict 方法"""

    def test_full_dict(self) -> None:
        user = RedmineUser(
            id=1, login="admin", firstname="Test", lastname="User",
            email="a@b.com", admin=True, status=1,
        )
        d = user.to_dict()
        assert d["id"] == 1
        assert d["login"] == "admin"
        assert d["email"] == "a@b.com"
        assert d["admin"] is True
        assert "custom_fields" in d
