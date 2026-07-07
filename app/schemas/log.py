from datetime import datetime

from pydantic import BaseModel


class OperationLogItem(BaseModel):
    # 操作紀錄 ID。
    id: int

    # 操作類型。
    action: str

    # 相關檔名。
    filename: str | None

    # 操作狀態。
    status: str

    # 操作細節。
    detail: str | None

    # 操作時間。
    created_at: datetime

    model_config = {"from_attributes": True}


class OperationLogListResult(BaseModel):
    # 回傳筆數。
    total: int

    # 操作紀錄清單。
    logs: list[OperationLogItem]
