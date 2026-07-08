from pathlib import Path

from app.core.config import settings
from app.schemas.excel import ExcelPreviewResult, ExcelValidationError
from app.services.excel_normalizer import normalize_excel_dataframe
from app.services.excel_validator import validate_excel_file


def preview_excel_file(filename: str, file_content: bytes, limit: int = 10) -> ExcelPreviewResult:
    # 預覽同時回傳驗證錯誤與樣本列，讓管理者可在匯入前修正檔案。
    validation = validate_excel_file(filename, file_content)

    safe_limit = max(1, min(limit, 100))

    try:
        dataframe = normalize_excel_dataframe(file_content)
        preview_rows = dataframe.head(safe_limit).to_dict(orient="records")
    except Exception:
        preview_rows = []

    return ExcelPreviewResult(
        filename=filename,
        validation=validation,
        preview_count=len(preview_rows),
        rows=preview_rows,
    )


def preview_uploaded_excel_file(saved_filename: str, limit: int = 10) -> ExcelPreviewResult:
    # 已保存檔案查詢必須限制在 storage/uploads 內。
    safe_filename = Path(saved_filename).name
    upload_path = Path(settings.upload_dir) / safe_filename

    if not upload_path.exists():
        validation = validate_excel_file(safe_filename, b"")
        validation.errors.append(
            ExcelValidationError(message=f"找不到已上傳檔案：{safe_filename}")
        )
        validation.is_valid = False
        return ExcelPreviewResult(
            filename=safe_filename,
            validation=validation,
            preview_count=0,
            rows=[],
        )

    return preview_excel_file(safe_filename, upload_path.read_bytes(), limit=limit)
