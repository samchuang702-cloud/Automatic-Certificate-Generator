from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    # 登入帳號。
    username: str = Field(min_length=1, max_length=100)

    # 登入密碼。
    password: str = Field(min_length=1, max_length=100)


class LoginResult(BaseModel):
    # JWT access token。
    access_token: str

    # token 類型，前端會用 Bearer 放進 Authorization header。
    token_type: str = "bearer"

    # 帳號資訊。
    username: str
    display_name: str
    role: str


class CurrentUserResult(BaseModel):
    # 目前登入者資訊。
    username: str
    display_name: str
    role: str
