from datetime import datetime, timedelta, timezone
import base64
import hashlib
import hmac
import json
import os
from typing import Any

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


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_access_token(payload: dict[str, Any]) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    body = {**payload, "exp": int(expires_at.timestamp())}

    header_part = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    body_part = _b64url_encode(json.dumps(body, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_part}.{body_part}".encode("ascii")
    signature = hmac.new(settings.jwt_secret_key.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{header_part}.{body_part}.{_b64url_encode(signature)}"


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        header_part, body_part, signature_part = token.split(".")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="JWT 格式錯誤。") from exc

    signing_input = f"{header_part}.{body_part}".encode("ascii")
    expected_signature = hmac.new(
        settings.jwt_secret_key.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()

    if not hmac.compare_digest(_b64url_encode(expected_signature), signature_part):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="JWT 簽章無效。")

    payload = json.loads(_b64url_decode(body_part))
    expires_at = int(payload.get("exp", 0))
    if expires_at < int(datetime.now(timezone.utc).timestamp()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="JWT 已過期。")

    return payload
