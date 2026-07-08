from pydantic import BaseModel, Field


class IdentityVerifyRequest(BaseModel):
    # 保留 user_id/national_id，讓舊版前端與 API 呼叫仍可相容。
    name: str | None = Field(default=None, min_length=1, max_length=100)
    user_id: str | None = Field(default=None, min_length=1, max_length=100)
    id_number: str | None = Field(default=None, min_length=1, max_length=30)
    national_id: str | None = Field(default=None, min_length=1, max_length=30)


class IdentityVerifyResult(BaseModel):
    verified: bool
    message: str
    user_id: str
    name: str | None = None
    available_certificate_count: int = 0
