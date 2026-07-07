from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.certificate_record import CertificateRecord
from app.schemas.excel import ExcelImportResult
from app.services.excel_normalizer import normalize_excel_dataframe
from app.services.excel_validator import validate_excel_file


def _clean_optional_value(value: object) -> str | None:
    # Excel 空白欄位轉成 None，避免資料庫存一堆空字串。
    text = str(value).strip()
    return text or None


def _row_values(row: dict[str, object], filename: str) -> dict[str, str | None]:
    # 將標準化後的 Excel 列轉成 CertificateRecord 可寫入的欄位。
    return {
        "national_id": str(row["national_id"]).strip().upper(),
        "name": str(row["name"]).strip(),
        "issue_date": str(row["issue_date"]).strip(),
        "certificate_id": _clean_optional_value(row.get("certificate_id", "")),
        "course_name": _clean_optional_value(row.get("course_name", "")),
        "completion_date": _clean_optional_value(row.get("completion_date", "")),
        "note": _clean_optional_value(row.get("note", "")),
        "source_filename": filename,
    }


def _apply_values(record: CertificateRecord, values: dict[str, str | None]) -> None:
    # 將匯入資料覆寫到既有紀錄。
    for field_name, field_value in values.items():
        setattr(record, field_name, field_value)


def import_excel_content(
    db: Session,
    filename: str,
    file_content: bytes,
) -> ExcelImportResult:
    # 匯入前先驗證 Excel，驗證失敗就不寫入資料庫。
    validation = validate_excel_file(filename, file_content)
    if not validation.is_valid:
        return ExcelImportResult(
            imported=False,
            filename=filename,
            validation=validation,
            inserted_count=0,
            updated_count=0,
            processed_count=0,
        )

    dataframe = normalize_excel_dataframe(file_content)

    inserted_count = 0
    updated_count = 0
    records_seen_in_batch: dict[tuple[str, str], CertificateRecord] = {}

    for row in dataframe.to_dict(orient="records"):
        user_id = str(row["user_id"]).strip()
        certificate_name = str(row["certificate_name"]).strip()
        record_key = (user_id, certificate_name)
        values = _row_values(row, filename)

        # 同一個 Excel 內可能有重複的「同人同活動」列，需更新同批新增的暫存物件。
        if record_key in records_seen_in_batch:
            _apply_values(records_seen_in_batch[record_key], values)
            updated_count += 1
            continue

        existing_record = db.scalar(
            select(CertificateRecord).where(
                CertificateRecord.user_id == user_id,
                CertificateRecord.certificate_name == certificate_name,
            )
        )

        if existing_record:
            _apply_values(existing_record, values)
            records_seen_in_batch[record_key] = existing_record
            updated_count += 1
            continue

        new_record = CertificateRecord(
            user_id=user_id,
            certificate_name=certificate_name,
            **values,
        )
        db.add(new_record)
        records_seen_in_batch[record_key] = new_record
        inserted_count += 1

    db.commit()

    return ExcelImportResult(
        imported=True,
        filename=filename,
        validation=validation,
        inserted_count=inserted_count,
        updated_count=updated_count,
        processed_count=inserted_count + updated_count,
    )


def import_uploaded_excel_file(db: Session, saved_filename: str) -> ExcelImportResult:
    # 從 storage/uploads 讀取已上傳檔案並匯入。
    safe_filename = Path(saved_filename).name
    upload_path = Path(settings.upload_dir) / safe_filename

    if not upload_path.exists():
        validation = validate_excel_file(safe_filename, b"")
        validation.is_valid = False
        return ExcelImportResult(
            imported=False,
            filename=safe_filename,
            validation=validation,
            inserted_count=0,
            updated_count=0,
            processed_count=0,
        )

    return import_excel_content(db, safe_filename, upload_path.read_bytes())
