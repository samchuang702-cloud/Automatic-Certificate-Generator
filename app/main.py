from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.db.session import create_db_and_tables
from app.routers.admin_excel import router as admin_excel_router
from app.routers.admin_logs import router as admin_logs_router
from app.routers.admin_template import router as admin_template_router
from app.routers.public_auth import router as public_auth_router
from app.routers.public_certificates import router as public_certificates_router
from app.services.generated_cleanup import cleanup_old_generated_files


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)

    # 生產環境不可沿用開發用 JWT secret，否則 token 可被偽造。
    if settings.app_env == "production" and (
        not settings.jwt_secret_key or settings.jwt_secret_key == "dev-change-me-certificate-system"
    ):
        raise RuntimeError("JWT secret_key 未設定或仍為預設值，請於生產環境透過 .env 設定強隨機字串。")

    # 目前仍採輕量 SQLite 啟動流程，尚未引入 migration 工具。
    create_db_and_tables()

    # 產出 PDF 屬於檔案系統 artifact，保留期限在應用啟動時統一處理。
    cleanup_old_generated_files()

    app.mount("/static", StaticFiles(directory="app/static"), name="static")

    app.include_router(admin_excel_router)
    app.include_router(admin_logs_router)
    app.include_router(admin_template_router)
    app.include_router(public_auth_router)
    app.include_router(public_certificates_router)

    @app.get("/", tags=["frontend"])
    def index() -> FileResponse:
        return FileResponse("app/static/index.html")

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

    @app.get("/health", tags=["system"])
    def health_check() -> dict[str, str]:
        return {
            "status": "ok",
            "app": settings.app_name,
            "env": settings.app_env,
        }

    return app


app = create_app()
