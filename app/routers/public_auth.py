from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_user
from app.db.session import get_db
from app.models.user_account import UserAccount
from app.schemas.account import CurrentUserResult, LoginRequest, LoginResult
from app.schemas.auth import IdentityVerifyRequest, IdentityVerifyResult
from app.services.account_service import authenticate_user, issue_user_identity_token
from app.services.identity_verifier import verify_identity


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResult)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResult:
    result = authenticate_user(db, payload.username, payload.password)
    if result is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="帳號或密碼錯誤。")
    return result


@router.post("/login/identity", response_model=LoginResult)
def login_with_identity(payload: IdentityVerifyRequest, db: Session = Depends(get_db)) -> LoginResult:
    # 身分登入只授予共用低權限 user 角色。
    identity = verify_identity(
        db,
        name=payload.name,
        id_number=payload.id_number,
        user_id=payload.user_id,
        national_id=payload.national_id,
    )
    if not identity.verified:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=identity.message)

    result = issue_user_identity_token(db, identity.name or payload.name or payload.user_id or "一般使用者")
    if result is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="使用者登入設定尚未建立。")

    return result


@router.get("/me", response_model=CurrentUserResult)
def get_me(current_user: UserAccount = Depends(get_current_user)) -> CurrentUserResult:
    return CurrentUserResult(
        username=current_user.username,
        display_name=current_user.display_name,
        role=current_user.role,
    )


@router.post("/verify", response_model=IdentityVerifyResult)
def verify_user_identity(
    payload: IdentityVerifyRequest,
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> IdentityVerifyResult:
    return verify_identity(
        db,
        name=payload.name,
        id_number=payload.id_number,
        user_id=payload.user_id,
        national_id=payload.national_id,
    )
