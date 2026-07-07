from pydantic import BaseModel, Field


class IdentityVerifyRequest(BaseModel):
    # 新版查詢使用姓名；保留 user_id 是為了相容舊版前端與測試。
    name: str | None = Field(default=None, min_length=1, max_length=100)
    user_id: str | None = Field(default=None, min_length=1, max_length=100)

    # 新版欄位名稱是 id_number；保留 national_id 是為了相容舊版 API。
    id_number: str | None = Field(default=None, min_length=1, max_length=30)
    national_id: str | None = Field(default=None, min_length=1, max_length=30)


class IdentityVerifyResult(BaseModel):
    # 是否通過身分驗證。
    verified: bool

    # 回傳給前端顯示的結果訊息。
    message: str

    # 資料庫中的使用者查詢 ID；CFD Excel 會用完整身分證作為 user_id。
    user_id: str

    # 驗證成功時回傳姓名；失敗時為 None。
    name: str | None = None

    # 驗證成功時可產生的證書數量。
    available_certificate_count: int = 0
