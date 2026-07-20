"""
数据导入接口测试

测试端点：
  POST /api/v1/import/              — 上传文件批量导入
  POST /api/v1/import/export-errors — 导出错误数据行
"""
import io
import csv
from unittest.mock import AsyncMock, patch

import pytest


# ═══════════════════════════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════════════════════════

def _make_csv_bytes(rows: list[list[str]]) -> bytes:
    """将二维列表生成 UTF-8 BOM CSV 的 bytes"""
    output = io.StringIO()
    writer = csv.writer(output)
    for row in rows:
        writer.writerow(row)
    return output.getvalue().encode("utf-8-sig")


# ═══════════════════════════════════════════════════════════════════════════════
# 测试数据
# ═══════════════════════════════════════════════════════════════════════════════

VALID_CSV_ROWS = [
    ["人员编号", "姓名", "性别", "年龄", "手机号", "邮箱", "部门", "职位", "入职日期"],
    ["EMP001", "张三", "男", "25", "13800138000", "zhangsan@test.com", "技术部", "工程师", "2024-01-01"],
    ["EMP002", "李四", "女", "30", "13900139000", "lisi@test.com", "产品部", "产品经理", "2023-06-15"],
]


# ═══════════════════════════════════════════════════════════════════════════════
# 导入接口测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestImportAPI:
    """测试 POST /api/v1/import/"""

    def test_import_csv_success(self, client, auth_headers):
        """上传合法 CSV 导入成功"""
        csv_bytes = _make_csv_bytes(VALID_CSV_ROWS)
        resp = client.post(
            "/api/v1/import/",
            files={"file": ("test.csv", csv_bytes, "text/csv")},
            data={"strategy": "skip"},
            headers=auth_headers,
        )
        assert resp.status_code == 200, f"导入失败: {resp.text}"
        data = resp.json()
        assert data["code"] == 200
        result = data["data"]
        assert result["total_rows"] == 2
        assert result["success_count"] >= 0

    def test_import_strategy_overwrite(self, client, auth_headers):
        """策略=overwrite 导入成功"""
        csv_bytes = _make_csv_bytes(VALID_CSV_ROWS)
        resp = client.post(
            "/api/v1/import/",
            files={"file": ("test.csv", csv_bytes, "text/csv")},
            data={"strategy": "overwrite"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_import_strategy_terminate(self, client, auth_headers):
        """策略=terminate 导入成功"""
        csv_bytes = _make_csv_bytes(VALID_CSV_ROWS)
        resp = client.post(
            "/api/v1/import/",
            files={"file": ("test.csv", csv_bytes, "text/csv")},
            data={"strategy": "terminate"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_import_default_strategy(self, client, auth_headers):
        """不指定策略时使用默认值 skip"""
        csv_bytes = _make_csv_bytes(VALID_CSV_ROWS)
        resp = client.post(
            "/api/v1/import/",
            files={"file": ("test.csv", csv_bytes, "text/csv")},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_import_empty_file(self, client, auth_headers):
        """空文件 → 400"""
        resp = client.post(
            "/api/v1/import/",
            files={"file": ("empty.csv", b"", "text/csv")},
            data={"strategy": "skip"},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_import_unsupported_format(self, client, auth_headers):
        """不支持的文件格式 → 400"""
        resp = client.post(
            "/api/v1/import/",
            files={"file": ("test.pdf", b"fake pdf", "application/pdf")},
            data={"strategy": "skip"},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_import_no_auth(self, client):
        """无 Token → 401"""
        csv_bytes = _make_csv_bytes(VALID_CSV_ROWS)
        resp = client.post(
            "/api/v1/import/",
            files={"file": ("test.csv", csv_bytes, "text/csv")},
        )
        assert resp.status_code == 401

    def test_import_invalid_strategy(self, client, auth_headers):
        """无效的策略值应降级为 skip 而非报错"""
        csv_bytes = _make_csv_bytes(VALID_CSV_ROWS)
        resp = client.post(
            "/api/v1/import/",
            files={"file": ("test.csv", csv_bytes, "text/csv")},
            data={"strategy": "invalid_strategy"},
            headers=auth_headers,
        )
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# 错误导出接口测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestExportErrors:
    """测试 POST /api/v1/import/export-errors"""

    def test_export_errors_success(self, client, auth_headers):
        """导出错误行 → 返回 CSV 文件"""
        csv_bytes = _make_csv_bytes(VALID_CSV_ROWS)
        resp = client.post(
            "/api/v1/import/export-errors",
            files={"file": ("test.csv", csv_bytes, "text/csv")},
            data={"error_rows": "2"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_export_errors_invalid_rows(self, client, auth_headers):
        """非法的 error_rows 值 → 400"""
        csv_bytes = _make_csv_bytes(VALID_CSV_ROWS)
        resp = client.post(
            "/api/v1/import/export-errors",
            files={"file": ("test.csv", csv_bytes, "text/csv")},
            data={"error_rows": "not_a_number"},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_export_errors_empty_rows(self, client, auth_headers):
        """空的 error_rows → 400"""
        csv_bytes = _make_csv_bytes(VALID_CSV_ROWS)
        resp = client.post(
            "/api/v1/import/export-errors",
            files={"file": ("test.csv", csv_bytes, "text/csv")},
            data={"error_rows": ""},
            headers=auth_headers,
        )
        assert resp.status_code == 400

class TestImportErrorPaths:
    def test_import_generic_exception_500(self,client,auth_headers):
        resp = client.post(
            "/api/v1/import",
            files = {"file":("test.csv","b","text/csv")},#空文件
            data = {"error_rows":"99999"},
            headers=auth_headers
        )
        assert resp.status_code == 400

    def test_export_errors_empty_row(self, client, auth_headers):
        """导出错误行 — 空 error_rows → 400"""
        resp = client.post(
            "/api/v1/import/export-errors",
            files={"file": ("test.csv", b"a,b\n1,2", "text/csv")},
            data={"error_rows": ""},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_export_errors_invalid_rows(self, client, auth_headers):
        """导出错误行 — 无效行号（超出范围）→ 400"""
        resp = client.post(
            "/api/v1/import/export-errors",
            files={"file": ("test.csv", b"a,b\n1,2", "text/csv")},
            data={"error_rows": "99999"},
            headers=auth_headers,
        )
        assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════════
# 异常路径覆盖 — 针对 import_api.py 中未覆盖的错误处理分支
# ═══════════════════════════════════════════════════════════════════════════════

class TestImportFileReadError:
    """覆盖 import_personnel_file 中 file.read() 异常分支 (lines 75-77)"""

    def test_file_read_raises_exception(self, client, auth_headers):
        """file.read() 抛异常 → 400"""
        csv_bytes = _make_csv_bytes(VALID_CSV_ROWS)
        with patch(
            "starlette.datastructures.UploadFile.read",
            new_callable=AsyncMock,
        ) as mock_read:
            mock_read.side_effect = OSError("磁盘 I/O 错误")
            resp = client.post(
                "/api/v1/import/",
                files={"file": ("test.csv", csv_bytes, "text/csv")},
                data={"strategy": "skip"},
                headers=auth_headers,
            )
        assert resp.status_code == 400
        assert "无法读取上传文件" in resp.json()["detail"]


class TestImportUnexpectedError:
    """覆盖 import_personnel_file 中非 FileImportException 的异常分支 (lines 90-92)"""

    def test_import_service_raises_unexpected_exception(self, client, auth_headers):
        """服务层抛非 FileImportException 的异常 → 500"""
        csv_bytes = _make_csv_bytes(VALID_CSV_ROWS)
        with patch(
            "backend.app.services.import_service.ImportService.import_file",
            new_callable=AsyncMock,
        ) as mock_import:
            mock_import.side_effect = RuntimeError("Redmine API 断连")
            resp = client.post(
                "/api/v1/import/",
                files={"file": ("test.csv", csv_bytes, "text/csv")},
                data={"strategy": "skip"},
                headers=auth_headers,
            )
        assert resp.status_code == 500
        assert "服务器内部错误" in resp.json()["detail"]


class TestImportResultMessageBranches:
    """覆盖响应消息构建的边界分支 (lines 96→98, 101)"""

    def test_success_count_zero(self, client, auth_headers):
        """全部导入失败 → success_count=0 → 不出现"成功 N 条"字样"""
        # 所有行手机号格式错误 → Pydantic 校验失败 → 0 成功
        bad_rows = [
            ["人员编号", "姓名", "性别", "年龄", "手机号", "邮箱", "部门", "职位", "入职日期"],
            ["B001", "无效一", "男", "20", "0000", "bad@t.com", "部", "职", "2024-01-01"],
            ["B002", "无效二", "女", "30", "1111", "bad2@t.com", "部", "职", "2024-01-01"],
        ]
        csv_bytes = _make_csv_bytes(bad_rows)
        resp = client.post(
            "/api/v1/import/",
            files={"file": ("bad.csv", csv_bytes, "text/csv")},
            data={"strategy": "skip"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["success_count"] == 0
        assert data["failed_count"] > 0
        assert "成功" not in resp.json()["message"]

    def test_duplicate_count_nonzero(self, client, auth_headers):
        """重复导入同一文件 → duplicate_count > 0 → 消息含"重复 N 条" """
        csv_bytes = _make_csv_bytes(VALID_CSV_ROWS)
        # 第一次导入
        resp1 = client.post(
            "/api/v1/import/",
            files={"file": ("dup.csv", csv_bytes, "text/csv")},
            data={"strategy": "skip"},
            headers=auth_headers,
        )
        assert resp1.status_code == 200
        # 第二次导入（skip 策略下重复行被跳过）
        resp2 = client.post(
            "/api/v1/import/",
            files={"file": ("dup.csv", csv_bytes, "text/csv")},
            data={"strategy": "skip"},
            headers=auth_headers,
        )
        assert resp2.status_code == 200
        data = resp2.json()["data"]
        assert data["duplicate_count"] > 0
        assert "重复" in resp2.json()["message"]


class TestExportErrorsFileReadError:
    """覆盖 export_error_rows 中 file.read() 异常分支 (lines 155-157)"""

    def test_file_read_raises_exception(self, client, auth_headers):
        """export-errors: file.read() 抛异常 → 400"""
        csv_bytes = _make_csv_bytes(VALID_CSV_ROWS)
        with patch(
            "starlette.datastructures.UploadFile.read",
            new_callable=AsyncMock,
        ) as mock_read:
            mock_read.side_effect = OSError("磁盘 I/O 错误")
            resp = client.post(
                "/api/v1/import/export-errors",
                files={"file": ("test.csv", csv_bytes, "text/csv")},
                data={"error_rows": "2,3"},
                headers=auth_headers,
            )
        assert resp.status_code == 400
        assert "无法读取上传文件" in resp.json()["detail"]


class TestExportErrorsEmptyFile:
    """覆盖 export_error_rows 中空文件检查 (line 159-160)"""

    def test_export_empty_file_content(self, client, auth_headers):
        """空文件内容 → 400"""
        resp = client.post(
            "/api/v1/import/export-errors",
            files={"file": ("empty.csv", b"", "text/csv")},
            data={"error_rows": "1,2"},
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert "文件内容为空" in resp.json()["detail"]

