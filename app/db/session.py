from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


database_path = settings.database_url.replace("sqlite:///", "")
if database_path and database_path != ":memory:":
    Path(database_path).parent.mkdir(parents=True, exist_ok=True)


# FastAPI 請求可能跨執行緒處理，因此 SQLite 連線需允許跨執行緒使用。
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_db_and_tables() -> None:
    # 匯入 app.models 是為了在 create_all 前註冊所有 SQLAlchemy model。
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_lightweight_schema_updates()

    from app.services.account_service import seed_default_users

    db = SessionLocal()
    try:
        seed_default_users(db)
    finally:
        db.close()


def _ensure_lightweight_schema_updates() -> None:
    # 這是小型本機系統，先用最小 ALTER 保持舊 SQLite 檔可用，不引入 Alembic。
    inspector = inspect(engine)
    if "certificate_generation_records" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("certificate_generation_records")}
    if "output_path" not in columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE certificate_generation_records ADD COLUMN output_path VARCHAR(500)"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
