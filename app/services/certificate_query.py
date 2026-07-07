from sqlalchemy.orm import Session

from app.schemas.certificate import CertificateListItem, CertificateListResult
from app.services.identity_verifier import (
    find_records_by_lookup_name,
    find_records_by_name_and_id,
    resolve_lookup_inputs,
)


def list_available_certificates(
    db: Session,
    name: str | None = None,
    id_number: str | None = None,
    user_id: str | None = None,
    national_id: str | None = None,
) -> CertificateListResult:
    # 使用姓名與 ID 查詢可產生的證書；舊版 user_id/national_id 仍相容。
    lookup_name, _ = resolve_lookup_inputs(name, id_number, user_id, national_id)
    _, _, matched_records = find_records_by_name_and_id(
        db,
        name=name,
        id_number=id_number,
        user_id=user_id,
        national_id=national_id,
    )

    if not lookup_name:
        return CertificateListResult(
            verified=False,
            message="請輸入姓名與 ID。",
            user_id="",
        )

    if not matched_records:
        name_only_records = find_records_by_lookup_name(db, lookup_name)
        if name_only_records:
            return CertificateListResult(
                verified=False,
                message="身分證字號不符合。",
                user_id=lookup_name,
            )

        return CertificateListResult(
            verified=False,
            message="查無符合姓名與 ID 的資料。",
            user_id=lookup_name,
        )

    certificates = [
        CertificateListItem(
            record_id=record.id,
            certificate_id=record.certificate_id,
            certificate_name=record.certificate_name,
            name=record.name,
            issue_date=record.issue_date,
            course_name=record.course_name,
            completion_date=record.completion_date,
            note=record.note,
        )
        for record in matched_records
    ]

    return CertificateListResult(
        verified=True,
        message="證書清單查詢成功。",
        user_id=matched_records[0].user_id,
        name=matched_records[0].name,
        total=len(certificates),
        certificates=certificates,
    )
