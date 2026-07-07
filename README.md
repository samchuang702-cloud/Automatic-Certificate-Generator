# 證書自動產生系統

使用 Python、FastAPI、SQLite、Pandas、OpenPyXL、Jinja2/HTML 模板與 WeasyPrint 建立的證書自動產生系統。

## Module 1 內容

本階段完成專案初始化與資料夾結構，先建立可啟動的 FastAPI 骨架，後續模組會逐步補上資料庫、Excel 上傳、驗證、PDF 與 ZIP 功能。

## 安裝

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 啟動

```powershell
uvicorn app.main:app --reload
```

啟動後可開啟：

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/docs`

## 專案結構

```text
app/
  main.py
  core/
    config.py
  db/
  models/
  schemas/
  routers/
  services/
  templates/
  static/
storage/
  uploads/
  generated/
  database/
tests/
```

## 開發模組

1. Module 1：專案初始化與資料夾結構
2. Module 2：資料庫設計
3. Module 3：後台 Excel 上傳功能
4. Module 4：Excel 讀取與欄位驗證
5. Module 5：Excel 匯入資料庫
6. Module 6：使用者身分驗證
7. Module 7：證書清單查詢
8. Module 8：證書模板設計與套版
9. Module 9：PDF 產生功能
10. Module 10：多份證書 ZIP 打包下載
11. Module 11：後台操作紀錄
12. Module 12：錯誤處理與資安檢查
