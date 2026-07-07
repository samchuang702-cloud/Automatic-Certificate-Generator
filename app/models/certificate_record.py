from datetime import datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class CertificateRecord(Base):
    # 這張表存放從 Excel 匯入的「使用者可產生證書」資料。
    # 後續 Module 6 身分驗證、Module 7 證書清單查詢都會讀這張表。
    __tablename__ = "certificate_records"

    # 同一個使用者同一張證書只保留一筆。
    # 重複匯入時會更新既有資料，不新增重複列。
    __table_args__ = (
        UniqueConstraint("user_id", "certificate_name", name="uq_user_certificate"),
    )

    # 資料庫主鍵。
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # 使用者 ID，使用者查詢自己證書時會輸入這個值。
    user_id: Mapped[str] = mapped_column(String(100), index=True)

    # 身分證字號，目前先明文保存。
    # Module 12 會再處理更完整的資安策略，例如遮罩、加密或雜湊。
    national_id: Mapped[str] = mapped_column(String(20), index=True)

    # 使用者姓名，後續會套入證書模板。
    name: Mapped[str] = mapped_column(String(100))

    # 證書名稱，後續會顯示在可產生證書清單。
    certificate_name: Mapped[str] = mapped_column(String(200), index=True)

    # 發證日期，先用字串保存，保留 Excel 原始語意。
    # 後續若日期規則穩定，可以改成 Date 欄位。
    issue_date: Mapped[str] = mapped_column(String(50))

    # 選填證書代碼。
    certificate_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # 選填課程或實習項目名稱。
    course_name: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # 選填完成日期。
    completion_date: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # 選填備註。
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # 來源 Excel 檔名，方便追蹤資料從哪次匯入而來。
    source_filename: Mapped[str] = mapped_column(String(255))

    # 建立時間。
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # 最後更新時間。
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
    )
