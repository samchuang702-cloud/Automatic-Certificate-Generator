# BaseSettings 可以自動讀取環境變數，適合管理不同環境的設定。
# SettingsConfigDict 用來指定 .env 檔案等設定來源。
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # 系統名稱，會出現在 API 文件與健康檢查回應中。
    app_name: str = "Certificate Generator System"

    # 執行環境名稱，例如 development、staging、production。
    app_env: str = "development"

    # SQLite 資料庫連線字串。
    # Module 2 會使用這個設定建立資料庫連線。
    database_url: str = "sqlite:///./storage/database/certificates.db"

    # Excel 上傳檔案存放位置。
    # Module 3 會把管理者上傳的 Excel 存到這裡。
    upload_dir: str = "storage/uploads"

    # PDF 或 ZIP 產生後的存放位置。
    # Module 9 和 Module 10 會使用這個資料夾。
    generated_dir: str = "storage/generated"

    # 產出的 PDF/ZIP 保留天數；系統啟動時會自動清掉更舊的產出檔案。
    generated_retention_days: int = 90

    # HTML/Jinja2 證書模板存放位置。
    # Module 8 會使用這個資料夾做證書套版。
    template_dir: str = "app/templates"

    # PowerPoint 證書模板檔案位置。
    # Module 8 會讀取這個 PPTX 的文字框與 {{placeholder}}，作為 PDF 套版基礎。
    certificate_template_path: str = "storage/templates/certificate_template.pptx"

    # Word 版 CFD 研習證明模板；存在時 PDF 產生器會優先使用這個版型。
    certificate_word_template_path: str = "storage/templates/cfd_certificate_template.doc"

    # docxtpl 使用的 .docx 模板；存在時會優先用 {{欄位}} 套版後再轉 PDF。
    certificate_docx_template_path: str = "storage/templates/cfd_certificate_template.docx"

    # 長期部署建議使用固定 PDF 背景，再由 Python 疊上姓名、課程、日期等文字。
    # 將空白證書背景放到這個路徑後，產生器會優先使用它，不需要 Microsoft Word。
    certificate_pdf_background_path: str = "storage/templates/cfd_certificate_background.pdf"

    # 是否允許使用 Microsoft Word COM 轉 PDF。
    # 若要完整保留原始 .doc 證書模板的底圖與排版，需開啟此流程。
    use_word_certificate_renderer: bool = True

    # JWT 簽章密鑰。
    # 開發階段先提供預設值；正式環境務必改成 .env 中的隨機長字串。
    jwt_secret_key: str = "dev-change-me-certificate-system"

    # JWT 有效時間，單位分鐘。
    jwt_expire_minutes: int = 480

    # 指定系統啟動時讀取 .env 檔。
    # 如果沒有 .env，就會使用上面定義的預設值。
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# 建立全域設定物件，其他模組可以直接匯入 settings 使用。
settings = Settings()
