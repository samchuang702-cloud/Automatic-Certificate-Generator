from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_user
from app.db.session import get_db
from app.models.user_account import UserAccount
from app.schemas.certificate import CertificateGenerateRequest, CertificateListRequest, CertificateListResult
from app.services.certificate_generator import generate_certificate_package
from app.services.certificate_query import list_available_certificates


# 使用者端證書查詢 API。
# 使用者通過身分驗證後，可以用這個 API 取得可產生證書清單。
router = APIRouter(prefix="/certificates", tags=["certificates"])


@router.post("/available", response_model=CertificateListResult)
def get_available_certificates(
    payload: CertificateListRequest,
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CertificateListResult:
    # 查詢前再次比對 user_id 與 national_id。
    # 目前尚未建立 session/token，所以每次查詢都要帶身分資料。
    return list_available_certificates(
        db,
        name=payload.name,
        id_number=payload.id_number,
        user_id=payload.user_id,
        national_id=payload.national_id,
    )


@router.post("/generate")
def generate_certificates(
    payload: CertificateGenerateRequest,
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    # 使用者勾選一份或多份證書後，系統產生 PDF 或 ZIP。
    # 一份證書回傳 PDF，多份證書會自動打包成 ZIP。
    result = generate_certificate_package(
        db,
        name=payload.name,
        id_number=payload.id_number,
        user_id=payload.user_id,
        national_id=payload.national_id,
        record_ids=payload.record_ids,
    )

    if not result.generated or result.download_path is None or result.output_filename is None:
        raise HTTPException(status_code=400, detail=result.message)

    output_path = Path(result.download_path)
    media_type = "application/pdf" if result.output_type == "pdf" else "application/zip"

    return FileResponse(
        path=output_path,
        filename=result.output_filename,
        media_type=media_type,
    )
