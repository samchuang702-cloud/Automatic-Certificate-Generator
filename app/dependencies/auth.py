from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user_account import UserAccount


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> UserAccount:
    # 從 Authorization: Bearer <token> 解析目前登入使用者。
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="請先登入。")

    payload = decode_access_token(credentials.credentials)
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="JWT 缺少使用者資訊。")

    user = db.scalar(select(UserAccount).where(UserAccount.username == username))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="使用者不存在。")

    return user


def require_roles(*allowed_roles: str) -> Callable[[UserAccount], UserAccount]:
    # 建立 role-based dependency。
    # 路由使用 Depends(require_roles("admin", "county_staff")) 即可限制角色。
    def dependency(current_user: UserAccount = Depends(get_current_user)) -> UserAccount:
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="權限不足。")
        return current_user

    return dependency
