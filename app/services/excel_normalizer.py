from io import BytesIO
import re

import pandas as pd

from app.core.excel_columns import EXCEL_COLUMN_ALIASES


NATIONAL_ID_PATTERN = re.compile(r"^[A-Z]\d{9}$")

# CFD 匯出檔常同時包含完整 ID 與顯示用遮罩 ID。
MASKED_NATIONAL_ID_PATTERN = re.compile(r"^[A-Z][0-9*]{9}$")

# 當 Excel 匯出後 ID 欄位變成未命名欄位時，使用此備援推測規則。
ID_LIKE_PATTERN = re.compile(r"^[A-Z0-9]{8,12}$")


def _clean_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def _clean_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    dataframe = dataframe.copy()
    dataframe.columns = [str(column).strip() for column in dataframe.columns]
    dataframe = dataframe.fillna("")
    return dataframe.map(lambda value: value.strip() if isinstance(value, str) else value)


def _first_existing(row: dict[str, object], candidates: list[str]) -> str:
    for column in candidates:
        if column in row:
            value = _clean_text(row[column])
            if value:
                return value
    return ""


def _find_full_national_id(row: dict[str, object]) -> str:
    # 優先使用已知欄名，再掃描整列；CFD 檔常把關鍵儲存格匯出成 Unnamed 欄位。
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
    # 僅作為推測規則：挑選最接近台灣身分證長度的第一個 ID-like 值。
    candidates: list[tuple[int, int, str]] = []

    for index, value in enumerate(row.values()):
        text = re.sub(r"[^A-Z0-9]", "", _clean_text(value).upper())
        if not text or not ID_LIKE_PATTERN.match(text):
            continue
        if not any(char.isdigit() for char in text):
            continue

        # 排除常見誤判：日期、民國日期片段與列號。
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
    # 保留 Excel 顯示值，讓證書可顯示遮罩 ID，同時驗證仍使用完整 ID。
    preferred_columns = ["身分證", "身分證1", "id_number_display"]
    for column in preferred_columns:
        value = _clean_text(row.get(column, "")).upper()
        if MASKED_NATIONAL_ID_PATTERN.match(value) and "*" in value:
            return value
    return ""


def _normalize_standard_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    dataframe = _clean_dataframe(dataframe)
    dataframe = dataframe.rename(columns=EXCEL_COLUMN_ALIASES)
    return dataframe


def _normalize_cfd_dataframe(dataframe: pd.DataFrame, sheet_name: str) -> pd.DataFrame:
    # 將醫院 CFD 工作簿格式轉成標準匯入共用的內部 schema。
    dataframe = _clean_dataframe(dataframe)
    normalized_rows: list[dict[str, str]] = []

    for _, raw_row in dataframe.iterrows():
        row = {str(column).strip(): raw_row[column] for column in dataframe.columns}
        national_id = _find_full_national_id(row)
        id_number_display = _find_masked_national_id(row) or national_id
        name = _first_existing(row, ["name", "姓名.1", "姓名", "Unnamed: 14"])
        activity = _first_existing(row, ["certificate_name", "活動", "Unnamed: 19"])
        issue_date = _first_existing(row, ["issue_date", "date", "日期", "代碼"])

        # 略過工作表頁尾、備註列與分隔列。
        if not any([national_id, name, activity, issue_date]):
            continue

        # 沒有完整 ID 的列無法支援身分驗證。
        if not national_id:
            continue

        unit = _first_existing(row, ["單位_報名表", "單位", "Unnamed: 15"])
        hours = _first_existing(row, ["時數", "Unnamed: 22"])
        category = _first_existing(row, ["種類", "B", "A", "Unnamed: 20", "Unnamed: 21"])
        certificate_id = _first_existing(row, ["certificate_id", "證書字號"])
        participation = _first_existing(row, ["參與方式"])

        # 模板專用資料放在 note，避免為每種來源格式擴充資料表欄位。
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
    # 每個工作表獨立正規化，因此可支援標準格式與 CFD 格式混合的工作簿。
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
    # 同時接受一般試算表日期與 CFD 證書使用的民國日期格式。
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
