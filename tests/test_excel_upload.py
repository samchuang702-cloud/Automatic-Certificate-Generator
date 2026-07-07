from io import BytesIO
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

from app.main import app
from tests.helpers import admin_headers


def build_excel_file(data: list[dict[str, str]]) -> BytesIO:
    # 建立測試用 Excel，不依賴外部檔案。
    excel_file = BytesIO()
    pd.DataFrame(data).to_excel(excel_file, index=False)
    excel_file.seek(0)
    return excel_file


def test_upload_excel_success_saves_file() -> None:
    # 準備一份格式正確的 Excel。
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
        "/admin/excel/upload",
        headers=admin_headers(client),
        files={
            "file": (
                "valid.xlsx",
                excel_file.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["uploaded"] is True
    assert body["validation"]["is_valid"] is True
    assert body["saved_path"] is not None
    assert Path(body["saved_path"]).exists()


def test_upload_excel_invalid_file_is_not_saved() -> None:
    # 準備一份缺少 national_id 的 Excel。
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
        "/admin/excel/upload",
        headers=admin_headers(client),
        files={
            "file": (
                "invalid.xlsx",
                excel_file.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["uploaded"] is False
    assert body["saved_path"] is None
    assert body["validation"]["is_valid"] is False
