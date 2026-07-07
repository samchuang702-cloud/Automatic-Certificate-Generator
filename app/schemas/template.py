from pydantic import BaseModel


class TemplateTextBoxItem(BaseModel):
    # 文字框內容。
    text: str

    # 文字框座標與大小，單位為 point。
    x: float
    y: float
    width: float
    height: float


class TemplateInspectResult(BaseModel):
    # 頁面寬度。
    width: float

    # 頁面高度。
    height: float

    # 模板文字框。
    text_boxes: list[TemplateTextBoxItem]
