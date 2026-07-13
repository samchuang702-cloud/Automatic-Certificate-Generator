#!/usr/bin/env python
"""
測試生產環境的 CORS 驗證
"""
import os
import sys

def test_production_cors_validation():
    """測試生產環境下的 CORS 驗證"""
    print("=" * 60)
    print("🧪 生產環境 CORS 安全驗證")
    print("=" * 60)
    
    # 測試 1: 生產環境 + 不安全的 CORS 配置 (通配符)
    print("\n❌ 測試 1: 生產環境 + 通配符 CORS (應該失敗)")
    os.environ["APP_ENV"] = "production"
    os.environ["CORS_ORIGINS"] = "*"
    
    try:
        # 強制重新載入模塊以應用新的環境變數
        if "app.core.config" in sys.modules:
            del sys.modules["app.core.config"]
        if "app.main" in sys.modules:
            del sys.modules["app.main"]
        
        from app.main import create_app
        app = create_app()
        print("   ❌ 不安全配置被接受 (這是個問題！)")
        sys.exit(1)
    except RuntimeError as e:
        print(f"   ✅ 正確拒絕不安全配置")
        print(f"   ✅ 錯誤信息: {str(e)[:80]}...")
    
    # 測試 2: 生產環境 + 不安全的 HTTP 源
    print("\n❌ 測試 2: 生產環境 + HTTP 源 (應該失敗)")
    os.environ["APP_ENV"] = "production"
    os.environ["CORS_ORIGINS"] = "http://example.com"
    
    try:
        if "app.main" in sys.modules:
            del sys.modules["app.main"]
        if "app.core.config" in sys.modules:
            del sys.modules["app.core.config"]
        
        from app.main import create_app
        app = create_app()
        print("   ❌ 不安全配置被接受 (這是個問題！)")
        sys.exit(1)
    except RuntimeError as e:
        print(f"   ✅ 正確拒絕 HTTP 源")
        print(f"   ✅ 錯誤信息: {str(e)[:80]}...")
    
    # 測試 3: 生產環境 + 安全的 HTTPS 源
    print("\n✅ 測試 3: 生產環境 + HTTPS 源 (應該成功)")
    os.environ["APP_ENV"] = "production"
    os.environ["CORS_ORIGINS"] = "https://yourhospital.com,https://app.yourhospital.com"
    os.environ["JWT_SECRET_KEY"] = "very-long-and-secure-secret-key-for-production-at-least-32-chars"
    
    try:
        if "app.main" in sys.modules:
            del sys.modules["app.main"]
        if "app.core.config" in sys.modules:
            del sys.modules["app.core.config"]
        
        from app.main import create_app
        app = create_app()
        print("   ✅ 安全配置被接受")
        print("   ✅ 允許的源:")
        from app.core.config import settings
        for origin in settings.cors_origins.split(","):
            print(f"      - {origin.strip()}")
    except RuntimeError as e:
        print(f"   ❌ 錯誤: {e}")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("🎉 生產環境 CORS 安全驗證完成！")
    print("=" * 60)
    
    print("\n生產環境安全規則:")
    print("  🔒 不允許使用通配符 '*'")
    print("  🔒 不允許使用 'http://' (必須 HTTPS)")
    print("  🔒 必須明確指定允許的源")
    print("  🔒 多個源用逗號分隔")
    
    print("\n配置範例:")
    print("  # .env (生產環境)")
    print("  APP_ENV=production")
    print("  CORS_ORIGINS=https://hospital.com,https://app.hospital.com")
    print("  JWT_SECRET_KEY=<your-secure-key>")

if __name__ == "__main__":
    test_production_cors_validation()
