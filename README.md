# 跨國法令與稅務風險監測系統（Tax Monitor API）

這個專案是一個以 FastAPI 為核心的稅務研究與風險監測原型，目標是把：

- 網路資料搜尋
- 文件匯入與整理
- 關鍵字訓練
- 風險分析
- 報告輸出

串成一條可直接執行的流程，之後再接到 `n8n` 做全自動化。

目前專案已經可以做到：

1. 從 UI 或 API 輸入搜尋關鍵字
2. 自動搜尋網路上的相關資料
3. 自動匯入文件到本地資料庫
4. 重新訓練關鍵字模型
5. 對文件做風險分析
6. 直接輸出 `.pptx` 報告

---

## 1. 目前專案的實際流程

### A. 文件層

- `POST /api/document/upload`
  - 上傳本機 `.txt` / `.pdf`
- `POST /api/document/ingest-url`
  - 匯入單一網頁或 PDF URL
- `POST /api/document/list`
  - 列出已匯入文件
- `GET /api/document/{doc_id}`
  - 看單篇文件內容
- `PATCH /api/document/{doc_id}`
  - 更新文件 metadata

### B. 搜尋層

- `POST /api/document/search`
  - 單純搜尋
  - 可選擇自動匯入
  - 可用手動 URL 清單

### C. 分析層

- `POST /api/analysis/run`
  - 對單篇文件做風險分析
- `POST /api/analysis/report`
  - 輸出 `obsidian` / `slides` / `pptx`
- `POST /api/analysis/evaluate`
  - 比較 rule-based 與 LLM 結果

### D. 整合流程層

- `POST /api/pipeline/search-train`
  - 搜尋
  - 自動匯入
  - 重訓關鍵字模型
  - 可選擇同步產出 PPTX
- `POST /api/pipeline/run`
  - 搜尋
  - 匯入
  - 分析
  - 輸出報告
  - 是目前最接近「一次 execute 完全部流程」的 API

### E. 使用者介面

- `GET /ui`
  - Workbench 前端介面
  - 適合直接輸入關鍵字、設定資料期間、筆數上限、搜尋來源、AI 擴寫、PPTX 產出

---

## 2. 目前檔案結構

```text
tax_monitor/
├─ main.py
├─ README.md
├─ requirements.txt
├─ desktop_app/
│  ├─ app.py
│  ├─ input_panel.py
│  ├─ results_panel.py
│  └─ worker.py
├─ examples/
│  ├─ sample_tax_update.html
│  └─ run_pipeline_smoke_test.py
├─ models/
│  └─ schemas.py
├─ routers/
│  ├─ analysis.py
│  ├─ document.py
│  └─ pipeline.py
├─ services/
│  ├─ analysis_service.py
│  ├─ document_parser_service.py
│  ├─ document_service.py
│  ├─ keyword_service.py
│  ├─ language_service.py
│  ├─ llm_service.py
│  ├─ pipeline_service.py
│  ├─ report_service.py
│  ├─ search_service.py
│  ├─ storage_service.py
│  └─ translator_service.py
├─ ui/
│  ├─ index.html
│  ├─ app.js
│  └─ styles.css
└─ data/
```

---

## 3. 核心模組說明

### `services/search_service.py`

負責搜尋資料來源，目前已經不是只用單一 Google News。

目前支援：

- Google News RSS
- Google News 全球 locale 聚合
- Google News 歷史事件補搜 `google_news_archive`
- Bing News RSS
- Bing 一般網頁搜尋
- Bing PDF 搜尋
- DuckDuckGo 一般網頁搜尋
- DuckDuckGo PDF 搜尋
- 指定 `site:` 官方 / 顧問 / 稅務站點的定向搜尋
- 已知公司官方種子來源 `official_seed`
- 跨國稅務制度參考來源 `reference_seed`

另外已加入 AI 輔助：

- 使用 Ollama 產生語意相近的 query variants
- 嘗試補出法規 / 生效日 / 申報義務 / draft / penalty 等相關查詢
- 補強公司別名與 group / holding / subsidiary 類詞
- 補強中文集團關係詞，例如控股 / 集團 / 子公司 / 母公司 / 關係企業
- 優先補搜公司年報、財報、公開資訊、子公司、關係企業、轉投資與關係人交易
- 若系統已知該公司的官方 IR / 財報 / 公司治理入口，會先放入 `official_seed`，避免搜尋引擎沒有收錄或短期新聞太少時完全抓不到資料
- 若系統只知道公司官方網域，會補入 `official_domain_seed` 作為保底，避免 DuckDuckGo / Bing 短暫無結果時整批搜尋歸零
- 若補充需求包含跨國稅務、全球最低稅負、Pillar Two、CFC、常設機構、扣繳稅或關稅，會額外補入 `reference_seed`，例如 OECD、PwC、Deloitte 類制度說明
- 若輸入包含 `查稅`、`稅務調查`、`補稅`、`裁罰`、`tax audit`、`tax notice`、`tax row` 等事件型風險詞，會先補搜新聞事件脈絡
- 若嚴格期間內沒有事件新聞，會用 `google_news_archive` 補少量歷史事件結果，避免重大歷史風險完全消失
- 對官方稅務站、四大與顧問站結果做加權重排
- 對 PDF、法規型、官方型、公開資訊型結果做優先排序
- 讓搜尋更接近「AI 自動研究助手」，而不是只做原字面比對

### `services/document_service.py`

負責：

- 上傳文件
- 網址內容抓取
- PDF 文字抽取
- 自動判斷語言
- 寫入 SQLite

現在如果搜尋結果是 PDF 網址，匯入流程也會直接下載 PDF 並抽文字。

### `services/keyword_service.py`

負責：

- 從資料庫所有文件重新訓練 TF-IDF 模型
- 對單篇文件抽關鍵字
- 建立使用者關鍵字 profile

### `services/analysis_service.py`

負責：

- `translate_first`
- `analyze_first`
- 風險等級判斷
- 風險標籤抽取
- 摘要與證據句整理

### `services/report_service.py`

負責：

- Obsidian 格式輸出
- 投影片大綱輸出
- 真正建立 `.pptx`

### `services/pipeline_service.py`

目前有兩種主流程：

1. `run_pipeline()`
   - 完整流程
2. `search_ingest_and_train()`
   - 先大量養資料、重訓關鍵字、必要時同步出 PPTX

---

## 4. 安裝方式

### 建議環境

- Windows 10/11
- Python 3.10+
- Ollama

### 安裝依賴

在專案根目錄執行：

```powershell
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

目前 `requirements.txt` 包含：

- `fastapi`
- `uvicorn`
- `python-multipart`
- `requests`
- `beautifulsoup4`
- `pypdf`
- `scikit-learn`
- `pandas`
- `python-pptx`

`python-pptx` 已經列在依賴中，所以只要完整安裝 `requirements.txt`，PPTX 輸出就能用。

---

## 5. 啟動方式

### 最穩定的啟動方法

```powershell
.\\.venv\\Scripts\\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8010
```

啟動後可用：

- Swagger: `http://127.0.0.1:8010/docs`
- Health check: `http://127.0.0.1:8010/`
- UI: `http://127.0.0.1:8010/ui`

### 為什麼 README 不預設 `--reload`

因為你現在的環境是：

- Windows
- OneDrive 路徑

這種組合下，`uvicorn --reload` 容易遇到：

- `WinError 10013`
- socket 權限問題
- 監看程序衝突

所以目前文件預設先用穩定版啟動方式，不先加 `--reload`。

如果你本機很穩，再自己改成：

```powershell
.\\.venv\\Scripts\\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8010
```

---

## 6. Ollama 設定

### 安裝後確認 Ollama 可用

```powershell
ollama list
```

### 若尚未下載 Qwen

```powershell
ollama pull qwen3:8b
```

### 測試模型

```powershell
ollama run qwen3:8b
```

### 專案目前預設模型

- provider: `ollama`
- model_name: `qwen3:8b`

Ollama 預設呼叫端點：

```text
http://localhost:11434/api/generate
```

---

## 7. Swagger 測試順序

如果你想先不碰 n8n，最簡單的測法是照這個順序。

### 方案 A：分段測

#### Step 1. 先上傳測試文件

`POST /api/document/upload`

可直接上傳 repo 內建的：

```text
demo_tax_update.txt
```

#### Step 2. 分析單篇文件

`POST /api/analysis/run`

範例：

```json
{
  "doc_id": "上一步拿到的 doc_id",
  "mode": "translate_first",
  "target_language": "zh",
  "use_llm": true,
  "provider": "ollama",
  "model_name": "qwen3:8b",
  "user_prompt": "highlight filing risk and effective date"
}
```

#### Step 3. 產出 PPTX

`POST /api/analysis/report`

範例：

```json
{
  "doc_id": "上一步的 doc_id",
  "output_format": "pptx",
  "provider": "ollama",
  "model_name": "qwen3:8b",
  "target_language": "zh",
  "user_prompt": "prepare a management-ready risk summary"
}
```

如果成功，回傳會有：

- `file_path`

通常會出現在：

```text
data/reports/
```

---

### 方案 B：直接跑完整管線

#### `POST /api/pipeline/run`

這是目前最完整的一次跑完版。

它會做：

1. 搜尋
2. 匯入
3. 分析
4. 報告輸出

範例：

```json
{
  "keywords": ["penalty", "tax reform", "filing obligation"],
  "user_prompt": "focus on high-risk tax updates for management review",
  "mode": "auto",
  "date_range": "1m",
  "max_results": 10,
  "country": "TW",
  "industry": "technology",
  "source_name": "all",
  "use_ai_query_expansion": true,
  "target_language": "zh",
  "analysis_mode": "translate_first",
  "provider": "ollama",
  "model_name": "qwen3:8b",
  "report_format": "pptx",
  "max_documents_to_process": 3,
  "high_risk_only": false
}
```

如果你要的是「從搜尋一路到最後生成 PPTX」，這是最接近需求的單一 API。

---

### 方案 C：先養資料池再重訓關鍵字

#### `POST /api/pipeline/search-train`

這條流程比較適合：

- 先大量搜尋資料
- 先匯入文件
- 先重訓關鍵字
- 視需要順便產生部分 PPTX

範例：

```json
{
  "keywords": ["penalty", "tax reform", "filing obligation"],
  "user_prompt": "focus on APAC technology companies",
  "mode": "auto",
  "date_range": "3m",
  "max_results": 30,
  "country": null,
  "industry": "technology",
  "source_name": "all",
  "candidate_urls": [],
  "auto_ingest": true,
  "use_ai_query_expansion": true,
  "generate_pptx": true,
  "target_language": "zh",
  "provider": "ollama",
  "model_name": "qwen3:8b",
  "max_documents_to_process": 3,
  "high_risk_only": false
}
```

---

## 8. UI 使用方式

打開：

```text
http://127.0.0.1:8010/ui
```

目前 UI 可以直接做：

1. 輸入搜尋關鍵字
2. 補充研究需求
3. 設定資料期間
4. 調整搜尋筆數上限
5. 切換自動 / 手動模式
6. 切換搜尋來源
7. 選擇是否不限地區
8. 選擇是否啟用 Ollama 智慧擴寫
9. 選擇是否同步產出 PPTX
10. 顯示：
   - 搜尋結果數
   - 成功匯入數
   - 訓練文件數
   - 詞彙量
   - 已產出 PPTX 數
   - 正規化後實際送出的關鍵字
   - 搜尋結果的網域、類型、分數與排序理由
   - 每篇文件的抽取關鍵字
   - 每篇文件的風險等級與風險標籤
   - PPTX 檔案路徑

---

## 9. 搜尋來源與 AI 自動研究助手

### 搜尋來源選項

UI / API 的 `source_name` 目前有四種主要模式：

#### `google_news_rss`

- 標準新聞搜尋

#### `google_news_rss_global`

- Google News 多 locale 聚合
- 適合跨區新聞觀察

#### `bing_web`

- Bing 一般網頁與 PDF 搜尋
- 適合公司年報、財報、公開資訊、投資人關係頁、子公司或關係企業資料
- 如果 DuckDuckGo 對中文公司名回傳太少，可以單獨切這個模式測

#### `all`

- 全網聚合搜尋
- 會嘗試整合：
  - Google News RSS
  - Bing News RSS
  - Bing 一般網頁搜尋
  - Bing PDF 搜尋
  - DuckDuckGo 網頁搜尋
  - DuckDuckGo PDF 搜尋
  - `site:` 官方 / 顧問 / 稅務網站定向搜尋
  - 稅務事件型查詢的 Google News 歷史脈絡補搜

### 不限地區

UI 的「不限地區」現在只會：

- 清空 `country`
- 讓搜尋不再卡在單一國家欄位

不會再偷偷把來源強制改回 Google News，這點已修正。

### AI 自動研究助手強化版

目前已加強的邏輯：

1. 使用 Ollama 根據關鍵字與補充需求產生語意擴寫查詢
2. 補出：
   - 稅務改革
   - 申報義務
   - 生效日
   - 草案
   - penalty / compliance / regulation 類詞
3. 補強公司主體詞：
   - group
   - holding
   - subsidiary
   - corporation
4. 對公司年報、財報、公開資訊、子公司、關係企業、轉投資與關係人交易先做高命中率查詢
5. 對官方 / 顧問 / 稅務站點做定向搜尋
6. 對已知公司先補入官方 IR、財報、年報、公司治理與關係人交易文件作為 `official_seed`
7. 對已知公司官方網域補入 `official_domain_seed`
8. 對跨國稅務研究補入 OECD、四大或專業稅務說明作為 `reference_seed`
9. 對事件型稅務風險補出查詢詞，例如 `查稅`、`稅務調查`、`補稅`、`虛假計稅`、`tax audit`、`tax notice`、`tariff impact`
10. 同時納入一般網頁、PDF、新聞與歷史事件脈絡
11. 針對官方站、公開資訊站、PDF、稅務關鍵語境、事件型新聞與公司別名結果做二次重排
12. 把每筆搜尋結果的排序理由回傳給前端，方便人工判斷這筆資料為什麼被拉上來

### 公司與子公司稅務風險搜尋模式

如果輸入像：

```text
任一公司及其子公司稅務風險
```

系統現在不會只拿原句硬搜，而會自動拆成公司研究任務：

- 公司主體：
  - 原始公司名稱
  - 去掉「稅務風險、子公司、集團、母公司」後的公司名稱
  - 常見法人後綴，例如 `公司`、`股份有限公司`、`集團`
  - 英文公司後綴，例如 `Inc`、`Corporation`、`Group`、`Holdings`
  - 若是已知公司，會額外補常見別名，例如 `ASUS` / `ASUSTeK`
- 稅務 / 風險主題：
  - `tax risk`
  - `tax governance`
  - `income tax`
  - `effective tax rate`
  - `transfer pricing`
  - `related party transactions`
  - `cross-border tax`
  - `international tax`
  - `global minimum tax`
  - `Pillar Two`
  - `BEPS`
  - `permanent establishment`
  - `withholding tax`
  - `customs duty`
  - `tariff`
  - `VAT / GST`
  - `CFC`
  - `subsidiaries`
  - `group structure`
  - `consolidated financial statements`
  - `tax litigation`
  - `annual report`
  - `sustainability report`
  - `年報`
  - `財報`
  - `稅務治理`
  - `所得稅`
  - `移轉訂價`
  - `關係人交易`
  - `跨國稅務`
  - `國際租稅`
  - `全球最低稅負`
  - `支柱二`
  - `常設機構`
  - `扣繳稅`
  - `關稅`
  - `海關估價`
  - `受控外國公司`
  - `子公司`
  - `關係企業`
  - `集團架構`
  - `合併財務報表`
  - `轉投資`
  - `查稅`
  - `稅務調查`
  - `稅務稽查`
  - `補稅`
  - `稅務裁罰`
  - `tax audit`
  - `tax investigation`
  - `tax notice`
  - `tax row`
  - `customs investigation`
  - `tariff impact`

同時會補搜：

- 公司官網與 ESG / IR 文件
- TWSE / MOPS 公開資訊
- 年報、財報、永續報告 PDF
- 子公司、關係企業、轉投資與關係人交易資料
- 顧問 / 稅務 / 官方站點
- 已知公司的官方種子資料，例如華碩、台積電、鴻海 / Foxconn、Toyota 的 IR、年報、財報、稅務政策、關係人交易或永續資訊
- 已知公司官方網域保底資料，例如 `asus.com`、`tsmc.com`、`honhai.com`、`foxconn.com`、`global.toyota`
- 跨國稅務制度資料，例如 OECD BEPS / Pillar Two、PwC CFC / 全球最低稅負、Deloitte 跨國稅務治理
- Google News / Bing News / Bing Web / DuckDuckGo 一般網頁與 PDF
- 稅務事件型新聞，例如查稅、稅務調查、補稅、裁罰、關稅衝擊、反傾銷稅與海關稽查

事件型搜尋有一個特別規則：如果你選 `3m` 或 `1y`，新聞搜尋會先尊重這個期間；但很多重大稅務事件不是最近才發生，系統會在結果不足時補少量 `google_news_archive` 歷史事件線索。這些結果會顯示為歷史脈絡，不代表它發生在你選的期間內，而是提醒分析時不可忽略的既有風險。

`all` 模式目前會優先查一般網頁、PDF 與官方定向搜尋，再用少量新聞來源補充。這樣比一開始先打大量 Google News locale 更快，也比較適合公司年報、稅務政策、子公司與關係人交易研究。

這是為了解決一個常見問題：網路資料不一定會直接使用「稅務風險」這四個字，也不一定會把母公司和子公司寫在同一篇新聞裡；真正有用的線索常出現在「年報、所得稅、有效稅率、關係人交易、移轉訂價、子公司清單、轉投資、合併財務報表、永續報告」等段落裡。

建議公司研究查詢：

```json
{
  "keywords": ["華碩及其子公司跨國稅務風險"],
  "user_prompt": "包含華碩旗下所有子公司、跨國稅務風險、年報、財報、所得稅、移轉訂價、關係人交易、關稅、全球最低稅負、Pillar Two、常設機構、扣繳稅、供應鏈與營運據點",
  "date_range": "1y",
  "max_results": 50,
  "source_name": "all",
  "use_ai_query_expansion": true,
  "report_format": "pptx"
}
```

目前已用這組條件驗證過完整流程，可從搜尋一路跑到 PPTX。測試結果包含：

- 華碩官方 2025 Q2 合併財報
- 華碩官方 2024 年報
- 華碩 IR 財報入口
- 華碩關係人交易管理辦法
- PwC CFC / 全球最低稅負制度說明

上述文件皆可被匯入、分析，並輸出到 `data/reports/`。

如果某家公司用中文名稱搜尋太少，可以把常見英文名稱也放進關鍵字或補充需求，例如：

```json
{
  "keywords": ["台積電 TSMC 子公司 稅務風險"],
  "user_prompt": "Taiwan Semiconductor Manufacturing annual report subsidiaries income tax transfer pricing related party transactions",
  "date_range": "3m",
  "max_results": 50,
  "source_name": "all",
  "use_ai_query_expansion": true,
  "report_format": "pptx"
}
```

如果你要查的是「公司是否曾被查稅、裁罰、補稅、稅務調查」，建議補充需求直接寫事件詞，系統會自動擴成多組公司別名與事件查詢：

```json
{
  "keywords": ["鴻海查稅風險"],
  "user_prompt": "包含富士康、鴻海、Hon Hai、Foxconn，搜尋稅務及用地調查、查稅結果、虛假計稅、補稅、稅務裁罰、子公司影響",
  "date_range": "1y",
  "max_results": 30,
  "source_name": "all",
  "use_ai_query_expansion": true,
  "report_format": "pptx"
}
```

這類查詢若近期沒有新新聞，仍可能補出歷史事件脈絡，例如 `google_news_archive` 來源的富士康查稅結果、補稅傳聞澄清、稅務調查報導等。

所以現在的搜尋已經比一開始更接近：

- AI 幫你理解主題
- AI 幫你放大搜索面，包含母公司、子公司、關係企業與公開資訊
- 再把結果餵進分析與報告流程

---

## 10. n8n 目前怎麼接

repo 內已有：

```text
n8n_tax_monitor_workflow.json
n8n_tax_monitor_obsidian_workflow.json
n8n_tax_monitor_alert_workflow.json
n8n_tax_monitor_gmail_alert_workflow.json
```

但如果你現在要先確認 FastAPI 本身能跑，建議先完成：

1. `document/upload`
2. `analysis/run`
3. `analysis/report`
4. `pipeline/run`

等這四步都穩，再回頭接 n8n。

---

## 11. 我建議你現在的實際操作順序

### 第一階段：確認本機安裝正常

1. `python -m pip install -r requirements.txt`
2. `.\\.venv\\Scripts\\Activate.ps1`
3. `ollama pull qwen3:8b`
4. `.\\.venv\\Scripts\\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8010`
5. 打開 `/docs`
6. 打開 `/ui`

### 第二階段：確認分析到 PPTX 正常

1. 上傳 `demo_tax_update.txt`
2. 執行 `/api/analysis/run`
3. 執行 `/api/analysis/report`
4. 確認 `data/reports/*.pptx`

### 第三階段：確認搜尋管線正常

1. 在 `/ui` 輸入關鍵字
2. `source_name` 選 `all`
3. 勾選 `用 Ollama 智慧擴寫搜尋意圖`
4. 設較大的 `max_results`
5. 看是否有：
   - 匯入文件
   - 關鍵字
   - 風險等級
   - PPTX 路徑

### 第四階段：最後再接 n8n

---

## 12. 一鍵驗證範例

如果你想確認「搜尋結果 → 匯入文件 → 分析 → 產出 PPTX」整條流程是否正常，可以直接跑 repo 內建的本機 smoke test。

```powershell
.\\.venv\\Scripts\\python.exe -B examples\\run_pipeline_smoke_test.py
```

這支腳本會自動：

1. 啟動一個本機暫時 HTTP server
2. 把 `examples/sample_tax_update.html` 當成搜尋結果網址
3. 呼叫 `PipelineService.run_pipeline()`
4. 匯入文件
5. 分析稅務風險
6. 產生 `.pptx`

成功時會看到類似：

```text
searched_result_count: 1
ingested_result_count: 1
processed_count: 1
report_file_path: ...\\data\\reports\\Sample 2026 Cross-Border Tax Filing Update.pptx
```

本機已驗證可產生：

```text
data/reports/Sample 2026 Cross-Border Tax Filing Update.pptx
```

這個 smoke test 不依賴外部網路，所以很適合用來確認核心程式沒有壞。

---

## 13. 已知限制

目前這版已經能跑，但還不是完整企業級爬研平台。

目前限制包括：

1. 外部搜尋結果仍受搜尋引擎與網站可見度影響
2. DuckDuckGo HTML 搜尋有時會回 403，現在程式會跳過失敗查詢並繼續處理其他來源
3. Google News RSS 有時會回傳 Google News 中介頁，標題可能顯示為 `Google News`
4. 還不是完整 agent 式自主瀏覽器
5. 尚未做多步深度網頁追蹤與 sitemap crawler
6. 尚未接正式向量資料庫
7. 尚未做多輪研究記憶與任務編排
8. 目前 SQLite 適合 PoC，不是最終正式版資料庫

---

## 14. 這版最重要的結論

是的，現在這個專案已經可以：

1. 按 README 安裝
2. 啟動 FastAPI
3. 從 UI 或 Swagger 執行流程
4. 從搜尋一路走到分析與 PPTX 產出

而且現在搜尋端也已經不再只卡在單一 Google News 思路，而是往「AI 自動研究助手」方向補強了。

接下來最值得做的下一步會是：

- 正式加入多站點 crawler
- 加入研究任務記憶
- 把搜尋結果做更強的相關性重排
- 接回 `n8n` 做定時自動研究與通知

---

## 15. 依最新反饋新增的改良方向

### Tkinter 桌面前端

目前已新增 `desktop_app/`，作為不依賴瀏覽器的桌面版操作介面。

啟動方式：

```powershell
.\\.venv\\Scripts\\python.exe -m desktop_app
```

桌面版目前分成多個模組：

- `desktop_app/app.py`
  - 主視窗
- `desktop_app/input_panel.py`
  - 搜尋與 pipeline 參數輸入
- `desktop_app/results_panel.py`
  - 摘要、搜尋結果、匯入文件、PPTX 結果顯示
- `desktop_app/worker.py`
  - 背景執行 pipeline，避免視窗卡住

桌面版會直接呼叫 `PipelineService`，所以不需要先啟動 FastAPI。

### MinerU 文件解析

目前已新增 `services/document_parser_service.py`。

文件解析流程現在會：

1. 優先嘗試呼叫本機 `mineru` CLI
2. 若 MinerU 不存在或解析失敗，PDF 會 fallback 到 `pypdf`
3. 一般文字檔會以 UTF-8 fallback 讀取

MinerU 安裝可參考官方 repo：

```text
https://github.com/opendatalab/mineru
```

本專案採取「可選安裝」方式，原因是 MinerU 依賴較重；未安裝時系統仍可使用既有 fallback。

### Web / PDF 搜尋模式

現在 `source_name` 建議依需求選：

```text
duckduckgo
bing_web
all
```

差異如下：

- `duckduckgo`
  - DuckDuckGo 一般網頁搜尋
  - DuckDuckGo PDF 搜尋
  - 官方 / 顧問 / 稅務網站定向 query
- `bing_web`
  - Bing 一般網頁搜尋
  - Bing PDF 搜尋
  - 對公司年報、財報、IR、公開資訊頁有時比 DuckDuckGo 更容易命中
- `all`
  - Google News / Bing News / Bing Web / DuckDuckGo 聚合
  - 公司與子公司稅務風險研究建議優先用這個

Tkinter 桌面版目前預設就是 `all`。

### PPTX 格式改良

目前 PPTX 已依照你提供的 Colab 簡報模板邏輯，改成本地 `python-pptx` 版本，不需要再進 Google Colab 才能輸出。

已整合的版型邏輯：

- 10 x 5.625 inch 的 16:9 投影片比例
- 封面頁使用中央圓角主題色標題框
- 內容頁使用統一頂部標題列
- 頁尾包含日期、中央頁碼、右下系統名稱
- 預設主題色為深藍 `#2C3E6B`
- 中文字型預設使用 `Taipei Sans TC Beta`
- 英文字型預設使用 `Times New Roman`
- 每個分析區塊會獨立成頁
- 第一張內容頁會自動產生 `Executive Snapshot`

目前本地版沒有搬入 Colab 的互動式 `ipywidgets` 編輯器與 Gemini 圖片生成功能，因為本專案主流程是自動搜尋、匯入、分析、輸出報告；簡報內容會直接由分析結果與 Ollama / API 模型產生。

### 現在建議的完整使用流程

#### 方案 1：桌面版操作

```powershell
.\\.venv\\Scripts\\python.exe -m desktop_app
```

桌面版適合一般使用者：

1. 輸入搜尋關鍵字
2. 輸入補充研究需求
3. 設定資料期間與資料筆數上限
4. 選擇 `all`，如果要單獨測網頁來源再切 `duckduckgo` 或 `bing_web`
5. 勾選 AI 智慧擴寫
6. 勾選產生 PPTX
7. 按下執行
8. 在結果頁查看：
   - 搜尋結果
   - 成功匯入文件
   - 關鍵字訓練結果
   - 風險分析結果
   - PPTX 檔案路徑

#### 方案 2：FastAPI Swagger 一次跑完

啟動：

```powershell
.\\.venv\\Scripts\\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8010
```

打開：

```text
http://127.0.0.1:8010/docs
```

使用：

```text
POST /api/pipeline/run
```

建議測試 JSON：

```json
{
  "keywords": ["tax reform", "penalty", "filing obligation"],
  "user_prompt": "focus on high-risk tax updates, effective date, filing deadline, and management action items",
  "mode": "auto",
  "date_range": "3m",
  "max_results": 30,
  "country": null,
  "industry": "",
  "source_name": "all",
  "use_ai_query_expansion": true,
  "target_language": "zh",
  "analysis_mode": "translate_first",
  "provider": "ollama",
  "model_name": "qwen3:8b",
  "report_format": "pptx",
  "max_documents_to_process": 5,
  "high_risk_only": false
}
```

成功後看回傳的：

- `results`
- `ingested_documents`
- `analyses`
- `reports`
- `pptx_files`

產出的簡報會在：

```text
data/reports/
```

### AI 自動研究助手加強方向

目前已經加強到：

1. 用 Ollama 依照使用者需求擴寫搜尋 query
2. 用 Google News、Google News 歷史事件補搜、Bing News、Bing Web、DuckDuckGo 搜尋一般網頁與 PDF
3. 對公司年報、財報、公開資訊、子公司、關係企業、轉投資與關係人交易做優先 query
4. 用官方 / 顧問 / 稅務網站定向 query 補強來源多樣性
5. 對已知公司補入官方 IR、年報、財報、公司治理與關係人交易文件作為 `official_seed`
6. 對已知公司補入官方網域保底資料作為 `official_domain_seed`
7. 對跨國稅務補入 OECD、PwC、Deloitte 等制度型參考作為 `reference_seed`
8. 對查稅、稅務調查、補稅、裁罰、關稅衝擊等事件型風險做專門 query expansion
9. 匯入網頁或 PDF 內容
10. 若安裝 MinerU，優先用 MinerU 做文件解析
11. 對匯入文件重訓關鍵字模型
12. 對文件做稅務風險分析
13. 輸出管理層簡報格式 PPTX

下一步如果要更像真正的 AI 研究員，可以再加：

- 多層網頁追蹤與 sitemap crawler
- 搜尋結果語意相似度重排
- 來源可信度評分
- 研究任務記憶
- PPTX 圖表與資料表自動生成
