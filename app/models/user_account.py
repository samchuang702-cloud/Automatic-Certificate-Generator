from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class UserAccount(Base):
    # 系統登入帳號資料表。
    # role 用來做 RBAC 權限控管，例如 admin、county_staff、user。
    __tablename__ = "user_accounts"

    # 資料庫主鍵。
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # 登入帳號。
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)

    # 密碼雜湊值，不保存明文密碼。
    password_hash: Mapped[str] = mapped_column(String(255))

    # 角色欄位，RBAC 會依照這個欄位判斷權限。
    role: Mapped[str] = mapped_column(String(50), index=True)

    # 帳號顯示名稱。
    display_name: Mapped[str] = mapped_column(String(100))

    # 建立時間。
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
