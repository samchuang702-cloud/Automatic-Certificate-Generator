from pydantic import BaseModel, Field


class CertificateListRequest(BaseModel):
    # 保留 user_id/national_id，讓舊版前端與 API 呼叫仍可相容。
    name: str | None = Field(default=None, min_length=1, max_length=100)
    user_id: str | None = Field(default=None, min_length=1, max_length=100)
    id_number: str | None = Field(default=None, min_length=1, max_length=30)
    national_id: str | None = Field(default=None, min_length=1, max_length=30)


class CertificateListItem(BaseModel):
    record_id: int
    certificate_id: str | None = None
    certificate_name: str
    name: str
    issue_date: str
    course_name: str | None = None
    completion_date: str | None = None
    note: str | None = None


class CertificateListResult(BaseModel):
    verified: bool
    message: str
    user_id: str
    name: str | None = None
    total: int = 0
    certificates: list[CertificateListItem] = []


class CertificateGenerateRequest(BaseModel):
    # 產生證書時重新帶入身分欄位，後端可再次限制 record_ids 的資料範圍。
    name: str | None = Field(default=None, min_length=1, max_length=100)
    user_id: str | None = Field(default=None, min_length=1, max_length=100)
    id_number: str | None = Field(default=None, min_length=1, max_length=30)
    national_id: str | None = Field(default=None, min_length=1, max_length=30)
    record_ids: list[int] = Field(min_length=1)


class CertificateGenerateResult(BaseModel):
    generated: bool
    message: str
    output_type: str | None
    output_filename: str | None
    download_path: str | None
    certificate_count: int
