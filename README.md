# 證書查詢與產生系統

這是本機 Windows 版的 FastAPI 證書系統。系統使用 Excel 匯入證書資料，儲存在 SQLite，使用者可用姓名與 ID 查詢並下載證書 PDF。

PDF 產生流程目前使用 Microsoft Word：

1. 讀取 `storage/templates/cfd_certificate_template.doc`
2. 替換模板中的姓名、身分證、課程、日期、證書字號等文字
3. 透過 Microsoft Word 匯出 PDF
4. PDF 存到 `storage/generated`

## 環境需求

- Windows
- Python 虛擬環境
- Microsoft Word

## 安裝

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 啟動

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8001
```

啟動後開啟：

- `http://127.0.0.1:8001/`
- `http://127.0.0.1:8001/health`
- `http://127.0.0.1:8001/docs`

## 主要資料夾

```text
app/                      系統程式
scripts/                  Microsoft Word 產 PDF 腳本
storage/database/          SQLite 資料庫
storage/uploads/           Excel 上傳暫存
storage/generated/         產出的 PDF 或 ZIP
storage/templates/         證書模板
tests/                    自動化測試
```

## 證書模板

正式 Word 模板：

```text
storage/templates/cfd_certificate_template.doc
```

目前系統會用 Microsoft Word 開啟這個模板，替換固定文字後輸出 PDF。若要調整版面，請直接用 Microsoft Word 修改這個 `.doc` 模板。

## 測試

```powershell
.\.venv\Scripts\python.exe -m pytest
```
