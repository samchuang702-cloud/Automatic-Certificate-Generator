# Automatic Certificate Generator

大林慈濟證書查詢與產生系統。  
這是一個以 FastAPI 建立的本機/內部使用版證書系統，支援 Excel 匯入證書資料、使用者查詢可產生證書、輸出 PDF 或 ZIP，以及後台操作紀錄。

目前 PDF 產生主流程使用 Microsoft Word 模板：

```text
storage/templates/cfd_certificate_template.doc
        ↓
Python 產生替換資料
        ↓
PowerShell 呼叫 Microsoft Word
        ↓
Word 匯出 PDF
        ↓
storage/generated/
```

## 目前功能

- 使用者登入
  - `admin`：後台管理者
  - `user`：一般使用者
- 一般使用者可用姓名與身分證字號查詢可產生的證書
- 後台可上傳、預覽、匯入 Excel
- 匯入資料儲存在 SQLite
- 證書可輸出單張 PDF
- 多張證書會打包成 ZIP
- PDF 證書身分證字號只顯示前 5 碼，其餘以 `*` 遮罩
- 後台操作紀錄
- JWT 登入驗證
- CORS 設定
- Excel 上傳大小限制，預設 50MB
- 前端避免直接使用 `innerHTML` 顯示外部資料，降低 XSS 風險
- 前端使用 `sessionStorage` 暫存登入資料，關閉分頁後不長期保留 token 與身分證查詢資料

## 技術架構

```text
Browser
  ↓
FastAPI
  ↓
SQLAlchemy ORM
  ↓
SQLite
  ↓
Microsoft Word + PowerShell
  ↓
PDF / ZIP
```

主要技術：

- Python
- FastAPI
- SQLAlchemy
- SQLite
- PyJWT
- Pandas / OpenPyXL
- Microsoft Word COM Automation
- PowerShell
- 原生 HTML / CSS / JavaScript
- Pytest

## 環境需求

建議環境：

- Windows
- Python 3.12
- Microsoft Word
- PowerShell
- Git

注意：目前正式 PDF 產生依賴 Microsoft Word，所以若執行環境沒有安裝 Word，證書 PDF 產生會失敗。

## 安裝

在 PowerShell 進入專案資料夾：

```powershell
cd "C:\Users\samch\Desktop\醫院實習專案"
```

建立虛擬環境：

```powershell
python -m venv .venv
```

安裝套件：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 環境設定

專案會讀取 `.env`，範本是 `.env.example`。

本機開發可以複製：

```powershell
Copy-Item .env.example .env
```

重要設定：

```env
APP_ENV=development
DATABASE_URL=sqlite:///./storage/database/certificates.db

DEFAULT_ADMIN_PASSWORD=請改成你的管理員密碼
DEFAULT_USER_PASSWORD=請改成你的使用者密碼

JWT_SECRET_KEY=請改成一串很長的隨機字串
JWT_EXPIRE_MINUTES=480

CORS_ORIGINS=http://localhost:8001,http://127.0.0.1:8001

UPLOAD_DIR=storage/uploads
GENERATED_DIR=storage/generated
GENERATED_RETENTION_DAYS=90

CERTIFICATE_WORD_TEMPLATE_PATH=storage/templates/cfd_certificate_template.doc
```

`.env` 不應該上傳 GitHub。  
`.gitignore` 已排除 `.env`。

## 啟動系統

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8001
```

啟動後開啟：

- 前端頁面：http://127.0.0.1:8001/
- API 文件：http://127.0.0.1:8001/docs
- 健康檢查：http://127.0.0.1:8001/health
- 路由總覽：http://127.0.0.1:8001/api/routes

## 預設帳號

若沒有設定 `.env`，開發環境會使用程式碼預設值：

```text
admin / admin123
user  / user123
```

正式環境務必透過 `.env` 或伺服器環境變數覆蓋預設密碼。

目前系統只保留兩種權限：

| 角色 | 說明 |
|---|---|
| `admin` | 可使用後台 Excel 管理、操作紀錄、模板檢查 |
| `user` | 可查詢並產生自己的證書 |

## 使用流程

### 管理者流程

1. 使用 `admin` 帳號登入
2. 選擇 Excel 檔案
3. 預覽資料
4. 匯入資料
5. 檢查操作紀錄

### 一般使用者流程

1. 輸入姓名與身分證字號登入
2. 系統查詢可產生的證書
3. 勾選證書
4. 產生 PDF
5. 若選擇多張，系統會輸出 ZIP

## Excel 匯入欄位

系統支援多種欄位別名，會在後端標準化成固定欄位。

主要欄位：

| 標準欄位 | 說明 |
|---|---|
| `user_id` | 使用者查詢 ID |
| `national_id` / `id_number` | 身分證字號 |
| `name` | 姓名 |
| `certificate_name` | 活動 / 證書名稱 |
| `issue_date` / `date` | 發證日期 |
| `certificate_id` | 證書字號 |
| `course_name` | 課程種類 |
| `completion_date` | 完成日期 |
| `note` | 備註 / 時數 |

無效 Excel 不會寫入資料庫。

## 證書 PDF 模板

正式 Word 模板：

```text
storage/templates/cfd_certificate_template.doc
```

PDF 產生腳本：

```text
scripts/render_word_certificate.ps1
```

目前會替換 Word 模板中的固定文字，例如：

- 姓名
- 身分證遮罩
- 發證日期
- 活動名稱
- 證書字號
- 時數
- 課程種類

若要調整證書版面，請直接用 Microsoft Word 修改：

```text
storage/templates/cfd_certificate_template.doc
```

## API 重點

| API | 說明 | 權限 |
|---|---|---|
| `POST /auth/login` | 帳號密碼登入 | 公開 |
| `POST /auth/login/identity` | 姓名與身分證登入 | 公開 |
| `POST /certificates/available` | 查詢可產生證書 | 登入 |
| `POST /certificates/generate` | 產生 PDF / ZIP | 登入 |
| `POST /admin/excel/preview` | 預覽 Excel | admin |
| `POST /admin/excel/upload` | 上傳 Excel | admin |
| `POST /admin/excel/import` | 直接匯入 Excel | admin |
| `GET /admin/logs` | 查看操作紀錄 | admin |
| `GET /admin/template/inspect` | 檢查 PPTX 模板資訊 | admin |

## 資料庫

目前使用 SQLite：

```text
storage/database/certificates.db
```

主要資料表：

| 資料表 | 說明 |
|---|---|
| `user_accounts` | 登入帳號、密碼 hash、角色 |
| `certificate_records` | 證書資料 |
| `certificate_generation_records` | 證書產生紀錄 |
| `operation_logs` | 後台操作紀錄 |

目前資料表由 SQLAlchemy ORM model 管理。

## 主要資料夾

```text
app/
  core/                 設定、安全、欄位對應
  db/                   SQLAlchemy session 與資料庫初始化
  dependencies/         JWT 與角色權限依賴
  models/               SQLAlchemy ORM models
  routers/              FastAPI API routes
  schemas/              Pydantic schemas
  services/             商業邏輯
  static/               前端 HTML/CSS/JS

scripts/                Microsoft Word 產 PDF 腳本
storage/
  database/             SQLite 資料庫
  generated/            產出的 PDF / ZIP
  templates/            證書模板
  uploads/              Excel 上傳檔案

tests/                  自動化測試
```

## 測試

執行完整測試：

```powershell
.\.venv\Scripts\python.exe -m pytest
```

目前測試涵蓋：

- 登入與 JWT
- 權限 RBAC
- Excel 驗證、預覽、上傳、匯入
- 證書查詢
- 證書 PDF / ZIP 產生
- 操作紀錄
- 上傳檔案大小限制
- CORS 設定
- 例外處理
- 產出檔案清理

## 安全設計與注意事項

目前已處理：

- 密碼以 PBKDF2 hash 保存，不保存明文密碼
- JWT 使用 PyJWT 產生與驗證
- 生產環境禁止使用預設 JWT secret
- 後端 API 檢查角色權限，不只依賴前端隱藏按鈕
- 前端顯示外部資料時避免直接使用 `innerHTML`
- 前端改用 `sessionStorage`，避免長期保存 token 與身分證查詢資料
- Excel 上傳有 50MB 大小限制
- 上傳檔名由後端重新產生，避免直接使用原始路徑
- 產出檔案有保留天數設定

正式上線仍建議補強：

- 改用 HTTPS
- SQLite 改 PostgreSQL 或 MySQL
- 使用正式資料庫備份策略
- 使用 httpOnly + Secure + SameSite cookie 管理登入狀態
- 增加帳號管理與修改密碼功能
- 增加更完整的 audit log，例如 IP、User-Agent、下載紀錄
- 在 Nginx / IIS / reverse proxy 設定 request body size
- PDF 產生改背景任務或 queue，避免 Word 轉檔阻塞 API worker
- 依醫院資安規範評估身分證欄位加密

## 正式部署建議

目前專案適合：

- 本機開發
- 展示
- 小型內部單機使用

若要正式多人上線，建議調整為：

```text
Nginx / IIS reverse proxy
  ↓ HTTPS
FastAPI / Uvicorn
  ↓
PostgreSQL 或 MySQL
  ↓
檔案儲存區
```

正式環境 `.env` 至少要設定：

```env
APP_ENV=production
DATABASE_URL=postgresql+psycopg://user:password@host:5432/dbname
JWT_SECRET_KEY=一串高強度隨機字串
CORS_ORIGINS=https://正式網域
DEFAULT_ADMIN_PASSWORD=正式強密碼
DEFAULT_USER_PASSWORD=正式強密碼
```

## 常見問題

### 1. 啟動時出現 `No module named jwt`

請重新安裝依賴：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. PDF 產生失敗

請確認：

- Windows 已安裝 Microsoft Word
- `storage/templates/cfd_certificate_template.doc` 存在
- PowerShell 可以執行 `scripts/render_word_certificate.ps1`
- Word 沒有跳出視窗卡住

### 3. Port 被占用

改用其他 port：

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8002
```

再開：

```text
http://127.0.0.1:8002/
```

### 4. 修改 `.env` 後沒有生效

請重新啟動 FastAPI。

### 5. 修改預設密碼後登入仍是舊密碼

開發環境啟動時會重新 seed 預設帳號。  
如果資料庫內已有帳號，請確認 `.env` 是否真的被讀取，或刪除/更新既有 SQLite 帳號資料。
