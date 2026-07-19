"""
数据导入 API 路由

提供文件上传导入和错误数据导出两个端点。
所有端点都需要 Bearer Token 认证（通过 get_current_user 依赖注入）。

端点列表：
  POST /api/v1/import/              — 上传并批量导入人员数据文件
  POST /api/v1/import/export-errors — 导出错误数据行（返回 CSV 文件下载）
"""
import io
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from ...core.dependencies import get_current_user, get_redmine_client
from ...core.redmine_client import RedmineClient
from ...schemas.common import ApiResponse
from ...schemas.import_schemas import ImportResultData
from ...services.import_service import ImportService
from ...utils.exceptions import FileImportException
from ...utils.logger import get_logger

logger = get_logger(__name__)


# 创建路由实例，prefix 直接定义在这里（与 personnel.py 保持一致的模式）
router = APIRouter(prefix="/api/v1/import", tags=["数据导入"])


def _get_service(redmine_client: RedmineClient = Depends(get_redmine_client)) -> ImportService:
    """依赖注入：创建 ImportService 实例"""
    return ImportService(redmine_client)


# ---------------------------------------------------------------------------
# POST /api/v1/import/
# 前端 import_page.py 的 do_import 回调向此端点发送 multipart/form-data 请求：
#   files: {"file": (filename, file_content)}
#   data:  {"strategy": "skip" | "overwrite" | "terminate"}
#
# 响应格式：ApiResponse[ImportResultData]
# 前端读取 data.total_rows / success_count / failed_count / duplicate_count
# 以及 data.error_messages 列表来渲染结果卡片和错误详情
# ---------------------------------------------------------------------------

@router.post(
    "/",
    response_model=ApiResponse[ImportResultData],
    summary="上传并批量导入人员数据",
)
async def import_personnel_file(
    file: UploadFile = File(..., description="待导入的 CSV 或 Excel 文件"),
    strategy: str = Form("skip", description="重复处理策略: skip / overwrite / terminate"),
    service: ImportService = Depends(_get_service),
    _current_user: dict = Depends(get_current_user),
):
    """
    上传并批量导入人员数据

    处理流程（由 ImportService.import_file 完成）：
      1. 根据文件扩展名选择 pandas 读取器（CSV / Excel）
      2. 列名映射（中文 → 英文）
      3. 逐行 Pydantic 校验（复用 PersonnelCreate 的所有 validator）
      4. 分页查询 Redmine 已有数据，构建 employee_id → issue_id 映射表
      5. 按策略逐行写入（创建新 Issue 或更新已有 Issue）
      6. 汇总统计结果并返回

    认证要求：需要在请求头中携带有效的 Bearer Token
    """
    # --- 读取上传文件的原始字节 ---
    try:
        file_content = await file.read()
    except Exception as e:
        logger.error("读取上传文件失败: %s", e)
        raise HTTPException(status_code=400, detail="无法读取上传文件，请重试")

    if not file_content:
        raise HTTPException(status_code=400, detail="上传的文件内容为空，请检查文件")

    # 获取原始文件名（用于判断格式：.csv / .xlsx / .xls）
    filename = file.filename or "unknown.csv"

    # --- 调用导入服务 ---
    try:
        result = await service.import_file(file_content, filename, strategy)
    except FileImportException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.exception("导入过程发生未预期错误: %s", e)
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")

    # --- 构建响应消息 ---
    msg_parts = [f"导入完成：共 {result.total_rows} 条"]
    if result.success_count:
        msg_parts.append(f"成功 {result.success_count} 条")
    if result.failed_count:
        msg_parts.append(f"失败 {result.failed_count} 条")
    if result.duplicate_count:
        msg_parts.append(f"重复 {result.duplicate_count} 条")

    return ApiResponse(code=200, message="，".join(msg_parts), data=result)


# ---------------------------------------------------------------------------
# POST /api/v1/import/export-errors
# 前端在导入完成后，如果存在错误行，可调用此端点下载仅包含错误行的 CSV 文件。
# 用户下载后修正数据并重新导入。
#
# 请求参数：
#   file:       原始上传文件（与导入时相同的文件）
#   error_rows: 逗号分隔的错误行号，例如 "3,7,12"
#
# 返回值：CSV 文件流（浏览器自动触发下载）
# ---------------------------------------------------------------------------

@router.post(
    "/export-errors",
    summary="导出错误数据行（返回 CSV 文件下载）",
    response_class=StreamingResponse,
)
async def export_error_rows(
    file: UploadFile = File(..., description="原始上传文件（与导入时相同的文件）"),
    error_rows: str = Form(..., description="逗号分隔的错误行号列表，例如 '3,7,12'"),
    _current_user: dict = Depends(get_current_user),
):
    """
    导出错误数据行

    接收原始文件和错误行号列表（逗号分隔的字符串），返回仅包含错误行的 CSV 文件。
    文件名格式：原文件名_错误数据.csv（带 BOM，确保 Excel 正确识别中文）

    前端调用示例（javascript）：
      const formData = new FormData();
      formData.append("file", originalFile);
      formData.append("error_rows", "3,7,12");
      fetch("/api/v1/import/export-errors", { method: "POST", body: formData });
    """
    # --- 解析错误行号 ---
    try:
        row_numbers = [int(r.strip()) for r in error_rows.split(",") if r.strip()]
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="error_rows 格式错误，应为逗号分隔的整数，例如 '3,7,12'",
        )

    if not row_numbers:
        raise HTTPException(status_code=400, detail="error_rows 不能为空")

    # --- 读取上传文件 ---
    try:
        file_content = await file.read()
    except Exception as e:
        logger.error("读取上传文件失败: %s", e)
        raise HTTPException(status_code=400, detail="无法读取上传文件")

    if not file_content:
        raise HTTPException(status_code=400, detail="上传的文件内容为空")

    filename = file.filename or "unknown.csv"

    # --- 调用静态方法导出错误行 ---
    try:
        csv_bytes = ImportService.export_error_rows(file_content, filename, row_numbers)
    except FileImportException as e:
        raise HTTPException(status_code=400, detail=e.message)

    # --- 返回 CSV 文件流 ---
    original_name = filename.rsplit(".", 1)[0]
    download_name = f"{original_name}_错误数据.csv"

    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv; charset=utf-8-sig",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{download_name}",
        },
    )
