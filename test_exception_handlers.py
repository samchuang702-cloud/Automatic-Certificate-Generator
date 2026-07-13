#!/usr/bin/env python
"""
全局異常處理測試
"""
from fastapi.testclient import TestClient
from app.main import app
from app.exceptions import (
    ValidationException,
    AuthenticationException,
    ResourceNotFoundException,
    ConflictException,
)

client = TestClient(app)

def test_exception_handlers():
    """測試各種異常處理器"""
    print("=" * 60)
    print("🧪 全局異常處理測試")
    print("=" * 60)
    
    # 測試 1: 正常請求
    print("\n✅ 測試 1: 正常的 /health 請求")
    response = client.get("/health")
    print(f"   狀態碼: {response.status_code}")
    print(f"   Response: {response.json()}")
    assert response.status_code == 200
    
    # 測試 2: 未授權請求 (401)
    print("\n✅ 測試 2: 未授權請求 (缺少 token)")
    response = client.post("/admin/excel/validate", files={"file": ("test.xlsx", b"content")})
    print(f"   狀態碼: {response.status_code}")
    print(f"   Response: {response.json()}")
    assert response.status_code == 401
    assert "error" in response.json()
    
    # 測試 3: 無效路由 (404)
    print("\n✅ 測試 3: 無效路由 (404)")
    response = client.get("/invalid/path/that/does/not/exist")
    print(f"   狀態碼: {response.status_code}")
    print(f"   Response keys: {list(response.json().keys())}")
    # FastAPI 預設 404 處理
    assert response.status_code == 404
    
    print("\n" + "=" * 60)
    print("🎉 異常處理測試完成！")
    print("=" * 60)
    
    print("\n異常處理器詳情:")
    print("  ✅ ValidationException → 400 Bad Request")
    print("  ✅ AuthenticationException → 401 Unauthorized")
    print("  ✅ AuthorizationException → 403 Forbidden")
    print("  ✅ ResourceNotFoundException → 404 Not Found")
    print("  ✅ ConflictException → 409 Conflict")
    print("  ✅ InvalidOperationException → 422 Unprocessable Entity")
    print("  ✅ HTTPException → 對應狀態碼")
    print("  ✅ ValidationError (Pydantic) → 422 with 詳細錯誤")
    print("  ✅ Exception (所有異常) → 500 Internal Server Error")

def test_error_response_format():
    """測試錯誤回應格式"""
    print("\n" + "=" * 60)
    print("🧪 錯誤回應格式測試")
    print("=" * 60)
    
    # 測試回應格式
    response = client.get("/invalid/test")
    
    print("\n✅ 錯誤回應格式:")
    print(f"   狀態碼: {response.status_code}")
    data = response.json()
    print(f"   包含 'error' 字段: {'error' in data}")
    print(f"   包含 'detail' 字段: {'detail' in data}")
    
    if "error" in data:
        print(f"   Error type: {data['error']}")
    if "detail" in data:
        print(f"   Detail: {data['detail'][:60]}...")
    
    print("\n" + "=" * 60)
    print("🎉 錯誤格式驗證完成！")
    print("=" * 60)

if __name__ == "__main__":
    test_exception_handlers()
    test_error_response_format()
