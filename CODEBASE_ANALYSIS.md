# FastAPI 醫院證書生成系統 - 完整代碼分析

**分析日期**: 2026-07-10  
**分析級別**: THOROUGH  
**框架**: FastAPI + SQLAlchemy + SQLite

---

## 1. 項目整體架構

### 1.1 分層架構設計

```
┌─────────────────────────────────────────────────────────────┐
│                      前端層 (Frontend)                       │
│                  Static: HTML/CSS/JS                        │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                      API 層 (Routers)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐   │
│  │ public_auth  │  │ public_       │  │ admin_excel    │   │
│  │              │  │ certificates  │  │ admin_logs     │   │
│  │              │  │              │  │ admin_template │   │
│  └──────────────┘  └──────────────┘  └────────────────┘   │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                    業務邏輯層 (Services)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐   │
│  │ Identity     │  │ Certificate  │  │ Excel          │   │
│  │ Verifier     │  │ Generator    │  │ Importer       │   │
│  │              │  │ Query        │  │ Validator      │   │
│  │              │  │              │  │ Reader         │   │
│  └──────────────┘  └──────────────┘  └────────────────┘   │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                    資料模型層 (Models)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐   │
│  │ CertRecord   │  │ UserAccount   │  │ OperationLog   │   │
│  │              │  │              │  │ CertGenRecord  │   │
│  └──────────────┘  └──────────────┘  └────────────────┘   │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│              核心層 (Core: 安全、配置、依賴)                 │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐   │
│  │ Security     │  │ Config       │  │ Dependencies   │   │
│  │ JWT/PWD Hash │  │ Settings     │  │ Auth, get_db   │   │
│  └──────────────┘  └──────────────┘  └────────────────┘   │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│              資料層 (Database & Storage)                     │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ SQLite (storage/database/certificates.db)          │  │
│  │ File System (uploads/, generated/, templates/)      │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 核心目錄結構

```
app/
├── __init__.py
├── main.py                          # 應用入口、路由註冊、CORS/異常處理
├── exceptions.py                    # 自定義異常定義
├── core/
│   ├── config.py                    # 配置管理 (Settings)
│   ├── security.py                  # JWT/密碼相關功能
│   └── excel_columns.py             # Excel 欄位定義
├── db/
│   └── session.py                   # SQLAlchemy 連線、表初始化
├── dependencies/
│   └── auth.py                      # 認證依賴注入 (JWT 驗證)
├── models/
│   ├── user_account.py              # 使用者帳號表
│   ├── certificate_record.py        # 證書紀錄表
│   ├── operation_log.py             # 操作日誌表
│   └── certificate_generation.py    # 證書生成紀錄表
├── routers/                         # API 路由
│   ├── public_auth.py               # 認證相關 (/auth/*)
│   ├── public_certificates.py       # 證書查詢/生成 (/certificates/*)
│   ├── admin_excel.py               # 管理 Excel 上傳/匯入
│   ├── admin_logs.py                # 管理 操作日誌
│   └── admin_template.py            # 管理 證書模板
├── schemas/                         # Pydantic 資料驗證
│   ├── account.py
│   ├── auth.py
│   ├── certificate.py
│   ├── excel.py
│   ├── log.py
│   └── template.py
├── services/                        # 業務邏輯層
│   ├── account_service.py           # 帳號、登入
│   ├── certificate_generator.py     # 證書生成 (Word/PDF)
│   ├── certificate_query.py         # 證書查詢
│   ├── certificate_template.py      # 模板管理
│   ├── excel_importer.py            # Excel 資料匯入
│   ├── excel_normalizer.py          # Excel 格式標準化
│   ├── excel_reader.py              # Excel 預覽讀取
│   ├── excel_upload.py              # Excel 上傳處理
│   ├── excel_validator.py           # Excel 驗證
│   ├── generated_cleanup.py         # 產出檔案清理
│   ├── identity_verifier.py         # 身分驗證查詢
│   └── operation_logger.py          # 操作日誌記錄
└── static/
    ├── index.html
    ├── app.js
    └── styles.css
```

---

## 2. 主要 API 端點和功能

### 2.1 系統端點

| 端點 | 方法 | 功能 |
|------|------|------|
| `/` | GET | 首頁 (index.html) |
| `/health` | GET | 健康檢查 |
| `/api/routes` | GET | API 路由清單 |
| `/docs` | GET | Swagger 文檔 |

### 2.2 認證端點 (`/auth/`)

| 端點 | 方法 | 授權 | 功能 |
|------|------|------|------|
| `/auth/login` | POST | 無 | 帳號/密碼登入 |
| `/auth/login/identity` | POST | 無 | 身分證驗證登入 (低權限) |
| `/auth/verify` | POST | 需 JWT | 驗證特定使用者身分 |
| `/auth/me` | GET | 需 JWT | 取得當前使用者資訊 |

**登入流程**:
1. 前端送 username + password 到 `/auth/login`
2. 後端驗證密碼並生成 PyJWT token (HS256)
3. Token 包含: `sub` (username), `role`, `display_name`, `exp`
4. 客戶端在後續請求的 `Authorization: Bearer {token}` 中使用

### 2.3 證書相關端點 (`/certificates/`)

| 端點 | 方法 | 授權 | 功能 |
|------|------|------|------|
| `/certificates/available` | POST | 需 JWT | 查詢該使用者可下載的證書清單 |
| `/certificates/generate` | POST | 需 JWT | 生成證書 PDF 或 ZIP |

**查詢參數** (CertificateListRequest):
```json
{
  "name": "王小明",
  "id_number": "A123456789",
  "user_id": "A123456789",          # 舊版欄位，相容
  "national_id": "A123456789"       # 舊版欄位，相容
}
```

**生成參數** (CertificateGenerateRequest):
```json
{
  "name": "王小明",
  "id_number": "A123456789",
  "record_ids": [1, 2, 3]           # 要產出的證書紀錄 ID
}
```

### 2.4 Excel 管理端點 (`/admin/excel/`) - 需 `admin` 角色

| 端點 | 方法 | 功能 |
|------|------|------|
| `/admin/excel/validate` | POST | 驗證上傳的 Excel |
| `/admin/excel/upload` | POST | 上傳並保存 Excel |
| `/admin/excel/preview` | POST | 預覽最近上傳的 Excel 資料 |
| `/admin/excel/preview/{filename}` | POST | 預覽指定上傳的 Excel |
| `/admin/excel/import` | POST | 匯入最近上傳的 Excel 到資料庫 |
| `/admin/excel/import/{filename}` | POST | 匯入指定上傳的 Excel |

### 2.5 日誌端點 (`/admin/logs/`) - 需 `admin` 角色

| 端點 | 方法 | 功能 |
|------|------|------|
| `/admin/logs` | GET | 取得最近的操作日誌 (預設 50 筆，最多 200 筆) |

### 2.6 模板端點 (`/admin/template/`) - 需 `admin` 角色

| 端點 | 方法 | 功能 |
|------|------|------|
| `/admin/template/inspect` | GET | 檢查證書模板配置 |

---

## 3. 安全機制分析

### 3.1 認證機制

**① JWT (PyJWT 庫)**
- **優點**:
  - 使用業界標準 PyJWT 2.13.0 (已審計)
  - 算法: HS256 (HMAC-SHA256)
  - 自動處理簽章驗證和過期檢查
  - Payload 包含用戶角色和顯示名稱

- **配置**:
  ```python
  jwt_secret_key: str = "dev-change-me-certificate-system"  # 開發用
  jwt_expire_minutes: int = 480                              # 8小時
  ```

- **生產環境強制檢查**:
  ```python
  if settings.app_env == "production" and (
      not settings.jwt_secret_key or 
      settings.jwt_secret_key == "dev-change-me-certificate-system"
  ):
      raise RuntimeError("JWT secret_key 未設定...")
  ```

**② 密碼雜湊 (PBKDF2)**
- 算法: SHA256 + 16 bytes salt + 120,000 次迭代
- 存儲: `base64(salt + digest)` (32 bytes)
- 驗證: `hmac.compare_digest()` 防止計時攻擊

### 3.2 授權機制 (RBAC)

**角色定義**:
- `admin`: 完全存取 Excel/日誌/模板管理
- `user`: 查詢及生成自己的證書

**實現方式**:
```python
def require_roles(*allowed_roles: str) -> Callable:
    def dependency(current_user: UserAccount = Depends(get_current_user)) -> UserAccount:
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="權限不足。")
        return current_user
    return dependency
```

**依賴注入**:
```python
@router.post("/admin/excel/validate", dependencies=[Depends(require_roles("admin"))])
```

### 3.3 CORS 配置

**開發環境**:
```
http://localhost:3000
http://localhost:8000
http://localhost:8001
http://127.0.0.1:3000
```

**生產環境強制檢查**:
- ❌ 禁止萬用字符 `*`
- ❌ 禁止 `http://` 非加密源
- ✅ 必須使用 `https://` 源

**CORS 頭配置**:
```python
allow_origins=allowed_origins,
allow_credentials=True,        # 允許 Cookie/認證
allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
allow_headers=["*"],
max_age=3600                   # 預檢快取 1 小時
```

### 3.4 文件大小限制 (防 DoS)

```python
MAX_EXCEL_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# 流式讀取 + 實時檢查
async def read_file_with_size_limit(file: UploadFile, max_size: int = MAX_EXCEL_FILE_SIZE) -> bytes:
    file_size = 0
    chunks = []
    async for chunk in file.file:
        file_size += len(chunk)
        if file_size > max_size:
            raise HTTPException(status_code=413, detail="檔案超過限制")
        chunks.append(chunk)
    return b"".join(chunks)
```

### 3.5 例外處理機制

**自定義異常**:
```python
- AppException              # 基類
- ValidationException       # 驗證失敗
- AuthenticationException   # 認證失敗
- AuthorizationException    # 授權失敗
- ResourceNotFoundException # 資源不存在
- ConflictException         # 衝突 (重複)
- InvalidOperationException # 無效操作
```

**全局異常處理** (main.py):
```python
@app.exception_handler(ValidationException)
@app.exception_handler(AuthenticationException)
@app.exception_handler(Pydantic ValidationError)
...
```

**錯誤回應格式**:
```json
{
  "detail": "具體錯誤訊息"
}
```

---

## 4. 數據流 - Excel 上傳到證書輸出完整流程

### 4.1 Excel 匯入流程

```
┌──────────────────────────────────────────────────────────┐
│ 1. 前端上傳 Excel 檔案                                    │
│    POST /admin/excel/upload (需 admin 角色)              │
└──────────┬───────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────┐
│ 2. read_file_with_size_limit()                            │
│    - 流式讀取，實時檢查大小 (最大 50MB)                  │
│    - 拒絕超大檔案 (HTTP 413)                             │
└──────────┬───────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────┐
│ 3. upload_excel_file()                                   │
│    - 生成唯一檔名: {timestamp}_{原始名}.xlsx             │
│    - 保存到 storage/uploads/                             │
│    - 返回上傳結果 (含檔名、路徑)                          │
└──────────┬───────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────┐
│ 4. 客戶端後續操作:                                        │
│    a) POST /admin/excel/preview/{filename}               │
│       - 預覽 Excel 內容 (不修改資料庫)                   │
│    b) POST /admin/excel/import/{filename}                │
│       - 正式匯入到資料庫                                 │
└──────────┬───────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────┐
│ 5. import_excel_content()                                │
│    a) validate_excel_file()                              │
│       - 檢查必要欄位: user_id, national_id, name         │
│                     certificate_name, issue_date         │
│       - 驗證日期格式                                     │
│       - 若失敗，返回驗證錯誤清單                          │
│                                                           │
│    b) normalize_excel_dataframe()                        │
│       - 讀取 .xlsx/.xls 檔案                             │
│       - 欄位名稱標準化                                   │
│       - 去除空行與空格                                   │
│                                                           │
│    c) 逐行處理:                                          │
│       - 對於每行記錄:                                    │
│         * 檢查是否已存在 (unique: user_id + cert_name)  │
│         * 如存在，更新; 不存在，新增                      │
│       - 同一 Excel 內重複記錄以最後一列為準              │
│                                                           │
│    d) db.commit()                                        │
│       - 事務提交到 SQLite                                │
│       - 返回統計: 新增數、更新數                          │
└──────────┬───────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────┐
│ 6. create_operation_log()                                │
│    - 記錄操作: 上傳者、檔名、成功/失敗、錯誤數           │
└──────────────────────────────────────────────────────────┘
```

### 4.2 證書查詢流程

```
┌──────────────────────────────────────────────────────────┐
│ 1. 前端查詢可用證書                                      │
│    POST /certificates/available                          │
│    Body: { name, id_number }                             │
└──────────┬───────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────┐
│ 2. list_available_certificates()                         │
│    a) resolve_lookup_inputs()                            │
│       - 相容新舊欄位名稱                                 │
│       - name/id_number 或 user_id/national_id           │
│                                                           │
│    b) find_records_by_name_and_id()                      │
│       - 查詢 WHERE                                       │
│         (name == lookup_name OR user_id == lookup_name)  │
│         AND national_id == lookup_id                     │
│                                                           │
│    c) 資料驗證:                                          │
│       - 查無記錄 → "查無符合資料"                        │
│       - 有同名但 ID 不符 → "身分證字號不符"              │
│       - 比對成功 → 返回符合記錄清單                      │
└──────────┬───────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────┐
│ 3. CertificateListResult 返回:                           │
│    {                                                      │
│      "verified": true/false,                             │
│      "message": "查詢成功/失敗原因",                      │
│      "total": 證書數,                                    │
│      "certificates": [                                   │
│        {                                                  │
│          "record_id": 1,                                 │
│          "certificate_name": "病歷管理證書",             │
│          "issue_date": "2026-07-01",                    │
│          "note": "時數：120"                             │
│        }                                                  │
│      ]                                                    │
│    }                                                      │
└──────────────────────────────────────────────────────────┘
```

### 4.3 證書生成流程 (最複雜部分)

```
┌──────────────────────────────────────────────────────────┐
│ 1. 前端請求生成證書                                      │
│    POST /certificates/generate                           │
│    Body: {                                               │
│      "name": "王小明",                                   │
│      "id_number": "A123456789",                          │
│      "record_ids": [1, 2, 3]  ◄── 要生成的證書 ID      │
│    }                                                      │
└──────────┬───────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────┐
│ 2. 驗證使用者身分 (verify_identity)                      │
│    - 確保使用者只能下載自己的證書                        │
│    - 檢查 name + id_number 符合記錄                     │
└──────────┬───────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────┐
│ 3. 從資料庫提取指定 record_ids 的記錄                    │
│    SELECT * FROM certificate_records                     │
│    WHERE id IN (1, 2, 3)                                 │
└──────────┬───────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────┐
│ 4. 對每條記錄生成 PDF:                                   │
│                                                           │
│    4a. 構建模板替換資料:                                 │
│         _certificate_data(record) → dict                │
│         {                                                │
│           "name": "王小明",                              │
│           "姓名": "王小明",                              │
│           "身分證": "A1234*****",    ◄── 後 5 碼遮罩   │
│           "活動": "病歷管理證書",                       │
│           "日期": "2026-07-01",                         │
│           "時數": "120",                                │
│           ...                                            │
│         }                                                │
│                                                           │
│    4b. 調用 Word 自動化 (Windows 專用):                  │
│         subprocess.run([                                 │
│           "powershell.exe",                              │
│           "scripts/render_word_certificate.ps1",         │
│           "--template", ".../cfd_certificate_template.doc"
│           "--output", ".../generated/xxx.pdf",           │
│           "--replacements", json_replacements           │
│         ])                                               │
│                                                           │
│    4c. Word 執行流程:                                    │
│         - 打開 .doc 模板                                │
│         - 批量替換文字 (使用 Word 書籤)                │
│         - 匯出為 PDF                                     │
│         - 返回成功/失敗                                  │
│                                                           │
│    4d. 若 use_word_certificate_renderer=False:           │
│         - 改用 ReportLab 直接生成 PDF                   │
│         - 疊加 PDF 背景 + 文字                          │
└──────────┬───────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────┐
│ 5. 組織輸出:                                             │
│                                                           │
│    5a. 單一證書:                                         │
│         - 直接返回 PDF                                   │
│         - Content-Type: application/pdf                 │
│                                                           │
│    5b. 多個證書:                                         │
│         - 將所有 PDF 打包成 ZIP                          │
│         - 名稱: {name}_{id}_多個證書_{timestamp}.zip     │
│         - Content-Type: application/zip                 │
└──────────┬───────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────┐
│ 6. 檔案保存與清理:                                       │
│    - 所有 PDF/ZIP 保存到 storage/generated/{日期時間}/   │
│    - cleanup_old_generated_files()                       │
│      * 定期清理超過 90 天的老舊檔案                       │
│      * 應用啟動時執行一次                                │
│      * 防止無限占用磁碟空間                              │
└──────────┬───────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────┐
│ 7. 返回給客戶端:                                         │
│    FileResponse(                                         │
│      path=生成的 PDF/ZIP 路徑,                           │
│      filename=王小明_證書.pdf,                           │
│      media_type=application/pdf                         │
│    )                                                     │
│    ◄── 瀏覽器直接下載或預覽                              │
└──────────────────────────────────────────────────────────┘
```

---

## 5. 外部依賴和集成

### 5.1 主要依賴概覽

| 依賴 | 版本 | 用途 | 類別 |
|------|------|------|------|
| **fastapi** | 0.116.1 | API 框架 | 核心 |
| **uvicorn** | 0.35.0 | ASGI 伺服器 | 核心 |
| **sqlalchemy** | 2.0.41 | ORM | 資料庫 |
| **pandas** | 2.3.1 | 資料處理 | Excel |
| **openpyxl** | 3.1.5 | Excel 讀寫引擎 | Excel |
| **PyJWT** | 2.13.0 | JWT 認證 | 安全 |
| **reportlab** | 5.0.0 | PDF 生成 | 文件 |
| **weasyprint** | 65.1 | HTML→PDF (備用) | 文件 |
| **python-multipart** | 0.0.20 | 文件上傳 | 工具 |
| **pytest** | 8.4.1 | 測試框架 | 測試 |
| **httpx** | 0.28.1 | HTTP 客戶端 | 測試 |

### 5.2 系統依賴

**Windows 環境**:
- ✅ **Microsoft Word** (用於 PDF 生成)
  - 調用方式: PowerShell 腳本 → COM 自動化
  - 文件: `scripts/render_word_certificate.ps1`
  
**Python 虛擬環境**:
- 使用 `python -m venv` 隔離依賴
- 啟動: `.\.venv\Scripts\Activate.ps1`

### 5.3 與 Microsoft Word 的集成

```powershell
# scripts/render_word_certificate.ps1
# 功能:
# 1. 接收模板路徑、替換資料、輸出路徑
# 2. 啟動 Word COM 物件
# 3. 開啟 .doc 模板
# 4. 批量查詢替換文字
# 5. 匯出為 PDF
# 6. 關閉 Word

# Python 調用:
subprocess.run([
    "powershell.exe",
    "scripts/render_word_certificate.ps1",
    "--template", template_path,
    "--output", output_pdf_path,
    "--replacements", json.dumps(replacement_dict)
])
```

---

## 6. 測試覆蓋情況

### 6.1 現有測試套件 (11 個測試模組)

```
tests/
├── __init__.py
├── helpers.py                      # 測試共用工具函數
├── test_health.py                  # 健康檢查
├── test_index.py                   # 首頁路由
├── test_rbac.py                    # RBAC 角色權限測試
├── test_excel_validation.py        # Excel 驗證
├── test_excel_upload.py            # Excel 上傳 (含文件大小限制)
├── test_excel_preview.py           # Excel 預覽
├── test_excel_import.py            # Excel 匯入資料庫
├── test_identity_verify.py         # 身分驗證
├── test_certificate_list.py        # 證書清單查詢
├── test_certificate_generation.py  # 證書生成
└── test_generated_cleanup.py       # 老舊檔案清理
```

### 6.2 測試覆蓋領域分析

| 領域 | 覆蓋狀態 | 測試文件 |
|------|---------|---------|
| **認證/授權** | ✅ 完整 | test_rbac.py |
| **身分驗證** | ✅ 完整 | test_identity_verify.py |
| **Excel 驗證** | ✅ 完整 | test_excel_validation.py |
| **Excel 上傳** | ✅ 完整 (含大小限制) | test_excel_upload.py |
| **Excel 導入** | ✅ 完整 | test_excel_import.py |
| **證書查詢** | ✅ 完整 | test_certificate_list.py |
| **證書生成** | ⚠️ 部分 | test_certificate_generation.py |
| **檔案清理** | ✅ 完整 | test_generated_cleanup.py |
| **路由/系統** | ✅ 基礎 | test_health.py, test_index.py |
| **Word 集成** | ❌ 未測 | - |
| **CORS** | ⚠️ 需加強 | - |

### 6.3 最近改進的測試覆蓋

**新增測試檔案** (根據 repo 內的 test_*.py 文件):
- `test_cors_config.py` - CORS 配置驗證
- `test_cors_functionality.py` - CORS 功能測試
- `test_exception_handlers.py` - 異常處理測試
- `test_exception_handlers_detailed.py` - 詳細異常處理測試
- `test_file_size_detailed.py` - 文件大小限制詳細測試
- `test_file_size_limit.py` - 文件大小限制測試
- `test_production_cors_security.py` - 生產環境 CORS 安全測試
- `test_pyjwt_integration.py` - PyJWT 集成測試

### 6.4 測試框架配置

```python
# pytest 配置
pytest==8.4.1
pytest-asyncio==1.4.0          # 異步測試支援
httpx==0.28.1                  # HTTP 客戶端 (測試用)

# 測試模式啟動:
pytest tests/
pytest tests/test_excel_import.py -v
pytest -k "test_excel" --cov=app
```

---

## 7. 代碼組織結構評估

### 7.1 ✅ 優點

| 面向 | 評價 | 說明 |
|------|------|------|
| **分層清晰** | ⭐⭐⭐⭐⭐ | 路由 → 服務 → 模型 → 資料庫，邏輯清晰 |
| **關注點分離** | ⭐⭐⭐⭐ | 各層職責明確，服務層獨立 |
| **相容性** | ⭐⭐⭐⭐⭐ | 新舊欄位相容，無強制遷移 |
| **安全機制** | ⭐⭐⭐⭐ | JWT (PyJWT) + PBKDF2 + CORS + 大小限制 |
| **異常處理** | ⭐⭐⭐⭐ | 自定義異常層級完整 |
| **配置管理** | ⭐⭐⭐⭐ | Settings + .env，生產環境驗證 |
| **操作日誌** | ⭐⭐⭐⭐ | 完整的審計日誌記錄 |

### 7.2 ⚠️ 可改進之處

| 項目 | 級別 | 說明 |
|------|------|------|
| **缺全局異常處理** | MEDIUM | main.py 異常處理不完整，部分異常未被捕獲 |
| **缺使用者輸入驗證層** | MEDIUM | 輸入驗證分散在各個服務，無統一層 |
| **SQLite 單線程** | MEDIUM | 生產環境需改為 PostgreSQL/MySQL |
| **Word 依賴** | MEDIUM | 生產環境需部署 Word，建議改為 ReportLab |
| **缺速率限制** | MEDIUM | 無請求頻率限制，易暴力攻擊 |
| **缺日誌框架** | LOW | 採用簡單 logging，無統一日誌配置 |
| **缺類型提示** | LOW | 某些地方缺 type hints |
| **Word 腳本未測** | MEDIUM | render_word_certificate.ps1 缺單元測試 |

---

## 8. 核心業務邏輯流程詳解

### 8.1 唯一性約束與重複處理

**資料庫約束**:
```python
UniqueConstraint("user_id", "certificate_name", name="uq_user_certificate")
```

**匯入邏輯** (excel_importer.py):
1. 檢查 (user_id, certificate_name) 組合是否在資料庫中存在
2. **若存在**: 更新記錄 (`updated_count += 1`)
3. **若不存在**: 插入新記錄 (`inserted_count += 1`)
4. **同一 Excel 內重複**: 以最後一列為準 (記錄在 `records_seen_in_batch`)

**場景範例**:
```
Excel 內容:
行1: user_id=A001, cert=病歷管理, name=王小明
行2: user_id=A001, cert=病歷管理, name=王小明 (重複)

處理:
- 行1: INSERT → inserted_count = 1
- 行2: UPDATE (因在 records_seen_in_batch 中存在) → updated_count = 1
```

### 8.2 身分驗證與鏡像欄位管理

**新舊欄位對映**:
```
新欄位              舊欄位 (仍相容)
name          ↔   user_id
id_number     ↔   national_id
```

**查詢邏輯** (identity_verifier.py):
```python
def resolve_lookup_inputs(name, id_number, user_id, national_id):
    lookup_name = (name or user_id or "").strip()        # 優先用新欄位
    lookup_id = normalize_national_id(id_number or national_id or "")
    return lookup_name, lookup_id

# 查詢條件 (OR):
SELECT * FROM certificate_records
WHERE (name == lookup_name OR user_id == lookup_name)
  AND national_id == lookup_id
```

### 8.3 證書 PDF 中的隱私保護

**身分證遮罩邏輯**:
```python
def _mask_national_id(value: str) -> str:
    if len(value) > 5:
        return f"{value[:5]}{'*' * (len(value) - 5)}"
    return value
# 例: "A123456789" → "A1234*****"
```

**備註欄提取** (支援民國年份等客製信息):
```python
def _note_value(note: str | None, label: str) -> str:
    # 備註格式: "時數：120；完成日期：中華民國110年"
    # 提取 label 對應的值
```

### 8.4 生產環境安全檢查機制

**應用啟動時 (main.py)**:

```python
# 1. JWT 秘鑰檢查
if settings.app_env == "production" and (
    not settings.jwt_secret_key or 
    settings.jwt_secret_key == "dev-change-me-certificate-system"
):
    raise RuntimeError("JWT secret_key 未設定或仍為預設值...")

# 2. CORS 安全檢查
if settings.app_env == "production":
    for origin in allowed_origins:
        if origin == "*" or origin.startswith("http://"):
            raise RuntimeError(
                f"生產環境 CORS 配置不安全。"
                "請設定具體的 HTTPS 源..."
            )

# 3. 資料庫表初始化
create_db_and_tables()

# 4. 老舊檔案清理
cleanup_old_generated_files()
```

---

## 9. 現有改進分析

### 9.1 PyJWT 集成 ✅

**改進前**: 自定義 JWT 實現 (易出錯)  
**改進後**: 使用 PyJWT 2.13.0 (業界標準)

```python
# app/core/security.py
def create_access_token(payload: dict[str, Any]) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode(
        {**payload, "exp": expires_at},
        settings.jwt_secret_key,
        algorithm="HS256"
    )

def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
    # 自動處理過期 (ExpiredSignatureError) 和無效 (InvalidTokenError)
```

### 9.2 CORS 配置 ✅

**改進前**: 無 CORS 配置 (跨域攻擊風險)  
**改進後**: FastAPI CORSMiddleware + 生產環境強制驗證

```python
# main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    max_age=3600,
)

# 生產環境檢查: 禁止 *, 必須 HTTPS
```

### 9.3 異常處理 ✅

**改進前**: 零散異常處理  
**改進後**: 層級化異常 + 全局處理

```python
# app/exceptions.py
class AppException(Exception): pass
class ValidationException(AppException): pass
class AuthenticationException(AppException): pass
class AuthorizationException(AppException): pass
...

# main.py 全局處理 (見 main.py 後半段)
@app.exception_handler(ValidationException)
def handle_validation_error(...): ...
```

### 9.4 文件大小限制 ✅

**改進前**: 一次性讀入內存 (DoS 風險)  
**改進後**: 流式讀取 + 實時大小檢查

```python
# app/routers/admin_excel.py
async def read_file_with_size_limit(file: UploadFile, max_size: int = MAX_EXCEL_FILE_SIZE) -> bytes:
    file_size = 0
    chunks = []
    async for chunk in file.file:
        file_size += len(chunk)
        if file_size > max_size:
            raise HTTPException(status_code=413, detail="檔案超過限制")
        chunks.append(chunk)
    return b"".join(chunks)
```

---

## 10. 可能的改進機會

### 10.1 ⭐⭐⭐ 高優先級

| # | 改進項 | 說明 | 工作量 |
|---|--------|------|--------|
| 1 | **速率限制** | 添加 slowapi/ratelimit，防止暴力攻擊 | 中 |
| 2 | **全局異常處理** | 完整的異常捕獲器，統一錯誤格式 | 中 |
| 3 | **PostgreSQL 遷移** | 生產環境用 PostgreSQL，支持併發 | 大 |
| 4 | **API 日誌中間件** | 記錄所有請求 (含響應時間、狀態碼) | 小 |
| 5 | **輸入驗證層** | 集中式輸入驗證，整合 Pydantic | 中 |

### 10.2 ⭐⭐ 中優先級

| # | 改進項 | 說明 | 工作量 |
|---|--------|------|--------|
| 6 | **非 Word 生成** | 改用 ReportLab 直接生成 PDF (不依賴 Word) | 大 |
| 7 | **非同步 API** | 將阻塞操作改為非同步 (asyncio + BackgroundTasks) | 大 |
| 8 | **分頁 API** | 日誌/結果列表添加分頁支援 | 小 |
| 9 | **API 版本化** | 引入 /api/v1/, /api/v2/ 支持演進 | 小 |
| 10 | **模板引擎** | 改用 Jinja2/Mako 管理文字替換邏輯 | 中 |

### 10.3 ⭐ 低優先級

| # | 改進項 | 說明 | 工作量 |
|---|--------|------|--------|
| 11 | **日誌框架** | 集成 structlog/loguru，結構化日誌 | 小 |
| 12 | **API 文檔** | 完善 OpenAPI 描述 (description, example) | 小 |
| 13 | **類型提示** | 全局補齊 type hints，使用 mypy 檢查 | 小 |
| 14 | **單元測試增強** | 補充 Word 集成、邊界情況測試 | 中 |
| 15 | **代碼風格** | 導入 Black/isort，自動格式化 | 小 |

### 10.4 具體改進建議

**1. 速率限制範例**:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/certificates/generate")
@limiter.limit("10/minute")  # 每分鐘最多 10 次
def generate_certificates(...): ...
```

**2. 全局異常處理補充**:
```python
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "伺服器發生錯誤"}
    )
```

**3. API 日誌中間件**:
```python
from fastapi import Request
import time

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.3f}s"
    )
    return response
```

**4. 非同步證書生成** (改進大檔案處理):
```python
from fastapi import BackgroundTasks

@app.post("/certificates/generate-async")
async def generate_certificates_async(
    payload: CertificateGenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    job_id = str(uuid4())
    background_tasks.add_task(
        generate_and_save_certificates,
        job_id, payload, db
    )
    return {"job_id": job_id, "status": "processing"}
```

---

## 11. 總結

### 11.1 系統現狀評分

| 維度 | 評分 | 備註 |
|------|------|------|
| **架構設計** | 8/10 | 分層清晰，職責分明 |
| **安全性** | 7/10 | JWT/CORS/大小限制完善，缺速率限制 |
| **代碼質量** | 7/10 | 相容性好，部分地方缺類型提示 |
| **測試覆蓋** | 7/10 | 覆蓋主要功能，缺 Word 集成測試 |
| **性能** | 6/10 | SQLite 限制，Word 依賴瓶頸 |
| **可維護性** | 8/10 | 代碼清晰，邏輯易懂 |
| **文檔** | 6/10 | 基礎文檔，缺詳細說明 |

**整體評價**: ⭐⭐⭐⭐ (4/5) - **生產級應用** (需加強性能和速率限制)

### 11.2 關鍵優勢

1. ✅ **安全至上**: JWT + CORS + 大小限制 + 生產環保檢查
2. ✅ **向後相容**: 新舊欄位共存，無強制遷移
3. ✅ **審計完善**: 操作日誌記錄詳細
4. ✅ **代碼組織**: 分層明確，易擴展
5. ✅ **異常處理**: 自定義異常層級完整

### 11.3 關鍵風險

1. ⚠️ **缺速率限制**: 易暴力攻擊
2. ⚠️ **SQLite 單線程**: 生產環境併發性能低
3. ⚠️ **Word 依賴**: Windows 專用，難跨平台部署
4. ⚠️ **缺統一日誌**: 無結構化日誌分析能力
5. ⚠️ **異常處理不完整**: 部分邊界情況未覆蓋

### 11.4 建議優先順序

1. **立即** (1-2 週): 添加速率限制、完善異常處理
2. **短期** (1-2 月): 遷移 PostgreSQL、非同步化、Word 改 ReportLab
3. **中期** (2-3 月): 結構化日誌、完整測試覆蓋
4. **長期** (3-6 月): 容器化部署、微服務架構考慮

