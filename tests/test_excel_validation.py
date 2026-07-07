from io import BytesIO

import pandas as pd
from fastapi.testclient import TestClient

from app.main import app
from tests.helpers import admin_headers


def build_excel_file(data: list[dict[str, str]]) -> BytesIO:
    # 建立記憶體中的 Excel 檔案，測試時不需要真的產生實體檔案。
    excel_file = BytesIO()
    pd.DataFrame(data).to_excel(excel_file, index=False)
    excel_file.seek(0)
    return excel_file


def test_validate_excel_success() -> None:
    # 準備一份欄位完整、資料格式正確的 Excel。
    excel_file = build_excel_file(
        [
            {
                "user_id": "U001",
                "national_id": "A123456789",
                "name": "SAM",
                "certificate_name": "實習完成證書",
                "issue_date": "2026-07-06",
            }
        ]
    )

    client = TestClient(app)
    response = client.post(
        "/admin/excel/validate",
        headers=admin_headers(client),
        files={
            "file": (
                "valid.xlsx",
                excel_file.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert response.status_code == 200
    assert response.json()["is_valid"] is True
    assert response.json()["row_count"] == 1
    assert response.json()["missing_columns"] == []


def test_validate_excel_missing_required_column() -> None:
    # 準備一份缺少 national_id 欄位的 Excel。
    excel_file = build_excel_file(
        [
            {
                "user_id": "U001",
                "name": "SAM",
                "certificate_name": "實習完成證書",
                "issue_date": "2026-07-06",
            }
        ]
    )

    client = TestClient(app)
    response = client.post(
        "/admin/excel/validate",
        headers=admin_headers(client),
        files={
            "file": (
                "missing_column.xlsx",
                excel_file.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert response.status_code == 200
    assert response.json()["is_valid"] is False
    assert "national_id" in response.json()["missing_columns"]
