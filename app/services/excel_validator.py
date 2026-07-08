import re

from app.core.excel_columns import (
    DATE_COLUMNS,
    OPTIONAL_EXCEL_COLUMNS,
    REQUIRED_EXCEL_COLUMNS,
)
from app.schemas.excel import ExcelValidationError, ExcelValidationResult
from app.services.excel_normalizer import is_valid_issue_date, normalize_excel_dataframe


# 匯入器允許醫院特定 ID，因此這裡只做格式檢查，不做 checksum 驗證。
NATIONAL_ID_PATTERN = re.compile(r"^[A-Z]\d{9}$")
GENERIC_ID_PATTERN = re.compile(r"^(?=.*[A-Z])(?=.*\d)[A-Z0-9]{8,12}$")


def validate_excel_file(filename: str, file_content: bytes) -> ExcelValidationResult:
    if not filename.lower().endswith((".xlsx", ".xls")):
        return ExcelValidationResult(
            is_valid=False,
            detected_columns=[],
            missing_columns=REQUIRED_EXCEL_COLUMNS,
            extra_columns=[],
            row_count=0,
            errors=[
                ExcelValidationError(
                    message="檔案格式錯誤，請上傳 .xlsx 或 .xls Excel 檔案。"
                )
            ],
        )

    # 先正規化再驗證，讓標準格式與 CFD 工作簿共用同一套驗證規則。
    try:
        dataframe = normalize_excel_dataframe(file_content)
    except Exception as exc:
        return ExcelValidationResult(
            is_valid=False,
            detected_columns=[],
            missing_columns=REQUIRED_EXCEL_COLUMNS,
            extra_columns=[],
            row_count=0,
            errors=[
                ExcelValidationError(
                    message=f"Excel 讀取失敗，請確認檔案未損毀且格式正確：{exc}"
                )
            ],
        )

    dataframe = dataframe.fillna("").map(lambda value: value.strip() if isinstance(value, str) else value)

    detected_columns = list(dataframe.columns)
    allowed_columns = set(REQUIRED_EXCEL_COLUMNS + OPTIONAL_EXCEL_COLUMNS)
    missing_columns = [column for column in REQUIRED_EXCEL_COLUMNS if column not in detected_columns]
    extra_columns = [column for column in detected_columns if column not in allowed_columns]

    errors: list[ExcelValidationError] = []

    # 即使缺欄位也繼續收集錯誤，讓管理者一次看到完整匯入報告。
    for column in missing_columns:
        errors.append(
            ExcelValidationError(
                column=column,
                message=f"缺少必要欄位：{column}",
            )
        )

    for column in REQUIRED_EXCEL_COLUMNS:
        if column not in dataframe.columns:
            continue

        empty_rows = dataframe.index[dataframe[column].astype(str).str.strip() == ""].tolist()
        for row_index in empty_rows:
            errors.append(
                ExcelValidationError(
                    row=row_index + 2,
                    column=column,
                    message=f"{column} 是必填欄位，不可空白。",
                )
            )

    if "national_id" in dataframe.columns:
        for row_index, value in dataframe["national_id"].items():
            national_id = str(value).strip().upper()
            if (
                national_id
                and not NATIONAL_ID_PATTERN.match(national_id)
                and not GENERIC_ID_PATTERN.match(national_id)
            ):
                errors.append(
                    ExcelValidationError(
                        row=row_index + 2,
                        column="national_id",
                        message="ID 格式錯誤，格式應為 8 到 12 碼英數混合內容。",
                    )
                )

    for column in DATE_COLUMNS:
        if column not in dataframe.columns:
            continue

        invalid_rows = [
            row_index
            for row_index, value in dataframe[column].items()
            if str(value).strip() and not is_valid_issue_date(str(value))
        ]
        for row_index in invalid_rows:
            errors.append(
                ExcelValidationError(
                    row=row_index + 2,
                    column=column,
                    message=f"{column} 日期格式錯誤，請使用 YYYY-MM-DD 或 Excel 日期格式。",
                )
            )

    return ExcelValidationResult(
        is_valid=len(errors) == 0,
        detected_columns=detected_columns,
        missing_columns=missing_columns,
        extra_columns=extra_columns,
        row_count=len(dataframe),
        errors=errors,
    )
