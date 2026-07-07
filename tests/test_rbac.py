from io import BytesIO

import pandas as pd
from fastapi.testclient import TestClient

from app.main import app
from tests.helpers import county_headers, user_headers


def build_excel_file() -> BytesIO:
    # 建立一份最小合法 Excel。
    excel_file = BytesIO()
    pd.DataFrame(
        [
            {
                "user_id": "RBAC001",
                "national_id": "A123456789",
                "name": "SAM",
                "certificate_name": "RBAC 測試證書",
                "issue_date": "2026-07-06",
            }
        ]
    ).to_excel(excel_file, index=False)
    excel_file.seek(0)
    return excel_file


def test_admin_excel_requires_login() -> None:
    client = TestClient(app)
    excel_file = build_excel_file()

    response = client.post(
        "/admin/excel/preview",
        files={
            "file": (
                "rbac.xlsx",
                excel_file.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert response.status_code == 401


def test_user_role_cannot_use_admin_excel() -> None:
    client = TestClient(app)
    excel_file = build_excel_file()

    response = client.post(
        "/admin/excel/preview",
        headers=user_headers(client),
        files={
            "file": (
                "rbac.xlsx",
                excel_file.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert response.status_code == 403


def test_county_staff_can_use_admin_excel() -> None:
    client = TestClient(app)
    excel_file = build_excel_file()

    response = client.post(
        "/admin/excel/preview",
        headers=county_headers(client),
        files={
            "file": (
                "rbac.xlsx",
                excel_file.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert response.status_code == 200
    assert response.json()["validation"]["is_valid"] is True


def test_certificate_query_requires_login() -> None:
    client = TestClient(app)

    response = client.post(
        "/certificates/available",
        json={"user_id": "A001", "national_id": "A123456789"},
    )

    assert response.status_code == 401
