# 匯入 FastAPI 主框架，用來建立 API 應用程式。
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# 匯入系統設定，例如專案名稱與執行環境。
from app.core.config import settings
from app.db.session import create_db_and_tables
from app.routers.admin_excel import router as admin_excel_router
from app.routers.admin_logs import router as admin_logs_router
from app.routers.admin_template import router as admin_template_router
from app.routers.public_auth import router as public_auth_router
from app.routers.public_certificates import router as public_certificates_router
from app.services.generated_cleanup import cleanup_old_generated_files


def create_app() -> FastAPI:
    # 建立 FastAPI 應用程式實例。
    # title 會顯示在 Swagger 文件頁面，也就是 /docs。
    app = FastAPI(title=settings.app_name)

    # 安全檢查：生產環境務必設定非預設的 JWT secret
    if settings.app_env == "production" and (
        not settings.jwt_secret_key or settings.jwt_secret_key == "dev-change-me-certificate-system"
    ):
        raise RuntimeError("JWT secret_key 未設定或仍為預設值，請於生產環境透過 .env 設定強隨機字串。")

    # 啟動時建立 SQLite 資料表。
    # 目前專案還在教學與開發階段，先用 create_all；正式環境可改用 Alembic migration。
    create_db_and_tables()

    # 啟動時清掉過期產出檔，避免 PDF/ZIP 長期累積。
    cleanup_old_generated_files()

    # 掛載前端靜態檔。
    # app/static 內的 CSS、JavaScript 都會透過 /static 路徑提供。
    app.mount("/static", StaticFiles(directory="app/static"), name="static")

    # 掛載後台 Excel 相關 API。
    # 目前先提供 Excel 欄位驗證，之後 Module 3 會再補正式上傳儲存流程。
    app.include_router(admin_excel_router)

    # 掛載後台操作紀錄 API。
    app.include_router(admin_logs_router)

    # 掛載後台模板檢查 API。
    app.include_router(admin_template_router)

    # 掛載使用者端身分驗證 API。
    # Module 6 使用這個路由確認 user_id 與 national_id 是否符合資料庫資料。
    app.include_router(public_auth_router)

    # 掛載使用者端證書清單 API。
    # Module 7 使用這個路由列出驗證成功者可產生的證書。
    app.include_router(public_certificates_router)

    # 系統首頁。
    # 回傳前端操作介面，讓管理者與使用者可以直接操作上傳、匯入、查詢與產生證書。
    @app.get("/", tags=["frontend"])
    def index() -> FileResponse:
        return FileResponse("app/static/index.html")

    # API 路由總覽。
    # 原本首頁回傳的 JSON 移到這裡，方便開發時查目前有哪些主要路由。
    @app.get("/api/routes", tags=["system"])
    def routes() -> dict[str, object]:
        return {
            "message": "Certificate Generator System is running.",
            "docs": "/docs",
            "health": "/health",
            "excel_validate": "/admin/excel/validate",
            "excel_upload": "/admin/excel/upload",
            "excel_preview": "/admin/excel/preview",
            "saved_excel_preview": "/admin/excel/uploads/{saved_filename}/preview",
            "excel_import": "/admin/excel/import",
            "saved_excel_import": "/admin/excel/uploads/{saved_filename}/import",
            "identity_verify": "/auth/verify",
            "available_certificates": "/certificates/available",
            "operation_logs": "/admin/logs",
            "template_inspect": "/admin/template/inspect",
            "certificate_generate": "/certificates/generate",
        }

    # 健康檢查 API。
    # 用途是確認後端服務是否有成功啟動，通常也是部署或監控時第一個檢查的路由。
    @app.get("/health", tags=["system"])
    def health_check() -> dict[str, str]:
        # 回傳目前服務狀態、系統名稱與執行環境。
        # 這裡先保持簡單，後續可以再加入資料庫連線狀態。
        return {
            "status": "ok",
            "app": settings.app_name,
            "env": settings.app_env,
        }

    # 回傳建立好的 FastAPI app，方便未來在測試或部署時重複使用。
    return app


# Uvicorn 會讀取這個變數作為啟動入口。
# 啟動指令範例：uvicorn app.main:app --reload
app = create_app()
