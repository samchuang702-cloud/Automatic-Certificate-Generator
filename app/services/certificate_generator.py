import logging
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.certificate_generation import CertificateGenerationRecord
from app.models.certificate_record import CertificateRecord
from app.schemas.certificate import CertificateGenerateResult
from app.services.identity_verifier import find_records_by_name_and_id, resolve_lookup_inputs
from app.services.operation_logger import create_operation_log


logger = logging.getLogger(__name__)


class CertificateGenerationError(RuntimeError):
    # 領域錯誤會回傳給 API 呼叫端，但不暴露內部實作細節。
    pass


def _note_value(note: str | None, label: str) -> str:
    # 備註欄以「標籤：值」格式保存只供模板使用的欄位。
    if not note:
        return ""

    for part in note.split("；"):
        key, separator, value = part.partition("：")
        if separator and key.strip() == label:
            return value.strip()
    return ""


def _mask_national_id(value: str) -> str:
    if len(value) > 5:
        return f"{value[:5]}{'*' * (len(value) - 5)}"
    return value


def _masked_national_id(record: CertificateRecord) -> str:
    # 證書輸出統一顯示前 5 碼，其餘以星號遮罩。
    if record.national_id:
        return _mask_national_id(record.national_id)

    # 舊資料若只有 Excel 匯入的顯示值，仍維持可產出。
    masked_value = _note_value(record.note, "顯示身分證")
    if masked_value:
        return _mask_national_id(masked_value)
    return ""


def _certificate_data(record: CertificateRecord) -> dict[str, str]:
    # Word 模板替換共用同一份渲染資料。
    hours = _note_value(record.note, "時數")
    return {
        "name": record.name,
        "姓名": record.name,
        "id_number": record.national_id,
        "national_id": record.national_id,
        "身分證": _masked_national_id(record),
        "certificate_name": record.certificate_name,
        "活動": record.certificate_name,
        "course_name": record.course_name or "",
        "種類": record.course_name or "",
        "date": record.issue_date,
        "issue_date": record.issue_date,
        "日期": record.issue_date,
        "completion_date": record.completion_date or "",
        "certificate_id": record.certificate_id or "",
        "證書字號": record.certificate_id or "",
        "hours": hours,
        "時數": hours,
        "note": record.note or "",
    }


def _word_template_data(record: CertificateRecord) -> dict[str, object]:
    # 替換資料用 UTF-8 JSON 傳遞，讓 PowerShell 腳本不必承擔中文編碼細節。
    data = _certificate_data(record)
    data["word_replacements"] = [
        {"old": "(115)慈林醫訓(教)字第1530號", "new": data["證書字號"]},
        {"old": "王俊隆", "new": data["姓名"]},
        {"old": "M1206*****", "new": data["身分證"]},
        {"old": "民國115年05月19日", "new": data["日期"]},
        {"old": "全院學術演講_跨領域團隊合作照護會議", "new": data["活動"]},
        {"old": "共計1小時", "new": f"共計{data['時數']}小時"},
        {"old": "教學能力-跨領域團隊合作照護教學", "new": data["種類"]},
    ]
    return data


def _safe_filename_part(text: str) -> str:
    return "".join(char if char.isalnum() else "_" for char in text).strip("_") or "certificate"


def _render_word_template_pdf(record: CertificateRecord, output_path: Path) -> Path:
    # 主要產生器；刻意透過 PowerShell 隔離 Word COM 操作。
    template_path = Path(settings.certificate_word_template_path).resolve()
    script_path = Path("scripts/render_word_certificate.ps1").resolve()
    if not template_path.exists():
        message = f"Word 證書模板不存在：{template_path}"
        logger.error(message)
        raise CertificateGenerationError(message)
    if not script_path.exists():
        message = f"Word 產 PDF 腳本不存在：{script_path}"
        logger.error(message)
        raise CertificateGenerationError(message)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    data_path = output_path.with_suffix(".data.json")
    working_doc_path = output_path.with_suffix(".doc")
    error_path = output_path.with_suffix(".word_error.txt")

    data_path.write_text(
        json.dumps(_word_template_data(record), ensure_ascii=False),
        encoding="utf-8",
    )

    try:
        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script_path),
                "-TemplatePath",
                str(template_path),
                "-WorkingDocPath",
                str(working_doc_path.resolve()),
                "-DataPath",
                str(data_path.resolve()),
                "-OutputPath",
                str(output_path.resolve()),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
    except subprocess.TimeoutExpired as exc:
        logger.exception("Microsoft Word 產 PDF 逾時：template=%s output=%s", template_path, output_path)
        raise CertificateGenerationError("Microsoft Word 產 PDF 逾時，請確認 Word 沒有跳出視窗或卡住。") from exc
    except OSError as exc:
        logger.exception("無法啟動 PowerShell 或 Microsoft Word 產 PDF 腳本")
        raise CertificateGenerationError(f"無法啟動 PowerShell 或 Microsoft Word 產 PDF 腳本：{exc}") from exc
    finally:
        data_path.unlink(missing_ok=True)

    if result.returncode != 0:
        error_text = f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
        error_path.write_text(error_text, encoding="utf-8")
        logger.error("Microsoft Word 產 PDF 失敗：%s", error_text)
        raise CertificateGenerationError("Microsoft Word 產 PDF 失敗，請確認本機已安裝 Word，且模板可正常開啟。")

    working_doc_path.unlink(missing_ok=True)
    error_path.unlink(missing_ok=True)

    if not output_path.exists() or output_path.stat().st_size <= 0:
        message = f"Microsoft Word 沒有輸出有效 PDF：{output_path}"
        logger.error(message)
        raise CertificateGenerationError(message)

    return output_path


def generate_certificate_pdf(record: CertificateRecord, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{record.id}_{_safe_filename_part(record.certificate_name)}.pdf"
    output_path = output_dir / filename

    return _render_word_template_pdf(record, output_path)


def render_certificate_pdf(record: CertificateRecord, output_dir: Path) -> Path:
    # 對 router/test 保持穩定介面，實際 renderer 選擇留在本模組內。
    return generate_certificate_pdf(record, output_dir)


def generate_certificate_package(
    db: Session,
    record_ids: list[int],
    name: str | None = None,
    id_number: str | None = None,
    user_id: str | None = None,
    national_id: str | None = None,
) -> CertificateGenerateResult:
    # 後端重新驗證資料歸屬，不能只信任 request 傳入的 record IDs。
    lookup_name, lookup_id = resolve_lookup_inputs(name, id_number, user_id, national_id)
    unique_record_ids = list(dict.fromkeys(record_ids))

    if not unique_record_ids:
        return CertificateGenerateResult(
            generated=False,
            message="請至少選擇一份證書。",
            output_type=None,
            output_filename=None,
            download_path=None,
            certificate_count=0,
        )

    _, _, verified_records = find_records_by_name_and_id(
        db,
        name=name,
        id_number=id_number,
        user_id=user_id,
        national_id=national_id,
    )
    verified_ids = {record.id for record in verified_records}
    matched_records = [record for record in verified_records if record.id in unique_record_ids]

    if len(matched_records) != len(unique_record_ids):
        return CertificateGenerateResult(
            generated=False,
            message="查無可產生的證書，請確認身分資料與勾選項目。",
            output_type=None,
            output_filename=None,
            download_path=None,
            certificate_count=0,
        )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_identity = matched_records[0].user_id if matched_records else lookup_name or lookup_id
    batch_dir = Path(settings.generated_dir) / f"{output_identity}_{timestamp}"
    try:
        pdf_paths = [render_certificate_pdf(record, batch_dir) for record in matched_records]
    except CertificateGenerationError as exc:
        create_operation_log(
            db,
            action="certificate_generate",
            filename=None,
            status="failed",
            detail={
                "user_id": output_identity,
                "lookup_name": lookup_name,
                "lookup_id": lookup_id,
                "record_ids": unique_record_ids,
                "error": str(exc),
            },
        )
        return CertificateGenerateResult(
            generated=False,
            message=str(exc),
            output_type=None,
            output_filename=None,
            download_path=None,
            certificate_count=0,
        )
    except Exception as exc:
        logger.exception("PDF 產生失敗：user_id=%s record_ids=%s", output_identity, unique_record_ids)
        create_operation_log(
            db,
            action="certificate_generate",
            filename=None,
            status="failed",
            detail={
                "user_id": output_identity,
                "lookup_name": lookup_name,
                "lookup_id": lookup_id,
                "record_ids": unique_record_ids,
                "error": str(exc),
            },
        )
        return CertificateGenerateResult(
            generated=False,
            message="PDF 產生失敗，請聯絡管理員查看後端 log。",
            output_type=None,
            output_filename=None,
            download_path=None,
            certificate_count=0,
        )

    if len(pdf_paths) == 1:
        output_path = pdf_paths[0]
        output_type = "pdf"
    else:
        output_path = batch_dir / f"{output_identity}_{timestamp}_certificates.zip"
        with ZipFile(output_path, "w", compression=ZIP_DEFLATED) as zip_file:
            for pdf_path in pdf_paths:
                zip_file.write(pdf_path, arcname=pdf_path.name)
        output_type = "zip"

    generation_record = CertificateGenerationRecord(
        user_id=output_identity,
        name=matched_records[0].name,
        record_ids=",".join(str(record.id) for record in matched_records),
        output_filename=output_path.name,
        output_path=output_path.as_posix(),
        output_type=output_type,
        certificate_count=len(matched_records),
    )
    db.add(generation_record)
    db.commit()

    create_operation_log(
        db,
        action="certificate_generate",
        filename=output_path.name,
        status="success",
        detail={
            "user_id": output_identity,
            "lookup_name": lookup_name,
            "lookup_id": lookup_id,
            "record_ids": unique_record_ids,
            "verified_record_ids": sorted(verified_ids),
            "output_type": output_type,
            "certificate_count": len(matched_records),
        },
    )

    return CertificateGenerateResult(
        generated=True,
        message="證書產生成功。",
        output_type=output_type,
        output_filename=output_path.name,
        download_path=output_path.as_posix(),
        certificate_count=len(matched_records),
    )
