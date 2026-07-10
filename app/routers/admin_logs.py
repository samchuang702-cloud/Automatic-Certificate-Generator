from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies.auth import require_roles
from app.db.session import get_db
from app.schemas.log import OperationLogListResult
from app.services.operation_logger import list_operation_logs


# 後台操作紀錄 API。
router = APIRouter(
    prefix="/admin/logs",
    tags=["admin-logs"],
    dependencies=[Depends(require_roles("admin"))],
)


@router.get("", response_model=OperationLogListResult)
def get_operation_logs(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> OperationLogListResult:
    # 回傳最近的後台操作紀錄。
    logs = list_operation_logs(db, limit=limit)
    return OperationLogListResult(total=len(logs), logs=logs)
