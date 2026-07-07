import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.operation_log import OperationLog


def create_operation_log(
    db: Session,
    action: str,
    filename: str | None = None,
    status: str = "success",
    detail: dict[str, Any] | None = None,
) -> OperationLog:
    # 將 dict 細節轉成 JSON 字串保存。
    # ensure_ascii=False 保留中文，後台查紀錄時比較容易閱讀。
    detail_text = json.dumps(detail, ensure_ascii=False) if detail is not None else None

    log = OperationLog(
        action=action,
        filename=filename,
        status=status,
        detail=detail_text,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def list_operation_logs(db: Session, limit: int = 50) -> list[OperationLog]:
    # 依照時間倒序回傳最近的操作紀錄。
    safe_limit = max(1, min(limit, 200))
    return db.scalars(
        select(OperationLog).order_by(OperationLog.created_at.desc()).limit(safe_limit)
    ).all()
