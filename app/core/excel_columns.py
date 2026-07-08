# Excel 欄位的標準結構；匯入、驗證、正規化都應以此為準。


# 可識別人員、授權查詢並產出證書所需的最小欄位。
REQUIRED_EXCEL_COLUMNS = [
    "user_id",
    "national_id",
    "name",
    "certificate_name",
    "issue_date",
]


# 選填欄位有提供就匯入，但不得阻擋舊格式 Excel。
OPTIONAL_EXCEL_COLUMNS = [
    "certificate_id",
    "course_name",
    "completion_date",
    "note",
    "source_sheet",
]


# 驗證器接受的日期欄位；正規化後仍以字串保留來源語意。
DATE_COLUMNS = [
    "issue_date",
    "completion_date",
]


# 外部 Excel 可能使用不同欄名，需先正規化再驗證與保存。
EXCEL_COLUMN_ALIASES = {
    "id_number": "national_id",
    "date": "issue_date",
    "ID": "national_id",
    "身分證": "national_id",
    "身分證1": "national_id",
    "身分證2": "national_id",
    "姓名": "name",
    "活動": "certificate_name",
    "日期": "issue_date",
    "證書字號": "certificate_id",
    "種類": "course_name",
}
