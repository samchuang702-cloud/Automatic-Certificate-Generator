from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class OperationLog(Base):
    # 後台與系統操作紀錄。
    # 目前用來記錄 Excel 上傳、匯入、證書產生等重要事件。
    __tablename__ = "operation_logs"

    # 資料庫主鍵。
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # 操作類型，例如 excel_upload、excel_import、certificate_generate。
    action: Mapped[str] = mapped_column(String(100), index=True)

    # 相關檔名，沒有檔案時可以為 NULL。
    filename: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # 操作是否成功。
    status: Mapped[str] = mapped_column(String(50), default="success")

    # 操作細節，先用文字保存 JSON 字串，方便 SQLite 簡單使用。
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 操作時間。
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
