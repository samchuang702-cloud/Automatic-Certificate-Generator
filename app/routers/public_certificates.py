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


router = APIRouter(prefix="/certificates", tags=["certificates"])


@router.post("/available", response_model=CertificateListResult)
def get_available_certificates(
    payload: CertificateListRequest,
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CertificateListResult:
    # 權杖只代表一般使用者層級權限，回傳資料仍需由姓名與 ID 限縮。
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
