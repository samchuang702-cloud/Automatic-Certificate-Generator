from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class CertificateGenerationRecord(Base):
    # 證書產生紀錄。
    # 每次使用者產生 PDF 或 ZIP 都會寫入一筆。
    __tablename__ = "certificate_generation_records"

    # 資料庫主鍵。
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # 使用者 ID。
    user_id: Mapped[str] = mapped_column(String(100), index=True)

    # 使用者姓名。
    name: Mapped[str] = mapped_column(String(100))

    # 被產生的 certificate_records.id 清單，以逗號分隔保存。
    record_ids: Mapped[str] = mapped_column(Text)

    # 產生的檔案名稱。
    output_filename: Mapped[str] = mapped_column(String(255))

    # 檔案類型：pdf 或 zip。
    output_type: Mapped[str] = mapped_column(String(20))

    # 產生幾份證書。
    certificate_count: Mapped[int] = mapped_column(Integer)

    # 建立時間。
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
