from dataclasses import dataclass
from pathlib import Path
import re
import zipfile
import xml.etree.ElementTree as ET

from app.core.config import settings


EMU_PER_INCH = 914400
POINTS_PER_INCH = 72


@dataclass
class TemplateTextBox:
    # PPTX 文字框原始文字。
    text: str

    # 文字框在 PDF 頁面上的座標與大小，單位為 point。
    x: float
    y: float
    width: float
    height: float


@dataclass
class CertificateTemplate:
    # 頁面寬高，單位為 point。
    width: float
    height: float

    # 模板中的文字框。
    text_boxes: list[TemplateTextBox]


def emu_to_points(value: str | int) -> float:
    # PowerPoint 使用 EMU 作為座標單位，PDF 使用 point。
    return int(value) / EMU_PER_INCH * POINTS_PER_INCH


def load_certificate_template(template_path: str | None = None) -> CertificateTemplate:
    # 讀取 PPTX 檔案內容。
    # PPTX 本質是 zip，slide XML 裡會有文字框、座標與尺寸。
    path = Path(template_path or settings.certificate_template_path)
    with zipfile.ZipFile(path) as pptx:
        presentation_xml = ET.fromstring(pptx.read("ppt/presentation.xml"))
        namespaces = {
            "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
            "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
        }

        slide_size = presentation_xml.find(".//p:sldSz", namespaces)
        if slide_size is None:
            raise ValueError("PPTX 模板缺少投影片尺寸資訊。")

        page_width = emu_to_points(slide_size.attrib["cx"])
        page_height = emu_to_points(slide_size.attrib["cy"])

        slide_xml = ET.fromstring(pptx.read("ppt/slides/slide1.xml"))
        text_boxes: list[TemplateTextBox] = []

        for shape in slide_xml.findall(".//p:sp", namespaces):
            texts = [node.text or "" for node in shape.findall(".//a:t", namespaces)]
            if not texts:
                continue

            offset = shape.find(".//a:off", namespaces)
            extent = shape.find(".//a:ext", namespaces)
            if offset is None or extent is None:
                continue

            x = emu_to_points(offset.attrib["x"])
            top = emu_to_points(offset.attrib["y"])
            width = emu_to_points(extent.attrib["cx"])
            height = emu_to_points(extent.attrib["cy"])

            # ReportLab 的 y 軸從頁面底部開始，PPTX 的 y 軸從頁面頂部開始。
            y = page_height - top - height

            text_boxes.append(
                TemplateTextBox(
                    text="".join(texts),
                    x=x,
                    y=y,
                    width=width,
                    height=height,
                )
            )

    return CertificateTemplate(width=page_width, height=page_height, text_boxes=text_boxes)


def render_template_text(raw_text: str, data: dict[str, str]) -> str:
    # 將 {{placeholder}} 替換成資料庫中的證書資料。
    def replace(match: re.Match[str]) -> str:
        key = match.group(1).strip()
        return data.get(key, "")

    return re.sub(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}", replace, raw_text)
