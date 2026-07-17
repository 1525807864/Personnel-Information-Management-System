"""
导入功能相关的 Pydantic 数据模型

定义导入请求配置、导入结果统计、错误详情等数据结构。
前端 import_page.py 的 do_import 回调依赖这些字段渲染统计卡片和错误列表。
"""
from pydantic import BaseModel, Field
from typing import List, Optional


class ImportErrorDetail(BaseModel):
    """
    单条导入错误的详细信息

    用于导入结果中的错误列表展示，同时也作为"错误数据导出"功能的数据源。
    """
    row: int = Field(
        ...,
        description="Excel/CSV 中的行号（从1开始，不含表头行）。例如第3行数据出错则 row=3",
    )
    employee_id: Optional[str] = Field(
        None,
        description="出错行对应的人员编号。如果该字段本身缺失或解析失败，则为 None",
    )
    reason: str = Field(
        ...,
        description="错误原因描述，例如：'手机号格式不正确'、'人员编号已存在'、'年龄不在18-65范围内'",
    )


class ImportResultData(BaseModel):
    """
    导入结果统计数据

    前端 import_page.py 的 do_import 回调会读取以下字段来渲染统计卡片：
      - total_rows      → "共 X 条" 卡片
      - success_count   → "成功 X 条" 卡片
      - failed_count    → "失败 X 条" 卡片
      - duplicate_count → "重复 X 条" 卡片
      - error_messages  → 错误详情列表（<ul> 渲染）
    """
    total_rows: int = Field(
        0,
        description="文件中实际解析出的数据行总数（不含表头，不含空行）",
    )
    success_count: int = Field(
        0,
        description="成功写入 Redmine 的记录数（含覆盖更新的行）",
    )
    failed_count: int = Field(
        0,
        description="校验未通过或 Redmine API 调用失败的行数",
    )
    duplicate_count: int = Field(
        0,
        description="检测到与已有数据人员编号重复的行数（在应用策略之前的原始重复数）",
    )
    skipped_count: int = Field(
        0,
        description="当策略为 'skip' 时，因重复而被跳过的行数",
    )
    overwritten_count: int = Field(
        0,
        description="当策略为 'overwrite' 时，被覆盖更新的行数",
    )
    error_messages: List[str] = Field(
        default_factory=list,
        description="错误消息列表（字符串格式），直接供前端 Dash 组件渲染 <ul><li>...</li></ul>",
    )
    error_details: List[ImportErrorDetail] = Field(
        default_factory=list,
        description="结构化的错误详情列表，供'导出错误数据'功能或其他后续处理使用",
    )
