from pydantic import BaseModel, Field


class CertificateListRequest(BaseModel):
    # 新版查詢使用姓名；保留 user_id 是為了相容舊版 API。
    name: str | None = Field(default=None, min_length=1, max_length=100)
    user_id: str | None = Field(default=None, min_length=1, max_length=100)

    # 新版欄位名稱是 id_number；保留 national_id 是為了相容舊版 API。
    id_number: str | None = Field(default=None, min_length=1, max_length=30)
    national_id: str | None = Field(default=None, min_length=1, max_length=30)


class CertificateListItem(BaseModel):
    # certificate_records 的主鍵，產生 PDF 時用來指定要下載哪幾張。
    record_id: int

    # 證書字號，會套到 CFD 模板的「證書字號」位置。
    certificate_id: str | None = None

    # 活動名稱，會套到 CFD 模板的「活動」位置。
    certificate_name: str

    # 姓名，會套到 CFD 模板的「姓名」位置。
    name: str

    # 發證或研習日期，會套到 CFD 模板的「日期」位置。
    issue_date: str

    # 種類，會套到 CFD 模板的「種類」位置。
    course_name: str | None = None

    # 預留欄位，保留原本系統支援。
    completion_date: str | None = None

    # 會保存顯示身分證、時數、單位等額外資料。
    note: str | None = None


class CertificateListResult(BaseModel):
    # 是否通過姓名與 ID 驗證。
    verified: bool

    # 前端顯示訊息。
    message: str

    # 資料庫中的查詢 ID；CFD Excel 會用完整身分證作為 user_id。
    user_id: str

    # 驗證成功時回傳姓名。
    name: str | None = None

    # 可產生證書數量。
    total: int = 0

    # 可勾選產生的證書清單。
    certificates: list[CertificateListItem] = []


class CertificateGenerateRequest(BaseModel):
    # 新版產生證書時仍需要姓名與 ID，再次做後端權限檢查。
    name: str | None = Field(default=None, min_length=1, max_length=100)
    user_id: str | None = Field(default=None, min_length=1, max_length=100)
    id_number: str | None = Field(default=None, min_length=1, max_length=30)
    national_id: str | None = Field(default=None, min_length=1, max_length=30)

    # 使用者勾選的 certificate_records.id。
    record_ids: list[int] = Field(min_length=1)


class CertificateGenerateResult(BaseModel):
    # 是否成功產生檔案。
    generated: bool

    # 回傳給前端顯示的結果訊息。
    message: str

    # 輸出類型：pdf 或 zip。
    output_type: str | None

    # 下載檔名。
    output_filename: str | None

    # 後端暫存檔案路徑。
    download_path: str | None

    # 此次產生的證書數量。
    certificate_count: int
