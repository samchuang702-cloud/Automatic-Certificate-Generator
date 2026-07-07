from pathlib import Path

from app.core.config import settings
from app.schemas.excel import ExcelPreviewResult, ExcelValidationError
from app.services.excel_normalizer import normalize_excel_dataframe
from app.services.excel_validator import validate_excel_file


def preview_excel_file(filename: str, file_content: bytes, limit: int = 10) -> ExcelPreviewResult:
    # 預覽時仍先做欄位驗證，讓後台能同時看到資料和錯誤。
    validation = validate_excel_file(filename, file_content)

    # 限制預覽筆數，避免大型 Excel 一次回傳太多資料。
    safe_limit = max(1, min(limit, 100))

    try:
        dataframe = normalize_excel_dataframe(file_content)
        preview_rows = dataframe.head(safe_limit).to_dict(orient="records")
    except Exception:
        # 如果 Excel 連讀取都失敗，驗證結果裡已經會有錯誤訊息。
        preview_rows = []

    return ExcelPreviewResult(
        filename=filename,
        validation=validation,
        preview_count=len(preview_rows),
        rows=preview_rows,
    )


def preview_uploaded_excel_file(saved_filename: str, limit: int = 10) -> ExcelPreviewResult:
    # 只接受檔名，不接受路徑，避免讀取 uploads 以外的檔案。
    safe_filename = Path(saved_filename).name
    upload_path = Path(settings.upload_dir) / safe_filename

    # 如果檔案不存在，回傳一個驗證失敗的預覽結果。
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
