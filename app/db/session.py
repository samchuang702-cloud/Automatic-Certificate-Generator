from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    # 所有 SQLAlchemy model 都繼承這個 Base。
    pass


# SQLite 資料庫檔案放在 storage/database。
database_path = settings.database_url.replace("sqlite:///", "")
if database_path and database_path != ":memory:":
    Path(database_path).parent.mkdir(parents=True, exist_ok=True)


# SQLite 在 FastAPI 多 request/thread 下需要 check_same_thread=False。
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)


# 每次 API request 會建立一個 session，用完後由 get_db 關閉。
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_db_and_tables() -> None:
    # 匯入 app.models 讓 SQLAlchemy 註冊所有資料表。
    import app.models  # noqa: F401

    # 開發階段直接 create_all；正式環境可改 Alembic migration。
    Base.metadata.create_all(bind=engine)

    # 建立預設登入帳號。
    from app.services.account_service import seed_default_users

    db = SessionLocal()
    try:
        seed_default_users(db)
    finally:
        db.close()


def get_db():
    # FastAPI dependency：提供每個 request 一個資料庫 session。
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
