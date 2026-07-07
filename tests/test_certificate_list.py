from io import BytesIO
from uuid import uuid4

import pandas as pd
from fastapi.testclient import TestClient

from app.main import app
from tests.helpers import admin_headers, user_headers


def build_excel_file(data: list[dict[str, str]]) -> BytesIO:
    # 建立測試用 Excel 檔案。
    excel_file = BytesIO()
    pd.DataFrame(data).to_excel(excel_file, index=False)
    excel_file.seek(0)
    return excel_file


def import_certificates_for_user(user_id: str, national_id: str = "A123456789") -> None:
    # 匯入同一位使用者的兩張證書。
    excel_file = build_excel_file(
        [
            {
                "user_id": user_id,
                "national_id": national_id,
                "name": "SAM",
                "certificate_name": "第一張證書",
                "issue_date": "2026-07-06",
                "course_name": "內科實習",
            },
            {
                "user_id": user_id,
                "national_id": national_id,
                "name": "SAM",
                "certificate_name": "第二張證書",
                "issue_date": "2026-07-07",
                "course_name": "外科實習",
            },
        ]
    )

    client = TestClient(app)
    client.post(
        "/admin/excel/import",
        headers=admin_headers(client),
        files={
            "file": (
                "certificate_list.xlsx",
                excel_file.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )


def test_list_available_certificates_success() -> None:
    user_id = f"CERTLIST_{uuid4().hex[:8]}"
    import_certificates_for_user(user_id)

    client = TestClient(app)
    response = client.post(
        "/certificates/available",
        headers=user_headers(client),
        json={"user_id": user_id, "national_id": "a123456789"},
    )

    body = response.json()

    assert response.status_code == 200
    assert body["verified"] is True
    assert body["name"] == "SAM"
    assert body["total"] == 2
    assert body["certificates"][0]["record_id"] > 0
    assert body["certificates"][0]["certificate_name"] == "第一張證書"
    assert body["certificates"][1]["certificate_name"] == "第二張證書"


def test_list_available_certificates_wrong_national_id_returns_no_items() -> None:
    user_id = f"CERTLIST_{uuid4().hex[:8]}"
    import_certificates_for_user(user_id)

    client = TestClient(app)
    response = client.post(
        "/certificates/available",
        headers=user_headers(client),
        json={"user_id": user_id, "national_id": "B123456789"},
    )

    body = response.json()

    assert response.status_code == 200
    assert body["verified"] is False
    assert body["total"] == 0
    assert body["certificates"] == []
    assert body["message"] == "身分證字號不符合。"
