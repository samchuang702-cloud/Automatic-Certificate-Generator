from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.certificate_record import CertificateRecord
from app.schemas.auth import IdentityVerifyResult


def normalize_national_id(national_id: str) -> str:
    # ID 統一去空白並轉大寫，讓 a123456789 也能比對 A123456789。
    return national_id.strip().upper()


def resolve_lookup_inputs(
    name: str | None = None,
    id_number: str | None = None,
    user_id: str | None = None,
    national_id: str | None = None,
) -> tuple[str, str]:
    # 新版使用 name + id_number；舊版 user_id + national_id 仍可傳入。
    lookup_name = (name or user_id or "").strip()
    lookup_id = normalize_national_id(id_number or national_id or "")
    return lookup_name, lookup_id


def find_records_by_name_and_id(
    db: Session,
    name: str | None = None,
    id_number: str | None = None,
    user_id: str | None = None,
    national_id: str | None = None,
) -> tuple[str, str, list[CertificateRecord]]:
    # 先用姓名查詢；為了相容舊版，也允許 lookup_name 命中 user_id。
    lookup_name, lookup_id = resolve_lookup_inputs(name, id_number, user_id, national_id)
    if not lookup_name or not lookup_id:
        return lookup_name, lookup_id, []

    records = db.scalars(
        select(CertificateRecord)
        .where(
            or_(
                CertificateRecord.name == lookup_name,
                CertificateRecord.user_id == lookup_name,
            ),
            CertificateRecord.national_id == lookup_id,
        )
        .order_by(CertificateRecord.issue_date, CertificateRecord.id)
    ).all()

    return lookup_name, lookup_id, records


def find_records_by_lookup_name(
    db: Session,
    lookup_name: str,
) -> list[CertificateRecord]:
    # 只用姓名或舊版 user_id 查詢，用來判斷是 ID 錯誤還是完全查無此人。
    if not lookup_name:
        return []

    return db.scalars(
        select(CertificateRecord).where(
            or_(
                CertificateRecord.name == lookup_name,
                CertificateRecord.user_id == lookup_name,
            )
        )
    ).all()


def verify_identity(
    db: Session,
    name: str | None = None,
    id_number: str | None = None,
    user_id: str | None = None,
    national_id: str | None = None,
) -> IdentityVerifyResult:
    # 驗證使用者輸入的姓名與 ID 是否能對到資料庫中的證書紀錄。
    lookup_name, _, records = find_records_by_name_and_id(
        db,
        name=name,
        id_number=id_number,
        user_id=user_id,
        national_id=national_id,
    )

    if not lookup_name:
        return IdentityVerifyResult(
            verified=False,
            message="請輸入姓名與 ID。",
            user_id="",
        )

    if not records:
        name_only_records = find_records_by_lookup_name(db, lookup_name)
        if name_only_records:
            return IdentityVerifyResult(
                verified=False,
                message="身分證字號不符合。",
                user_id=lookup_name,
            )

        if user_id and not name:
            return IdentityVerifyResult(
                verified=False,
                message="查無此使用者 ID。",
                user_id=lookup_name,
            )

        return IdentityVerifyResult(
            verified=False,
            message="查無符合姓名與 ID 的資料。",
            user_id=lookup_name,
        )

    first_record = records[0]
    return IdentityVerifyResult(
        verified=True,
        message="身分驗證成功。",
        user_id=first_record.user_id,
        name=first_record.name,
        available_certificate_count=len(records),
    )
