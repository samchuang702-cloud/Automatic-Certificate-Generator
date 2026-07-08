from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class CertificateGenerationRecord(Base):
    __tablename__ = "certificate_generation_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(100), index=True)
    name: Mapped[str] = mapped_column(String(100))

    # 目前只需輕量稽核紀錄，暫不為產出紀錄建立額外關聯表。
    record_ids: Mapped[str] = mapped_column(Text)

    output_filename: Mapped[str] = mapped_column(String(255))

    # 只保存檔案路徑，PDF/ZIP 不以二進位形式寫進資料庫。
    output_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    output_type: Mapped[str] = mapped_column(String(20))
    certificate_count: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
