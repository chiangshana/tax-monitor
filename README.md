# 跨國法令與稅務風險監測系統（Tax Monitor API）

這是一個以 FastAPI 建立的後端原型，目標是把「法規資料蒐集、語言處理、風險判斷、報告輸出」整理成可被 `n8n` 串接的分析核心。

目前系統已支援：

- 文件上傳與網站內容匯入
- 文件分頁查詢、單篇詳情檢索與中繼資料更新
- 關鍵字抽取與關鍵字設定檔訓練
- 多語言分析
- `translate_first` / `analyze_first` 兩種分析模式
- 可切換 `ollama / openai / gemini / claude`
- 風險標籤與中英對照摘要輸出
- `rule-based vs LLM` 比較用 evaluation endpoint
- 搜尋結果自動匯入
- 輸出 Obsidian 筆記格式或投影片大綱格式

## 專案目標

1. 自動整理跨國法規、稅務公告與政策更新
2. 協助辨識潛在稅務風險與申報影響
3. 降低人工閱讀與整理成本
4. 作為 `n8n` 全自動化流程的分析後端

## 依雙周報告對齊的 PoC 方向

這一版依照 `2026/4/3` 與 `2026/4/17` 雙周進度報告，優先往以下方向對齊：

1. 保留 `FastAPI + SQLite + Ollama/Qwen + n8n` 的 PoC 基礎架構
2. 補上報告提到的資料欄位與文件管理需求，例如 `country`、`source_name`、`published_date`
3. 補上文件列表、詳情查詢、更新與分頁機制，讓前端或 Streamlit 可直接接
4. 把風險標籤、中英摘要與 prompt engineering 寫入分析邏輯
5. 建立簡化版 evaluation framework，先做 `rule-based vs LLM` 比較

## 目前架構

- `main.py`：FastAPI 入口
- `routers/`：API 路由
- `services/`：核心商業邏輯
- `models/`：Pydantic schema
- `data/`：原始資料與資料庫

### Service 分工

- `document_service.py`：處理檔案上傳、PDF 文字抽取、網址內容抓取
- `search_service.py`：依關鍵字與時間區間搜尋資料來源
- `keyword_service.py`：TF-IDF 關鍵字抽取、使用者需求關鍵字擴展
- `analysis_service.py`：摘要、證據句抽取、風險等級判斷、風險標籤、evaluation
- `translator_service.py`：翻譯流程
- `llm_service.py`：統一管理不同 LLM provider 呼叫
- `report_service.py`：輸出 Obsidian / Slides 格式內容
- `storage_service.py`：SQLite 存取與 fallback storage 控制

## 分析流程

### 1. 文件來源

可由以下方式進入系統：

- 手動上傳檔案
- 匯入網址內容
- 搜尋關鍵字後自動匯入搜尋結果

### 2. 分析模式

- `translate_first`：先翻譯再分析
- `analyze_first`：先分析再翻譯

### 3. 模型供應商

`AnalysisRequest` 與 `ReportRequest` 目前支援：

- `ollama`
- `openai`
- `gemini`
- `claude`

### 4. 搜尋時間區間

`SearchRequest.date_range` 目前支援：

- `7d`
- `1m`
- `3m`
- `6m`
- `1y`
- `custom`

## 專案結構

```text
tax_monitor/
├─ main.py
├─ README.md
├─ requirements.txt
├─ models/
│  └─ schemas.py
├─ routers/
│  ├─ analysis.py
│  └─ document.py
├─ services/
│  ├─ analysis_service.py
│  ├─ document_service.py
│  ├─ keyword_service.py
│  ├─ language_service.py
│  ├─ llm_service.py
│  ├─ report_service.py
│  ├─ search_service.py
│  ├─ storage_service.py
│  └─ translator_service.py
└─ data/
```

## 安裝與啟動

```bash
pip install -r requirements.txt
python -m uvicorn main:app --reload
```

啟動後可查看 Swagger：

```text
http://127.0.0.1:8000/docs
```

如果 Windows / OneDrive 環境下 `8001` 無法綁定，建議改用：

```bash
python -m uvicorn main:app --host 127.0.0.1 --port 8010
```

## 環境變數

若要切換不同模型供應商，請先準備對應 API Key：

```bash
OPENAI_API_KEY=...
GEMINI_API_KEY=...
ANTHROPIC_API_KEY=...
```

若使用本地 Ollama，預設呼叫：

```text
http://localhost:11434/api/generate
```

## API 概覽

### Document APIs

#### 1. 上傳文件

`POST /api/document/upload`

用途：
- 上傳文字檔或 PDF
- 自動判斷語言
- 存入文件資料
- 重新訓練 TF-IDF 關鍵字模型
- 關鍵字抽取會自動過濾常見英文功能詞

#### 2. 匯入網址內容

`POST /api/document/ingest-url`

用途：
- 抓取網站內容
- 轉成純文字
- 存成文件資料供後續分析

#### 3. 列出文件

`POST /api/document/list`

用途：
- 支援分頁
- 支援 `country / industry / language / source_name / keyword` 篩選

範例 request：

```json
{
  "page": 1,
  "page_size": 10,
  "country": "TW",
  "source_name": "oecd",
  "keyword": "pillar two"
}
```

#### 4. 查看單篇文件詳情

`GET /api/document/{doc_id}`

#### 5. 更新文件中繼資料

`PATCH /api/document/{doc_id}`

用途：
- 更新標題、國家、產業、來源名稱、發布日期

#### 6. 搜尋並自動匯入

`POST /api/document/search`

用途：
- 根據關鍵字與使用者補充需求搜尋資料
- 可手動傳入 `candidate_urls`
- 可設定搜尋區間
- 可自動把結果匯入系統

範例 request：

```json
{
  "keywords": ["tax reform", "withholding tax"],
  "user_prompt": "focus on APAC technology companies",
  "mode": "auto",
  "date_range": "3m",
  "max_results": 5,
  "country": "TW",
  "industry": "technology",
  "auto_ingest": true
}
```

#### 7. 重新訓練關鍵字模型

`POST /api/document/train-keywords`

#### 8. 訓練關鍵字設定檔

`POST /api/document/train-keyword-profile`

用途：
- 將使用者需求關鍵字、稅務風險標籤與模型擴展關鍵字一起存起來
- 給搜尋端或 `n8n` 後續工作流重複使用

範例 request：

```json
{
  "profile_name": "apac-tax-risk",
  "user_keywords": ["tax risk", "tax reform"],
  "risk_labels": ["penalty", "filing obligation", "compliance"],
  "user_prompt": "monitor APAC cross-border tax updates",
  "provider": "ollama",
  "model_name": "qwen3:8b"
}
```

#### 9. 列出關鍵字設定檔

`GET /api/document/keyword-profiles`

#### 10. 查看單一文件關鍵字

`GET /api/document/keywords/{doc_id}`

### Analysis APIs

#### 1. 執行分析

`POST /api/analysis/run`

範例 request：

```json
{
  "doc_id": "your-doc-id",
  "mode": "translate_first",
  "target_language": "zh",
  "use_llm": true,
  "provider": "ollama",
  "model_name": "qwen3:8b",
  "user_prompt": "highlight filing risk and effective date"
}
```

回傳重點：
- `risk_level`
- `risk_tags`
- `summary`
- `translated_summary`
- `bilingual_summary`
- `evidence`

#### 2. 翻譯預覽

`GET /api/analysis/translation-preview/{doc_id}?target_language=zh`

#### 3. 比較 rule-based 與 LLM

`POST /api/analysis/evaluate`

用途：
- 建立簡化版 evaluation framework
- 快速比較 baseline 規則摘要與 LLM 摘要差異
- 觀察 overlap score 與風險等級是否一致

範例 request：

```json
{
  "doc_id": "your-doc-id",
  "target_language": "zh",
  "provider": "ollama",
  "model_name": "qwen3:8b",
  "compare_mode": "rule_vs_llm"
}
```

#### 4. 生成報告

`POST /api/analysis/report`

用途：
- 產出 Obsidian 格式 Markdown
- 或輸出可供簡報生成流程使用的 slide outline

範例 request：

```json
{
  "doc_id": "your-doc-id",
  "output_format": "obsidian",
  "provider": "ollama",
  "model_name": "qwen3:8b",
  "target_language": "zh",
  "user_prompt": "prepare a management-ready risk summary"
}
```

## 與 n8n 整合建議

目前最適合的 `n8n` 自動化流程大致如下：

1. `Cron` 定時觸發
2. 讀取既有 keyword profile
3. 呼叫 `POST /api/document/search`
4. 取得新資料並自動匯入
5. 對新文件呼叫 `POST /api/analysis/run`
6. 視需要呼叫 `POST /api/analysis/evaluate` 做品質比較
7. 對高風險文件呼叫 `POST /api/analysis/report`
8. 寫入：
   - Obsidian
   - Google Sheets
   - Notion
   - Email / Slack / LINE / Teams

### n8n Workflow 範本

repo 內已附上一份可匯入的 `n8n` workflow：

```text
n8n_tax_monitor_workflow.json
n8n_tax_monitor_obsidian_workflow.json
n8n_tax_monitor_alert_workflow.json
n8n_tax_monitor_email_alert_workflow.json
n8n_tax_monitor_gmail_alert_workflow.json
```

這份 workflow 目前包含：

1. `Schedule Trigger`
2. `Prepare Search Payload`
3. `POST /api/document/search`
4. 擷取 `ingested_doc_id`
5. `POST /api/analysis/run`
6. 判斷 `risk_level == High`
7. `POST /api/analysis/report`
8. 整理輸出內容供後續寫入 Obsidian / 通知節點

另外兩份變體：

- `n8n_tax_monitor_obsidian_workflow.json`
  - 專門走 `search -> report(obsidian) -> prepare markdown file`
  - 適合接 Obsidian vault、同步資料夾或本機 markdown 寫出流程

- `n8n_tax_monitor_alert_workflow.json`
  - 專門走 `search -> analysis -> high-risk filter -> report(slides) -> prepare alert message`
  - 適合接 Slack、Teams、Email、LINE Notify 類通知節點

- `n8n_tax_monitor_email_alert_workflow.json`
  - 專門走 `search -> analysis -> high-risk filter -> report(slides) -> prepare email -> send email`
  - 適合直接做高風險稅務更新 email demo

- `n8n_tax_monitor_gmail_alert_workflow.json`
  - 專門走 `search -> analysis -> high-risk filter -> report(slides) -> prepare Gmail message -> send Gmail SMTP`
  - 適合用 Gmail App Password 快速做可寄出的 demo

### 匯入後要先改的地方

1. repo 內附的 workflow 預設已改成 `http://127.0.0.1:8010`，如果你的 FastAPI 位址不同，再自行替換
2. 在 `Prepare Search Payload` 裡修改：
   - `keywords`
   - `date_range`
   - `country`
   - `industry`
   - `user_prompt`
3. 在 `Analyze Document` 與 `Generate Report` 裡修改：
   - `provider`
   - `model_name`
   - `target_language`
4. 在 `Prepare Output` 後面接你要的目的地節點

如果你匯入的是變體 workflow，最後一個節點名稱會不同：

- Obsidian 版：`Prepare Markdown File`
- Alert 版：`Prepare Alert Message`
- Email Alert 版：`Prepare Email Message`、`Send Email`
- Gmail Alert 版：`Prepare Gmail Message`、`Send Gmail SMTP`

如果你匯入的是 email 版 workflow，還要另外設定：

1. `Prepare Search Payload` 裡的 `alert_email_to`
2. `Send Email` 節點裡的寄件者 email
3. `Send Email` 節點對應的 SMTP / email credential

如果你匯入的是 Gmail 版 workflow，建議這樣設：

1. `Prepare Search Payload` 裡修改：
   - `alert_email_to`
   - `gmail_sender`
2. 在 n8n 建立 `SMTP` credential：
   - Host: `smtp.gmail.com`
   - Port: `465` 或 `587`
   - User: 你的 Gmail
   - Password: Gmail App Password
3. 把 `Send Gmail SMTP` 節點綁到你剛建立的 Gmail SMTP credential
4. Gmail 帳號需先開啟兩步驟驗證，才能建立 App Password

### 建議後續可接的節點

- Obsidian：
  - 寫入本機資料夾
  - 或先寫成 Markdown 檔再由同步工具帶入 vault
- Slack / Teams：
  - 只通知 `risk_level = High`
- Google Sheets / Notion：
  - 紀錄 `doc_id`、標題、風險等級、摘要、來源網址
- Email：
  - 寄送高風險稅務更新摘要

### 推薦使用方式

- 想快速做知識庫 demo：
  - 匯入 `n8n_tax_monitor_obsidian_workflow.json`
- 想快速做高風險預警 demo：
  - 匯入 `n8n_tax_monitor_alert_workflow.json`
- 想快速做自動 email 通知 demo：
  - 匯入 `n8n_tax_monitor_email_alert_workflow.json`
- 想快速做 Gmail 可寄出版 demo：
  - 匯入 `n8n_tax_monitor_gmail_alert_workflow.json`
- 想自己再擴充完整流程：
  - 從 `n8n_tax_monitor_workflow.json` 開始改

### Gmail Alert 五分鐘設定流程

如果你想最快做出「抓到高風險稅務更新就寄 Gmail」的 demo，可以照這個順序：

#### Step 1. 啟動 FastAPI 後端

```bash
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8001
```

確認 Swagger 可開：

```text
http://127.0.0.1:8010/docs
```

#### Step 2. 確認 Ollama 與 qwen3:8b 可用

```bash
ollama list
ollama run qwen3:8b
```

如果 `qwen3:8b` 還沒下載：

```bash
ollama pull qwen3:8b
```

#### Step 3. 準備 Gmail App Password

1. 登入你的 Gmail / Google 帳號
2. 開啟兩步驟驗證
3. 到 Google 帳號安全性頁面建立 `App Password`
4. 記下 16 碼 App Password

#### Step 4. 在 n8n 建立 Gmail SMTP credential

建議設定如下：

- Host: `smtp.gmail.com`
- Port: `465`
- Secure: `true`
- User: 你的 Gmail
- Password: 你的 Gmail App Password

如果你用 `587`：

- Port: `587`
- Secure: `false`

#### Step 5. 匯入 Gmail workflow

在 n8n 匯入：

```text
n8n_tax_monitor_gmail_alert_workflow.json
```

#### Step 6. 修改 workflow 內的必要欄位

先改 `Prepare Search Payload`：

- `keywords`
- `date_range`
- `country`
- `industry`
- `alert_email_to`
- `gmail_sender`

再改所有 HTTP Request node 的 base URL：

```text
http://127.0.0.1:8010
```

如果你的 FastAPI 不在本機或不是 `8001`，這裡一起改掉。

#### Step 7. 綁定 Gmail SMTP credential

打開 `Send Gmail SMTP` 節點，綁到你剛剛建立的 Gmail SMTP credential。

#### Step 8. 手動執行一次 workflow

建議先不要等排程，直接在 n8n 手動執行一次：

1. Search
2. Ingest
3. Analyze
4. If High Risk
5. Generate Alert Report
6. Prepare Gmail Message
7. Send Gmail SMTP

#### Step 9. 驗證寄出結果

你應該會看到：

- FastAPI 有收到 `/api/document/search`
- FastAPI 有收到 `/api/analysis/run`
- 高風險文件會再打 `/api/analysis/report`
- 收件匣收到 `[Tax Monitor] High Risk - ...` 的郵件

#### Step 10. Demo 建議

現場 demo 時，建議先用這種比較容易判成高風險的關鍵字：

- `penalty`
- `audit`
- `filing obligation`
- `draft tax reform`
- `effective date`

這樣比較容易讓流程走到寄信節點。

## 目前已知限制

1. 目前搜尋來源先以 RSS 型來源為主，後續可再擴充更多來源
2. 目前 evaluation 為簡化版比較框架，尚未接入人工標註資料或正式 benchmark
3. 風險等級判斷仍以規則式與關鍵字為主，尚未完成專用分類模型
4. 關鍵字擴展目前屬於輔助式訓練，不是完整監督式訓練管線
5. 某些執行環境下 SQLite 檔案可能是唯讀，因此 `storage_service` 目前有 fallback 機制，必要時會自動退到 shared in-memory DB，讓 API 仍可運作
6. 若專案目錄下的上傳資料夾不可寫入，`document_service` 會自動退到系統暫存目錄 `tax_monitor_uploads`

## 開發備註

- 後續每次功能調整，請同步更新本 `README.md`
- 若要正式接上 `n8n` 與多供應商 API，建議下一步補上：
  - 統一設定檔
  - 正式的資料來源 connector（四大、OECD、稅局、RSS、網站 sitemap）
  - 去重機制
  - 任務狀態追蹤
  - 更完整的 provider error handling
  - 人工標註評估資料與更完整的 LLM evaluation framework
  - 正式可寫入的資料庫路徑
