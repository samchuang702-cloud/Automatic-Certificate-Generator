from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
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


# 檔案上傳大小限制：50MB
MAX_EXCEL_FILE_SIZE = 50 * 1024 * 1024
UPLOAD_READ_CHUNK_SIZE = 1024 * 1024

router = APIRouter(
    prefix="/admin/excel",
    tags=["admin-excel"],
    dependencies=[Depends(require_roles("admin"))],
)


async def read_file_with_size_limit(file: UploadFile, max_size: int = MAX_EXCEL_FILE_SIZE) -> bytes:
    """
    讀取上傳檔案並檢查大小限制，防止 DoS 攻擊。
    
    Args:
        file: 上傳的檔案
        max_size: 最大允許的檔案大小（位元組）
        
    Returns:
        檔案內容（字節）
        
    Raises:
        HTTPException: 如果檔案超過大小限制
    """
    file_size = 0
    chunks: list[bytes] = []

    while True:
        chunk = await file.read(UPLOAD_READ_CHUNK_SIZE)
        if not chunk:
            break

        file_size += len(chunk)
        if file_size > max_size:
            max_size_mb = max_size / (1024 * 1024)
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"檔案大小超過限制。最大允許：{max_size_mb:.1f}MB，實際大小超過 {max_size_mb:.1f}MB",
            )

        chunks.append(chunk)

    return b"".join(chunks)


@router.post("/validate", response_model=ExcelValidationResult)
async def validate_excel_upload(file: UploadFile = File(...)) -> ExcelValidationResult:
    file_content = await read_file_with_size_limit(file)
    return validate_excel_file(file.filename or "", file_content)


@router.post("/upload", response_model=ExcelUploadResult)
async def upload_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> ExcelUploadResult:
    # 讀入檔案並執行大小限制檢查
    file_content = await read_file_with_size_limit(file)

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
    file_content = await read_file_with_size_limit(file)

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
    file_content = await read_file_with_size_limit(file)

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
