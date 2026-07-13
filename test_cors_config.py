#!/usr/bin/env python
"""驗證 CORS 配置"""
from app.main import app
from app.core.config import settings

print("✅ 應用導入成功")
print(f"✅ 環境: {settings.app_env}")

origins = settings.cors_origins.split(",")
print(f"✅ CORS 允許的源數量: {len(origins)}")
print("\nCORS 允許的源:")
for origin in origins:
    print(f"  - {origin.strip()}")
