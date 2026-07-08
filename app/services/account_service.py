from sqlalchemy import select
from sqlalchemy.orm import Session
import os

from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user_account import UserAccount
from app.schemas.account import LoginResult


# 預設帳號供本機操作使用，密碼仍可透過環境變數覆寫。
DEFAULT_USERS = [
    {
        "username": "admin",
        "password": os.getenv("DEFAULT_ADMIN_PASSWORD", "admin123"),
        "display_name": "系統管理者",
        "role": "admin",
    },
    {
        "username": "county",
        "password": os.getenv("DEFAULT_COUNTY_PASSWORD", "county123"),
        "display_name": "縣市承辦人員",
        "role": "county_staff",
    },
    {
        "username": "user",
        "password": os.getenv("DEFAULT_USER_PASSWORD", "user123"),
        "display_name": "一般使用者",
        "role": "user",
    },
]


def seed_default_users(db: Session) -> None:
    # 本機 demo 需保持可預期；生產環境則避免意外覆蓋正式帳密。
    for user_data in DEFAULT_USERS:
        existing_user = db.scalar(
            select(UserAccount).where(UserAccount.username == user_data["username"])
        )
        if existing_user:
            if settings.app_env != "production":
                existing_user.password_hash = hash_password(user_data["password"])
                existing_user.display_name = user_data["display_name"]
                existing_user.role = user_data["role"]
            continue

        db.add(
            UserAccount(
                username=user_data["username"],
                password_hash=hash_password(user_data["password"]),
                display_name=user_data["display_name"],
                role=user_data["role"],
            )
        )
    db.commit()


def _login_result_for_user(user: UserAccount, display_name: str | None = None) -> LoginResult:
    result_display_name = display_name or user.display_name
    token = create_access_token(
        {
            "sub": user.username,
            "role": user.role,
            "display_name": result_display_name,
        }
    )
    return LoginResult(
        access_token=token,
        username=user.username,
        display_name=result_display_name,
        role=user.role,
    )


def authenticate_user(db: Session, username: str, password: str) -> LoginResult | None:
    cleaned_username = username.strip().replace("\ufeff", "")
    cleaned_password = password.strip().replace("\ufeff", "")
    user = db.scalar(select(UserAccount).where(UserAccount.username == cleaned_username))
    if not user or not verify_password(cleaned_password, user.password_hash):
        return None

    return _login_result_for_user(user)


def issue_user_identity_token(db: Session, display_name: str) -> LoginResult | None:
    # 姓名/ID 驗證成功後映射到共用低權限帳號，權限仍由角色控管。
    user = db.scalar(select(UserAccount).where(UserAccount.username == "user"))
    if not user:
        return None

    return _login_result_for_user(user, display_name=display_name)
