# TestClient 讓我們不用真的啟動伺服器，也能測試 FastAPI API。
from fastapi.testclient import TestClient

# 匯入目前專案的 FastAPI app。
from app.main import app


def test_health_check() -> None:
    # 建立測試用 client，之後可用它發送 GET、POST 等請求。
    client = TestClient(app)

    # 呼叫健康檢查 API。
    response = client.get("/health")

    # 確認 API 有正常回應 HTTP 200。
    assert response.status_code == 200

    # 確認回傳內容中的 status 是 ok，代表服務狀態正常。
    assert response.json()["status"] == "ok"
