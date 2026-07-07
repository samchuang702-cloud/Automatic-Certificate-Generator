from fastapi import APIRouter, Depends

from app.dependencies.auth import require_roles
from app.schemas.template import TemplateInspectResult, TemplateTextBoxItem
from app.services.certificate_template import load_certificate_template


# 後台模板 API。
router = APIRouter(
    prefix="/admin/template",
    tags=["admin-template"],
    dependencies=[Depends(require_roles("admin", "county_staff"))],
)


@router.get("/inspect", response_model=TemplateInspectResult)
def inspect_certificate_template() -> TemplateInspectResult:
    # 讀取目前設定的 PPTX 證書模板，回傳文字框與座標資訊。
    template = load_certificate_template()
    return TemplateInspectResult(
        width=template.width,
        height=template.height,
        text_boxes=[
            TemplateTextBoxItem(
                text=text_box.text,
                x=text_box.x,
                y=text_box.y,
                width=text_box.width,
                height=text_box.height,
            )
            for text_box in template.text_boxes
        ],
    )
