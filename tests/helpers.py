from fastapi.testclient import TestClient


def auth_headers(client: TestClient, username: str = "admin", password: str = "admin123") -> dict[str, str]:
    # 登入測試帳號並取得 JWT header。
    response = client.post("/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def admin_headers(client: TestClient) -> dict[str, str]:
    # admin 可以使用所有後台功能。
    return auth_headers(client, "admin", "admin123")


def user_headers(client: TestClient) -> dict[str, str]:
    # 一般 user 只能使用使用者端證書查詢/產生功能。
    return auth_headers(client, "user", "user123")
