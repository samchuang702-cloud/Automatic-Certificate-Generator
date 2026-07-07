from datetime import datetime
from pathlib import Path
from uuid import uuid4

from app.core.config import settings
from app.schemas.excel import ExcelUploadResult
from app.services.excel_validator import validate_excel_file


def build_safe_upload_filename(original_filename: str) -> str:
    # 只取檔名，不接受使用者傳入的資料夾路徑。
    # 例如 ../../hack.xlsx 會被轉成 hack.xlsx。
    source_name = Path(original_filename).name

    # 取得副檔名並轉成小寫，方便後續辨識檔案類型。
    suffix = Path(source_name).suffix.lower()

    # 產生時間戳，讓管理者之後能大致看出上傳時間。
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 加上短 UUID，避免同一秒上傳同名檔案時互相覆蓋。
    unique_id = uuid4().hex[:8]

    return f"{timestamp}_{unique_id}{suffix}"


def upload_excel_file(original_filename: str, file_content: bytes) -> ExcelUploadResult:
    # 先做 Excel 欄位與資料格式驗證。
    # Module 3 只處理「上傳保存」，不把資料匯入資料庫。
    validation = validate_excel_file(original_filename, file_content)

    # 如果驗證失敗，就不保存檔案。
    # 這樣 storage/uploads 只會保留符合目前規格的 Excel。
    if not validation.is_valid:
        return ExcelUploadResult(
            uploaded=False,
            original_filename=original_filename,
            validation=validation,
        )

    # 確保上傳資料夾存在。
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    # 建立安全且不容易重複的保存檔名。
    saved_filename = build_safe_upload_filename(original_filename)
    saved_path = upload_dir / saved_filename

    # 將原始 Excel bytes 寫入 storage/uploads。
    saved_path.write_bytes(file_content)

    return ExcelUploadResult(
        uploaded=True,
        original_filename=original_filename,
        saved_filename=saved_filename,
        saved_path=saved_path.as_posix(),
        validation=validation,
    )
