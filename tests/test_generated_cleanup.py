import os
import time

from app.core.config import settings
from app.services.generated_cleanup import cleanup_old_generated_files


def test_cleanup_old_generated_files_removes_items_older_than_retention(tmp_path, monkeypatch) -> None:
    generated_dir = tmp_path / "generated"
    generated_dir.mkdir()
    old_batch = generated_dir / "GEN_old"
    old_batch.mkdir()
    old_pdf = old_batch / "old.pdf"
    old_pdf.write_bytes(b"old")
    recent_pdf = generated_dir / "recent.pdf"
    recent_pdf.write_bytes(b"recent")

    old_timestamp = time.time() - (91 * 24 * 60 * 60)
    os.utime(old_pdf, (old_timestamp, old_timestamp))
    os.utime(old_batch, (old_timestamp, old_timestamp))

    monkeypatch.setattr(settings, "generated_dir", str(generated_dir))

    summary = cleanup_old_generated_files(retention_days=90)

    assert summary["deleted"] == 1
    assert not old_batch.exists()
    assert recent_pdf.exists()


def test_cleanup_old_generated_files_ignores_missing_directory(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "generated_dir", str(tmp_path / "missing"))

    summary = cleanup_old_generated_files(retention_days=90)

    assert summary == {"deleted": 0, "failed": 0, "kept": 0}
