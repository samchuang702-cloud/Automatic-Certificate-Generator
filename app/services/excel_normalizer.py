from io import BytesIO
import re

import pandas as pd

from app.core.excel_columns import EXCEL_COLUMN_ALIASES


# 完整 ID 格式，例如 A123456789、U900002704。
NATIONAL_ID_PATTERN = re.compile(r"^[A-Z]\d{9}$")

# CFD Excel 內常見的遮罩身分證格式，例如 Q2235*****、T2********。
MASKED_NATIONAL_ID_PATTERN = re.compile(r"^[A-Z][0-9*]{9}$")

# 沒有明確 ID 欄名時，從內容長度接近 10 的欄位推測 ID。
ID_LIKE_PATTERN = re.compile(r"^[A-Z0-9]{8,12}$")


def _clean_text(value: object) -> str:
    # 把 Excel 儲存格轉成乾淨文字，空值統一回傳空字串。
    if pd.isna(value):
        return ""
    return str(value).strip()


def _clean_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    # 清理欄位名稱與儲存格前後空白，讓後續欄位比對更穩定。
    dataframe = dataframe.copy()
    dataframe.columns = [str(column).strip() for column in dataframe.columns]
    dataframe = dataframe.fillna("")
    return dataframe.map(lambda value: value.strip() if isinstance(value, str) else value)


def _first_existing(row: dict[str, object], candidates: list[str]) -> str:
    # 依照候選欄位順序取第一個有值的欄位。
    for column in candidates:
        if column in row:
            value = _clean_text(row[column])
            if value:
                return value
    return ""


def _find_full_national_id(row: dict[str, object]) -> str:
    # 優先從明確欄位抓完整身分證，再掃描整列避免 Unnamed 欄位漏掉。
    preferred_columns = [
        "national_id",
        "id_number",
        "ID",
        "身分證2",
        "身分證1",
        "身分證",
        "Unnamed: 12",
        "Unnamed: 13",
    ]
    for column in preferred_columns:
        value = _clean_text(row.get(column, "")).upper()
        if NATIONAL_ID_PATTERN.match(value):
            return value

    for value in row.values():
        text = _clean_text(value).upper()
        if NATIONAL_ID_PATTERN.match(text):
            return text

    inferred_id = _find_length_similar_id(row)
    if inferred_id:
        return inferred_id

    return ""


def _find_length_similar_id(row: dict[str, object]) -> str:
    # 如果資料表沒有 ID 欄名，就挑選內容長度最接近身分證長度的欄位作為 ID。
    candidates: list[tuple[int, int, str]] = []

    for index, value in enumerate(row.values()):
        text = re.sub(r"[^A-Z0-9]", "", _clean_text(value).upper())
        if not text or not ID_LIKE_PATTERN.match(text):
            continue
        if not any(char.isdigit() for char in text):
            continue

        # 排除日期、民國年月、序號等常見非 ID 值。
        if text.isdigit() and len(text) <= 8:
            continue
        if re.match(r"^\d{2,3}0?\d{1,2}0?\d{1,2}$", text):
            continue

        length_distance = abs(len(text) - 10)
        candidates.append((length_distance, index, text))

    if not candidates:
        return ""

    candidates.sort(key=lambda item: (item[0], item[1]))
    return candidates[0][2]


def _find_masked_national_id(row: dict[str, object]) -> str:
    # 模板上的身分證通常用遮罩格式，優先保留 Excel 原本顯示值。
    preferred_columns = ["身分證", "身分證1", "id_number_display"]
    for column in preferred_columns:
        value = _clean_text(row.get(column, "")).upper()
        if MASKED_NATIONAL_ID_PATTERN.match(value) and "*" in value:
            return value
    return ""


def _normalize_standard_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    # 支援原本標準欄位格式，透過 aliases 轉成系統內部欄位名稱。
    dataframe = _clean_dataframe(dataframe)
    dataframe = dataframe.rename(columns=EXCEL_COLUMN_ALIASES)
    return dataframe


def _normalize_cfd_dataframe(dataframe: pd.DataFrame, sheet_name: str) -> pd.DataFrame:
    # 將 CFD Excel 欄位轉成系統通用格式。
    dataframe = _clean_dataframe(dataframe)
    normalized_rows: list[dict[str, str]] = []

    for _, raw_row in dataframe.iterrows():
        row = {str(column).strip(): raw_row[column] for column in dataframe.columns}
        national_id = _find_full_national_id(row)
        id_number_display = _find_masked_national_id(row) or national_id
        name = _first_existing(row, ["name", "姓名.1", "姓名", "Unnamed: 14"])
        activity = _first_existing(row, ["certificate_name", "活動", "Unnamed: 19"])
        issue_date = _first_existing(row, ["issue_date", "date", "日期", "代碼"])

        # 空白列直接略過，避免表尾或註記列被匯入。
        if not any([national_id, name, activity, issue_date]):
            continue

        # 系統驗證身分必須使用完整身分證，只有遮罩值的列無法用於登入驗證。
        if not national_id:
            continue

        unit = _first_existing(row, ["單位_報名表", "單位", "Unnamed: 15"])
        hours = _first_existing(row, ["時數", "Unnamed: 22"])
        category = _first_existing(row, ["種類", "B", "A", "Unnamed: 20", "Unnamed: 21"])
        certificate_id = _first_existing(row, ["certificate_id", "證書字號"])
        participation = _first_existing(row, ["參與方式"])

        # note 保存模板需要但資料庫目前沒有獨立欄位的資料。
        note_parts = []
        for label, value in [
            ("顯示身分證", id_number_display),
            ("單位", unit),
            ("時數", hours),
            ("參與方式", participation),
            ("來源工作表", sheet_name),
        ]:
            if value:
                note_parts.append(f"{label}：{value}")

        normalized_rows.append(
            {
                # CFD Excel 沒有獨立使用者 ID，先用完整身分證作為查詢 ID。
                "user_id": _first_existing(row, ["user_id"]) or national_id,
                "national_id": national_id,
                "name": name,
                "certificate_name": activity,
                "issue_date": issue_date,
                "certificate_id": certificate_id,
                "course_name": category,
                "completion_date": "",
                "note": "；".join(note_parts),
                "source_sheet": sheet_name,
            }
        )

    return pd.DataFrame(normalized_rows)


def normalize_excel_dataframe(file_content: bytes) -> pd.DataFrame:
    # 讀取所有工作表，逐一判斷是標準格式或 CFD 格式。
    workbook = pd.read_excel(BytesIO(file_content), dtype=str, sheet_name=None)
    normalized_frames: list[pd.DataFrame] = []

    for sheet_name, dataframe in workbook.items():
        standard_dataframe = _normalize_standard_dataframe(dataframe)
        if {"user_id", "national_id", "name", "certificate_name", "issue_date"}.issubset(
            set(standard_dataframe.columns)
        ):
            standard_dataframe["source_sheet"] = sheet_name
            normalized_frames.append(standard_dataframe)
            continue

        normalized_frames.append(_normalize_cfd_dataframe(dataframe, sheet_name))

    if not normalized_frames:
        return pd.DataFrame()

    result = pd.concat(normalized_frames, ignore_index=True)
    result = result.fillna("")
    return result.map(lambda value: value.strip() if isinstance(value, str) else str(value))


def is_valid_issue_date(value: str) -> bool:
    # 支援西元日期、民國文字日期與 115.05.23 這類 CFD 日期格式。
    text = value.strip()
    if not text:
        return True

    roc_patterns = [
        r"^民國\d{2,3}年\d{1,2}月\d{1,2}.*日$",
        r"^\d{2,3}\.\d{1,2}\.\d{1,2}.*$",
    ]
    if any(re.match(pattern, text) for pattern in roc_patterns):
        return True

    return not pd.isna(pd.to_datetime(text, errors="coerce"))
