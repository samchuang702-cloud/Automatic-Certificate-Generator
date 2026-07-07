from io import BytesIO
from uuid import uuid4

import pandas as pd
from fastapi.testclient import TestClient

from app.main import app
from tests.helpers import admin_headers, user_headers


def build_excel_file(data: list[dict[str, str]]) -> BytesIO:
    # 建立測試用 Excel 檔案，透過既有匯入 API 先把資料寫入資料庫。
    excel_file = BytesIO()
    pd.DataFrame(data).to_excel(excel_file, index=False)
    excel_file.seek(0)
    return excel_file


def import_test_user(user_id: str, national_id: str = "A123456789") -> None:
    # 匯入一筆可供身分驗證測試的使用者資料。
    excel_file = build_excel_file(
        [
            {
                "user_id": user_id,
                "national_id": national_id,
                "name": "SAM",
                "certificate_name": "身分驗證測試證書",
                "issue_date": "2026-07-06",
            }
        ]
    )

    client = TestClient(app)
    client.post(
        "/admin/excel/import",
        headers=admin_headers(client),
        files={
            "file": (
                "identity_verify.xlsx",
                excel_file.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )


def test_verify_identity_success() -> None:
    user_id = f"VERIFY_{uuid4().hex[:8]}"
    import_test_user(user_id)

    client = TestClient(app)
    response = client.post(
        "/auth/verify",
        headers=user_headers(client),
        json={"user_id": user_id, "national_id": "a123456789"},
    )

    body = response.json()

    assert response.status_code == 200
    assert body["verified"] is True
    assert body["name"] == "SAM"
    assert body["available_certificate_count"] == 1


def test_identity_login_issues_user_token() -> None:
    user_id = f"VERIFY_{uuid4().hex[:8]}"
    import_test_user(user_id)

    client = TestClient(app)
    response = client.post(
        "/auth/login/identity",
        json={"name": "SAM", "id_number": "a123456789"},
    )

    body = response.json()

    assert response.status_code == 200
    assert body["username"] == "user"
    assert body["display_name"] == "SAM"
    assert body["role"] == "user"
    assert body["access_token"]


def test_identity_login_rejects_wrong_id() -> None:
    user_id = f"VERIFY_{uuid4().hex[:8]}"
    import_test_user(user_id)

    client = TestClient(app)
    response = client.post(
        "/auth/login/identity",
        json={"name": "SAM", "id_number": "B123456789"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "身分證字號不符合。"


def test_verify_identity_wrong_national_id() -> None:
    user_id = f"VERIFY_{uuid4().hex[:8]}"
    import_test_user(user_id)

    client = TestClient(app)
    response = client.post(
        "/auth/verify",
        headers=user_headers(client),
        json={"user_id": user_id, "national_id": "B123456789"},
    )

    body = response.json()

    assert response.status_code == 200
    assert body["verified"] is False
    assert body["message"] == "身分證字號不符合。"


def test_verify_identity_unknown_user_id() -> None:
    client = TestClient(app)
    response = client.post(
        "/auth/verify",
        headers=user_headers(client),
        json={"user_id": f"UNKNOWN_{uuid4().hex[:8]}", "national_id": "A123456789"},
    )

    body = response.json()

    assert response.status_code == 200
    assert body["verified"] is False
    assert body["message"] == "查無此使用者 ID。"
