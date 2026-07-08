from datetime import datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class CertificateRecord(Base):
    __tablename__ = "certificate_records"

    # 重複匯入同一使用者同一證書時更新既有列，避免產生重複資料。
    __table_args__ = (
        UniqueConstraint("user_id", "certificate_name", name="uq_user_certificate"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(100), index=True)
    national_id: Mapped[str] = mapped_column(String(20), index=True)
    name: Mapped[str] = mapped_column(String(100))
    certificate_name: Mapped[str] = mapped_column(String(200), index=True)

    # 日期保留來源文字，因為證書可能使用民國格式或顯示用後綴。
    issue_date: Mapped[str] = mapped_column(String(50))

    certificate_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    course_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    completion_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # 保留來源檔名，方便支援與稽核時追查匯入來源。
    source_filename: Mapped[str] = mapped_column(String(255))

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
    )
