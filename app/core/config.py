from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Certificate Generator System"

    app_env: str = "development"

    database_url: str = "sqlite:///./storage/database/certificates.db"

    upload_dir: str = "storage/uploads"

    generated_dir: str = "storage/generated"

    # 產出檔類似 cache artifact，保留天數需可設定以避免磁碟無限制成長。
    generated_retention_days: int = 90

    template_dir: str = "app/templates"

    # 保留舊 PPTX 備援，供模板檢查與非 Word 修復路徑使用。
    certificate_template_path: str = "storage/templates/certificate_template.pptx"

    # 主要證書產生器：Microsoft Word 開啟此模板並匯出 PDF。
    certificate_word_template_path: str = "storage/templates/cfd_certificate_template.doc"

    # 選用固定背景產生器，日後替換 Word 自動化時可使用。
    certificate_pdf_background_path: str = "storage/templates/cfd_certificate_background.pdf"

    use_word_certificate_renderer: bool = True

    # 開發環境以外必須覆寫；生產模式啟動時會強制檢查。
    jwt_secret_key: str = "dev-change-me-certificate-system"

    jwt_expire_minutes: int = 480

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
