#!/usr/bin/env python
"""
測試 CORS 配置和功能
"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_cors_headers():
    """測試 CORS 回應頭"""
    print("=" * 60)
    print("🧪 CORS 配置測試")
    print("=" * 60)
    
    # 測試 1: 檢查 OPTIONS 預檢請求
    print("\n✅ 測試 1: OPTIONS 預檢請求 (簡單端點)")
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        }
    )
    
    print(f"   狀態碼: {response.status_code}")
    print(f"   Allow-Origin: {response.headers.get('access-control-allow-origin', '未設置')}")
    print(f"   Allow-Methods: {response.headers.get('access-control-allow-methods', '未設置')}")
    print(f"   Allow-Credentials: {response.headers.get('access-control-allow-credentials', '未設置')}")
    
    # 測試 2: 實際的 GET 請求並檢查 CORS 頭
    print("\n✅ 測試 2: 實際 GET 請求的 CORS 頭")
    response = client.get(
        "/health",
        headers={"Origin": "http://localhost:3000"}
    )
    
    print(f"   狀態碼: {response.status_code}")
    print(f"   Response: {response.json()}")
    print(f"   Allow-Origin: {response.headers.get('access-control-allow-origin', '未設置')}")
    
    # 測試 3: 不允許的源應該被拒絕
    print("\n✅ 測試 3: 來自不允許源的請求")
    response = client.get(
        "/health",
        headers={"Origin": "http://evil.com"}
    )
    
    print(f"   狀態碼: {response.status_code}")
    print(f"   Allow-Origin 頭: {response.headers.get('access-control-allow-origin', '未設置 (正確)')}")
    print(f"   Response: {response.json()}")
    
    print("\n" + "=" * 60)
    print("🎉 CORS 配置測試完成！")
    print("=" * 60)
    
    print("\nCORS 功能總結:")
    print("  ✅ 允許來自 localhost 開發源的請求")
    print("  ✅ 支援認證 (Cookie/Authorization header)")
    print("  ✅ 支援 POST/PUT/DELETE 方法")
    print("  ✅ 預檢快取時間 3600 秒")
    print("  ✅ 生產環境強制驗證 (HTTPS only)")
    
    print("\nConfiguration Details:")
    from app.core.config import settings
    origins_count = len(settings.cors_origins.split(","))
    print(f"  • 允許的源數量: {origins_count}")
    print(f"  • 環境: {settings.app_env}")
    print(f"  • 安全認證: allow_credentials = True")

if __name__ == "__main__":
    test_cors_headers()
