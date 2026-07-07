from __future__ import annotations

import shutil
import time
from pathlib import Path

from app.core.config import settings


def cleanup_old_generated_files(retention_days: int | None = None) -> dict[str, int]:
    # 只清理產出資料夾第一層項目，避免誤刪專案其他資料。
    generated_dir = Path(settings.generated_dir).resolve()
    days = settings.generated_retention_days if retention_days is None else retention_days
    summary = {"deleted": 0, "failed": 0, "kept": 0}

    if days < 0 or not generated_dir.exists():
        return summary

    cutoff_timestamp = time.time() - (days * 24 * 60 * 60)

    for item in generated_dir.iterdir():
        try:
            if item.resolve().parent != generated_dir:
                summary["kept"] += 1
                continue

            if item.stat().st_mtime >= cutoff_timestamp:
                summary["kept"] += 1
                continue

            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
            summary["deleted"] += 1
        except OSError:
            summary["failed"] += 1

    return summary
