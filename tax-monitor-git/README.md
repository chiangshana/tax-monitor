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

---

## 16. 資料蒐集強化進度（2026-05 更新）

這一輪重點放在「把資料來源從一般搜尋擴大到官方資料庫＋公司原始檔」，讓 AI 研究助理在面對跨國稅務題材時不再只能仰賴 Google News。

### 16.1 新增的官方／監管／公開資訊來源

`services/search_service.py` 新增以下資料抓取器：

| 抓取器 | 來源 | 用途 |
|--------|------|------|
| `_search_sec_edgar` | SEC EDGAR Full-Text Search JSON API | 精準命中 10-K / 20-F / 10-Q / 8-K / 6-K / 40-F 等揭露文件，內含所得稅、遞延所得稅、子公司、關係人交易與不確定稅務部位 |
| `_search_eur_lex` | EUR-Lex 官方法規檢索 | 補入歐盟法規、指令、判例與跨境稅務制度文件 |
| `_search_taiwan_law` | 全國法規資料庫（law.moj.gov.tw） | 中華民國稅法、關稅、法規條文（所得稅法、加值營業稅、貨物稅、CFC 等） |
| `_search_company_sitemap` | 公司官方 `sitemap.xml` / `sitemap_index.xml` | 從已知公司網域（華碩、台積電、鴻海、Toyota…）的 sitemap 主動找出年報、永續報告、IR、稅務治理頁面 |

新來源都會：

- 排序時得到額外加權（EDGAR +1.8、EUR-Lex +1.5、Taiwan MOJ +1.5、Sitemap +1.2）
- 進入既有的去重 / 低訊號網域過濾流程
- 在前端的 `match_reasons` 顯示為對應 source

### 16.2 新增 `deep_research` 搜尋模式

新模式 `source_name = "deep_research"` 會走「先官方、後新聞」的研究路線：

1. 先放入 `official_seed` / `official_domain_seed` / `reference_seed`
2. 跑公司 sitemap probe，撈出官方文件入口
3. 呼叫 SEC EDGAR JSON API（依公司主體別名）
4. 呼叫 EUR-Lex 與 Taiwan MOJ 法規檢索
5. 用 `site:` 對官方稅務 / 顧問站做定向搜尋
6. 最後再補少量 Google News RSS 作為新聞脈絡

`source_name = "all"` 也已順便插入 sitemap 與 SEC EDGAR 補強，原本的事件型 / 多 locale 新聞流程不變。

桌面版（Tkinter）的 `Source` 下拉新增 `deep_research` 選項，預設仍保留 `all`，可手動切換。

### 16.3 HTTP 抓取層的穩定性與效能

過去每個搜尋呼叫都是 `requests.get(...)` 直接用，且無 retry、無 cache、無 UA 輪替。現在已重構為：

- `requests.Session` + `HTTPAdapter`（retry：429/5xx, backoff 0.6s, total=2）
- 連線池 16 / pool_maxsize 32，重用 TCP 連線
- 三組桌面類 User-Agent 輪替，避免單一 UA 被封
- 內建 `Accept-Encoding: gzip, deflate` 與多語 `Accept-Language`
- 加入 `_cached_request` TTL 快取（預設 600 秒、最多 256 筆，LRU 退場）
- SEC EDGAR 呼叫使用符合官方 fair-use 規範的 `User-Agent: Tax Monitor Research Bot acc.capstone.115@gmail.com`

效益：

- 同一輪 pipeline 重複跑相同 query variant 時不再重複打外部
- 多家搜尋引擎被短暫風控時整批不再炸開
- 連線複用後 `all` / `deep_research` 模式整體耗時下降

### 16.4 已擴大的官方稅務 / 監管網域清單

`OFFICIAL_TAX_DOMAINS` 與 `DISCLOSURE_DOMAINS` 補入：

- 亞太：`nta.go.jp`、`mof.go.jp`、`nts.go.kr`、`moef.go.kr`、`iras.gov.sg`、`ird.gov.hk`、`chinatax.gov.cn`、`mof.gov.cn`、`incometax.gov.in`、`gst.gov.in`、`ato.gov.au`、`ird.govt.nz`
- 台灣：`law.moj.gov.tw`、`ntbt.gov.tw`、`ntbk.gov.tw`、`ntbsa.gov.tw`、`tax.gov.tw`、`fsc.gov.tw`、`tpex.org.tw`
- 歐美：`hmrc.gov.uk`、`treasury.gov`、`bundesfinanzministerium.de`、`impots.gouv.fr`、`agenziaentrate.gov.it`、`eur-lex.europa.eu`、`taxation-customs.ec.europa.eu`、`canada.ca`
- 其他：`sars.gov.za`、`sat.gob.mx`、`rfb.gov.br`、`afip.gob.ar`
- 公開資訊：`efts.sec.gov`、`jpx.co.jp`、`release.tdnet.info`、`hkexnews.hk`、`krx.co.kr`、`sgx.com`、`asx.com.au`、`bseindia.com`、`nseindia.com`、`sse.com.cn`、`szse.cn`
- 顧問補充：`bdo.global`、`grantthornton.global`、`tax.thomsonreuters.com`、`internationaltaxreview.com`

任何來自上述網域的搜尋結果都會自動拿到 `official_bonus` / `disclosure_bonus`。

### 16.5 文件匯入：自動回收嵌入文件連結

`services/document_service.py` 在 ingest 一張 HTML 頁面時，現在會額外解析頁面內所有 `<a href="...">`，並回傳一份 `embedded_document_links`，內含：

- 直接副檔名是 `.pdf` / `.docx` / `.xlsx` / `.pptx` 的檔案
- URL 或連結文字命中年報、永續、稅、財報、投資人、子公司、關係企業、governance、investor、ESG 等關鍵詞的頁面

`models/schemas.py` 也新增 `EmbeddedDocumentLink`，並把它放入 `UploadResponse`。

效益：當搜尋結果丟回一張 IR 入口頁，使用者（或下一輪 pipeline）可以直接看到該頁列出的所有年報與永續報告下載連結，不再需要手動翻官網。

### 16.6 試用方式

```json
POST /api/pipeline/run
{
  "keywords": ["華碩 ASUS 全球稅務治理"],
  "user_prompt": "包含 ASUS、華碩電腦、子公司、關係企業、年報、永續報告、SEC、EUR-Lex、Taiwan MOJ 法規檢索",
  "date_range": "1y",
  "max_results": 30,
  "source_name": "deep_research",
  "use_ai_query_expansion": true,
  "report_format": "pptx"
}
```

預期回傳的 `results` 中會看到：

- `source = "company_sitemap"`：來自 `asus.com` sitemap 撈到的年報 / IR 頁
- `source = "sec_edgar"`：若公司有美股 ADR / 子公司在美登記揭露
- `source = "eur_lex"`：跨國稅務制度
- `source = "taiwan_law_moj"`：所得稅法、加值營業稅法等條文
- 既有 `official_seed` / `bing_web` / `duckduckgo_html` 結果

每筆結果的 `match_reasons` 會明確顯示「官方 / 顧問 / 稅務站點加權」與「年報 / 財報 / 公開資訊來源加權」，方便人工審核資料來源。

---

## 17. LLM 供應商切換（2026-05 更新）

### 17.1 桌面版直接切供應商與模型

`desktop_app/input_panel.py` 新增「LLM provider」與「LLM model」兩個下拉選單。預設仍是 Ollama + `qwen3:8b`，但現在可以直接切到：

| Provider | 預設模型 | 內建快選清單 |
|----------|----------|---------------|
| `ollama` | `qwen3:8b` | qwen3 全系列（0.6b/1.7b/4b/8b/14b/32b、coder:30b）、qwen2.5 全系列（1.5b/3b/7b/14b/32b/72b、coder 系列）、llama3.1/3.2、mistral、mixtral、deepseek-r1、phi3、gemma2 |
| `claude` | `claude-sonnet-4-6` | claude-opus-4-7、claude-sonnet-4-6、claude-haiku-4-5-20251001、claude-3-7-sonnet-latest、claude-3-5-sonnet-latest、claude-3-5-haiku-latest、claude-3-opus-latest |
| `openai` | `gpt-4o-mini` | gpt-4o、gpt-4o-mini、gpt-4.1、gpt-4.1-mini、gpt-4.1-nano、gpt-4-turbo、gpt-3.5-turbo、o1、o1-mini、o3-mini |
| `gemini` | `gemini-2.5-flash` | gemini-2.5-pro、gemini-2.5-flash、gemini-2.0-flash、gemini-2.0-flash-lite、gemini-1.5-pro、gemini-1.5-flash |

兩個下拉皆為 `ttk.Combobox`：

- 切換 provider 會自動把 model 下拉的選項換成該 provider 的快選清單，並把 model 重設為該 provider 的建議預設值
- model 下拉是 `state="normal"`，可直接輸入清單沒列出的客製模型名稱（例如新版 GGUF tag、Bedrock model id、Azure deployment name 等）

選定後的 provider / model 會同步傳進 `PipelineService.search_ingest_and_train`，因此搜尋層的 AI query expansion、文件分析、報告產出都會用同一組設定。

### 17.2 API key 即時覆寫

下方的 `API key (optional, overrides env var for this session)` 是一個遮罩輸入欄。流程：

1. 切到 `claude` / `openai` / `gemini` 任一 provider
2. 在 API key 欄貼入金鑰
3. 按 `Run research`

桌面版會在送出 payload 之前 `os.environ[env_var] = key`，所以 `services/llm_service.py` 的 `_call_claude` / `_call_openai` / `_call_gemini` 可以透過 `_require_env(...)` 拿到。金鑰只存在於目前 process 記憶體，不會寫入磁碟，視窗關閉就消失。

如果 API key 欄留空，則回退使用 shell / 系統層級的環境變數（`ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `GEMINI_API_KEY`）。供應商旁邊會顯示一行狀態提示：

- 綠色：「`OPENAI_API_KEY` detected. Ready to call openai.」
- 紅色：「`OPENAI_API_KEY` is not set. Set it in your shell before launching to call openai.」
- 灰色：「Local provider (Ollama). Make sure `ollama serve` is running.」

### 17.3 對應的 Provider 路由

`services/llm_service.py` 已內建四個供應商呼叫器，現在桌面版只是把選擇權暴露給使用者：

- `_call_ollama` → `http://localhost:11434/api/generate`
- `_call_openai` → `https://api.openai.com/v1/chat/completions`
- `_call_gemini` → `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`
- `_call_claude` → `https://api.anthropic.com/v1/messages`（`anthropic-version: 2023-06-01`）

所以從桌面版選 `claude` + `claude-opus-4-7`，AI query expansion、`AnalysisService` 的 LLM 摘要、`ReportService` 的簡報內容生成都會走 Claude。

### 17.4 順帶優化的效能項目

切供應商有時會搭到付費 API，因此這一輪也順手把 pipeline 跑下來最浪費的地方修了：

- `services/document_service.process_url` / `process_upload` 新增 `defer_keyword_training: bool` 參數
- `services/pipeline_service` 在批次 ingest 時將該參數設為 `True`，並在所有文件 ingest 完之後**只訓練一次** TF-IDF 模型
- 之前一次 30 篇就會做 30 次完整 corpus 重訓，現在只做 1 次；對 1m+ 字元的累積資料庫差異很大
- 既有 `/api/document/upload`、`/api/document/ingest-url` 單筆 API 不受影響（預設仍是 `False`）

### 17.5 試用方式

```powershell
# 1. 啟動桌面版
.\.venv\Scripts\python.exe -m desktop_app

# 2. 在 LLM provider 選 "claude"
# 3. 在 LLM model 選 "claude-opus-4-7"（或自行輸入其他 Claude model id）
# 4. 在 API key 欄貼上 sk-ant-...
# 5. 按 Run research
```

或直接在 API 端：

```json
POST /api/pipeline/run
{
  "keywords": ["華碩 ASUS 全球稅務治理"],
  "user_prompt": "包含子公司、年報、SEC、EUR-Lex、Taiwan MOJ",
  "source_name": "deep_research",
  "provider": "claude",
  "model_name": "claude-opus-4-7",
  "report_format": "pptx"
}
```

只要環境變數 `ANTHROPIC_API_KEY` 已設定，整條 pipeline（搜尋擴寫、風險分析、PPTX 內容）都會交給 Claude。換成 `provider: "openai", model_name: "gpt-4o"` 或 `provider: "gemini", model_name: "gemini-2.5-pro"` 也是同一個寫法。

---

## 18. 查詢擴寫加強：抓抽樣／選案查核風險（2026-05 更新）

這一輪解的核心問題：搜尋稅務「抽樣風險」資料時，網路上幾乎不會用「抽樣風險」四個字直接寫出來，真正會寫出來的是各國國稅局自己用語，例如台灣「選案查核」「補徵稅款」、日本「税務調査」「更正処分」、韓國「세무조사」、中國大陸「税务稽查」「随机抽查」、IRS「Notice of Deficiency」「risk-based audit」。所以光靠原始字面或單一語言擴寫會漏掉一大塊。

### 18.1 多語言、多管轄區稅務同義詞典

`services/search_service.py` 新增三個常數：

| 常數 | 內容 | 用途 |
|------|------|------|
| `AUDIT_SAMPLING_TERMS` | 58 個抽樣／選案查核相關用語（中／英／日／韓／簡體） | 直接餵入查詢與排序加權 |
| `TAX_AUDIT_THESAURUS` | 10 個概念：audit / sampling / penalty / transfer_pricing / pillar_two / cfc / permanent_establishment / withholding_tax / tariff / vat_gst | 概念 → 多語同義詞 |
| `JURISDICTION_PROFILE` | 9 個管轄區（TW / JP / KR / CN / HK / SG / US / EU / IN）的審查機關別名、查核用語、申報用語 | 命中管轄區後做專屬擴寫 |

特色：

- 不依賴 LLM、零延遲、零 token 成本
- 即使 Ollama / 雲端 API 全壞，這層仍能擴寫
- 會自動抓出輸入裡的管轄區暗示（例如 `Taiwan`、`国税庁`、`IRS`、`SEC.gov`），對應到 `JURISDICTION_PROFILE` 補出當地查核用語

### 18.2 結構化意圖解析

新增 `_extract_intent_with_llm`，把單次 LLM 呼叫的輸出固定成 JSON schema：

```json
{
  "entities": ["primary company / group / subsidiary"],
  "jurisdictions": ["TW", "JP", "US"],
  "time_period": "FY2024",
  "risk_categories": ["audit", "sampling", "penalty", "transfer_pricing"],
  "document_types": ["annual_report", "regulatory_filing"],
  "focused_subsidiaries": [...],
  "must_have_terms": [...],
  "exclude_terms": [...]
}
```

`_build_intent_queries` 拿到這份 JSON 後做笛卡爾積：`entity × risk_category synonyms × jurisdiction audit_terms × must_have_terms`，產出最高 60 個帶引號的精準查詢。

例如使用者輸入「華碩跨國子公司 抽樣查核風險」，意圖解析會把它拆成：

- entities: `華碩`、`ASUS`、`ASUSTeK`
- jurisdictions: `TW`、`US`、`CN`、`HK`
- risk_categories: `audit`、`sampling`、`transfer_pricing`、`permanent_establishment`
- 產出查詢例：`"ASUS" risk-based audit selection`、`"華碩" 選案查核 113年度`、`"ASUSTeK" Notice of Deficiency`、`"華碩" 移轉訂價選案`

### 18.3 偽相關回饋（Pseudo-Relevance Feedback, PRF）

新增 `_pseudo_relevance_feedback`，邏輯：

1. 第一輪搜尋拿回的 titles + snippets 做 token 化
2. 英文：`[A-Za-z][A-Za-z0-9.-]{3,}`
3. 中文：對連續 CJK 段做 4 / 3 / 2-gram 滑窗（沒裝 jieba，這樣最穩）
4. 過濾掉低訊號詞與已存在於原查詢的詞
5. 排序頻率，取 top-N 與主體別名 + `tax audit / 稅務查核 / 税務調査` 重新組合
6. 拿這批新 query 再跑一輪 DuckDuckGo / Bing

實測：給「ASUS 移轉訂價查核補徵稅款」相關 snippet，PRF 會回饋出 `"ASUSTeK" 移轉訂 tax audit` 這類查詢，把第一輪沒命中的相鄰文件帶回。

### 18.4 排序與理由更新

| 加權項 | 分數 |
|--------|------|
| `sampling_hits`（命中 AUDIT_SAMPLING_TERMS） | +1.4 / 命中 |
| match_reasons 新增 | `命中抽樣／選案查核線索：...` |

所以前端結果列表會直接看到「為什麼這筆被抓出來」，例如 `命中抽樣／選案查核線索：選案查核, 補徵稅款`。

### 18.5 控制參數

- `_search_deep_research` 新增 `provider`、`model_name`、`use_intent_extraction` 三個入參
- `search()` 在 `source_name == "deep_research"` 時自動把這三個值傳下去
- 當 `use_ai_query_expansion = False` 時，意圖解析與 LLM 擴寫一起跳過，PRF 與多語同義詞典仍會跑（純規則式）

### 18.6 試用

```json
POST /api/pipeline/run
{
  "keywords": ["華碩 ASUS"],
  "user_prompt": "包含旗下子公司、跨國抽樣／選案查核風險、移轉訂價查核、補徵稅款、稅務裁罰書、稅務及用地調查",
  "date_range": "1y",
  "max_results": 30,
  "source_name": "deep_research",
  "provider": "ollama",
  "model_name": "qwen3:8b",
  "use_ai_query_expansion": true,
  "report_format": "pptx"
}
```

預期變化：

- `query_variants` 從原本的 ~36 上升到 48 上限，且新增 `_expand_with_thesaurus` 產出的 60 個多語擴寫
- 多一輪 `intent_queries`（最高 60 個）跑 DuckDuckGo + Bing
- 末端多一輪 `pseudo_relevance_feedback`，把第一輪命中的 snippet 反饋回搜尋
- 結果頁的 `match_reasons` 會出現「命中抽樣／選案查核線索：…」與「命中稅務事件線索：…」

### 18.7 還沒動但下一步可以接

1. **TF-IDF 自身詞彙回收** — 在 `_pseudo_relevance_feedback` 裡也讀一次 `KeywordService.feature_names`，把與輸入別名共現高頻的詞補進去（要做跨服務注入）
2. **Embedding 相似度重排** — `sentence-transformers` 或 Ollama embedding 模型，把搜尋結果語意相似度當第二排序軸
3. **Query negation** — 把意圖解析的 `exclude_terms` 轉成 `-noise -term` 的搜尋運算子
4. **Per-jurisdiction parallel fetch** — 偵測到多管轄區時開 thread pool 平行打各國新聞 RSS 與官方檢索

---

## 19. 搜尋層第二輪加強（2026-05 更新）

接續 §18，把上一輪「下一步」清單裡的事都做了，加上幾個結構性效能與品質改造。

### 19.1 平行化抓取（concurrent fan-out）

新增 `_run_parallel_searches`：

- 包成 `concurrent.futures.ThreadPoolExecutor`，預設 6 worker
- 依 task 數量自動縮放（`min(6, max(2, len(tasks)))`）
- 任何一個 task 拉滿 `candidate_limit` 就會 `cancel()` 還在排隊的 future，提早結束

`_search_deep_research` 整條流程已重寫成「分組平行」：

| 階段 | 內容 | 平行抓取 |
|------|------|----------|
| 1. seed | `official_seed` / `reference_seed` / `official_domain_seed` | — |
| 2. official tasks | sitemap、SEC EDGAR、EUR-Lex、Taiwan MOJ、（偵測到 JP）EDINET、（偵測到 KR）DART | ✅ |
| 3. intent tasks | 來自意圖解析的 6 個高精度查詢 × DuckDuckGo + Bing | ✅ |
| 4. targeted tasks | `site:` 官方／顧問定向查詢 | ✅ |
| 5. news tasks | Google News RSS（多 variant） | ✅ |
| 6. PRF tasks | 從第一波結果反饋出的 query | ✅ |

實測：5 個假任務（serial 約 0.35s）平行版只花 **0.118s**，速度約 3×。

### 19.2 來源健康度追蹤

新增 `_source_stats`：

- 每個 adapter（`_search_sec_edgar` / `_search_bing_web` ...）以 function name 作 key
- 追蹤 `success / fail / consecutive_fail`
- `consecutive_fail >= 3` 時自動進入 unhealthy 狀態，`_safe_search_call` 直接 short-circuit 回空陣列
- 任一次 success 就把連續失敗計數歸零，恢復正常排程
- 公開 `get_source_health_snapshot()` 給上層用

效益：DuckDuckGo 整輪都 403 的情況下，剩下 12 次 query variant 不會再去敲它，省下約 96 秒（8s timeout × 12）。

### 19.3 標題相似度 dedup（Jaccard n-gram）

`_dedup_by_title_similarity` 在 `_rank_results` 之後執行：

- 英文：lowercase + alpha-num token
- 中文：對連續 CJK 段做 2/3-gram 滑窗
- 用 Jaccard 相似度 ≥ **0.7** 視為近重複
- 高分結果保留，低分結果合併進 `duplicate_titles`，避免單一新聞稿被多家轉載灌爆排序

### 19.4 意圖層 must_have / exclude_terms 接到排序

`_rank_results` 接受 `intent` 參數：

- `must_have_bonus`：每命中一個 `must_have_terms` +1.6
- `exclude_penalty`：每命中一個 `exclude_terms` -2.5
- `match_reasons` 顯示「命中意圖必含詞：…」與「命中意圖排除詞 (扣分)：…」，方便人工檢查 LLM 抽出的詞是否合理

這也代表 §18 加的結構化意圖 JSON（`exclude_terms`、`must_have_terms`）終於有實際排序效果，而不只是被打印出來。

### 19.5 新增日韓官方揭露來源

| 抓取器 | 來源 | 內容 |
|--------|------|------|
| `_search_edinet_jp` | 金融庁 EDINET（disclosure2.edinet-fsa.go.jp） | 有価証券報告書、四半期報告書、臨時報告書，含合併所得稅、關係人交易、區段稅務揭露 |
| `_search_dart_kr` | 韓國 FSS DART（dart.fss.or.kr） | 사업보고서、분기보고서、주요사항보고서；한국 상장사 法人税、이전가격、특수관계자 거래 |

啟用條件：`_search_deep_research` 偵測到 JP / KR jurisdiction，或公司網域以 `.jp`／`.kr` 結尾，會把 EDINET / DART 自動排入第 2 階段平行 task。

排序加權：`edinet_jp` / `dart_kr` 各 +1.6（介於 SEC EDGAR +1.8 與 EUR-Lex +1.5 之間）。對應網域加入 `DISCLOSURE_DOMAINS`，自動拿到 `disclosure_bonus`。

### 19.6 PRF 接 KeywordService 詞彙回收

`_pseudo_relevance_feedback` 現在會在做 n-gram 統計後，再去 `services/keyword_service.py` 的 TF-IDF feature_names（最多 200 詞）撈一輪：

- 已被 TF-IDF 訓練出來的領域詞，如果在第一波結果的 title/snippet 裡出現，就加進候選詞
- 排除既有 query / 低訊號詞
- 結果與 n-gram 候選詞合併排序，做為 PRF 第二輪查詢的種子

意義：`KeywordService` 累積的領域詞庫終於回流到搜尋層，讓每次 ingest 完的「集團架構、合併財務報表、所得稅費用、移轉訂價、有效稅率」這些 TF-IDF 高分詞自動進到下一輪查詢。

### 19.7 控制與觀察

- 平行 worker 上限：`SearchService.PARALLEL_FETCH_WORKERS`（預設 6）
- 來源健康度門檻：`SearchService.SOURCE_HEALTH_FAIL_THRESHOLD`（預設 3）
- Dedup 相似度門檻：`_dedup_by_title_similarity(threshold=0.7)`
- 觀察當前健康狀態：`search_service.get_source_health_snapshot()`

### 19.8 試用

```json
POST /api/pipeline/run
{
  "keywords": ["TSMC 台積電 抽樣選案查核風險"],
  "user_prompt": "包含日本子公司、韓國子公司、移轉訂價、補徵稅款、有效稅率，不要新聞稿轉載",
  "date_range": "1y",
  "max_results": 30,
  "source_name": "deep_research",
  "provider": "claude",
  "model_name": "claude-sonnet-4-6",
  "use_ai_query_expansion": true
}
```

預期變化：

- 意圖解析會把 `jurisdictions: ["TW", "JP", "KR"]` 抽出來
- 第 2 階段平行 fan-out 會同時打 **sitemap、SEC EDGAR、EUR-Lex、Taiwan MOJ、EDINET、DART**（6 個 adapter 並行）
- `exclude_terms: ["press release", "新聞稿"]` 會給轉載稿扣 -2.5
- Jaccard dedup 會把多家媒體轉載同一篇 TSMC 新聞合併
- 第一輪結果裡若 TF-IDF 已有「合併財務報表」「有效稅率」，PRF 第二輪會自動把這兩個詞當種子查詢
- 結果頁的 `match_reasons` 多了「命中意圖必含詞」「命中意圖排除詞 (扣分)」「命中抽樣／選案查核線索」

---

## 20. 跨層加強：去重、歷史、全文檢索、LLM 韌性（2026-05 更新）

這一輪不再只動搜尋層，把 storage / LLM / pipeline 等之前沒碰過的薄弱環節一次補上。

### 20.1 內容雜湊去重（idempotent ingestion）

`services/storage_service.py` 新增 `content_hash TEXT` 欄與索引 `idx_documents_content_hash`。

`services/document_service.py` ingest 流程現在會：

1. 抽出 `raw_text` 後做 `re.sub(r"\s+", " ", text).lower()` 正規化
2. 算 `sha256` 得到 `content_hash`
3. 呼叫 `storage_service.find_document_by_content_hash(hash)` 查重
4. 若已存在，**直接回傳既有 `doc_id` 與 `deduplicated: True`**，不重寫資料庫、不重抽關鍵字

效益：

- 同一篇 PDF 被不同 URL（IR 入口、SEC 鏡像、media archive）指向時，現在只算一次，不會在 DB 與報告流程裡重做
- 同一輪 `deep_research` 平行 fan-out 命中相同檔案時也會被攔下
- 對應 LLM 分析、PPTX 產出的成本下降

### 20.2 SQLite FTS5 全文索引

`documents` 同步影子表 `documents_fts`（virtual table，`unicode61 remove_diacritics 2` tokenizer）。

- `save_document()` 自動寫入 / 更新 FTS
- 新增 `storage_service.fts_search_documents(query, limit)`：用 `bm25()` 排序，回傳含 `snippet(documents_fts, 2, '«', '»', ' … ', 12)` 的高亮片段
- 新增 API `POST /api/document/fts-search` 回 `FtsSearchResponse`（含 doc 中繼資料 + 高亮 snippet + bm25 rank）

對既有的 `LIKE %keyword%` 是 100×–1000× 級的速度差距；中文也能命中（unicode61 tokenizer 切字）。

### 20.3 Pipeline 執行歷史持久化

新表 `pipeline_runs`：

```
run_id (PK), started_at, finished_at, status,
source_name, provider, model_name, keywords (JSON),
user_prompt, payload (JSON), result_summary (JSON), error
```

`services/pipeline_service.py` 兩個入口都包了 `_start_run` / `_finalize_run`：

- 進入 pipeline 立即寫一筆 `status="running"` + 完整 payload
- 成功後寫 `status="success"` + `_summarize_pipeline_result()`（只存 doc_id / title / risk_level / report_file_path 的精簡版）
- 失敗會寫 `status="failed"` + `error=str(exc)`，例外照樣往上拋

新 API：

| 方法 | 端點 | 用途 |
|------|------|------|
| GET | `/api/pipeline/history?limit=50` | 列最近執行 |
| GET | `/api/pipeline/history/{run_id}` | 單筆完整紀錄（含 payload） |

`PipelineRunResponse` / `SearchTrainResponse` 也都新增 `run_id` 欄，前端可以直接拿來追蹤。

### 20.4 LLM JSON 修復 + 自動 retry

之前 `LLMService.generate_json` 一遇到模型回 markdown fence 就 `except Exception: pass` 直接 fallback 到空 schema。改成：

1. `JSON_PARSE_RETRIES = 1`：第一次失敗後等 0.4s 再呼叫一次模型
2. `_safe_json_loads` 三段修復：
   - 純 `json.loads`
   - 去 ` ```json` / ``` ``` ``` 圍欄
   - 用 `\{[\s\S]*\}` 截出第一段疑似 JSON、再修 trailing comma 與單引號
3. 兩次都失敗才回 schema fallback

煙霧測試結果：

| 輸入 | 結果 |
|------|------|
| `{"a":1}` | ✓ |
| ` ```json\n{"a":2}\n``` ` | ✓ |
| `Here is your output: {"a":3, "b":[1,2,3]}` | ✓ |
| `{"a":4,}` | ✓ |
| `not json at all` | None（合理 fallback） |

對 Ollama 上 qwen3 / deepseek-r1 這類偶爾多吐一行 reasoning 的模型，影響特別明顯。

### 20.5 Anthropic prompt caching

`services/llm_service.py._call_claude` 改成標準 system + user 雙區塊格式，當區塊長度 ≥ `CACHE_PROMPT_THRESHOLD_CHARS = 1500` 時自動加 `cache_control = {"type": "ephemeral"}`：

- `system` 區塊：固定的 Tax Monitor 領域背景（稅務同義詞集、保留原公司名等規則）
- `user` 區塊：實際 prompt（搜尋擴寫 / 風險分析 / 報告大綱）

對 Claude Opus 4.7 / Sonnet 4.6，重複呼叫同一份 system + 大段 prompt 命中 cache 後 input tokens 計費 0.1× 左右；同一輪 pipeline 多篇文件分析 → 直接體現在帳單上。

### 20.6 試用

```bash
# 1. FTS 對已 ingest 的 corpus 做全文檢索
curl -s -X POST http://127.0.0.1:8010/api/document/fts-search \
  -H "Content-Type: application/json" \
  -d '{"query": "transfer pricing audit OR 移轉訂價 OR 補徵稅款", "limit": 10}'

# 2. 看歷次 pipeline run
curl -s http://127.0.0.1:8010/api/pipeline/history?limit=20

# 3. 看單筆執行 payload + summary
curl -s http://127.0.0.1:8010/api/pipeline/history/<run_id>
```

### 20.7 還沒做、價值高的下一輪候選

- Pipeline 進度事件（SSE / WebSocket）讓 UI 即時顯示「搜尋中 / 分析第 2 篇 / 產 PPTX」
- desktop_app 加 History tab 直接消費 `/api/pipeline/history`
- PPTX 自動加「資料來源」頁，含 URL + 抓取時間 + 命中理由
- 每域 polite rate limiter（token bucket）+ HEAD precheck 跳 404
- 文件 ingest size cap + 超大 PDF chunk 處理
- 把 `services/document_parser_service.py` 接 OCR fallback（掃描 PDF 不會空白）

---

## 21. 韌性與可追溯性強化（2026-05 更新）

接續 §20 的清單，這一輪做了 5 件不需要新依賴、但每件都直接影響使用者觀感的事。

### 21.1 每域 polite rate limiter

`services/search_service.py` 新增 `_respect_domain_rate_limit` / `_mark_domain_request`：

- 預設 `DOMAIN_MIN_INTERVAL_SECONDS = 0.7`
- 對 SEC EDGAR、Taiwan MOJ、EUR-Lex、EDINET、DART 等公務 / 監管站做更嚴格的 override（0.9–1.2s）
- 每個 domain 單獨 lock，不會跨域互相阻塞
- 與既有的 `ThreadPoolExecutor` 平行 fan-out 無衝突：同 domain 自動排隊，不同 domain 仍然並行

效益：

- SEC EDGAR 過去最容易被 429 banned，因為 official rate guide 是 ≤10 req/s；現在嚴守 ≥1.1s 區間
- 法務 / 公務站若在某輪查詢被 throttled，整支 pipeline 不會再 cascade 失敗

### 21.2 HEAD precheck

新增 `_head_precheck(url)`：

- 走 `requests.Session.head(allow_redirects=True)`
- 命中 404 / 410 / 451 → 回 `False`（不去拉全文）
- `Content-Length > 25 MB` → 回 `False`（避免下載 200MB 年報原檔）
- `Content-Type` 是 video / audio / image → 回 `False`
- 連線失敗 fail-open（回 `True`，不誤殺）

`pipeline_service.py` 的 ingest loop 在抓任何文件前先 precheck，省下 404 與超大檔的全文下載 + parser 開銷。

### 21.3 文件 ingest size cap + 串流下載

`services/document_service.py` 新增兩個常數：

- `MAX_FETCH_BYTES = 25 * 1024 * 1024`（25 MB）
- `MAX_RAW_TEXT_CHARS = 600_000`（≈ Claude 4.x Opus context 中段）

`_fetch_url_content` 改成：

1. `requests.get(stream=True)`，先看 `Content-Length`，超 cap 直接拒絕
2. 64 KB chunk 串流下載，過程中也檢查 size，避免回應 header 撒謊
3. PDF / HTML 都會經過 `_cap_text(text)` — 超過 600k 字元就截斷並附 `[...truncated by tax-monitor: original exceeded 600000 chars]`

效益：

- 不會再因為一份 200 MB 的掃描年報把 Python process 撐爆
- 後續送進 LLM 分析的字數有 ceiling，避免 1M context 模型也被打到 token 上限

### 21.4 PPTX 自動產出「資料來源 / Sources & Citations」頁

`services/report_service.py` 新增 `_build_sources_slide`，在 `output_format == "pptx"` 時自動 append 到 slide_outline：

固定欄位（依 document / analysis 中繼資料）：

| 欄位 | 內容 |
|------|------|
| 原始文件 / Source title | document.title |
| 來源網址 / URL | document.url |
| 原始檔名 / File name | document.file_name |
| 來源類型 / Source | source_type via source_name（例：`pdf via sec_edgar`） |
| 原文語言 / Original language | document.language |
| 地區 / 產業 | country · industry |
| 原始發布 / Published | document.published_date |
| 匯入時間 / Ingested at | document.created_at |
| 風險判斷 / Risk | risk_level + risk_tags |
| 分析模型 / Generated by | provider / model / target language |
| 報告時間 / Report timestamp | 報告 build 當下時間 |
| 使用者意圖 / Research intent | user_prompt（截 240 字） |

對稅務簡報的可追溯性是必須項；管理層 review 時可直接從這頁判斷資料新鮮度與模型版本。

### 21.5 Desktop History Tab

`desktop_app/results_panel.py` 新增第五個 tab `History`：

- 直接呼叫 `StorageService.list_pipeline_runs(limit=50)`，不需要先啟動 FastAPI
- 切到該 tab 時自動 refresh（`<<NotebookTabChanged>>`）
- 工具列有 `Refresh` 按鈕手動重抓
- 每筆顯示：status、run_id、started/finished 時間、provider/model、source、keywords、prompt 摘要、result summary（searched / ingested / processed）、error

對使用者：跑了 5 次 pipeline 之後可以直接在桌面比對哪一組關鍵字命中率最高、PPTX 落在哪裡，不需要再去翻 SQLite。

### 21.6 控制與觀察

- 速率限制：`SearchService.DOMAIN_MIN_INTERVAL_SECONDS`、`SearchService.DOMAIN_MIN_INTERVAL_OVERRIDES`
- HEAD 上限：`SearchService.HEAD_PRECHECK_MAX_BYTES = 25 MB`
- 文件大小上限：`document_service.MAX_FETCH_BYTES`、`MAX_RAW_TEXT_CHARS`
- 桌面歷史頁切換時自動 refresh，可以隨時手動按 Refresh

### 21.7 還沒做、下一輪候選

- Pipeline 進度事件（SSE / WebSocket）：`run_pipeline` 注入 callback，UI 即時顯示「已搜尋 12 筆 / 分析第 2 篇 / 產 PPTX 中」
- OCR fallback（pytesseract / EasyOCR）：掃描 PDF 不再回空字串
- PDF 表格抽取（camelot / pdfplumber）：年報常把所得稅費用、移轉訂價金額放表格內
- KeywordService 增量訓練：跨 ingest batch reuse vectorizer，省 fit time
- 桌面版加 dark mode + 字型切換

---

## 22. 平行匯入、表格抽取、進度回呼、Markdown 報告（2026-05 更新）

接續 §21.7 的清單，這一輪做 4 件：把 ingest 從序列改平行、PDF 表格不再被丟掉、桌面 UI 即時看到進度、報告多一個純 markdown 格式。

### 22.1 平行文件匯入（asyncio.gather + Semaphore）

之前 `pipeline_service` 是 `for item in results: await process_url(...)`，5 篇文件等於 5 次序列 HTTP+parse。

改造：

1. `services/document_service.py` 把 `_fetch_url_content`（同步阻塞）包進 `await asyncio.to_thread(self._fetch_url_content, url)`，讓 `process_url` 真的能在多 coroutine 並行
2. `services/pipeline_service.py` 新增 `_ingest_items_concurrently`：`asyncio.Semaphore(INGEST_CONCURRENCY=4)` 控制最多 4 個同時下載
3. 兩個 pipeline 入口（`run_pipeline` / `search_ingest_and_train`）的 ingest 迴圈都改用這個 helper

實測（synthetic 8 篇 × 0.3s）：

```
serial estimate: 2.40s
concurrent actual: 0.633s   (≈ 3.8× speedup, concurrency=4)
```

對實際 30 篇 × 1–3s 的 HTTP 抓取，整體 wall-clock 通常會降到原本的 25–35%。

### 22.2 PDF 表格抽取（pdfplumber）

稅務年報最關鍵的數字（所得稅費用、有效稅率、移轉訂價金額、子公司清單）幾乎都在表格裡，pypdf 把表格扁平化會破壞欄位對齊。

`services/document_parser_service.py` 改成：

1. 嘗試 `import pdfplumber`，沒裝就 graceful skip（**pdfplumber 是選用**，加進 `requirements.txt` 就會啟用）
2. PDF 解析完後呼叫 `_enrich_pdf_with_tables`：對每頁跑 `extract_tables()`，把每張表 render 成 `cell | cell | cell` 行，附 `[Table extracted via pdfplumber] page=X table=Y` header，append 到 raw_text
3. 上限 `PDFPLUMBER_MAX_PAGES=50`、`PDFPLUMBER_MAX_TABLES=30`，避免百頁年報塞爆 raw_text
4. 過濾掉「行數 < 2 或有效 cell < 4」的雜訊表格

未安裝 pdfplumber 時行為與之前完全一致；安裝後 raw_text 末段會多出結構化表格，KeywordService 與 LLM 分析都吃得到。

### 22.3 Pipeline 進度回呼

`services/pipeline_service.py` 新增 `progress_callback: Optional[PipelineProgressCallback]` 參數。觸發點：

| 事件 | 內容 |
|------|------|
| `run_started` | run_id + payload |
| `search_started` / `search_completed` | source_name, keywords / count |
| `ingest_phase_started` / `ingest_phase_completed` | total / ingested |
| `ingest_started` / `ingest_completed` / `ingest_failed` / `ingest_skipped` | index, url, deduplicated, error |
| `analysis_started` / `analysis_completed` | doc_id, risk_level |
| `report_started` / `report_completed` | format, file_path |
| `run_completed` / `run_failed` | run_id, processed/error |

`desktop_app/worker.py` 接受 `on_progress` 回呼；`desktop_app/app.py` 把事件 marshal 到主執行緒；`desktop_app/results_panel.py` 新增 `update_progress` + `_format_progress_event`，把每個事件變成一行人類看的字，更新到原本的 `Status` label。

實際使用體感：

```
Searching (deep_research): ASUS, 查稅
Search returned 27 candidates
Ingesting 12 candidates (concurrent=4)...
Ingested 1/12
Ingested 2/12 (deduplicated)
Analyzing #0: ASUS Q3 audit risk
Analysis #0 done: risk=High
Generating pptx report for #0
Report ready: ...\data\reports\ASUS Q3 audit risk.pptx
Pipeline complete: ingested=8 processed=3
```

之前一直停在 `Running...`；現在每幾秒就有一行新的進度。

### 22.4 Markdown 報告輸出

之前只有 obsidian / slides / pptx。新增 `markdown` 格式：

- `models/schemas.py` `ReportRequest.output_format` / `PipelineRunRequest.report_format` 的 regex 加上 `|markdown`
- `services/report_service.py` 新增 `_build_markdown_report` + `_write_markdown_file`，輸出純 GitHub-flavored markdown
- 結構：Executive summary → Risk level / tags → Auto-extracted keywords → Key evidence → Notes → Slide outline → **Sources & metadata**（含 URL、生成模型、報告時間、使用者意圖）

對外分享比 obsidian frontmatter 乾淨，比 PPTX 輕量；可直接貼到 GitHub Issue / Wiki / Notion。

### 22.5 試用

```json
POST /api/pipeline/run
{
  "keywords": ["TSMC 抽樣選案查核風險"],
  "source_name": "deep_research",
  "max_results": 30,
  "max_documents_to_process": 5,
  "report_format": "markdown",
  "provider": "claude",
  "model_name": "claude-sonnet-4-6",
  "use_ai_query_expansion": true
}
```

或 desktop：

1. `python -m desktop_app`
2. 輸入關鍵字、按 `Run research`
3. 上方 Status label 即時跳：`Searching… → Ingested 3/12 → Analyzing #1 → Report ready: …`
4. 在 `data/reports/` 出現 `.md` 檔（如果切到 markdown），或 `.pptx`（預設）

選用安裝：

```powershell
.\.venv\Scripts\python.exe -m pip install pdfplumber
```

裝完之後 PDF ingest 會自動把表格塞進 raw_text。

### 22.6 還沒做、下一輪候選

- **OCR fallback**（pytesseract / EasyOCR）：掃描型 PDF 不會回空字串
- **CSV / XLSX 匯出**：把 search_results、ingested_documents、analyses 一鍵匯出表格
- **Run comparison**：`/api/pipeline/runs/compare?a=...&b=...` 回傳兩次執行的 doc 差集
- **Pipeline cancel**：worker 暴露 cancel token，desktop UI 加紅色停止鈕
- **Dark mode / 字型切換**
- **Per-pipeline 成本追蹤**：累積 LLM tokens / 估算 USD，存進 `pipeline_runs.cost_summary`

---

## 23. 成本追蹤、Pipeline 中斷、表格匯出、Dark Mode（2026-05 更新）

這一輪解 4 個從營運面長出來的需求：切到付費 LLM 後想知道花多少、長 pipeline 想中途停、給法務同事的報告要試算表、桌面要 dark mode。

### 23.1 LLM token 用量追蹤

`services/llm_service.py` 每個 provider 呼叫器改成回傳 `(text, usage)`，並把每次 usage 寫進 thread-safe 的 `_usage_records`：

| Provider | input | output | cache_read | cache_write |
|----------|-------|--------|------------|-------------|
| Claude | `usage.input_tokens` | `usage.output_tokens` | `usage.cache_read_input_tokens` | `usage.cache_creation_input_tokens` |
| OpenAI | `usage.prompt_tokens` | `usage.completion_tokens` | `prompt_tokens_details.cached_tokens` | — |
| Gemini | `usageMetadata.promptTokenCount` | `usageMetadata.candidatesTokenCount` | `cachedContentTokenCount` | — |
| Ollama | `prompt_eval_count` | `eval_count` | — | — |

新公開方法：

- `LLMService.consume_usage_records()` — 取走並清空（pipeline 結束時呼叫）
- `LLMService.reset_usage_records()` — pipeline 開始時清零
- `LLMService.get_usage_summary()` — 即時看當下累積

### 23.2 Per-pipeline cost summary

`services/pipeline_service.py`：

1. `_reset_token_counters()` 在 pipeline 開始時對 search / analysis / report / keyword 四個 service 的 `llm_service` 全部 `reset_usage_records`
2. `_collect_token_usage()` 聚合所有 service 的 records，產生 `{ totals, per_model }` 結構
3. 成功 / 失敗 / 取消 三條路徑都會把 `cost` 存進 `pipeline_runs.result_summary` 並透過 progress callback 暴露
4. `_summarize_pipeline_result()` 也帶入 `cost`，這樣 `/api/pipeline/history` 直接看得到

實測（synthetic）：

```json
{
  "totals": { "calls": 4, "input_tokens": 7000, "output_tokens": 1420, "cache_read_tokens": 3800 },
  "per_model": {
    "claude::claude-sonnet-4-6": { "calls": 2, "input_tokens": 4900, "output_tokens": 620, "cache_read_tokens": 3800 },
    "ollama::qwen3:8b":          { "calls": 1, "input_tokens": 1200, "output_tokens": 600 },
    "openai::gpt-4o-mini":       { "calls": 1, "input_tokens": 900, "output_tokens": 200 }
  }
}
```

`cache_read_tokens` 顯示 §20.5 的 Anthropic prompt caching 真的有命中，在連續呼叫同 system prompt 時能直接看到 token 重用。

### 23.3 Pipeline 取消

新類別 `PipelineCancelled(Exception)`。`pipeline_service` 接受 `cancel_event: Optional[threading.Event]`：

- `_check_cancel(event)` 檢查 event，set 了就 raise `PipelineCancelled`
- 檢查點：search 前後、ingest 階段前後、analysis 與 report 每篇開始前
- 並行 ingest 也會在每個 task 進入時檢查；已 in-flight 的 HTTP 抓取會自然完成不會中斷（避免 partial state）
- 結束路徑：取消 → `status="cancelled"` 寫入 `pipeline_runs`，並把當下累積的 cost 一起存

桌面整合：

- `desktop_app/worker.py` 內建 `threading.Event` cancel_event；公開 `cancel()` / `is_running()`
- 新增 `on_cancelled` callback
- `desktop_app/input_panel.py` 新增 **Stop** 按鈕（執行中才 enable）
- `desktop_app/app.py` 把 Stop 連到 `worker.cancel()`，UI 上立即顯示 `Cancellation requested...`
- `desktop_app/results_panel.py` 加 `run_cancelled` 事件處理，狀態列顯示 `Pipeline cancelled by user`

### 23.4 文件 CSV / XLSX 匯出

新 endpoint：

```
GET /api/document/export?format=csv&keyword=tax&country=TW&limit=500
GET /api/document/export?format=xlsx&industry=technology&limit=200
```

- CSV 用標準函式庫 `csv` + UTF-8 BOM（Excel 開繁中不亂碼）
- XLSX 走 `openpyxl`（選用），未安裝時回 503 並提示安裝
- 欄位：`doc_id, title, source_type, source_name, language, country, industry, published_date, created_at, updated_at, url`
- 過濾參數沿用 `list_documents`：keyword / country / industry / language
- 檔名自動加時戳：`tax_monitor_documents_20260507_163215.csv`

### 23.5 Dark Mode 切換

`desktop_app/app.py` 抽出 `LIGHT_THEME` / `DARK_THEME` palette 與 `apply_theme(dark)` 方法。底層改：

- ttk 的 TFrame / TLabel / TCheckbutton / TNotebook / TNotebook.Tab / TCombobox 全部跟著切換
- 透過 `_apply_text_theme` 遞迴把所有 `tk.Text` widget 的 background / foreground / insertbackground 也換掉
- `desktop_app/input_panel.py` 新增 `Dark mode` checkbox，切換時呼叫 root window 的 `apply_theme`
- 預設 light，狀態存在 `tk.BooleanVar`，視窗關閉就回到 light（不持久化）

### 23.6 試用

```powershell
# 桌面：跑一次 → 看 status 列尾巴顯示 LLM tokens
.\.venv\Scripts\python.exe -m desktop_app
# 切到 Dark mode；按 Stop 中斷；關掉 Dark mode

# API：CSV 匯出
curl -o asus.csv "http://127.0.0.1:8010/api/document/export?format=csv&keyword=ASUS"

# API：XLSX 匯出（需先 pip install openpyxl）
curl -o tw_tax.xlsx "http://127.0.0.1:8010/api/document/export?format=xlsx&country=TW&industry=technology"

# API：歷史紀錄看 cost
curl http://127.0.0.1:8010/api/pipeline/history?limit=10
```

進度列尾巴範例：

```
Pipeline complete: ingested=8 processed=3 · LLM tokens in/out=42100/8200 cache_read=18400
```

### 23.7 還沒做、下一輪候選

- **USD 估價層**（per-provider per-model 單價表，自動把 tokens × 單價算成 USD）
- **OCR fallback**（pytesseract）
- **Run comparison**（兩次執行的 doc 差集、新增 / 移除文件）
- **Pipeline retry on transient failure**（HTTP 5xx 自動重跑單篇）
- **API 認證**（FastAPI Bearer token）
- **Document age annotation**（搜尋結果旁邊顯示 `30 days ago`）
