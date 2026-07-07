from io import BytesIO

import pandas as pd
from fastapi.testclient import TestClient

from app.main import app
from tests.helpers import admin_headers


def build_excel_file(data: list[dict[str, str]]) -> BytesIO:
    # 建立測試用 Excel 檔案。
    excel_file = BytesIO()
    pd.DataFrame(data).to_excel(excel_file, index=False)
    excel_file.seek(0)
    return excel_file


def test_preview_excel_upload_returns_rows() -> None:
    # 準備兩筆資料，並要求 API 只預覽第一筆。
    excel_file = build_excel_file(
        [
            {
                "user_id": "U001",
                "national_id": "A123456789",
                "name": "SAM",
                "certificate_name": "實習完成證書",
                "issue_date": "2026-07-06",
            },
            {
                "user_id": "U002",
                "national_id": "B123456789",
                "name": "Alex",
                "certificate_name": "訓練完成證書",
                "issue_date": "2026-07-07",
            },
        ]
    )

    client = TestClient(app)
    response = client.post(
        "/admin/excel/preview?limit=1",
        headers=admin_headers(client),
        files={
            "file": (
                "preview.xlsx",
                excel_file.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["validation"]["is_valid"] is True
    assert body["preview_count"] == 1
    assert body["rows"][0]["user_id"] == "U001"


def test_preview_saved_excel_returns_rows() -> None:
    # 先用上傳 API 保存一份 Excel。
    excel_file = build_excel_file(
        [
            {
                "user_id": "U003",
                "national_id": "C123456789",
                "name": "Chris",
                "certificate_name": "實習完成證書",
                "issue_date": "2026-07-08",
            }
        ]
    )

    client = TestClient(app)
    upload_response = client.post(
        "/admin/excel/upload",
        headers=admin_headers(client),
        files={
            "file": (
                "saved_preview.xlsx",
                excel_file.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    saved_filename = upload_response.json()["saved_filename"]

    # 再用保存後的檔名讀取預覽。
    preview_response = client.get(
        f"/admin/excel/uploads/{saved_filename}/preview",
        headers=admin_headers(client),
    )
    body = preview_response.json()

    assert preview_response.status_code == 200
    assert body["validation"]["is_valid"] is True
    assert body["preview_count"] == 1
    assert body["rows"][0]["user_id"] == "U003"
