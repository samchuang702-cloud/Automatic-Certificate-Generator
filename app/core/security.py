from datetime import datetime, timedelta, timezone
import base64
import hashlib
import hmac
import os
from typing import Any

import jwt
from fastapi import HTTPException, status

from app.core.config import settings


def hash_password(password: str) -> str:
    # salt 與 digest 合併保存，避免為密碼雜湊拆出多個欄位。
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return base64.urlsafe_b64encode(salt + digest).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        decoded = base64.urlsafe_b64decode(password_hash.encode("ascii"))
    except Exception:
        return False

    if len(decoded) <= 32:
        return False

    salt = decoded[:16]
    expected_digest = decoded[16:]
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return hmac.compare_digest(digest, expected_digest)


def create_access_token(payload: dict[str, Any]) -> str:
    """
    使用 PyJWT 生成安全的 JWT token。
    
    使用經過 RFC 審計的 PyJWT 庫替代自定義實現，提升安全性。
    """
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload_with_exp = {**payload, "exp": expires_at}
    
    return jwt.encode(
        payload_with_exp,
        settings.jwt_secret_key,
        algorithm="HS256"
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """
    使用 PyJWT 驗證和解碼 JWT token。
    
    自動處理簽章驗證、過期檢查和所有邊界情況。
    """
    try:
        return jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=["HS256"]
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="JWT 已過期。"
        )
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="JWT 無效或簽章錯誤。"
        ) from exc
