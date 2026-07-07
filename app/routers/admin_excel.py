from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from app.dependencies.auth import require_roles
from app.db.session import get_db
from app.schemas.excel import (
    ExcelImportResult,
    ExcelPreviewResult,
    ExcelUploadResult,
    ExcelValidationResult,
)
from app.services.excel_importer import import_excel_content, import_uploaded_excel_file
from app.services.excel_reader import preview_excel_file, preview_uploaded_excel_file
from app.services.excel_upload import upload_excel_file
from app.services.excel_validator import validate_excel_file
from app.services.operation_logger import create_operation_log


# 建立後台 Excel API router。
# prefix 代表這個檔案中的所有路由都會以 /admin/excel 開頭。
# 只有 admin 和 county_staff 可以使用 Excel 上傳、預覽、匯入功能。
router = APIRouter(
    prefix="/admin/excel",
    tags=["admin-excel"],
    dependencies=[Depends(require_roles("admin", "county_staff"))],
)


@router.post("/validate", response_model=ExcelValidationResult)
async def validate_excel_upload(file: UploadFile = File(...)) -> ExcelValidationResult:
    # 讀取上傳檔案內容。
    # 目前這個 API 只做驗證，不會把檔案存進 storage/uploads。
    file_content = await file.read()

    # 將檔名與檔案 bytes 交給 service 做實際 Excel 讀取與欄位檢查。
    return validate_excel_file(file.filename or "", file_content)


@router.post("/upload", response_model=ExcelUploadResult)
async def upload_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> ExcelUploadResult:
    # 讀取上傳檔案內容。
    # 這裡會先完整讀到記憶體，後續 Module 12 可以再加上檔案大小限制。
    file_content = await file.read()

    # 呼叫上傳 service。
    # service 會先驗證 Excel，通過後才保存到 storage/uploads。
    result = upload_excel_file(file.filename or "", file_content)
    create_operation_log(
        db,
        action="excel_upload",
        filename=result.saved_filename or result.original_filename,
        status="success" if result.uploaded else "failed",
        detail={
            "original_filename": result.original_filename,
            "saved_path": result.saved_path,
            "row_count": result.validation.row_count,
            "errors": [error.message for error in result.validation.errors],
        },
    )
    return result


@router.post("/preview", response_model=ExcelPreviewResult)
async def preview_excel_upload(
    file: UploadFile = File(...),
    limit: int = Query(default=10, ge=1, le=100),
) -> ExcelPreviewResult:
    # 讀取使用者剛上傳的 Excel，但不保存檔案。
    # 適合在後台匯入前先確認 Excel 前幾筆資料長什麼樣子。
    file_content = await file.read()

    return preview_excel_file(file.filename or "", file_content, limit=limit)


@router.get("/uploads/{saved_filename}/preview", response_model=ExcelPreviewResult)
def preview_saved_excel(
    saved_filename: str,
    limit: int = Query(default=10, ge=1, le=100),
) -> ExcelPreviewResult:
    # 讀取已經保存到 storage/uploads 的 Excel。
    # Module 5 匯入資料庫前，可以先用這個 API 查看已上傳檔案內容。
    return preview_uploaded_excel_file(saved_filename, limit=limit)


@router.post("/import", response_model=ExcelImportResult)
async def import_excel_upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> ExcelImportResult:
    # 直接上傳 Excel 並匯入資料庫。
    # 這個 API 不會先保存檔案，只負責把通過驗證的資料寫入 certificate_records。
    file_content = await file.read()

    result = import_excel_content(db, file.filename or "", file_content)
    create_operation_log(
        db,
        action="excel_import",
        filename=result.filename,
        status="success" if result.imported else "failed",
        detail={
            "inserted_count": result.inserted_count,
            "updated_count": result.updated_count,
            "processed_count": result.processed_count,
            "errors": [error.message for error in result.validation.errors],
        },
    )
    return result


@router.post("/uploads/{saved_filename}/import", response_model=ExcelImportResult)
def import_saved_excel(
    saved_filename: str,
    db: Session = Depends(get_db),
) -> ExcelImportResult:
    # 匯入已經保存到 storage/uploads 的 Excel。
    # 這是後台常見流程：先 upload，再 preview，確認沒問題後再 import。
    result = import_uploaded_excel_file(db, saved_filename)
    create_operation_log(
        db,
        action="excel_import_saved",
        filename=result.filename,
        status="success" if result.imported else "failed",
        detail={
            "inserted_count": result.inserted_count,
            "updated_count": result.updated_count,
            "processed_count": result.processed_count,
            "errors": [error.message for error in result.validation.errors],
        },
    )
    return result
