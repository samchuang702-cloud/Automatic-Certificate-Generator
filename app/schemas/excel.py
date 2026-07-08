from pydantic import BaseModel


class ExcelValidationError(BaseModel):
    # row 回報 Excel 表格列號，不使用 dataframe 從 0 開始的索引。
    row: int | None = None
    column: str | None = None
    message: str


class ExcelValidationResult(BaseModel):
    is_valid: bool
    detected_columns: list[str]
    missing_columns: list[str]
    extra_columns: list[str]
    row_count: int
    errors: list[ExcelValidationError]


class ExcelUploadResult(BaseModel):
    uploaded: bool
    original_filename: str

    # 保存檔名由後端產生，避免路徑穿越與檔名碰撞。
    saved_filename: str | None = None

    saved_path: str | None = None
    validation: ExcelValidationResult


class ExcelPreviewResult(BaseModel):
    filename: str
    validation: ExcelValidationResult
    preview_count: int
    rows: list[dict[str, str]]


class ExcelImportResult(BaseModel):
    imported: bool
    filename: str
    validation: ExcelValidationResult
    inserted_count: int
    updated_count: int
    processed_count: int
