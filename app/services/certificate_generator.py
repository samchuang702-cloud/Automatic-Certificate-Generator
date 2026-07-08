import logging
import json
import re
import subprocess
from datetime import datetime
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from pypdf import PdfReader, PdfWriter
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.certificate_generation import CertificateGenerationRecord
from app.models.certificate_record import CertificateRecord
from app.schemas.certificate import CertificateGenerateResult
from app.services.certificate_template import load_certificate_template, render_template_text
from app.services.identity_verifier import find_records_by_name_and_id, resolve_lookup_inputs
from app.services.operation_logger import create_operation_log


logger = logging.getLogger(__name__)

FONT_NAME = "MicrosoftJhengHei"
FONT_PATH = "C:/Windows/Fonts/msjh.ttc"
KAI_FONT_NAME = "DFKaiShu"
KAI_FONT_PATH = "C:/Windows/Fonts/kaiu.ttf"


class CertificateGenerationError(RuntimeError):
    # 領域錯誤會回傳給 API 呼叫端，但不暴露內部實作細節。
    pass


def register_certificate_font() -> str:
    # ReportLab 繪製中文前必須先註冊中日韓字型。
    if FONT_NAME not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(FONT_NAME, FONT_PATH))
    return FONT_NAME


def register_kai_font() -> str:
    if Path(KAI_FONT_PATH).exists() and KAI_FONT_NAME not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(KAI_FONT_NAME, KAI_FONT_PATH))
    return KAI_FONT_NAME if Path(KAI_FONT_PATH).exists() else register_certificate_font()


def _note_value(note: str | None, label: str) -> str:
    # 備註欄以「標籤：值」格式保存只供模板使用的欄位。
    if not note:
        return ""

    for part in note.split("；"):
        key, separator, value = part.partition("：")
        if separator and key.strip() == label:
            return value.strip()
    return ""


def _masked_national_id(record: CertificateRecord) -> str:
    # 優先使用 Excel 匯入的遮罩值；沒有遮罩時仍讓舊資料可被產出。
    masked_value = _note_value(record.note, "顯示身分證")
    if masked_value:
        return masked_value
    if len(record.national_id) > 5:
        return f"{record.national_id[:5]}*****"
    return record.national_id


def _certificate_data(record: CertificateRecord) -> dict[str, str]:
    # Word 替換、PDF 疊字與備援產生器共用同一份渲染資料。
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


def _issue_date_parts(issue_date: str) -> tuple[str, str, str]:
    # 證書輸出需要民國年月日元件，但匯入資料可能是民國文字、點分格式或 ISO 日期。
    text = issue_date.strip()
    roc_match = re.search(r"民國\s*(\d{2,3})年\s*(\d{1,2})月\s*(\d{1,2})", text)
    if roc_match:
        year, month, day = roc_match.groups()
        return year, month.zfill(2), day.zfill(2)

    dotted_match = re.search(r"(\d{2,3})\.(\d{1,2})\.(\d{1,2})", text)
    if dotted_match:
        year, month, day = dotted_match.groups()
        return year, month.zfill(2), day.zfill(2)

    iso_match = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", text)
    if iso_match:
        year, month, day = iso_match.groups()
        return str(int(year) - 1911), month.zfill(2), day.zfill(2)

    return "", "", ""


def _roc_date_text(issue_date: str) -> str:
    year, month, day = _issue_date_parts(issue_date)
    if year and month and day:
        return f"民國{year}年{month}月{day}日"
    return issue_date


def _safe_filename_part(text: str) -> str:
    return "".join(char if char.isalnum() else "_" for char in text).strip("_") or "certificate"


def _wrap_text(text: str, max_width: float, font_name: str, font_size: int) -> list[str]:
    # 中文通常沒有空白分詞，換行必須逐字量測寬度。
    lines: list[str] = []
    current = ""

    for char in text:
        candidate = current + char
        if pdfmetrics.stringWidth(candidate, font_name, font_size) <= max_width:
            current = candidate
            continue

        if current:
            lines.append(current)
        current = char

    if current:
        lines.append(current)

    return lines


def _draw_centered_text(
    pdf: canvas.Canvas,
    text: str,
    y: float,
    font_name: str,
    font_size: int,
    page_width: float,
) -> None:
    pdf.setFont(font_name, font_size)
    pdf.drawCentredString(page_width / 2, y, text)


def _draw_wrapped_paragraph(
    pdf: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    max_width: float,
    font_name: str,
    font_size: int,
    leading: int,
) -> float:
    pdf.setFont(font_name, font_size)
    for line in _wrap_text(text, max_width, font_name, font_size):
        pdf.drawString(x, y, line)
        y -= leading
    return y


def _draw_cfd_certificate_content(
    pdf: canvas.Canvas,
    data: dict[str, str],
    page_width: float,
    page_height: float,
    font_name: str,
) -> None:
    # 當正式 Word/PDF 背景不可用時，使用此備援版面。
    is_portrait = page_height > page_width
    margin_x = page_width * (0.12 if is_portrait else 0.07)
    content_width = page_width - margin_x * 2
    title_size = 32 if is_portrait else 34
    body_size = 18 if is_portrait else 20
    body_leading = 32 if is_portrait else 34

    _draw_centered_text(pdf, "研習證明", page_height * 0.76, font_name, title_size, page_width)

    pdf.setFont(font_name, 12)
    pdf.drawRightString(page_width - margin_x, page_height * 0.68, data["證書字號"])

    hours_text = f"，共計{data['時數']}小時" if data["時數"] else ""
    paragraph = (
        f"茲證明 {data['姓名']}({data['身分證']})君 於{data['日期']}參加本院教師培育中心主辦之"
        f"教師培育課程「{data['活動']}」{hours_text} ({data['種類']})。"
    )
    next_y = _draw_wrapped_paragraph(
        pdf=pdf,
        text=paragraph,
        x=margin_x,
        y=page_height * 0.55,
        max_width=content_width,
        font_name=font_name,
        font_size=body_size,
        leading=body_leading,
    )

    _draw_wrapped_paragraph(
        pdf=pdf,
        text="特此證明",
        x=margin_x,
        y=next_y - 20,
        max_width=content_width,
        font_name=font_name,
        font_size=body_size,
        leading=30,
    )

    _draw_centered_text(pdf, "佛教慈濟醫療財團法人大林慈濟醫院", page_height * 0.28, font_name, 20, page_width)
    _draw_centered_text(pdf, f"中華{data['日期']}", page_height * 0.19, font_name, 18, page_width)


def _draw_official_landscape_overlay(
    pdf: canvas.Canvas,
    data: dict[str, str],
    page_width: float,
    page_height: float,
    font_name: str,
) -> None:
    # 座標綁定正式橫式證書背景；模板異動時需同步調整。
    pdf.setFillColorRGB(1, 1, 1)
    pdf.rect(575, 328, 225, 76, stroke=0, fill=1)
    pdf.rect(50, 175, 735, 175, stroke=0, fill=1)
    pdf.rect(205, 58, 430, 48, stroke=0, fill=1)

    pdf.setFillColorRGB(0, 0, 0)
    pdf.setFont(font_name, 12)
    pdf.drawRightString(page_width - 82, 350, data["證書字號"])

    issue_date_text = _roc_date_text(data["日期"])
    name_line = f"茲證明  {data['姓名']}({data['身分證']})君  於{issue_date_text}參加本"
    body_line_1 = "院教師培育中心主辦之教師培育課程「"
    hours_text = f"，共計{data['時數']}小時" if data["時數"] else ""
    body_line_2 = f"{data['活動']}」{hours_text} ({data['種類']})。"

    pdf.setFont(font_name, 23)
    pdf.drawString(62, 306, name_line)
    pdf.drawString(62, 264, body_line_1)
    for index, line in enumerate(_wrap_text(body_line_2, page_width - 124, font_name, 23)):
        pdf.drawString(62, 222 - (index * 42), line)

    pdf.setFont(font_name, 22)
    pdf.drawString(62, 162, "特此證明")

    year, month, day = _issue_date_parts(data["日期"])
    if year and month and day:
        date_text = f"中 華 民 國   {year}  年   {month}  月   {day}  日"
    else:
        date_text = f"中華民國{data['日期']}"
    pdf.setFont(font_name, 20)
    pdf.drawCentredString(page_width / 2, 70, date_text)


def _render_background_overlay_pdf(record: CertificateRecord, output_path: Path) -> bool:
    # 選用的非 Word 路徑：設定固定 PDF 背景後，將可變文字疊上去。
    background_path = Path(settings.certificate_pdf_background_path)
    if not background_path.exists():
        return False

    try:
        background_reader = PdfReader(str(background_path))
        if not background_reader.pages:
            return False

        background_page = background_reader.pages[0]
        page_width = float(background_page.mediabox.width)
        page_height = float(background_page.mediabox.height)

        overlay_buffer = BytesIO()
        overlay = canvas.Canvas(overlay_buffer, pagesize=(page_width, page_height))
        data = _certificate_data(record)
        if page_width > page_height:
            _draw_official_landscape_overlay(
                pdf=overlay,
                data=data,
                page_width=page_width,
                page_height=page_height,
                font_name=register_kai_font(),
            )
        else:
            _draw_cfd_certificate_content(
                pdf=overlay,
                data=data,
                page_width=page_width,
                page_height=page_height,
                font_name=register_certificate_font(),
            )
        overlay.save()
        overlay_buffer.seek(0)

        overlay_page = PdfReader(overlay_buffer).pages[0]
        background_page.merge_page(overlay_page)

        writer = PdfWriter()
        writer.add_page(background_page)
        with output_path.open("wb") as output_file:
            writer.write(output_file)
    except Exception as exc:
        output_path.with_suffix(".background_error.txt").write_text(str(exc), encoding="utf-8")
        return False

    output_path.with_suffix(".background_error.txt").unlink(missing_ok=True)
    return output_path.exists() and output_path.stat().st_size > 0


def _render_cfd_word_style_pdf(record: CertificateRecord, output_path: Path) -> None:
    # Word 自動化不可用時的最後備援近似版面。
    font_name = register_certificate_font()
    page_width, page_height = A4
    pdf = canvas.Canvas(str(output_path), pagesize=A4)
    data = _certificate_data(record)

    pdf.setStrokeColorRGB(0.18, 0.24, 0.32)
    pdf.setLineWidth(2)
    pdf.rect(42, 42, page_width - 84, page_height - 84)
    pdf.setLineWidth(0.8)
    pdf.rect(54, 54, page_width - 108, page_height - 108)

    _draw_cfd_certificate_content(pdf, data, page_width, page_height, font_name)

    pdf.save()


def _render_pptx_template_pdf(record: CertificateRecord, output_path: Path) -> None:
    # 保留舊 PPTX 備援，支援早期模板實驗。
    template = load_certificate_template()
    font_name = register_certificate_font()
    pdf = canvas.Canvas(str(output_path), pagesize=(template.width, template.height))

    pdf.setStrokeColorRGB(0.15, 0.22, 0.35)
    pdf.setLineWidth(3)
    pdf.rect(24, 24, template.width - 48, template.height - 48)
    pdf.setLineWidth(1)
    pdf.rect(38, 38, template.width - 76, template.height - 76)

    data = _certificate_data(record)
    for text_box in template.text_boxes:
        text = render_template_text(text_box.text, data)
        font_size = 26 if "{{" not in text_box.text and len(text) <= 10 else 18
        pdf.setFont(font_name, font_size)
        pdf.drawString(text_box.x, text_box.y + text_box.height * 0.35, text)

    pdf.save()


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
