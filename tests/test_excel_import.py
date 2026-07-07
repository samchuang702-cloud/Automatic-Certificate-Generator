from io import BytesIO
from uuid import uuid4

import pandas as pd
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal, create_db_and_tables
from app.main import app
from app.models.certificate_record import CertificateRecord
from tests.helpers import admin_headers


def build_excel_file(data: list[dict[str, str]]) -> BytesIO:
    # 建立測試用 Excel 檔案。
    excel_file = BytesIO()
    pd.DataFrame(data).to_excel(excel_file, index=False)
    excel_file.seek(0)
    return excel_file


def count_record(user_id: str, certificate_name: str) -> int:
    # 查詢指定使用者與證書名稱在資料庫中的筆數。
    create_db_and_tables()
    db = SessionLocal()
    try:
        records = db.scalars(
            select(CertificateRecord).where(
                CertificateRecord.user_id == user_id,
                CertificateRecord.certificate_name == certificate_name,
            )
        ).all()
        return len(records)
    finally:
        db.close()


def test_import_excel_upload_inserts_records() -> None:
    user_id = f"IMPORT_{uuid4().hex[:8]}"

    # 準備一份格式正確的 Excel。
    excel_file = build_excel_file(
        [
            {
                "user_id": user_id,
                "national_id": "A123456789",
                "name": "SAM",
                "certificate_name": "Module 5 測試證書",
                "issue_date": "2026-07-06",
            }
        ]
    )

    client = TestClient(app)
    response = client.post(
        "/admin/excel/import",
        headers=admin_headers(client),
        files={
            "file": (
                "import.xlsx",
                excel_file.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["imported"] is True
    assert body["inserted_count"] == 1
    assert body["updated_count"] == 0
    assert count_record(user_id, "Module 5 測試證書") == 1


def test_import_excel_upload_updates_existing_record() -> None:
    user_id = f"IMPORT_{uuid4().hex[:8]}"

    # 第一次匯入使用舊姓名。
    first_excel = build_excel_file(
        [
            {
                "user_id": user_id,
                "national_id": "B123456789",
                "name": "Old Name",
                "certificate_name": "可更新證書",
                "issue_date": "2026-07-06",
            }
        ]
    )

    # 第二次匯入相同 user_id + certificate_name，但改姓名。
    second_excel = build_excel_file(
        [
            {
                "user_id": user_id,
                "national_id": "B123456789",
                "name": "New Name",
                "certificate_name": "可更新證書",
                "issue_date": "2026-07-07",
            }
        ]
    )

    client = TestClient(app)
    client.post(
        "/admin/excel/import",
        headers=admin_headers(client),
        files={
            "file": (
                "first.xlsx",
                first_excel.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    response = client.post(
        "/admin/excel/import",
        headers=admin_headers(client),
        files={
            "file": (
                "second.xlsx",
                second_excel.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["imported"] is True
    assert body["updated_count"] == 1
    assert count_record(user_id, "可更新證書") == 1


def test_import_saved_excel_file() -> None:
    user_id = f"IMPORT_{uuid4().hex[:8]}"

    # 先上傳保存 Excel。
    excel_file = build_excel_file(
        [
            {
                "user_id": user_id,
                "national_id": "C123456789",
                "name": "Saved User",
                "certificate_name": "已保存檔案匯入證書",
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
                "saved_import.xlsx",
                excel_file.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    saved_filename = upload_response.json()["saved_filename"]

    # 再匯入已保存的 Excel。
    import_response = client.post(
        f"/admin/excel/uploads/{saved_filename}/import",
        headers=admin_headers(client),
    )
    body = import_response.json()

    assert import_response.status_code == 200
    assert body["imported"] is True
    assert body["processed_count"] == 1
    assert count_record(user_id, "已保存檔案匯入證書") == 1
