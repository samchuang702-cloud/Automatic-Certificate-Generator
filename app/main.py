import logging
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from app.core.config import settings
from app.db.session import create_db_and_tables
from app.exceptions import (
    AppException,
    AuthenticationException,
    AuthorizationException,
    ConflictException,
    InvalidOperationException,
    ResourceNotFoundException,
    ValidationException,
)
from app.routers.admin_excel import router as admin_excel_router
from app.routers.admin_logs import router as admin_logs_router
from app.routers.admin_template import router as admin_template_router
from app.routers.public_auth import router as public_auth_router
from app.routers.public_certificates import router as public_certificates_router
from app.services.generated_cleanup import cleanup_old_generated_files

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)

    # 生產環境不可沿用開發用 JWT secret，否則 token 可被偽造。
    if settings.app_env == "production" and (
        not settings.jwt_secret_key or settings.jwt_secret_key == "dev-change-me-certificate-system"
    ):
        raise RuntimeError("JWT secret_key 未設定或仍為預設值，請於生產環境透過 .env 設定強隨機字串。")

    # CORS 中間件配置：允許前端應用程式跨域訪問 API
    allowed_origins = [origin.strip() for origin in settings.cors_origins.split(",")]
    
    # 生產環境下驗證 CORS 配置
    if settings.app_env == "production":
        for origin in allowed_origins:
            if origin == "*" or origin.startswith("http://"):
                raise RuntimeError(
                    f"生產環境 CORS 配置不安全。不允許使用通配符 '*' 或 'http://'。"
                    f"請於生產環境透過 .env 設定具體的 HTTPS 源，例如: 'https://yourhospital.com,https://app.yourhospital.com'"
                )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,           # 允許 Cookie/Authorization 認證
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],              # 允許所有自訂 headers
        max_age=3600,                     # 預檢快取時間 (秒)
    )

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

    # ====== 全局異常處理器 ======
    
    @app.exception_handler(ValidationException)
    async def validation_exception_handler(request: Request, exc: ValidationException) -> JSONResponse:
        """處理驗證異常"""
        logger.warning(f"驗證失敗: {exc}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "validation_error",
                "detail": str(exc),
                "request_path": str(request.url.path),
            }
        )

    @app.exception_handler(AuthenticationException)
    async def authentication_exception_handler(request: Request, exc: AuthenticationException) -> JSONResponse:
        """處理認證異常"""
        logger.warning(f"認證失敗: {exc}")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": "authentication_error",
                "detail": str(exc),
            }
        )

    @app.exception_handler(AuthorizationException)
    async def authorization_exception_handler(request: Request, exc: AuthorizationException) -> JSONResponse:
        """處理授權異常"""
        logger.warning(f"授權失敗: {exc}")
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "error": "authorization_error",
                "detail": str(exc),
            }
        )

    @app.exception_handler(ResourceNotFoundException)
    async def resource_not_found_handler(request: Request, exc: ResourceNotFoundException) -> JSONResponse:
        """處理資源未找到異常"""
        logger.info(f"資源未找到: {exc}")
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": "not_found",
                "detail": str(exc),
            }
        )

    @app.exception_handler(ConflictException)
    async def conflict_exception_handler(request: Request, exc: ConflictException) -> JSONResponse:
        """處理衝突異常"""
        logger.warning(f"資源衝突: {exc}")
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": "conflict_error",
                "detail": str(exc),
            }
        )

    @app.exception_handler(InvalidOperationException)
    async def invalid_operation_handler(request: Request, exc: InvalidOperationException) -> JSONResponse:
        """處理無效操作異常"""
        logger.warning(f"無效操作: {exc}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "invalid_operation",
                "detail": str(exc),
            }
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """處理 FastAPI HTTPException"""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": f"http_error_{exc.status_code}",
                "detail": exc.detail,
            }
        )

    @app.exception_handler(ValidationError)
    async def pydantic_validation_handler(request: Request, exc: ValidationError) -> JSONResponse:
        """處理 Pydantic 驗證異常"""
        logger.warning(f"請求驗證失敗: {exc}")
        errors = []
        for error in exc.errors():
            errors.append({
                "field": ".".join(str(x) for x in error["loc"][1:]),
                "message": error["msg"],
                "type": error["type"],
            })
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "validation_error",
                "detail": "請求數據驗證失敗",
                "errors": errors,
            }
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """通用異常處理器 - 捕捉所有未預期的異常"""
        logger.error(f"未預期的異常: {type(exc).__name__}: {exc}", exc_info=True)
        
        # 生產環境不暴露詳細錯誤信息
        if settings.app_env == "production":
            detail = "內部伺服器錯誤，請聯繫管理員"
        else:
            detail = f"{type(exc).__name__}: {str(exc)}"
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "internal_server_error",
                "detail": detail,
                "request_path": str(request.url.path),
            }
        )

    return app


app = create_app()
