from fastapi.testclient import TestClient

from app.main import app


def test_index_returns_frontend_html() -> None:
    # 測試根路徑是否能正常回應。
    # 這讓瀏覽器打開 http://127.0.0.1:8000/ 時會看到前端操作介面。
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "證書查詢" in response.text
    assert "登入系統" in response.text
    assert "<span>名字</span>" in response.text
    assert '<input id="passwordInput" type="text" />' in response.text
    assert "usernameInput" in response.text
    assert "verifyButton" not in response.text
    assert "userIdInput" not in response.text
    assert "nationalIdInput" not in response.text
    assert "adminNavLink" not in response.text
    assert 'id="admin" class="panel hidden"' in response.text
    assert 'id="user" class="panel hidden"' in response.text
    assert "API 文件" not in response.text


def test_static_assets_are_available() -> None:
    # 測試前端 CSS 與 JavaScript 能被 FastAPI 正常提供。
    client = TestClient(app)

    css_response = client.get("/static/styles.css")
    js_response = client.get("/static/app.js")

    assert css_response.status_code == 200
    assert js_response.status_code == 200
    assert "generateCertificates" in js_response.text
    assert "Authorization" in js_response.text
    assert "county_staff" not in js_response.text


def test_routes_lists_available_routes() -> None:
    # API 路由總覽保留在 /api/routes，方便開發時檢查目前功能。
    client = TestClient(app)

    response = client.get("/api/routes")

    assert response.status_code == 200
    assert response.json()["excel_validate"] == "/admin/excel/validate"
    assert response.json()["excel_upload"] == "/admin/excel/upload"
    assert response.json()["excel_preview"] == "/admin/excel/preview"
    assert response.json()["excel_import"] == "/admin/excel/import"
    assert response.json()["available_certificates"] == "/certificates/available"
    assert response.json()["certificate_generate"] == "/certificates/generate"
    assert response.json()["template_inspect"] == "/admin/template/inspect"
