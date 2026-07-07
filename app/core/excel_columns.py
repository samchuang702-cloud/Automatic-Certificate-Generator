# 這個檔案集中管理 Excel 欄位規格。
# 你目前還不確定最終會有幾個欄位，所以先用一組「最小可用欄位」開始。
# 未來要增減欄位時，優先修改這裡，不需要到處找驗證程式。


# 系統目前要求 Excel 一定要有的欄位。
# user_id：使用者輸入的 ID，用來查詢自己的資料。
# national_id：身分證字號，用來做第二層身分驗證。
# name：姓名，後續會套入證書模板。
# certificate_name：證書名稱，後續用來顯示可產生的證書清單。
# issue_date：證書日期，後續會套入 PDF。
REQUIRED_EXCEL_COLUMNS = [
    "user_id",
    "national_id",
    "name",
    "certificate_name",
    "issue_date",
]


# 這些欄位目前先允許出現在 Excel 中，但不是必填。
# certificate_id：之後如果同名證書很多，可以用代碼識別。
# course_name：如果證書跟課程或實習項目有關，可以記錄課程名稱。
# completion_date：如果結業日跟發證日不同，可以分開保存。
# note：備註欄位，方便管理者補充資訊。
OPTIONAL_EXCEL_COLUMNS = [
    "certificate_id",
    "course_name",
    "completion_date",
    "note",
    "source_sheet",
]


# 日期欄位需要能被 pandas 轉成日期。
# 先驗證 issue_date，之後有 completion_date 時也一起檢查。
DATE_COLUMNS = [
    "issue_date",
    "completion_date",
]


# Excel 欄位別名對應。
# 你的測試資料使用 id_number/date，系統內部使用 national_id/issue_date。
# 這裡集中轉換，讓不同 Excel 標題可以對應到同一套資料庫欄位。
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
