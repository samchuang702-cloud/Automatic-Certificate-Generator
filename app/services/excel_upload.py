from datetime import datetime
from pathlib import Path
from uuid import uuid4

from app.core.config import settings
from app.schemas.excel import ExcelUploadResult
from app.services.excel_validator import validate_excel_file


def build_safe_upload_filename(original_filename: str) -> str:
    # 產生後端檔名前先移除使用者輸入中的路徑片段。
    source_name = Path(original_filename).name
    suffix = Path(source_name).suffix.lower()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid4().hex[:8]

    return f"{timestamp}_{unique_id}{suffix}"


def upload_excel_file(original_filename: str, file_content: bytes) -> ExcelUploadResult:
    # 只有通過驗證的檔案才會保存；匯入是另一個明確操作。
    validation = validate_excel_file(original_filename, file_content)

    if not validation.is_valid:
        return ExcelUploadResult(
            uploaded=False,
            original_filename=original_filename,
            validation=validation,
        )

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    saved_filename = build_safe_upload_filename(original_filename)
    saved_path = upload_dir / saved_filename

    saved_path.write_bytes(file_content)

    return ExcelUploadResult(
        uploaded=True,
        original_filename=original_filename,
        saved_filename=saved_filename,
        saved_path=saved_path.as_posix(),
        validation=validation,
    )
