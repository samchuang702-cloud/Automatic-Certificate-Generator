from io import BytesIO
from pathlib import Path
from uuid import uuid4
from zipfile import ZipFile

import pandas as pd
from fastapi.testclient import TestClient
from pypdf import PdfReader
from reportlab.pdfgen import canvas

from app.db.session import SessionLocal
from app.main import app
from app.models.certificate_generation import CertificateGenerationRecord
from app.services import certificate_generator
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


def fake_render_word_template_pdf(record, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(output_path))
    pdf.drawString(72, 720, f"PDF generated for {record.name}")
    pdf.save()
    return output_path


def test_template_inspect_reads_pptx_template() -> None:
    client = TestClient(app)

    response = client.get("/admin/template/inspect", headers=admin_headers(client))
    body = response.json()

    assert response.status_code == 200
    assert body["width"] > 0
    assert body["height"] > 0
    assert any("{{name}}" in item["text"] for item in body["text_boxes"])


def test_generate_single_certificate_pdf(monkeypatch) -> None:
    monkeypatch.setattr(certificate_generator, "_render_word_template_pdf", fake_render_word_template_pdf)
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

    db = SessionLocal()
    try:
        generation_record = (
            db.query(CertificateGenerationRecord)
            .filter(CertificateGenerationRecord.user_id == user_id)
            .order_by(CertificateGenerationRecord.id.desc())
            .first()
        )
        assert generation_record is not None
        assert generation_record.output_path
        assert generation_record.output_path.endswith(".pdf")
    finally:
        db.close()


def test_generate_multiple_certificates_zip(monkeypatch) -> None:
    monkeypatch.setattr(certificate_generator, "_render_word_template_pdf", fake_render_word_template_pdf)
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
