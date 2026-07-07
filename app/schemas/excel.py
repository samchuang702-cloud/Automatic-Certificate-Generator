from pydantic import BaseModel


class ExcelValidationError(BaseModel):
    # 錯誤發生的列號。
    # Excel 第 1 列通常是標題，所以資料列會從第 2 列開始。
    row: int | None = None

    # 錯誤發生的欄位名稱。
    # 如果是整份檔案層級的錯誤，例如缺少欄位，這裡可以是 None。
    column: str | None = None

    # 錯誤說明，提供給前端或後台管理者查看。
    message: str


class ExcelValidationResult(BaseModel):
    # 這份 Excel 是否通過目前欄位與資料格式檢查。
    is_valid: bool

    # Excel 中偵測到的欄位名稱。
    detected_columns: list[str]

    # 系統要求但 Excel 沒有提供的欄位。
    missing_columns: list[str]

    # Excel 有提供、但目前系統規格中沒有定義的欄位。
    extra_columns: list[str]

    # Excel 的資料筆數，不包含標題列。
    row_count: int

    # 詳細錯誤清單。
    errors: list[ExcelValidationError]


class ExcelUploadResult(BaseModel):
    # 檔案是否成功上傳並保存。
    # 只有 Excel 驗證通過時才會保存檔案。
    uploaded: bool

    # 管理者原本上傳的檔案名稱。
    original_filename: str

    # 系統保存後的檔案名稱。
    # 這個名稱會加上時間戳與隨機字串，避免檔名重複。
    saved_filename: str | None = None

    # 檔案保存位置。
    # 目前回傳相對路徑，避免把完整本機路徑暴露給 API 使用者。
    saved_path: str | None = None

    # Excel 欄位與資料格式驗證結果。
    validation: ExcelValidationResult


class ExcelPreviewResult(BaseModel):
    # 這次預覽的來源檔名。
    filename: str

    # Excel 欄位與資料格式驗證結果。
    validation: ExcelValidationResult

    # 預覽回傳的資料筆數。
    # 預覽筆數通常會小於或等於 Excel 總筆數。
    preview_count: int

    # Excel 前幾筆資料。
    # key 是欄位名稱，value 是該欄位的內容。
    rows: list[dict[str, str]]


class ExcelImportResult(BaseModel):
    # 是否成功完成匯入。
    imported: bool

    # 匯入來源檔名。
    filename: str

    # Excel 驗證結果。
    validation: ExcelValidationResult

    # 新增到資料庫的筆數。
    inserted_count: int

    # 更新既有資料的筆數。
    updated_count: int

    # 實際處理的資料筆數。
    processed_count: int
