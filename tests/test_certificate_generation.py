from io import BytesIO
from pathlib import Path
from uuid import uuid4
from zipfile import ZipFile

import pandas as pd
from fastapi.testclient import TestClient
from pypdf import PdfReader

from app.main import app
from tests.helpers import admin_headers, user_headers


def build_excel_file(data: list[dict[str, str]]) -> BytesIO:
    # 建立測試用 Excel 檔案。
    excel_file = BytesIO()
    pd.DataFrame(data).to_excel(excel_file, index=False)
    excel_file.seek(0)
    return excel_file


def import_user_certificates(user_id: str) -> list[int]:
    # 使用 id_number/date 欄位測試欄位別名是否能正確匯入。
    excel_file = build_excel_file(
        [
            {
                "user_id": user_id,
                "name": "SAM",
                "id_number": "A123456789",
                "certificate_name": "PDF 測試證書",
                "course_name": "AI 課程",
                "date": "2026-07-06",
            },
            {
                "user_id": user_id,
                "name": "SAM",
                "id_number": "A123456789",
                "certificate_name": "ZIP 測試證書",
                "course_name": "Python 課程",
                "date": "2026-07-07",
            },
        ]
    )

    client = TestClient(app)
    import_response = client.post(
        "/admin/excel/import",
        headers=admin_headers(client),
        files={
            "file": (
                "alias_import.xlsx",
                excel_file.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert import_response.status_code == 200
    assert import_response.json()["imported"] is True

    list_response = client.post(
        "/certificates/available",
        headers=user_headers(client),
        json={"user_id": user_id, "national_id": "A123456789"},
    )
    return [item["record_id"] for item in list_response.json()["certificates"]]


def test_template_inspect_reads_pptx_template() -> None:
    client = TestClient(app)

    response = client.get("/admin/template/inspect", headers=admin_headers(client))
    body = response.json()

    assert response.status_code == 200
    assert body["width"] > 0
    assert body["height"] > 0
    assert any("{{name}}" in item["text"] for item in body["text_boxes"])


def test_generate_single_certificate_pdf() -> None:
    user_id = f"GEN_{uuid4().hex[:8]}"
    record_ids = import_user_certificates(user_id)

    client = TestClient(app)
    response = client.post(
        "/certificates/generate",
        headers=user_headers(client),
        json={"user_id": user_id, "national_id": "A123456789", "record_ids": [record_ids[0]]},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")

    pdf_path = Path("storage/generated/test_single_certificate.pdf")
    pdf_path.write_bytes(response.content)
    assert len(PdfReader(str(pdf_path)).pages) == 1


def test_generate_multiple_certificates_zip() -> None:
    user_id = f"GEN_{uuid4().hex[:8]}"
    record_ids = import_user_certificates(user_id)

    client = TestClient(app)
    response = client.post(
        "/certificates/generate",
        headers=user_headers(client),
        json={"user_id": user_id, "national_id": "A123456789", "record_ids": record_ids},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"

    zip_path = Path("storage/generated/test_certificates.zip")
    zip_path.write_bytes(response.content)
    with ZipFile(zip_path) as zip_file:
        assert len(zip_file.namelist()) == 2
        assert all(name.endswith(".pdf") for name in zip_file.namelist())
