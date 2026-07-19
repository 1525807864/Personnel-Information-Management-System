"""
人员管理 API 路由
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body, status

from ...core.dependencies import get_current_user, get_redmine_client
from ...core.redmine_client import RedmineClient
from ...schemas.common import ApiResponse, PaginationData
from ...schemas.personnel import (
    PersonnelCreate,
    PersonnelUpdate,
    PersonnelResponse,
    PersonnelSearchRequest,
    BatchDeleteResponse,
)
from ...services.personnel_service import PersonnelService
from ...utils.logger import get_logger

logger = get_logger(__name__)

# prefix 已经是 /api/v1/personnel，路由用 "/" 表示 /api/v1/personnel/
router = APIRouter(prefix="/api/v1/personnel", tags=["人员管理"])


def _get_service(redmine_client: RedmineClient = Depends(get_redmine_client)) -> PersonnelService:
    """依赖注入：创建 PersonnelService 实例"""
    return PersonnelService(redmine_client)


# =============================================================================
# 2.1 新增人员  POST /api/v1/personnel/
# =============================================================================

@router.post(
    "/",
    response_model=ApiResponse[PersonnelResponse],
    status_code=status.HTTP_200_OK,
    summary="新增人员",
)
async def create_personnel(
    data: PersonnelCreate,
    current_user: dict = Depends(get_current_user),
    service: PersonnelService = Depends(_get_service),
):
    logger.info("API-新增人员 | operator=%s | employee_id=%s | name=%s",
                current_user["username"], data.employee_id, data.name)
    try:
        result = await service.create_personnel(data)
    except ValueError as e:
        logger.warning("API-新增人员-业务校验失败 | %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": 409, "message": str(e), "data": None},
        )
    except RuntimeError as e:
        logger.error("API-新增人员-系统错误 | %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": 500, "message": str(e), "data": None},
        )
    return ApiResponse(code=200, message="新增成功", data=result)


# =============================================================================
# 2.2 查询人员列表  GET /api/v1/personnel/
# =============================================================================

@router.get(
    "/",
    response_model=ApiResponse[PaginationData[PersonnelResponse]],
    summary="查询人员列表",
)
async def get_personnel_list(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    keyword: str = Query(None, description="搜索关键词"),
    department: str = Query(None, description="部门筛选"),
    position: str = Query(None, description="职位筛选"),
    start_date: str = Query(None, description="入职开始日期"),
    end_date: str = Query(None, description="入职结束日期"),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", description="排序方式 asc/desc"),
    current_user: dict = Depends(get_current_user),
    service: PersonnelService = Depends(_get_service),
):
    logger.info("API-查询人员列表 | operator=%s | page=%s", current_user["username"], page)
    try:
        result = await service.get_personnel_list(
            page=page, size=size, keyword=keyword,
            department=department, position=position,
            start_date=start_date, end_date=end_date,
            sort_by=sort_by, sort_order=sort_order,
        )
    except RuntimeError as e:
        logger.error("API-查询人员列表-系统错误 | %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": 500, "message": str(e), "data": None},
        )
    pagination = PaginationData[PersonnelResponse](
        total=result["total"], page=result["page"],
        size=result["size"], items=result["items"],
    )
    return ApiResponse(code=200, message="success", data=pagination)


# =============================================================================
# 2.3 高级搜索  POST /api/v1/personnel/search
# =============================================================================

@router.post(
    "/search",
    response_model=ApiResponse[PaginationData[PersonnelResponse]],
    summary="高级搜索",
)
async def search_personnel(
    search_data: PersonnelSearchRequest,
    current_user: dict = Depends(get_current_user),
    service: PersonnelService = Depends(_get_service),
):
    logger.info("API-高级搜索 | operator=%s | keyword=%s", current_user["username"], search_data.keyword)
    try:
        result = await service.search_personnel(search_data)
    except RuntimeError as e:
        logger.error("API-高级搜索-系统错误 | %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": 500, "message": str(e), "data": None},
        )
    pagination = PaginationData[PersonnelResponse](
        total=result["total"], page=result["page"],
        size=result["size"], items=result["items"],
    )
    return ApiResponse(code=200, message="success", data=pagination)


# =============================================================================
# 2.8 获取部门列表  GET /api/v1/personnel/departments
# =============================================================================

@router.get(
    "/departments",
    response_model=ApiResponse[List[str]],
    summary="获取部门列表",
)
async def get_departments(
    current_user: dict = Depends(get_current_user),
    service: PersonnelService = Depends(_get_service),
):
    logger.info("API-获取部门列表 | operator=%s", current_user["username"])
    departments = await service.get_departments()
    return ApiResponse(code=200, message="success", data=departments)


# =============================================================================
# 2.9 获取职位列表  GET /api/v1/personnel/positions
# =============================================================================

@router.get(
    "/positions",
    response_model=ApiResponse[List[str]],
    summary="获取职位列表",
)
async def get_positions(
    current_user: dict = Depends(get_current_user),
    service: PersonnelService = Depends(_get_service),
):
    logger.info("API-获取职位列表 | operator=%s", current_user["username"])
    positions = await service.get_positions()
    return ApiResponse(code=200, message="success", data=positions)


# =============================================================================
# 2.7 批量删除  POST /api/v1/personnel/batch
# =============================================================================

@router.post(
    "/batch",
    response_model=ApiResponse[BatchDeleteResponse],
    summary="批量删除",
)
async def batch_delete_personnel(
    ids: List[int] = Body(..., min_items=1, description="要删除的人员ID列表"),
    current_user: dict = Depends(get_current_user),
    service: PersonnelService = Depends(_get_service),
):
    logger.info("API-批量删除 | operator=%s | count=%s", current_user["username"], len(ids))
    deleted_count = await service.batch_delete(ids)
    if deleted_count == len(ids):
        msg = f"成功删除 {deleted_count} 条记录"
    elif deleted_count > 0:
        msg = f"部分删除成功：{deleted_count}/{len(ids)} 条记录"
    else:
        msg = "删除失败"
    return ApiResponse(
        code=200, message=msg,
        data=BatchDeleteResponse(deleted_count=deleted_count),
    )


# =============================================================================
# 以下路由含 {personnel_id}，必须在固定路径之后定义
# =============================================================================

# 2.4 查询人员详情  GET /api/v1/personnel/{personnel_id}

@router.get(
    "/{personnel_id}",
    response_model=ApiResponse[PersonnelResponse],
    summary="查询人员详情",
)
async def get_personnel_detail(
    personnel_id: int = Path(..., ge=1, description="人员ID"),
    current_user: dict = Depends(get_current_user),
    service: PersonnelService = Depends(_get_service),
):
    logger.info("API-查询人员详情 | operator=%s | id=%s", current_user["username"], personnel_id)
    try:
        result = await service.get_personnel_detail(personnel_id)
    except ValueError as e:
        logger.warning("API-查询人员详情-不存在 | id=%s", personnel_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 404, "message": str(e), "data": None},
        )
    return ApiResponse(code=200, message="success", data=result)


# 2.5 修改人员  PUT /api/v1/personnel/{personnel_id}

@router.put(
    "/{personnel_id}",
    response_model=ApiResponse[PersonnelResponse],
    summary="修改人员信息",
)
async def update_personnel(
    personnel_id: int = Path(..., ge=1, description="人员ID"),
    data: PersonnelUpdate = Body(..., description="要更新的字段"),
    current_user: dict = Depends(get_current_user),
    service: PersonnelService = Depends(_get_service),
):
    logger.info("API-修改人员 | operator=%s | id=%s | fields=%s",
                current_user["username"], personnel_id,
                list(data.model_dump(exclude_unset=True).keys()))
    try:
        result = await service.update_personnel(personnel_id, data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 404, "message": str(e), "data": None},
        )
    except RuntimeError as e:
        logger.error("API-修改人员-系统错误 | %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": 500, "message": str(e), "data": None},
        )
    return ApiResponse(code=200, message="修改成功", data=result)


# 2.6 删除人员  DELETE /api/v1/personnel/{personnel_id}

@router.delete(
    "/{personnel_id}",
    response_model=ApiResponse[None],
    summary="删除人员（软删除）",
)
async def delete_personnel(
    personnel_id: int = Path(..., ge=1, description="人员ID"),
    current_user: dict = Depends(get_current_user),
    service: PersonnelService = Depends(_get_service),
):
    logger.info("API-删除人员 | operator=%s | id=%s", current_user["username"], personnel_id)
    try:
        await service.delete_personnel(personnel_id)
    except RuntimeError as e:
        logger.error("API-删除人员-系统错误 | %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": 500, "message": str(e), "data": None},
        )
    return ApiResponse(code=200, message="删除成功", data=None)
