"""
数据导入服务

负责解析上传的 CSV/Excel 文件 → 字段映射 → 逐行校验 → 重复检查 → 按策略写入 Redmine。
支持三种重复数据处理策略：skip（跳过）、overwrite（覆盖）、terminate（终止导入）。

整体处理流程：
  1. 根据文件扩展名判断格式，用 pandas 读取为 DataFrame
  2. 将中文列名映射为 Personnel 模型对应的英文字段名
  3. 逐行校验字段格式（复用 PersonnelCreate 的 Pydantic 校验规则）
  4. 批量分页查询 Redmine 中已有的人员编号，构建 employee_id → issue_id 映射表
  5. 根据策略处理每一行：
     - skip:      遇到重复编号 → 跳过该行，记录 skipped_count
     - overwrite: 遇到重复编号 → 调用 Redmine update_issue 更新已有记录
     - terminate: 遇到重复编号 → 立即停止，已处理的行不回滚
  6. 汇总统计结果并返回 ImportResultData
"""
import io
from typing import Dict, List, Tuple

import pandas as pd
from pydantic import ValidationError

from ..core.config import settings
from ..core.redmine_client import RedmineClient
from ..schemas.personnel import PersonnelCreate
from ..schemas.import_schemas import ImportErrorDetail, ImportResultData
from ..utils.exceptions import FileImportException
from ..utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# 中文列名 → 英文字段名 映射表
# 前端 import_page.py 提示用户使用中文列名，因此优先支持中文列名。
# 同时也兼容英文列名，方便有技术背景的用户直接使用英文字段名。
# ---------------------------------------------------------------------------
COLUMN_MAPPING: Dict[str, str] = {
    # 中文列名（主要支持）
    "人员编号": "employee_id",
    "姓名":    "name",
    "性别":    "gender",
    "年龄":    "age",
    "手机号":  "phone",
    "邮箱":    "email",
    "部门":    "department",
    "职位":    "position",
    "入职日期": "hire_date",
    # 英文列名（兼容）
    "employee_id": "employee_id",
    "name":         "name",
    "gender":       "gender",
    "age":          "age",
    "phone":        "phone",
    "email":        "email",
    "department":   "department",
    "position":     "position",
    "hire_date":    "hire_date",
}

# 所有必填字段列表（与 PersonnelCreate 的必填字段保持一致）
REQUIRED_FIELDS = [
    "employee_id", "name", "gender", "age",
    "phone", "email", "department", "position", "hire_date",
]


class ImportService:
    """
    数据导入服务

    通过依赖注入获取 RedmineClient 实例，所有人员数据的读写最终都通过 Redmine API 完成。
    RedmineClient 的所有方法都是异步的，因此本服务的核心方法也统一为异步。
    """

    def __init__(self, redmine_client: RedmineClient):
        """
        Args:
            redmine_client: Redmine API 客户端，用于人员记录的增/改/查操作
        """
        self.redmine = redmine_client

    # ------------------------------------------------------------------
    # 公开方法：import_file — 前端 POST /api/v1/import/ → 调用此方法
    # ------------------------------------------------------------------

    async def import_file(
        self,
        file_content: bytes,
        filename: str,
        strategy: str = "skip",
    ) -> ImportResultData:
        """
        执行完整的文件导入流程

        Args:
            file_content: 上传文件的原始字节内容
            filename:     原始文件名（如 "人员数据.xlsx"），用于判断格式
            strategy:     重复处理策略，可选值：skip / overwrite / terminate
                         非法值会自动降级为 "skip"

        Returns:
            ImportResultData: 包含总数、成功数、失败数、重复数、跳过数、覆盖数、错误详情

        Raises:
            FileImportException: 文件解析失败或内容为空
        """
        # --- 参数归一化 ---
        strategy = strategy.lower().strip()
        if strategy not in ("skip", "overwrite", "terminate"):
            logger.warning("未知策略 '%s'，降级为 'skip'", strategy)
            strategy = "skip"

        # --- 第1步：解析文件为 DataFrame ---
        df = self._parse_file(file_content, filename)

        if df.empty:
            raise FileImportException("文件中没有可读取的数据行，请检查文件内容")

        # --- 第2步：映射列名（中文 → 英文）---
        df = self._map_columns(df)

        # --- 第3步：逐行 Pydantic 校验 ---
        valid_rows, error_details = self._validate_rows(df)

        # --- 第4步：批量查询 Redmine 已有数据，构建 employee_id → issue_id 映射 ---
        existing_map = await self._fetch_existing_employee_ids()

        # --- 第5步：按策略逐行写入 Redmine ---
        result = await self._process_rows(
            valid_rows=valid_rows,
            error_details=error_details,
            existing_map=existing_map,
            strategy=strategy,
            total_rows=len(df),
        )

        logger.info(
            "导入完成 | 总数=%d | 成功=%d | 失败=%d | 重复=%d | 跳过=%d | 覆盖=%d",
            result.total_rows, result.success_count, result.failed_count,
            result.duplicate_count, result.skipped_count, result.overwritten_count,
        )
        return result

    # ------------------------------------------------------------------
    # 私有方法：文件解析（同步，仅做 pandas 操作）
    # ------------------------------------------------------------------

    def _parse_file(self, file_content: bytes, filename: str) -> pd.DataFrame:
        """
        根据文件扩展名选择 pandas 读取器解析文件

        支持格式：
          - .csv       → pd.read_csv(encoding="utf-8-sig"，兼容 UTF-8 BOM 头)
          - .xlsx/.xls → pd.read_excel()

        Raises:
            FileImportException: 文件格式不支持 或 解析失败
        """
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

        try:
            if ext == "csv":
                # utf-8-sig 可自动处理 UTF-8 BOM 头（Excel 导出 CSV 时常带 BOM）
                return pd.read_csv(io.BytesIO(file_content), encoding="utf-8-sig")

            elif ext in ("xlsx", "xls"):
                # Excel 文件使用 read_excel（不是 read_csv）
                return pd.read_excel(io.BytesIO(file_content))

            else:
                raise FileImportException(
                    f"不支持的文件格式 '.{ext}'，请上传 CSV (.csv) 或 Excel (.xlsx / .xls) 文件"
                )
        except FileImportException:
            raise
        except Exception as e:
            logger.error("文件解析失败: %s", e)
            raise FileImportException(f"文件解析失败，请检查文件格式是否正确: {str(e)}")

    # ------------------------------------------------------------------
    # 私有方法：列名映射（同步）
    # ------------------------------------------------------------------

    def _map_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        将 DataFrame 的列名从中文（或英文）统一映射为标准英文字段名

        处理逻辑：
          1. 去除列名首尾空格
          2. 查找 COLUMN_MAPPING 映射表进行重命名
          3. 无法识别的列名保留原样（不影响处理，只是不会被校验到）
          4. 删除所有列值均为空的空行
          5. 缺失的必填列自动补充为空列（避免后续校验时 KeyError）

        Raises:
            FileImportException: 映射后没有任何有效数据行
        """
        # 去除列名首尾空格（用户可能在 Excel 中不小心加了空格）
        df.columns = [str(col).strip() for col in df.columns]

        # 中文列名 → 英文字段名
        df.rename(columns=COLUMN_MAPPING, inplace=True)

        # 删除完全为空的数据行（用户可能在 Excel 中留了空行）
        df.dropna(how="all", inplace=True)
        df.reset_index(drop=True, inplace=True)

        # 补充缺失的必填字段列（值为空字符串，后续 Pydantic 校验会捕获这些缺失）
        for field in REQUIRED_FIELDS:
            if field not in df.columns:
                df[field] = ""

        # 注意：空值检查放在 for 循环外面，不是里面
        if df.empty:
            raise FileImportException("文件映射后没有有效数据，请检查列名是否正确")

        return df

    # ------------------------------------------------------------------
    # 私有方法：逐行 Pydantic 校验（同步）
    # ------------------------------------------------------------------

    def _validate_rows(
        self, df: pd.DataFrame
    ) -> Tuple[List[dict], List[ImportErrorDetail]]:
        """
        对 DataFrame 的每一行进行字段级校验

        校验方式：将每行数据转为 dict，尝试用 PersonnelCreate(**row_dict) 做 Pydantic 校验。
        这样做的好处是复用 schema 中已有的所有 validator（手机号正则、年龄范围、性别枚举、
        邮箱格式、入职日期不晚于今天等）。

        Args:
            df: 已映射列名的 DataFrame

        Returns:
            (valid_rows, error_details):
              - valid_rows:    校验通过的行数据列表，每项为 dict，可直接用于构建 Redmine payload
              - error_details: 校验失败行的 ImportErrorDetail 列表
        """
        valid_rows: List[dict] = []
        error_details: List[ImportErrorDetail] = []

        for idx, row in df.iterrows():
            # 行号从1开始（idx 是 reset_index 后的0-based索引）
            row_num = int(idx) + 1

            # 将 pandas Series 转为普通 dict，并把 NaN 替换为 None 方便 Pydantic 处理
            row_dict = row.where(pd.notna(row), None).to_dict()

            # pandas 读取 Excel/CSV 时会自动推断类型，纯数字字段（手机号等）
            # 会被转为 int64/numpy 数值类型，但 Pydantic 的 str 字段不做隐式转换，
            # 收到 int 会直接报 "Input should be a valid string"。因此需要提前转换。
            for str_field in ("phone", "employee_id", "department", "position"):
                val = row_dict.get(str_field)
                if val is not None and not isinstance(val, str):
                    row_dict[str_field] = str(val)

            # 提取员工编号用于错误报告（可能为 None）
            employee_id = row_dict.get("employee_id")

            try:
                # 使用 PersonnelCreate schema 进行 Pydantic 校验
                # 如果所有字段都符合规则，这里不会抛异常
                PersonnelCreate(**row_dict)
                valid_rows.append(row_dict)

            except ValidationError as e:
                # Pydantic 校验失败 → 收集所有字段的错误信息
                error_msgs: List[str] = []
                for error in e.errors():
                    # error 结构: {"loc": ("field_name",), "msg": "错误描述", "type": "..."}
                    field_name = error.get("loc", ("unknown",))[0]
                    error_msg = error.get("msg", "未知错误")
                    error_msgs.append(f"[{field_name}] {error_msg}")

                reason = "；".join(error_msgs)
                error_details.append(
                    ImportErrorDetail(
                        row=row_num,
                        employee_id=str(employee_id) if employee_id else None,
                        reason=reason,
                    )
                )

        return valid_rows, error_details

    # ------------------------------------------------------------------
    # 私有方法：获取已有人员编号 → issue_id 映射（异步，需调 Redmine API）
    # ------------------------------------------------------------------

    async def _fetch_existing_employee_ids(self) -> Dict[str, int]:
        """
        从 Redmine 获取当前项目下所有未删除人员记录的 编号→issue_id 映射

        实现方式：分页查询 Redmine issues，从每条 issue 的 custom_fields 中
        提取 cf_1（即 employee_id），构建 {employee_id: issue_id} 字典。

        RedmineClient.get_issues 默认只返回 status_id=open 的记录，
        因此已被软删除的记录不会出现在映射表中，导入时不会误判为重复。

        如果 Redmine API 查询失败，返回空映射表（降级：所有记录视为新增），
        不会阻塞导入流程。

        Returns:
            Dict[str, int]: key=人员编号, value=Redmine issue ID
        """
        existing_map: Dict[str, int] = {}
        page = 1

        try:
            while True:
                resp = await self.redmine.get_issues(
                    project_id=settings.REDMINE_PROJECT_ID,
                    page=page,
                    limit=100,
                )
                issues = resp.get("issues", [])
                if not issues:
                    break

                for issue in issues:
                    for cf in issue.get("custom_fields", []):
                        if cf.get("id") == 1:
                            emp_id = str(cf.get("value", "")).strip()
                            if emp_id:
                                existing_map[emp_id] = issue["id"]
                            break

                # 如果返回数量小于 limit，说明已经是最后一页
                if len(issues) < 100:
                    break
                page += 1

        except Exception as e:
            # 查询失败不阻塞导入流程，降级为空映射表
            logger.warning("查询已有人员数据失败，将跳过重复检查: %s", e)

        logger.info("已加载 %d 条已有人员编号用于重复检查", len(existing_map))
        return existing_map

    # ------------------------------------------------------------------
    # 私有方法：按策略逐行写入 Redmine（异步）
    # ------------------------------------------------------------------

    async def _process_rows(
        self,
        valid_rows: List[dict],
        error_details: List[ImportErrorDetail],
        existing_map: Dict[str, int],
        strategy: str,
        total_rows: int,
    ) -> ImportResultData:
        """
        遍历所有校验通过的行，根据重复策略执行创建或更新操作

        三种策略的行为：
          skip:
            重复 → 跳过，记录 skipped_count + duplicate_count
            不重复 → 创建新 Redmine Issue
          overwrite:
            重复 → 更新已有 Issue，记录 overwritten_count + duplicate_count
            不重复 → 创建新 Redmine Issue
          terminate:
            重复 → 立即返回结果（已处理的行不回滚）
            不重复 → 创建新 Redmine Issue

        Redmine API 调用失败的异常会被捕获并转为 error_detail，
        不会中断整个导入流程。只有 terminate 策略下遇到重复才会提前终止。
        """
        success = 0
        skipped = 0
        overwritten = 0
        duplicate = 0

        for row_data in valid_rows:
            employee_id = str(row_data.get("employee_id", "")).strip()

            # --- 检查是否与已有数据重复 ---
            if employee_id in existing_map:
                duplicate += 1

                if strategy == "skip":
                    skipped += 1
                    error_details.append(
                        ImportErrorDetail(
                            row=0,
                            employee_id=employee_id,
                            reason=f"人员编号 '{employee_id}' 已存在，策略为 skip，已跳过",
                        )
                    )
                    continue

                elif strategy == "overwrite":
                    issue_id = existing_map[employee_id]
                    try:
                        payload = self._build_payload(row_data, for_update=True)
                        await self.redmine.update_issue(issue_id, payload)
                        overwritten += 1
                        success += 1
                    except Exception as e:
                        error_details.append(
                            ImportErrorDetail(
                                row=0,
                                employee_id=employee_id,
                                reason=f"覆盖更新失败 (issue_id={issue_id}): {str(e)}",
                            )
                        )
                    continue

                elif strategy == "terminate":
                    error_details.append(
                        ImportErrorDetail(
                            row=0,
                            employee_id=employee_id,
                            reason=f"人员编号 '{employee_id}' 已存在，策略为 terminate，导入已终止",
                        )
                    )
                    return self._build_result(
                        total_rows, success, len(error_details),
                        duplicate, skipped, overwritten, error_details,
                    )

            # --- 不重复：创建新 Redmine Issue ---
            try:
                payload = self._build_payload(row_data)
                create_result = await self.redmine.create_issue(payload)
                # 创建成功后，将该编号加入 existing_map，避免同一批次中后续行重复创建
                new_issue_id = create_result.get("issue", {}).get("id")
                if new_issue_id:
                    existing_map[employee_id] = new_issue_id
                success += 1

            except Exception as e:
                error_details.append(
                    ImportErrorDetail(
                        row=0,
                        employee_id=employee_id,
                        reason=f"创建 Redmine Issue 失败: {str(e)}",
                    )
                )

        return self._build_result(
            total_rows, success, len(error_details),
            duplicate, skipped, overwritten, error_details,
        )

    # ------------------------------------------------------------------
    # 辅助方法：构建 Redmine API payload
    # ------------------------------------------------------------------

    def _build_payload(self, row_data: dict, *, for_update: bool = False) -> dict:
        """将导入行数据构建为 Redmine Issue API payload"""
        from ..models.custom_field import PersonnelFieldMapping

        hire_date = row_data.get("hire_date")
        return PersonnelFieldMapping.build_payload(
            {
                "employee_id": str(row_data.get("employee_id", "")).strip(),
                "name": str(row_data.get("name", "")).strip(),
                "gender": str(row_data.get("gender", "")).strip(),
                "age": str(row_data.get("age", "")).strip(),
                "phone": str(row_data.get("phone", "")).strip(),
                "email": str(row_data.get("email", "")).strip(),
                "department": str(row_data.get("department", "")).strip(),
                "position": str(row_data.get("position", "")).strip(),
                "start_datetime": str(hire_date) if hire_date else "",
            },
            project_id=0 if for_update else settings.REDMINE_PROJECT_ID,
            include_meta=not for_update,
        )

    # ------------------------------------------------------------------
    # 辅助方法：组装结果对象
    # ------------------------------------------------------------------

    def _build_result(
        self,
        total_rows: int,
        success_count: int,
        failed_count: int,
        duplicate_count: int,
        skipped_count: int,
        overwritten_count: int,
        error_details: List[ImportErrorDetail],
    ) -> ImportResultData:
        """
        组装最终的导入结果对象

        error_messages 字段直接生成字符串列表，供前端 Dash 组件用 <ul><li> 直接渲染。
        error_details 字段保留结构化数据，供"导出错误数据"功能使用。
        """
        error_messages = [
            f"第 {e.row} 行（编号: {e.employee_id or '未知'}）: {e.reason}"
            for e in error_details
        ]

        return ImportResultData(
            total_rows=total_rows,
            success_count=success_count,
            failed_count=failed_count,
            duplicate_count=duplicate_count,
            skipped_count=skipped_count,
            overwritten_count=overwritten_count,
            error_messages=error_messages,
            error_details=error_details,
        )

    # ------------------------------------------------------------------
    # 静态方法：导出错误数据（同步，仅做 pandas 操作，不需要 Redmine）
    # ------------------------------------------------------------------

    @staticmethod
    def export_error_rows(
        file_content: bytes,
        filename: str,
        error_rows: List[int],
    ) -> bytes:
        """
        从原始文件中提取指定行号的错误行，生成带 BOM 的 CSV 文件供下载

        使用场景：用户导入完成后，如果存在校验失败的行，可调用此方法导出仅包含
        这些行的 CSV 文件，用户修正数据后可重新导入。

        Args:
            file_content: 原始上传文件的字节内容
            filename:    原始文件名（用于判断格式，支持 .csv / .xlsx / .xls）
            error_rows:  需要导出的错误行号列表（从1开始的数据行号）

        Returns:
            CSV 文件内容的 bytes，可直接用 StreamingResponse 返回给浏览器下载

        Raises:
            FileImportException: 文件格式不支持、解析失败或无有效错误行
        """
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

        try:
            if ext == "csv":
                df = pd.read_csv(io.BytesIO(file_content), encoding="utf-8-sig")
            elif ext in ("xlsx", "xls"):
                df = pd.read_excel(io.BytesIO(file_content))
            else:
                raise FileImportException(
                    f"不支持的文件格式 '.{ext}'，请上传 CSV (.csv) 或 Excel (.xlsx / .xls) 文件"
                )
        except FileImportException:
            raise
        except Exception as e:
            raise FileImportException(f"文件解析失败: {str(e)}")

        # 将1-based行号转为0-based索引，同时过滤掉超出范围的行号
        max_idx = len(df) - 1
        valid_indices = [r - 1 for r in error_rows if 1 <= r - 1 <= max_idx]

        if not valid_indices:
            raise FileImportException("没有有效的错误行可用于导出")

        error_df = df.iloc[valid_indices]

        # 导出为带 BOM 的 UTF-8 CSV（确保 Excel 能正确识别中文编码）
        output = io.BytesIO()
        error_df.to_csv(output, index=False, encoding="utf-8-sig")
        output.seek(0)
        return output.getvalue()
