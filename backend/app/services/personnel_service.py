"""
人员管理 — 业务逻辑层，数据以 Redmine Issue 形式存储在项目内
"""
from datetime import date as date_type
from typing import Optional, List, Dict, Any

from ..core.redmine_client import RedmineClient
from ..core.config import settings
from ..core import redis_client
from ..models.personnel import Personnel
from ..schemas.personnel import (
    PersonnelCreate,
    PersonnelUpdate,
    PersonnelResponse,
    PersonnelSearchRequest,
)
from ..utils.logger import get_logger

logger = get_logger(__name__)


class PersonnelService:
    """人员管理服务（基于 Redmine Issue）"""

    def __init__(self, redmine_client: RedmineClient):
        self.redmine = redmine_client

    # =========================================================================
    # 公开方法
    # =========================================================================

    async def create_personnel(self, data: PersonnelCreate) -> PersonnelResponse:
        """新增人员 → 在 Redmine 项目中创建一个 Issue（带分布式锁防并发重复）"""
        lock_key = f"lock:personnel:create:{data.employee_id}"
        lock_acquired = await redis_client.set_nx(lock_key, ttl=10)
        if not lock_acquired:
            logger.warning("获取创建锁失败，可能有并发请求 | employee_id=%s", data.employee_id)
            raise ValueError(f"人员编号 {data.employee_id} 正在被创建，请稍后重试")

        try:
            exists = await self._check_employee_id_exists(data.employee_id)
            if exists:
                logger.warning("新增人员失败：编号已存在 | employee_id=%s", data.employee_id)
                raise ValueError(f"人员编号 {data.employee_id} 已存在")

            payload = self._build_create_payload(data)
            logger.info("正在创建人员 | employee_id=%s | name=%s", data.employee_id, data.name)
            try:
                response = await self.redmine.create_issue(payload)
            except Exception as e:
                logger.error("Redmine 创建 Issue 失败 | employee_id=%s | error=%s", data.employee_id, str(e))
                raise RuntimeError(f"创建人员失败：{str(e)}") from e

            issue = response.get("issue", response)
            personnel = Personnel.from_redmine_issue(issue)
            logger.info("人员创建成功 | id=%s | employee_id=%s", personnel.id, personnel.employee_id)
            return personnel.to_response()
        finally:
            await redis_client.delete(lock_key)

    async def get_personnel_list(
        self, page: int = 1, size: int = 20,
        keyword: Optional[str] = None,
        department: Optional[str] = None,
        position: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> Dict[str, Any]:
        """查询人员列表（分页+筛选+排序）"""
        logger.info("查询人员列表 | page=%s | size=%s", page, size)

        filters = {}
        # keyword 不做 Redmine 服务端过滤（Redmine API 不支持 subject 模糊匹配），
        # 统一在内存中按 name / employee_id 进行模糊查找
        if department:
            filters["cf_6"] = department
        if position:
            filters["cf_7"] = position

        # 当存在需要内存过滤的条件时，一次拉取更多数据避免分页遗漏
        _need_memory_filter = bool(keyword or start_date or end_date)
        _fetch_limit = 100 if _need_memory_filter else min(size, 100)

        try:
            raw_response = await self.redmine.get_issues(
                project_id=settings.REDMINE_PROJECT_ID,
                page=1, limit=_fetch_limit, filters=filters if filters else None,
            )
        except Exception as e:
            logger.error("获取人员列表失败 | error=%s", str(e))
            raise RuntimeError(f"获取人员列表失败：{str(e)}") from e

        issues_data = raw_response.get("issues", [])

        personnel_list: List[Personnel] = []
        for issue_data in issues_data:
            try:
                personnel = Personnel.from_redmine_issue(issue_data)
                personnel_list.append(personnel)
            except Exception as e:
                logger.warning("单条数据转换失败 | issue_id=%s | error=%s", issue_data.get("id"), str(e))
                continue

        # 内存过滤（日期范围和关键词 Redmine 不支持服务端过滤，保留内存处理）
        if start_date:
            sd = date_type.fromisoformat(start_date) if isinstance(start_date, str) else start_date
            personnel_list = [p for p in personnel_list if p.start_datetime and p.start_datetime >= sd]
        if end_date:
            ed = date_type.fromisoformat(end_date) if isinstance(end_date, str) else end_date
            personnel_list = [p for p in personnel_list if p.start_datetime and p.start_datetime <= ed]
        if keyword:
            kw = keyword.lower()
            personnel_list = [p for p in personnel_list if kw in p.name.lower() or kw in p.employee_id.lower()]

        # 排序
        sort_field_map = {
            "employee_id": "employee_id", "name": "name", "gender": "gender",
            "age": "age", "department": "department", "position": "position",
            "hire_date": "start_datetime", "created_at": "create_datetime",
        }
        actual_field = sort_field_map.get(sort_by, "create_datetime")
        reverse = (sort_order == "desc")

        if actual_field in ("start_datetime", "create_datetime"):
            valid = [p for p in personnel_list if getattr(p, actual_field, None) is not None]
            none_items = [p for p in personnel_list if getattr(p, actual_field, None) is None]
            valid.sort(key=lambda p: getattr(p, actual_field), reverse=reverse)
            personnel_list = valid + none_items
        elif actual_field == "age":
            personnel_list.sort(key=lambda p: int(p.age) if p.age and p.age.isdigit() else 0, reverse=reverse)
        else:
            personnel_list.sort(key=lambda p: getattr(p, actual_field, "") or "", reverse=reverse)

        # 内存过滤后的实际总数
        filtered_total = len(personnel_list)

        # 内存分页
        start_idx = (page - 1) * size
        end_idx = start_idx + size
        paged = personnel_list[start_idx:end_idx]

        items = [p.to_response() for p in paged]
        return {"total": filtered_total, "page": page, "size": size, "items": items}

    async def search_personnel(self, search_data: PersonnelSearchRequest) -> Dict[str, Any]:
        """高级搜索"""
        start_str = search_data.start_date.isoformat() if search_data.start_date else None
        end_str = search_data.end_date.isoformat() if search_data.end_date else None
        return await self.get_personnel_list(
            page=search_data.page, size=search_data.size,
            keyword=search_data.keyword, department=search_data.department,
            position=search_data.position, start_date=start_str, end_date=end_str,
            sort_by=search_data.sort_by, sort_order=search_data.sort_order,
        )

    async def get_personnel_detail(self, personnel_id: int) -> PersonnelResponse:
        """查询人员详情"""
        logger.info("查询人员详情 | id=%s", personnel_id)
        try:
            response = await self.redmine.get_issue(personnel_id)
        except Exception as e:
            logger.error("查询详情失败 | id=%s | error=%s", personnel_id, str(e))
            raise ValueError(f"人员不存在 (ID: {personnel_id})") from e
        issue = response.get("issue", response)
        personnel = Personnel.from_redmine_issue(issue)
        return personnel.to_response()

    async def update_personnel(self, personnel_id: int, data: PersonnelUpdate) -> PersonnelResponse:
        """修改人员信息"""
        logger.info("修改人员 | id=%s | fields=%s", personnel_id,
                     list(data.model_dump(exclude_unset=True).keys()))

        try:
            response = await self.redmine.get_issue(personnel_id)
        except Exception as e:
            raise ValueError(f"人员不存在 (ID: {personnel_id})") from e

        issue = response.get("issue", response)
        existing = Personnel.from_redmine_issue(issue)

        update_dict = data.model_dump(exclude_unset=True)
        if "hire_date" in update_dict:
            update_dict["start_datetime"] = update_dict.pop("hire_date")
        for field, value in update_dict.items():
            if hasattr(existing, field):
                setattr(existing, field, value)

        payload = existing.to_redmine_payload()
        try:
            await self.redmine.update_issue(personnel_id, payload)
        except Exception as e:
            logger.error("更新 Issue 失败 | id=%s | error=%s", personnel_id, str(e))
            raise RuntimeError(f"更新人员失败：{str(e)}") from e

        return await self.get_personnel_detail(personnel_id)

    async def delete_personnel(self, personnel_id: int) -> None:
        """
        软删除：将 Issue 状态改为 5（已关闭）
        Redmine 默认状态: 1=新建 2=进行中 3=已解决 4=反馈 5=已关闭
        """
        logger.info("软删除人员 | id=%s", personnel_id)
        try:
            await self.redmine.update_issue(personnel_id, {"status_id": 5})
        except Exception as e:
            logger.error("删除人员失败 | id=%s | error=%s", personnel_id, str(e))
            raise RuntimeError(f"删除人员失败 (ID: {personnel_id})") from e

    async def batch_delete(self, ids: List[int]) -> int:
        """批量删除"""
        logger.info("批量删除 | ids=%s", ids)
        deleted = 0
        for pid in ids:
            try:
                await self.delete_personnel(pid)
                deleted += 1
            except Exception as e:
                logger.warning("批量删除-单条失败 | id=%s | error=%s", pid, str(e))
        return deleted

    async def get_departments(self) -> List[str]:
        """获取部门列表（去重）"""
        try:
            response = await self.redmine.get_issues(project_id=settings.REDMINE_PROJECT_ID, page=1, limit=100)
        except Exception:
            return []
        depts = set()
        for issue_data in response.get("issues", []):
            try:
                p = Personnel.from_redmine_issue(issue_data)
                if p.department:
                    depts.add(p.department)
            except Exception:
                continue
        return sorted(depts)

    async def get_positions(self) -> List[str]:
        """获取职位列表（去重）"""
        try:
            response = await self.redmine.get_issues(project_id=settings.REDMINE_PROJECT_ID, page=1, limit=100)
        except Exception:
            return []
        positions = set()
        for issue_data in response.get("issues", []):
            try:
                p = Personnel.from_redmine_issue(issue_data)
                if p.position:
                    positions.add(p.position)
            except Exception:
                continue
        return sorted(positions)

    # =========================================================================
    # 私有方法
    # =========================================================================

    async def _check_employee_id_exists(self, employee_id: str) -> bool:
        """通过 Issue 的 cf_1（employee_id）检查编号是否重复"""
        try:
            response = await self.redmine.get_issues(
                project_id=settings.REDMINE_PROJECT_ID,
                page=1, limit=1,
                filters={"cf_1": employee_id},
            )
            issues = response.get("issues", [])
            for iss in issues:
                for cf in iss.get("custom_fields", []):
                    if cf.get("id") == 1 and cf.get("value") == employee_id:
                        return True
            return False
        except Exception as e:
            logger.warning("检查编号重复出错 | employee_id=%s | error=%s", employee_id, str(e))
            return False

    def _build_create_payload(self, data: PersonnelCreate) -> Dict[str, Any]:
        """将 PersonnelCreate 转为 Redmine Issue 创建的 payload"""
        from ..models.custom_field import PersonnelFieldMapping

        return PersonnelFieldMapping.build_payload(
            {
                "employee_id": data.employee_id,
                "name": data.name,
                "gender": data.gender,
                "age": data.age,
                "phone": data.phone,
                "email": data.email,
                "department": data.department,
                "position": data.position,
                "start_datetime": data.hire_date.isoformat(),
            },
            project_id=settings.REDMINE_PROJECT_ID,
            include_meta=True,
        )

