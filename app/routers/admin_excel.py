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


router = APIRouter(
    prefix="/admin/excel",
    tags=["admin-excel"],
    dependencies=[Depends(require_roles("admin", "county_staff"))],
)


@router.post("/validate", response_model=ExcelValidationResult)
async def validate_excel_upload(file: UploadFile = File(...)) -> ExcelValidationResult:
    file_content = await file.read()
    return validate_excel_file(file.filename or "", file_content)


@router.post("/upload", response_model=ExcelUploadResult)
async def upload_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> ExcelUploadResult:
    # 目前流程會一次讀入完整檔案；若要支援大型 Excel，需先加上大小限制。
    file_content = await file.read()

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
    file_content = await file.read()

    return preview_excel_file(file.filename or "", file_content, limit=limit)


@router.get("/uploads/{saved_filename}/preview", response_model=ExcelPreviewResult)
def preview_saved_excel(
    saved_filename: str,
    limit: int = Query(default=10, ge=1, le=100),
) -> ExcelPreviewResult:
    return preview_uploaded_excel_file(saved_filename, limit=limit)


@router.post("/import", response_model=ExcelImportResult)
async def import_excel_upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> ExcelImportResult:
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
