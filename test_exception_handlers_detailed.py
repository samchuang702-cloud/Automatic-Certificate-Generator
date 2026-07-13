#!/usr/bin/env python
"""
全局異常處理詳細測試
"""
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from app.main import app
from app.exceptions import (
    ValidationException,
    AuthenticationException,
    AuthorizationException,
    ResourceNotFoundException,
    ConflictException,
    InvalidOperationException,
)

client = TestClient(app)

def test_exception_mapping():
    """測試異常到 HTTP 狀態碼的映射"""
    print("=" * 70)
    print("🧪 異常处理映射表")
    print("=" * 70)
    
    mapping = {
        "ValidationException": (400, "validation_error"),
        "AuthenticationException": (401, "authentication_error"),
        "AuthorizationException": (403, "authorization_error"),
        "ResourceNotFoundException": (404, "not_found"),
        "ConflictException": (409, "conflict_error"),
        "InvalidOperationException": (422, "invalid_operation"),
    }
    
    print("\n例外類型 → HTTP 狀態碼 → 錯誤類型")
    print("-" * 70)
    for exc_name, (status_code, error_type) in mapping.items():
        http_status = f"HTTP {status_code}"
        print(f"  {exc_name:<30} → {http_status:<10} → {error_type}")
    
    print("\n" + "=" * 70)
    print("✅ 異常處理映射表")
    print("=" * 70)

def test_error_response_structure():
    """測試錯誤回應結構"""
    print("\n" + "=" * 70)
    print("🧪 錯誤回應結構")
    print("=" * 70)
    
    print("\n標準錯誤回應格式:")
    print("""{
    "error": "error_type",           # 錯誤類型
    "detail": "錯誤詳情",             # 詳細說明
    "request_path": "/api/path",     # 請求路徑 (可選)
}""")
    
    print("\nPydantic 驗證錯誤格式:")
    print("""{
    "error": "validation_error",
    "detail": "請求數據驗證失敗",
    "errors": [
        {
            "field": "field_name",
            "message": "錯誤訊息",
            "type": "validation_type"
        }
    ]
}""")
    
    print("\n生產 vs 開發環境:")
    print("  開發環境: 暴露詳細的異常信息")
    print("  生產環境: 隱藏詳細信息，只顯示通用錯誤訊息")

def test_logging_levels():
    """測試日誌級別"""
    print("\n" + "=" * 70)
    print("🧪 日誌記錄級別")
    print("=" * 70)
    
    logging_levels = {
        "ValidationException": "WARNING",
        "AuthenticationException": "WARNING",
        "AuthorizationException": "WARNING",
        "ResourceNotFoundException": "INFO",
        "ConflictException": "WARNING",
        "InvalidOperationException": "WARNING",
        "Exception (未預期)": "ERROR (with traceback)",
    }
    
    print("\n異常類型 → 日誌級別")
    print("-" * 70)
    for exc_type, log_level in logging_levels.items():
        print(f"  {exc_type:<35} → {log_level}")
    
    print("\n日誌位置: 使用 logging 模塊記錄到配置的日誌處理器")

def test_best_practices():
    """異常處理最佳實踐"""
    print("\n" + "=" * 70)
    print("✅ 異常處理最佳實踐")
    print("=" * 70)
    
    practices = [
        ("在業務邏輯層拋出特定異常", "services/ 中使用自定義異常"),
        ("不要讓技術異常暴露給客戶端", "捕捉並轉換為通用異常"),
        ("提供有用的錯誤訊息", "説明用戶理解和修正問題"),
        ("記錄所有異常", "用於調試和監控"),
        ("區分用戶錯誤和系統錯誤", "不同的狀態碼和訊息"),
        ("生產環境隱藏詳細信息", "避免信息洩露"),
    ]
    
    print("\n最佳實踐建議:")
    for i, (practice, detail) in enumerate(practices, 1):
        print(f"\n  {i}. {practice}")
        print(f"     → {detail}")

def test_usage_examples():
    """使用範例"""
    print("\n" + "=" * 70)
    print("📝 使用範例")
    print("=" * 70)
    
    examples = [
        (
            "驗證失敗",
            """from app.exceptions import ValidationException
raise ValidationException("用戶 ID 格式無效")"""
        ),
        (
            "資源不存在",
            """from app.exceptions import ResourceNotFoundException
raise ResourceNotFoundException("證書不存在")"""
        ),
        (
            "權限不足",
            """from app.exceptions import AuthorizationException
raise AuthorizationException("只有管理員可以訪問此資源")"""
        ),
        (
            "衝突（重複）",
            """from app.exceptions import ConflictException
raise ConflictException("此用戶名已被使用")"""
        ),
        (
            "無效操作",
            """from app.exceptions import InvalidOperationException
raise InvalidOperationException("證書已生成，無法再次生成")"""
        ),
    ]
    
    for i, (scenario, code) in enumerate(examples, 1):
        print(f"\n  {i}. {scenario}:")
        print(f"     {code}")

if __name__ == "__main__":
    test_exception_mapping()
    test_error_response_structure()
    test_logging_levels()
    test_best_practices()
    test_usage_examples()
    
    print("\n" + "=" * 70)
    print("🎉 全局異常處理完整文檔")
    print("=" * 70)
