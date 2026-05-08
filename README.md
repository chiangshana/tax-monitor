# Tax Monitor 交付版快速指南

最後整理日期：2026-05-08

Tax Monitor 是一套稅務風險自動研究工具，主流程可以一次完成：

1. 輸入公司、子公司、產業或稅務風險關鍵字
2. 自動搜尋 DuckDuckGo / Bing / Google News / 深度研究來源
3. 匯入網路文件與 PDF / HTML / 文字內容
4. 使用本地 Ollama 或雲端 LLM 分析稅務風險
5. 使用 RAG 交叉比對已匯入文件，補強分析脈絡
6. 訓練關鍵字模型
7. 產出 PPTX 稅務風險報告
8. 匯出 n8n workflow 做排程自動化

## 本輪檢查結果

目前主流程符合專案需求：

- Tkinter 桌面版可輸入關鍵字、補充需求、期間、資料筆數上限與來源
- 搜尋層支援 `all` / `deep_research`，可用 DuckDuckGo、Bing、Google News、官方頁、SEC/IR/sitemap 等來源補強
- 文件匯入後會訓練關鍵字模型
- 分析與 PPTX 輸出可用 Ollama 或 OpenAI / Gemini / Claude / Qwen Cloud API
- n8n 分頁可依目前設定匯出自動化 workflow
- 新增 RAG：分析每篇文件時會從本機已匯入資料庫抓相關片段，作為 LLM 交叉比對背景

仍需注意：

- RAG 只能強化「已匯入文件之間的關聯分析」，不能取代前面的網路搜尋；若搜尋結果太少，仍要提高 `Max results`、改用 `deep_research`、或在 Assistant 補充公司英文名、子公司名與稅務議題。
- 安裝包目前是 Windows 版且未簽章，部分公司電腦可能需要 IT 放行。

## 目前保留的乾淨資料夾結構

```text
tax-monitor-main/
├─ desktop_app/       # Tkinter 桌面版
├─ services/          # 搜尋、文件、LLM、分析、報告、pipeline 核心邏輯
├─ routers/           # FastAPI routes
├─ models/            # Pydantic schemas
├─ ui/                # 舊版瀏覽器 UI
├─ examples/          # smoke test 與範例 HTML
├─ data/              # 執行時輸出，預設保留空資料夾
├─ tools/             # 打包腳本
├─ release/           # 對外交付安裝包
├─ main.py            # FastAPI entrypoint
├─ requirements.txt
└─ README.md
```

已清掉的內容：

- `build/`
- `dist/`
- `__pycache__/`
- 舊版 `TaxMonitor-Setup-fixed*.exe`
- 舊 SHA 檔
- runtime DB / db journal
- 測試輸出 PPTX
- 舊的重複專案資料夾 `tax-monitor-git/`

目前 `release/` 只保留三個交付檔：

```text
release/
├─ TaxMonitor-Setup.exe
├─ TaxMonitor-Windows-Installer.zip
└─ SHA256SUMS.txt
```

## 一般使用者：一鍵安裝

把這個檔案給使用者：

```text
release/TaxMonitor-Setup.exe
```

安裝流程：

1. 雙擊 `TaxMonitor-Setup.exe`
2. 如果 Windows SmartScreen 提醒未知發行者，確認來源可信後選擇繼續執行
3. 安裝完成後，桌面會出現 `Tax Monitor` 捷徑
4. 雙擊捷徑啟動 Tkinter 桌面程式

適用環境：

- Windows 10 / Windows 11
- 64-bit x86 電腦
- 一般使用者權限即可安裝到 `%LOCALAPPDATA%\Programs\TaxMonitor`

注意：

- 這不是 macOS / Linux 安裝包
- 安裝包未做程式碼簽章，公司電腦可能被 IT 原則擋下
- 本地 LLM 模型不會包進 EXE，因為模型通常數 GB，需要另外下載

## 桌面版使用流程

開啟 `Tax Monitor` 後：

1. 左側 `Search keywords` 輸入公司與風險詞，例如：

```text
華碩, ASUS, ASUSTeK, transfer pricing, withholding tax, Pillar Two, permanent establishment
```

2. `Research intent` 輸入研究需求，例如：

```text
搜尋華碩與旗下子公司在最近 3 個月可能需要注意的跨國稅務風險，包含轉讓訂價、扣繳稅、常設機構、全球最低稅負、稅務稽查與補稅新聞。
```

3. 建議設定：

```text
Source: all 或 deep_research
Period: 3m
Max results: 30-100
PPTX limit: 3-10
LLM provider: ollama
LLM model: qwen3:8b
Use AI query expansion: checked
Use RAG context: checked
RAG chunks: 4
Generate PPTX: checked
```

4. 按 `Run research`
5. 右側分頁查看 `Summary`、`Search results`、`Documents`、`PPTX`、`Assistant`、`LLM Setup`、`n8n Automation`、`History`

## LLM Setup 分頁

`LLM Setup` 分頁可協助一般使用者設定本地 LLM：

- 檢查是否已安裝 Ollama
- 用 `winget` 嘗試安裝 Ollama
- 從清單選模型並執行 `ollama pull`
- 查看已安裝模型

建議模型：

```text
qwen3:8b
qwen3.5:9b
qwen3.5:27b
```

手動指令：

```powershell
ollama pull qwen3:8b
ollama pull qwen3.5:9b
ollama pull qwen3.5:27b
ollama run qwen3:8b
ollama run qwen3.5:27b
```

`qwen3.5:27b` 下載大小約 17GB，適合記憶體與顯示卡資源較充足的電腦。Ollama 目前常見 tag 是 `qwen3.5:0.8b`、`qwen3.5:2b`、`qwen3.5:4b`、`qwen3.5:9b`、`qwen3.5:27b`、`qwen3.5:35b`、`qwen3.5:122b`；目前沒有獨立的 `qwen3.5:17b` tag。

雲端模型不需要下載，只要在左側 API key 欄位輸入，或事先設定 `OPENAI_API_KEY`、`GEMINI_API_KEY`、`ANTHROPIC_API_KEY`、`DASHSCOPE_API_KEY`。

Qwen Cloud / Alibaba Model Studio 適合想用 `qwen3.6-plus`、`qwen3.6-max-preview`、`qwen-max`、`qwen-max-latest`、`qwen3.5-397b-a17b` 這類雲端模型的情境。桌面版請選：

```text
LLM provider: qwen
LLM model: qwen3.6-plus
API key: 貼上 DASHSCOPE_API_KEY
```

若你的 DashScope 帳號綁定特定區域，可用環境變數覆蓋 API base URL：

```powershell
$env:DASHSCOPE_BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
```

`max` 與 `3.6` 系列是雲端 API 模型，不會出現在 `LLM Setup` 的 Ollama 安裝清單；本機安裝仍請使用 `qwen3:8b`、`qwen3.5:9b`、`qwen3.5:27b` 等 Ollama tag。

## Assistant 分頁

如果搜尋結果太少、來源太集中、沒有涵蓋子公司或跨國稅務議題，可以切到 `Assistant`。

範例：

```text
這次結果太少，請擴大到華碩旗下子公司、英文來源、轉讓訂價、扣繳稅、常設機構、Pillar Two、稅務稽查與補稅相關資料。
```

Assistant 會回傳下一輪建議，可按 `Apply settings` 或 `Apply + rerun`。

## RAG 增強分析

RAG 預設開啟。它會在分析每篇文件時：

1. 從本機 SQLite 文件庫讀取已匯入文件
2. 將長文件切成片段
3. 用 TF-IDF 相似度找出與目前公司、子公司、稅務風險最相關的片段
4. 把片段放進 LLM prompt，要求模型只把有證據的內容寫進報告
5. 在 PPTX 中加入 RAG 交叉比對來源

桌面版設定：

```text
Use RAG cross-document context: checked
RAG chunks: 4
```

API 參數：

```json
{
  "use_rag_context": true,
  "rag_top_k": 4
}
```

快速驗證 RAG：

```powershell
.\.venv\Scripts\python.exe -B examples\run_rag_smoke_test.py
```

成功時會看到：

```text
rag_chunk_count: 1
rag_smoke_test: ok
```

## n8n Automation 分頁

`n8n Automation` 分頁可把目前左側設定轉成 n8n workflow。

建議流程：

1. 左側先設定好搜尋與模型
2. 到 `n8n Automation`
3. 按 `Start API server`
4. 按 `Check API`
5. 按 `Export n8n JSON`
6. 到 n8n 匯入 JSON

匯出的 workflow 會呼叫：

```text
POST http://127.0.0.1:8010/api/pipeline/run
```

如果使用 n8n Cloud，`127.0.0.1` 會指向 n8n Cloud 自己，不會指向使用者電腦；這時需要把 Tax Monitor API 部署成雲端可連線服務，或用 tunnel 暫時暴露本機 API。

## 開發者：從原始碼啟動

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

啟動 FastAPI：

```powershell
python -m uvicorn main:app --host 127.0.0.1 --port 8010
```

啟動 Tkinter 桌面版：

```powershell
python -m desktop_app
```

## FastAPI 一次跑完整流程

Endpoint：

```text
POST /api/pipeline/run
```

範例 JSON：

```json
{
  "keywords": ["華碩", "ASUS", "ASUSTeK", "transfer pricing", "Pillar Two"],
  "user_prompt": "搜尋華碩及旗下子公司最近 3 個月跨國稅務風險，包含轉讓訂價、扣繳稅、常設機構、全球最低稅負、稅務稽查與補稅新聞。",
  "mode": "auto",
  "date_range": "3m",
  "max_results": 30,
  "country": null,
  "industry": "technology",
  "source_name": "all",
  "candidate_urls": [],
  "use_ai_query_expansion": true,
  "target_language": "zh",
  "analysis_mode": "translate_first",
  "provider": "ollama",
  "model_name": "qwen3:8b",
  "report_format": "pptx",
  "max_documents_to_process": 5,
  "high_risk_only": false,
  "use_rag_context": true,
  "rag_top_k": 4
}
```

輸出 PPTX 預設會放在：

```text
data/reports/
```

如果是使用 `release/TaxMonitor-Setup.exe` 安裝後的桌面版，輸出會放在使用者資料夾：

```text
%LOCALAPPDATA%\TaxMonitor\data\reports\
```

執行過程若看到 `Ingest phase done: N documents`，代表搜尋與匯入已完成，接下來會進入 LLM 分析與 PPTX 產生。新版桌面版會繼續顯示 `Analyzing...`、`Generating pptx report...`、`Report ready...` 等狀態；若舊版畫面停在 ingest 階段但資料夾已有新 `.pptx`，通常是 UI 進度未更新，請換用新版安裝包。

若 `Search results` 有數字但 `Ingested` 是 0，通常代表網址找得到、但文件下載被擋住。常見原因是 Windows 環境變數裡有壞掉的 proxy，例如：

```powershell
HTTP_PROXY=http://127.0.0.1:9
HTTPS_PROXY=http://127.0.0.1:9
ALL_PROXY=http://127.0.0.1:9
```

新版 Tax Monitor 預設會忽略這類環境 proxy，讓公開網站可直接下載。若公司內網真的必須走 proxy，再手動設定：

```powershell
$env:TAX_MONITOR_TRUST_PROXY = "1"
```

桌面版 Summary 也會顯示前幾筆匯入錯誤，方便判斷是網站封鎖、PDF 下載失敗、網路逾時，還是 proxy 問題。

## 重新打包 Windows 安裝包

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\build_windows_installer.ps1
```

打包完成後檢查：

```text
release/TaxMonitor-Setup.exe
release/TaxMonitor-Windows-Installer.zip
release/SHA256SUMS.txt
```

## 清理規則

專案已更新 `.gitignore`，以下內容視為可重建或執行時產物：

- `build/`
- `dist/`
- `*.spec`
- `__pycache__/`
- `*.pyc`
- `tax_monitor_runtime.db`
- `*.db-journal`
- `data/reports/*`
- `data/uploads/*`
- `data/upload_files/*`
- `upload_files/*`

`release/` 建議只保留：

```text
TaxMonitor-Setup.exe
TaxMonitor-Windows-Installer.zip
SHA256SUMS.txt
```

日後可用清理腳本重新整理：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\clean_project.ps1 -CleanRuntimeData
```

## 常見問題

### 打開 Ollama API 出現 405

直接用瀏覽器開 `http://localhost:11434/api/generate` 看到 `405 method not allowed` 是正常的，因為這是 POST API，不是網頁。

### 桌面沒有捷徑

可直接執行：

```text
%LOCALAPPDATA%\Programs\TaxMonitor\TaxMonitor.exe
```

或重新執行最新版 `release/TaxMonitor-Setup.exe`。

### 搜尋結果太少

建議：

- `Source` 改成 `all` 或 `deep_research`
- `Max results` 提高到 50-100
- 開啟 `Use AI query expansion`
- 開啟 `Use RAG cross-document context`
- 到 `Assistant` 說明缺少哪些資料
- 補上英文公司名、股票代號、子公司名、國家、稅務議題英文詞

---

以下為舊版開發紀錄，僅供追溯。

# è·¨åœ‹æ³•ä»¤èˆ‡ç¨…å‹™é¢¨éšªç›£æ¸¬ç³»çµ±ï¼ˆTax Monitor APIï¼‰

é€™å€‹å°ˆæ¡ˆæ˜¯ä¸€å€‹ä»¥ FastAPI ç‚ºæ ¸å¿ƒçš„ç¨…å‹™ç ”ç©¶èˆ‡é¢¨éšªç›£æ¸¬åŽŸåž‹ï¼Œç›®æ¨™æ˜¯æŠŠï¼š

- ç¶²è·¯è³‡æ–™æœå°‹
- æ–‡ä»¶åŒ¯å…¥èˆ‡æ•´ç†
- é—œéµå­—è¨“ç·´
- é¢¨éšªåˆ†æž
- å ±å‘Šè¼¸å‡º

ä¸²æˆä¸€æ¢å¯ç›´æŽ¥åŸ·è¡Œçš„æµç¨‹ï¼Œä¹‹å¾Œå†æŽ¥åˆ° `n8n` åšå…¨è‡ªå‹•åŒ–ã€‚

ç›®å‰å°ˆæ¡ˆå·²ç¶“å¯ä»¥åšåˆ°ï¼š

1. å¾ž UI æˆ– API è¼¸å…¥æœå°‹é—œéµå­—
2. è‡ªå‹•æœå°‹ç¶²è·¯ä¸Šçš„ç›¸é—œè³‡æ–™
3. è‡ªå‹•åŒ¯å…¥æ–‡ä»¶åˆ°æœ¬åœ°è³‡æ–™åº«
4. é‡æ–°è¨“ç·´é—œéµå­—æ¨¡åž‹
5. å°æ–‡ä»¶åšé¢¨éšªåˆ†æž
6. ç›´æŽ¥è¼¸å‡º `.pptx` å ±å‘Š

---

## 1. ç›®å‰å°ˆæ¡ˆçš„å¯¦éš›æµç¨‹

### A. æ–‡ä»¶å±¤

- `POST /api/document/upload`
  - ä¸Šå‚³æœ¬æ©Ÿ `.txt` / `.pdf`
- `POST /api/document/ingest-url`
  - åŒ¯å…¥å–®ä¸€ç¶²é æˆ– PDF URL
- `POST /api/document/list`
  - åˆ—å‡ºå·²åŒ¯å…¥æ–‡ä»¶
- `GET /api/document/{doc_id}`
  - çœ‹å–®ç¯‡æ–‡ä»¶å…§å®¹
- `PATCH /api/document/{doc_id}`
  - æ›´æ–°æ–‡ä»¶ metadata

### B. æœå°‹å±¤

- `POST /api/document/search`
  - å–®ç´”æœå°‹
  - å¯é¸æ“‡è‡ªå‹•åŒ¯å…¥
  - å¯ç”¨æ‰‹å‹• URL æ¸…å–®

### C. åˆ†æžå±¤

- `POST /api/analysis/run`
  - å°å–®ç¯‡æ–‡ä»¶åšé¢¨éšªåˆ†æž
- `POST /api/analysis/report`
  - è¼¸å‡º `obsidian` / `slides` / `pptx`
- `POST /api/analysis/evaluate`
  - æ¯”è¼ƒ rule-based èˆ‡ LLM çµæžœ

### D. æ•´åˆæµç¨‹å±¤

- `POST /api/pipeline/search-train`
  - æœå°‹
  - è‡ªå‹•åŒ¯å…¥
  - é‡è¨“é—œéµå­—æ¨¡åž‹
  - å¯é¸æ“‡åŒæ­¥ç”¢å‡º PPTX
- `POST /api/pipeline/run`
  - æœå°‹
  - åŒ¯å…¥
  - åˆ†æž
  - è¼¸å‡ºå ±å‘Š
  - æ˜¯ç›®å‰æœ€æŽ¥è¿‘ã€Œä¸€æ¬¡ execute å®Œå…¨éƒ¨æµç¨‹ã€çš„ API

### E. ä½¿ç”¨è€…ä»‹é¢

- `GET /ui`
  - Workbench å‰ç«¯ä»‹é¢
  - é©åˆç›´æŽ¥è¼¸å…¥é—œéµå­—ã€è¨­å®šè³‡æ–™æœŸé–“ã€ç­†æ•¸ä¸Šé™ã€æœå°‹ä¾†æºã€AI æ“´å¯«ã€PPTX ç”¢å‡º

---

## 2. ç›®å‰æª”æ¡ˆçµæ§‹

```text
tax_monitor/
â”œâ”€ main.py
â”œâ”€ README.md
â”œâ”€ requirements.txt
â”œâ”€ desktop_app/
â”‚  â”œâ”€ app.py
â”‚  â”œâ”€ input_panel.py
â”‚  â”œâ”€ results_panel.py
â”‚  â””â”€ worker.py
â”œâ”€ examples/
â”‚  â”œâ”€ sample_tax_update.html
â”‚  â””â”€ run_pipeline_smoke_test.py
â”œâ”€ models/
â”‚  â””â”€ schemas.py
â”œâ”€ routers/
â”‚  â”œâ”€ analysis.py
â”‚  â”œâ”€ document.py
â”‚  â””â”€ pipeline.py
â”œâ”€ services/
â”‚  â”œâ”€ analysis_service.py
â”‚  â”œâ”€ document_parser_service.py
â”‚  â”œâ”€ document_service.py
â”‚  â”œâ”€ keyword_service.py
â”‚  â”œâ”€ language_service.py
â”‚  â”œâ”€ llm_service.py
â”‚  â”œâ”€ pipeline_service.py
â”‚  â”œâ”€ report_service.py
â”‚  â”œâ”€ search_service.py
â”‚  â”œâ”€ storage_service.py
â”‚  â””â”€ translator_service.py
â”œâ”€ ui/
â”‚  â”œâ”€ index.html
â”‚  â”œâ”€ app.js
â”‚  â””â”€ styles.css
â””â”€ data/
```

---

## 3. æ ¸å¿ƒæ¨¡çµ„èªªæ˜Ž

### `services/search_service.py`

è² è²¬æœå°‹è³‡æ–™ä¾†æºï¼Œç›®å‰å·²ç¶“ä¸æ˜¯åªç”¨å–®ä¸€ Google Newsã€‚

ç›®å‰æ”¯æ´ï¼š

- Google News RSS
- Google News å…¨çƒ locale èšåˆ
- Google News æ­·å²äº‹ä»¶è£œæœ `google_news_archive`
- Bing News RSS
- Bing ä¸€èˆ¬ç¶²é æœå°‹
- Bing PDF æœå°‹
- DuckDuckGo ä¸€èˆ¬ç¶²é æœå°‹
- DuckDuckGo PDF æœå°‹
- æŒ‡å®š `site:` å®˜æ–¹ / é¡§å• / ç¨…å‹™ç«™é»žçš„å®šå‘æœå°‹
- å·²çŸ¥å…¬å¸å®˜æ–¹ç¨®å­ä¾†æº `official_seed`
- è·¨åœ‹ç¨…å‹™åˆ¶åº¦åƒè€ƒä¾†æº `reference_seed`

å¦å¤–å·²åŠ å…¥ AI è¼”åŠ©ï¼š

- ä½¿ç”¨ Ollama ç”¢ç”Ÿèªžæ„ç›¸è¿‘çš„ query variants
- å˜—è©¦è£œå‡ºæ³•è¦ / ç”Ÿæ•ˆæ—¥ / ç”³å ±ç¾©å‹™ / draft / penalty ç­‰ç›¸é—œæŸ¥è©¢
- è£œå¼·å…¬å¸åˆ¥åèˆ‡ group / holding / subsidiary é¡žè©ž
- è£œå¼·ä¸­æ–‡é›†åœ˜é—œä¿‚è©žï¼Œä¾‹å¦‚æŽ§è‚¡ / é›†åœ˜ / å­å…¬å¸ / æ¯å…¬å¸ / é—œä¿‚ä¼æ¥­
- å„ªå…ˆè£œæœå…¬å¸å¹´å ±ã€è²¡å ±ã€å…¬é–‹è³‡è¨Šã€å­å…¬å¸ã€é—œä¿‚ä¼æ¥­ã€è½‰æŠ•è³‡èˆ‡é—œä¿‚äººäº¤æ˜“
- è‹¥ç³»çµ±å·²çŸ¥è©²å…¬å¸çš„å®˜æ–¹ IR / è²¡å ± / å…¬å¸æ²»ç†å…¥å£ï¼Œæœƒå…ˆæ”¾å…¥ `official_seed`ï¼Œé¿å…æœå°‹å¼•æ“Žæ²’æœ‰æ”¶éŒ„æˆ–çŸ­æœŸæ–°èžå¤ªå°‘æ™‚å®Œå…¨æŠ“ä¸åˆ°è³‡æ–™
- è‹¥ç³»çµ±åªçŸ¥é“å…¬å¸å®˜æ–¹ç¶²åŸŸï¼Œæœƒè£œå…¥ `official_domain_seed` ä½œç‚ºä¿åº•ï¼Œé¿å… DuckDuckGo / Bing çŸ­æš«ç„¡çµæžœæ™‚æ•´æ‰¹æœå°‹æ­¸é›¶
- è‹¥è£œå……éœ€æ±‚åŒ…å«è·¨åœ‹ç¨…å‹™ã€å…¨çƒæœ€ä½Žç¨…è² ã€Pillar Twoã€CFCã€å¸¸è¨­æ©Ÿæ§‹ã€æ‰£ç¹³ç¨…æˆ–é—œç¨…ï¼Œæœƒé¡å¤–è£œå…¥ `reference_seed`ï¼Œä¾‹å¦‚ OECDã€PwCã€Deloitte é¡žåˆ¶åº¦èªªæ˜Ž
- è‹¥è¼¸å…¥åŒ…å« `æŸ¥ç¨…`ã€`ç¨…å‹™èª¿æŸ¥`ã€`è£œç¨…`ã€`è£ç½°`ã€`tax audit`ã€`tax notice`ã€`tax row` ç­‰äº‹ä»¶åž‹é¢¨éšªè©žï¼Œæœƒå…ˆè£œæœæ–°èžäº‹ä»¶è„ˆçµ¡
- è‹¥åš´æ ¼æœŸé–“å…§æ²’æœ‰äº‹ä»¶æ–°èžï¼Œæœƒç”¨ `google_news_archive` è£œå°‘é‡æ­·å²äº‹ä»¶çµæžœï¼Œé¿å…é‡å¤§æ­·å²é¢¨éšªå®Œå…¨æ¶ˆå¤±
- å°å®˜æ–¹ç¨…å‹™ç«™ã€å››å¤§èˆ‡é¡§å•ç«™çµæžœåšåŠ æ¬Šé‡æŽ’
- å° PDFã€æ³•è¦åž‹ã€å®˜æ–¹åž‹ã€å…¬é–‹è³‡è¨Šåž‹çµæžœåšå„ªå…ˆæŽ’åº
- è®“æœå°‹æ›´æŽ¥è¿‘ã€ŒAI è‡ªå‹•ç ”ç©¶åŠ©æ‰‹ã€ï¼Œè€Œä¸æ˜¯åªåšåŽŸå­—é¢æ¯”å°

### `services/document_service.py`

è² è²¬ï¼š

- ä¸Šå‚³æ–‡ä»¶
- ç¶²å€å…§å®¹æŠ“å–
- PDF æ–‡å­—æŠ½å–
- è‡ªå‹•åˆ¤æ–·èªžè¨€
- å¯«å…¥ SQLite

ç¾åœ¨å¦‚æžœæœå°‹çµæžœæ˜¯ PDF ç¶²å€ï¼ŒåŒ¯å…¥æµç¨‹ä¹Ÿæœƒç›´æŽ¥ä¸‹è¼‰ PDF ä¸¦æŠ½æ–‡å­—ã€‚

### `services/keyword_service.py`

è² è²¬ï¼š

- å¾žè³‡æ–™åº«æ‰€æœ‰æ–‡ä»¶é‡æ–°è¨“ç·´ TF-IDF æ¨¡åž‹
- å°å–®ç¯‡æ–‡ä»¶æŠ½é—œéµå­—
- å»ºç«‹ä½¿ç”¨è€…é—œéµå­— profile

### `services/analysis_service.py`

è² è²¬ï¼š

- `translate_first`
- `analyze_first`
- é¢¨éšªç­‰ç´šåˆ¤æ–·
- é¢¨éšªæ¨™ç±¤æŠ½å–
- æ‘˜è¦èˆ‡è­‰æ“šå¥æ•´ç†

### `services/report_service.py`

è² è²¬ï¼š

- Obsidian æ ¼å¼è¼¸å‡º
- æŠ•å½±ç‰‡å¤§ç¶±è¼¸å‡º
- çœŸæ­£å»ºç«‹ `.pptx`

### `services/pipeline_service.py`

ç›®å‰æœ‰å…©ç¨®ä¸»æµç¨‹ï¼š

1. `run_pipeline()`
   - å®Œæ•´æµç¨‹
2. `search_ingest_and_train()`
   - å…ˆå¤§é‡é¤Šè³‡æ–™ã€é‡è¨“é—œéµå­—ã€å¿…è¦æ™‚åŒæ­¥å‡º PPTX

---

## 4. å®‰è£æ–¹å¼

### å»ºè­°ç’°å¢ƒ

- Windows 10/11
- Python 3.10+
- Ollama

### å®‰è£ä¾è³´

åœ¨å°ˆæ¡ˆæ ¹ç›®éŒ„åŸ·è¡Œï¼š

```powershell
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

ç›®å‰ `requirements.txt` åŒ…å«ï¼š

- `fastapi`
- `uvicorn`
- `python-multipart`
- `requests`
- `beautifulsoup4`
- `pypdf`
- `scikit-learn`
- `pandas`
- `python-pptx`

`python-pptx` å·²ç¶“åˆ—åœ¨ä¾è³´ä¸­ï¼Œæ‰€ä»¥åªè¦å®Œæ•´å®‰è£ `requirements.txt`ï¼ŒPPTX è¼¸å‡ºå°±èƒ½ç”¨ã€‚

---

## 5. å•Ÿå‹•æ–¹å¼

### æœ€ç©©å®šçš„å•Ÿå‹•æ–¹æ³•

```powershell
.\\.venv\\Scripts\\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8010
```

å•Ÿå‹•å¾Œå¯ç”¨ï¼š

- Swagger: `http://127.0.0.1:8010/docs`
- Health check: `http://127.0.0.1:8010/`
- UI: `http://127.0.0.1:8010/ui`

### ç‚ºä»€éº¼ README ä¸é è¨­ `--reload`

å› ç‚ºä½ ç¾åœ¨çš„ç’°å¢ƒæ˜¯ï¼š

- Windows
- OneDrive è·¯å¾‘

é€™ç¨®çµ„åˆä¸‹ï¼Œ`uvicorn --reload` å®¹æ˜“é‡åˆ°ï¼š

- `WinError 10013`
- socket æ¬Šé™å•é¡Œ
- ç›£çœ‹ç¨‹åºè¡çª

æ‰€ä»¥ç›®å‰æ–‡ä»¶é è¨­å…ˆç”¨ç©©å®šç‰ˆå•Ÿå‹•æ–¹å¼ï¼Œä¸å…ˆåŠ  `--reload`ã€‚

å¦‚æžœä½ æœ¬æ©Ÿå¾ˆç©©ï¼Œå†è‡ªå·±æ”¹æˆï¼š

```powershell
.\\.venv\\Scripts\\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8010
```

---

## 6. Ollama è¨­å®š

### å®‰è£å¾Œç¢ºèª Ollama å¯ç”¨

```powershell
ollama list
```

### è‹¥å°šæœªä¸‹è¼‰ Qwen

```powershell
ollama pull qwen3:8b
```

### æ¸¬è©¦æ¨¡åž‹

```powershell
ollama run qwen3:8b
```

### å°ˆæ¡ˆç›®å‰é è¨­æ¨¡åž‹

- provider: `ollama`
- model_name: `qwen3:8b`

Ollama é è¨­å‘¼å«ç«¯é»žï¼š

```text
http://localhost:11434/api/generate
```

---

## 7. Swagger æ¸¬è©¦é †åº

å¦‚æžœä½ æƒ³å…ˆä¸ç¢° n8nï¼Œæœ€ç°¡å–®çš„æ¸¬æ³•æ˜¯ç…§é€™å€‹é †åºã€‚

### æ–¹æ¡ˆ Aï¼šåˆ†æ®µæ¸¬

#### Step 1. å…ˆä¸Šå‚³æ¸¬è©¦æ–‡ä»¶

`POST /api/document/upload`

å¯ç›´æŽ¥ä¸Šå‚³ repo å…§å»ºçš„ï¼š

```text
demo_tax_update.txt
```

#### Step 2. åˆ†æžå–®ç¯‡æ–‡ä»¶

`POST /api/analysis/run`

ç¯„ä¾‹ï¼š

```json
{
  "doc_id": "ä¸Šä¸€æ­¥æ‹¿åˆ°çš„ doc_id",
  "mode": "translate_first",
  "target_language": "zh",
  "use_llm": true,
  "provider": "ollama",
  "model_name": "qwen3:8b",
  "user_prompt": "highlight filing risk and effective date"
}
```

#### Step 3. ç”¢å‡º PPTX

`POST /api/analysis/report`

ç¯„ä¾‹ï¼š

```json
{
  "doc_id": "ä¸Šä¸€æ­¥çš„ doc_id",
  "output_format": "pptx",
  "provider": "ollama",
  "model_name": "qwen3:8b",
  "target_language": "zh",
  "user_prompt": "prepare a management-ready risk summary"
}
```

å¦‚æžœæˆåŠŸï¼Œå›žå‚³æœƒæœ‰ï¼š

- `file_path`

é€šå¸¸æœƒå‡ºç¾åœ¨ï¼š

```text
data/reports/
```

---

### æ–¹æ¡ˆ Bï¼šç›´æŽ¥è·‘å®Œæ•´ç®¡ç·š

#### `POST /api/pipeline/run`

é€™æ˜¯ç›®å‰æœ€å®Œæ•´çš„ä¸€æ¬¡è·‘å®Œç‰ˆã€‚

å®ƒæœƒåšï¼š

1. æœå°‹
2. åŒ¯å…¥
3. åˆ†æž
4. å ±å‘Šè¼¸å‡º

ç¯„ä¾‹ï¼š

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

å¦‚æžœä½ è¦çš„æ˜¯ã€Œå¾žæœå°‹ä¸€è·¯åˆ°æœ€å¾Œç”Ÿæˆ PPTXã€ï¼Œé€™æ˜¯æœ€æŽ¥è¿‘éœ€æ±‚çš„å–®ä¸€ APIã€‚

---

### æ–¹æ¡ˆ Cï¼šå…ˆé¤Šè³‡æ–™æ± å†é‡è¨“é—œéµå­—

#### `POST /api/pipeline/search-train`

é€™æ¢æµç¨‹æ¯”è¼ƒé©åˆï¼š

- å…ˆå¤§é‡æœå°‹è³‡æ–™
- å…ˆåŒ¯å…¥æ–‡ä»¶
- å…ˆé‡è¨“é—œéµå­—
- è¦–éœ€è¦é †ä¾¿ç”¢ç”Ÿéƒ¨åˆ† PPTX

ç¯„ä¾‹ï¼š

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

## 8. UI ä½¿ç”¨æ–¹å¼

æ‰“é–‹ï¼š

```text
http://127.0.0.1:8010/ui
```

ç›®å‰ UI å¯ä»¥ç›´æŽ¥åšï¼š

1. è¼¸å…¥æœå°‹é—œéµå­—
2. è£œå……ç ”ç©¶éœ€æ±‚
3. è¨­å®šè³‡æ–™æœŸé–“
4. èª¿æ•´æœå°‹ç­†æ•¸ä¸Šé™
5. åˆ‡æ›è‡ªå‹• / æ‰‹å‹•æ¨¡å¼
6. åˆ‡æ›æœå°‹ä¾†æº
7. é¸æ“‡æ˜¯å¦ä¸é™åœ°å€
8. é¸æ“‡æ˜¯å¦å•Ÿç”¨ Ollama æ™ºæ…§æ“´å¯«
9. é¸æ“‡æ˜¯å¦åŒæ­¥ç”¢å‡º PPTX
10. é¡¯ç¤ºï¼š
   - æœå°‹çµæžœæ•¸
   - æˆåŠŸåŒ¯å…¥æ•¸
   - è¨“ç·´æ–‡ä»¶æ•¸
   - è©žå½™é‡
   - å·²ç”¢å‡º PPTX æ•¸
   - æ­£è¦åŒ–å¾Œå¯¦éš›é€å‡ºçš„é—œéµå­—
   - æœå°‹çµæžœçš„ç¶²åŸŸã€é¡žåž‹ã€åˆ†æ•¸èˆ‡æŽ’åºç†ç”±
   - æ¯ç¯‡æ–‡ä»¶çš„æŠ½å–é—œéµå­—
   - æ¯ç¯‡æ–‡ä»¶çš„é¢¨éšªç­‰ç´šèˆ‡é¢¨éšªæ¨™ç±¤
   - PPTX æª”æ¡ˆè·¯å¾‘

---

## 9. æœå°‹ä¾†æºèˆ‡ AI è‡ªå‹•ç ”ç©¶åŠ©æ‰‹

### æœå°‹ä¾†æºé¸é …

UI / API çš„ `source_name` ç›®å‰æœ‰å››ç¨®ä¸»è¦æ¨¡å¼ï¼š

#### `google_news_rss`

- æ¨™æº–æ–°èžæœå°‹

#### `google_news_rss_global`

- Google News å¤š locale èšåˆ
- é©åˆè·¨å€æ–°èžè§€å¯Ÿ

#### `bing_web`

- Bing ä¸€èˆ¬ç¶²é èˆ‡ PDF æœå°‹
- é©åˆå…¬å¸å¹´å ±ã€è²¡å ±ã€å…¬é–‹è³‡è¨Šã€æŠ•è³‡äººé—œä¿‚é ã€å­å…¬å¸æˆ–é—œä¿‚ä¼æ¥­è³‡æ–™
- å¦‚æžœ DuckDuckGo å°ä¸­æ–‡å…¬å¸åå›žå‚³å¤ªå°‘ï¼Œå¯ä»¥å–®ç¨åˆ‡é€™å€‹æ¨¡å¼æ¸¬

#### `all`

- å…¨ç¶²èšåˆæœå°‹
- æœƒå˜—è©¦æ•´åˆï¼š
  - Google News RSS
  - Bing News RSS
  - Bing ä¸€èˆ¬ç¶²é æœå°‹
  - Bing PDF æœå°‹
  - DuckDuckGo ç¶²é æœå°‹
  - DuckDuckGo PDF æœå°‹
  - `site:` å®˜æ–¹ / é¡§å• / ç¨…å‹™ç¶²ç«™å®šå‘æœå°‹
  - ç¨…å‹™äº‹ä»¶åž‹æŸ¥è©¢çš„ Google News æ­·å²è„ˆçµ¡è£œæœ

### ä¸é™åœ°å€

UI çš„ã€Œä¸é™åœ°å€ã€ç¾åœ¨åªæœƒï¼š

- æ¸…ç©º `country`
- è®“æœå°‹ä¸å†å¡åœ¨å–®ä¸€åœ‹å®¶æ¬„ä½

ä¸æœƒå†å·å·æŠŠä¾†æºå¼·åˆ¶æ”¹å›ž Google Newsï¼Œé€™é»žå·²ä¿®æ­£ã€‚

### AI è‡ªå‹•ç ”ç©¶åŠ©æ‰‹å¼·åŒ–ç‰ˆ

ç›®å‰å·²åŠ å¼·çš„é‚è¼¯ï¼š

1. ä½¿ç”¨ Ollama æ ¹æ“šé—œéµå­—èˆ‡è£œå……éœ€æ±‚ç”¢ç”Ÿèªžæ„æ“´å¯«æŸ¥è©¢
2. è£œå‡ºï¼š
   - ç¨…å‹™æ”¹é©
   - ç”³å ±ç¾©å‹™
   - ç”Ÿæ•ˆæ—¥
   - è‰æ¡ˆ
   - penalty / compliance / regulation é¡žè©ž
3. è£œå¼·å…¬å¸ä¸»é«”è©žï¼š
   - group
   - holding
   - subsidiary
   - corporation
4. å°å…¬å¸å¹´å ±ã€è²¡å ±ã€å…¬é–‹è³‡è¨Šã€å­å…¬å¸ã€é—œä¿‚ä¼æ¥­ã€è½‰æŠ•è³‡èˆ‡é—œä¿‚äººäº¤æ˜“å…ˆåšé«˜å‘½ä¸­çŽ‡æŸ¥è©¢
5. å°å®˜æ–¹ / é¡§å• / ç¨…å‹™ç«™é»žåšå®šå‘æœå°‹
6. å°å·²çŸ¥å…¬å¸å…ˆè£œå…¥å®˜æ–¹ IRã€è²¡å ±ã€å¹´å ±ã€å…¬å¸æ²»ç†èˆ‡é—œä¿‚äººäº¤æ˜“æ–‡ä»¶ä½œç‚º `official_seed`
7. å°å·²çŸ¥å…¬å¸å®˜æ–¹ç¶²åŸŸè£œå…¥ `official_domain_seed`
8. å°è·¨åœ‹ç¨…å‹™ç ”ç©¶è£œå…¥ OECDã€å››å¤§æˆ–å°ˆæ¥­ç¨…å‹™èªªæ˜Žä½œç‚º `reference_seed`
9. å°äº‹ä»¶åž‹ç¨…å‹™é¢¨éšªè£œå‡ºæŸ¥è©¢è©žï¼Œä¾‹å¦‚ `æŸ¥ç¨…`ã€`ç¨…å‹™èª¿æŸ¥`ã€`è£œç¨…`ã€`è™›å‡è¨ˆç¨…`ã€`tax audit`ã€`tax notice`ã€`tariff impact`
10. åŒæ™‚ç´å…¥ä¸€èˆ¬ç¶²é ã€PDFã€æ–°èžèˆ‡æ­·å²äº‹ä»¶è„ˆçµ¡
11. é‡å°å®˜æ–¹ç«™ã€å…¬é–‹è³‡è¨Šç«™ã€PDFã€ç¨…å‹™é—œéµèªžå¢ƒã€äº‹ä»¶åž‹æ–°èžèˆ‡å…¬å¸åˆ¥åçµæžœåšäºŒæ¬¡é‡æŽ’
12. æŠŠæ¯ç­†æœå°‹çµæžœçš„æŽ’åºç†ç”±å›žå‚³çµ¦å‰ç«¯ï¼Œæ–¹ä¾¿äººå·¥åˆ¤æ–·é€™ç­†è³‡æ–™ç‚ºä»€éº¼è¢«æ‹‰ä¸Šä¾†

### å…¬å¸èˆ‡å­å…¬å¸ç¨…å‹™é¢¨éšªæœå°‹æ¨¡å¼

å¦‚æžœè¼¸å…¥åƒï¼š

```text
ä»»ä¸€å…¬å¸åŠå…¶å­å…¬å¸ç¨…å‹™é¢¨éšª
```

ç³»çµ±ç¾åœ¨ä¸æœƒåªæ‹¿åŽŸå¥ç¡¬æœï¼Œè€Œæœƒè‡ªå‹•æ‹†æˆå…¬å¸ç ”ç©¶ä»»å‹™ï¼š

- å…¬å¸ä¸»é«”ï¼š
  - åŽŸå§‹å…¬å¸åç¨±
  - åŽ»æŽ‰ã€Œç¨…å‹™é¢¨éšªã€å­å…¬å¸ã€é›†åœ˜ã€æ¯å…¬å¸ã€å¾Œçš„å…¬å¸åç¨±
  - å¸¸è¦‹æ³•äººå¾Œç¶´ï¼Œä¾‹å¦‚ `å…¬å¸`ã€`è‚¡ä»½æœ‰é™å…¬å¸`ã€`é›†åœ˜`
  - è‹±æ–‡å…¬å¸å¾Œç¶´ï¼Œä¾‹å¦‚ `Inc`ã€`Corporation`ã€`Group`ã€`Holdings`
  - è‹¥æ˜¯å·²çŸ¥å…¬å¸ï¼Œæœƒé¡å¤–è£œå¸¸è¦‹åˆ¥åï¼Œä¾‹å¦‚ `ASUS` / `ASUSTeK`
- ç¨…å‹™ / é¢¨éšªä¸»é¡Œï¼š
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
  - `å¹´å ±`
  - `è²¡å ±`
  - `ç¨…å‹™æ²»ç†`
  - `æ‰€å¾—ç¨…`
  - `ç§»è½‰è¨‚åƒ¹`
  - `é—œä¿‚äººäº¤æ˜“`
  - `è·¨åœ‹ç¨…å‹™`
  - `åœ‹éš›ç§Ÿç¨…`
  - `å…¨çƒæœ€ä½Žç¨…è² `
  - `æ”¯æŸ±äºŒ`
  - `å¸¸è¨­æ©Ÿæ§‹`
  - `æ‰£ç¹³ç¨…`
  - `é—œç¨…`
  - `æµ·é—œä¼°åƒ¹`
  - `å—æŽ§å¤–åœ‹å…¬å¸`
  - `å­å…¬å¸`
  - `é—œä¿‚ä¼æ¥­`
  - `é›†åœ˜æž¶æ§‹`
  - `åˆä½µè²¡å‹™å ±è¡¨`
  - `è½‰æŠ•è³‡`
  - `æŸ¥ç¨…`
  - `ç¨…å‹™èª¿æŸ¥`
  - `ç¨…å‹™ç¨½æŸ¥`
  - `è£œç¨…`
  - `ç¨…å‹™è£ç½°`
  - `tax audit`
  - `tax investigation`
  - `tax notice`
  - `tax row`
  - `customs investigation`
  - `tariff impact`

åŒæ™‚æœƒè£œæœï¼š

- å…¬å¸å®˜ç¶²èˆ‡ ESG / IR æ–‡ä»¶
- TWSE / MOPS å…¬é–‹è³‡è¨Š
- å¹´å ±ã€è²¡å ±ã€æ°¸çºŒå ±å‘Š PDF
- å­å…¬å¸ã€é—œä¿‚ä¼æ¥­ã€è½‰æŠ•è³‡èˆ‡é—œä¿‚äººäº¤æ˜“è³‡æ–™
- é¡§å• / ç¨…å‹™ / å®˜æ–¹ç«™é»ž
- å·²çŸ¥å…¬å¸çš„å®˜æ–¹ç¨®å­è³‡æ–™ï¼Œä¾‹å¦‚è¯ç¢©ã€å°ç©é›»ã€é´»æµ· / Foxconnã€Toyota çš„ IRã€å¹´å ±ã€è²¡å ±ã€ç¨…å‹™æ”¿ç­–ã€é—œä¿‚äººäº¤æ˜“æˆ–æ°¸çºŒè³‡è¨Š
- å·²çŸ¥å…¬å¸å®˜æ–¹ç¶²åŸŸä¿åº•è³‡æ–™ï¼Œä¾‹å¦‚ `asus.com`ã€`tsmc.com`ã€`honhai.com`ã€`foxconn.com`ã€`global.toyota`
- è·¨åœ‹ç¨…å‹™åˆ¶åº¦è³‡æ–™ï¼Œä¾‹å¦‚ OECD BEPS / Pillar Twoã€PwC CFC / å…¨çƒæœ€ä½Žç¨…è² ã€Deloitte è·¨åœ‹ç¨…å‹™æ²»ç†
- Google News / Bing News / Bing Web / DuckDuckGo ä¸€èˆ¬ç¶²é èˆ‡ PDF
- ç¨…å‹™äº‹ä»¶åž‹æ–°èžï¼Œä¾‹å¦‚æŸ¥ç¨…ã€ç¨…å‹™èª¿æŸ¥ã€è£œç¨…ã€è£ç½°ã€é—œç¨…è¡æ“Šã€åå‚¾éŠ·ç¨…èˆ‡æµ·é—œç¨½æŸ¥

äº‹ä»¶åž‹æœå°‹æœ‰ä¸€å€‹ç‰¹åˆ¥è¦å‰‡ï¼šå¦‚æžœä½ é¸ `3m` æˆ– `1y`ï¼Œæ–°èžæœå°‹æœƒå…ˆå°Šé‡é€™å€‹æœŸé–“ï¼›ä½†å¾ˆå¤šé‡å¤§ç¨…å‹™äº‹ä»¶ä¸æ˜¯æœ€è¿‘æ‰ç™¼ç”Ÿï¼Œç³»çµ±æœƒåœ¨çµæžœä¸è¶³æ™‚è£œå°‘é‡ `google_news_archive` æ­·å²äº‹ä»¶ç·šç´¢ã€‚é€™äº›çµæžœæœƒé¡¯ç¤ºç‚ºæ­·å²è„ˆçµ¡ï¼Œä¸ä»£è¡¨å®ƒç™¼ç”Ÿåœ¨ä½ é¸çš„æœŸé–“å…§ï¼Œè€Œæ˜¯æé†’åˆ†æžæ™‚ä¸å¯å¿½ç•¥çš„æ—¢æœ‰é¢¨éšªã€‚

`all` æ¨¡å¼ç›®å‰æœƒå„ªå…ˆæŸ¥ä¸€èˆ¬ç¶²é ã€PDF èˆ‡å®˜æ–¹å®šå‘æœå°‹ï¼Œå†ç”¨å°‘é‡æ–°èžä¾†æºè£œå……ã€‚é€™æ¨£æ¯”ä¸€é–‹å§‹å…ˆæ‰“å¤§é‡ Google News locale æ›´å¿«ï¼Œä¹Ÿæ¯”è¼ƒé©åˆå…¬å¸å¹´å ±ã€ç¨…å‹™æ”¿ç­–ã€å­å…¬å¸èˆ‡é—œä¿‚äººäº¤æ˜“ç ”ç©¶ã€‚

é€™æ˜¯ç‚ºäº†è§£æ±ºä¸€å€‹å¸¸è¦‹å•é¡Œï¼šç¶²è·¯è³‡æ–™ä¸ä¸€å®šæœƒç›´æŽ¥ä½¿ç”¨ã€Œç¨…å‹™é¢¨éšªã€é€™å››å€‹å­—ï¼Œä¹Ÿä¸ä¸€å®šæœƒæŠŠæ¯å…¬å¸å’Œå­å…¬å¸å¯«åœ¨åŒä¸€ç¯‡æ–°èžè£¡ï¼›çœŸæ­£æœ‰ç”¨çš„ç·šç´¢å¸¸å‡ºç¾åœ¨ã€Œå¹´å ±ã€æ‰€å¾—ç¨…ã€æœ‰æ•ˆç¨…çŽ‡ã€é—œä¿‚äººäº¤æ˜“ã€ç§»è½‰è¨‚åƒ¹ã€å­å…¬å¸æ¸…å–®ã€è½‰æŠ•è³‡ã€åˆä½µè²¡å‹™å ±è¡¨ã€æ°¸çºŒå ±å‘Šã€ç­‰æ®µè½è£¡ã€‚

å»ºè­°å…¬å¸ç ”ç©¶æŸ¥è©¢ï¼š

```json
{
  "keywords": ["è¯ç¢©åŠå…¶å­å…¬å¸è·¨åœ‹ç¨…å‹™é¢¨éšª"],
  "user_prompt": "åŒ…å«è¯ç¢©æ——ä¸‹æ‰€æœ‰å­å…¬å¸ã€è·¨åœ‹ç¨…å‹™é¢¨éšªã€å¹´å ±ã€è²¡å ±ã€æ‰€å¾—ç¨…ã€ç§»è½‰è¨‚åƒ¹ã€é—œä¿‚äººäº¤æ˜“ã€é—œç¨…ã€å…¨çƒæœ€ä½Žç¨…è² ã€Pillar Twoã€å¸¸è¨­æ©Ÿæ§‹ã€æ‰£ç¹³ç¨…ã€ä¾›æ‡‰éˆèˆ‡ç‡Ÿé‹æ“šé»ž",
  "date_range": "1y",
  "max_results": 50,
  "source_name": "all",
  "use_ai_query_expansion": true,
  "report_format": "pptx"
}
```

ç›®å‰å·²ç”¨é€™çµ„æ¢ä»¶é©—è­‰éŽå®Œæ•´æµç¨‹ï¼Œå¯å¾žæœå°‹ä¸€è·¯è·‘åˆ° PPTXã€‚æ¸¬è©¦çµæžœåŒ…å«ï¼š

- è¯ç¢©å®˜æ–¹ 2025 Q2 åˆä½µè²¡å ±
- è¯ç¢©å®˜æ–¹ 2024 å¹´å ±
- è¯ç¢© IR è²¡å ±å…¥å£
- è¯ç¢©é—œä¿‚äººäº¤æ˜“ç®¡ç†è¾¦æ³•
- PwC CFC / å…¨çƒæœ€ä½Žç¨…è² åˆ¶åº¦èªªæ˜Ž

ä¸Šè¿°æ–‡ä»¶çš†å¯è¢«åŒ¯å…¥ã€åˆ†æžï¼Œä¸¦è¼¸å‡ºåˆ° `data/reports/`ã€‚

å¦‚æžœæŸå®¶å…¬å¸ç”¨ä¸­æ–‡åç¨±æœå°‹å¤ªå°‘ï¼Œå¯ä»¥æŠŠå¸¸è¦‹è‹±æ–‡åç¨±ä¹Ÿæ”¾é€²é—œéµå­—æˆ–è£œå……éœ€æ±‚ï¼Œä¾‹å¦‚ï¼š

```json
{
  "keywords": ["å°ç©é›» TSMC å­å…¬å¸ ç¨…å‹™é¢¨éšª"],
  "user_prompt": "Taiwan Semiconductor Manufacturing annual report subsidiaries income tax transfer pricing related party transactions",
  "date_range": "3m",
  "max_results": 50,
  "source_name": "all",
  "use_ai_query_expansion": true,
  "report_format": "pptx"
}
```

å¦‚æžœä½ è¦æŸ¥çš„æ˜¯ã€Œå…¬å¸æ˜¯å¦æ›¾è¢«æŸ¥ç¨…ã€è£ç½°ã€è£œç¨…ã€ç¨…å‹™èª¿æŸ¥ã€ï¼Œå»ºè­°è£œå……éœ€æ±‚ç›´æŽ¥å¯«äº‹ä»¶è©žï¼Œç³»çµ±æœƒè‡ªå‹•æ“´æˆå¤šçµ„å…¬å¸åˆ¥åèˆ‡äº‹ä»¶æŸ¥è©¢ï¼š

```json
{
  "keywords": ["é´»æµ·æŸ¥ç¨…é¢¨éšª"],
  "user_prompt": "åŒ…å«å¯Œå£«åº·ã€é´»æµ·ã€Hon Haiã€Foxconnï¼Œæœå°‹ç¨…å‹™åŠç”¨åœ°èª¿æŸ¥ã€æŸ¥ç¨…çµæžœã€è™›å‡è¨ˆç¨…ã€è£œç¨…ã€ç¨…å‹™è£ç½°ã€å­å…¬å¸å½±éŸ¿",
  "date_range": "1y",
  "max_results": 30,
  "source_name": "all",
  "use_ai_query_expansion": true,
  "report_format": "pptx"
}
```

é€™é¡žæŸ¥è©¢è‹¥è¿‘æœŸæ²’æœ‰æ–°æ–°èžï¼Œä»å¯èƒ½è£œå‡ºæ­·å²äº‹ä»¶è„ˆçµ¡ï¼Œä¾‹å¦‚ `google_news_archive` ä¾†æºçš„å¯Œå£«åº·æŸ¥ç¨…çµæžœã€è£œç¨…å‚³èžæ¾„æ¸…ã€ç¨…å‹™èª¿æŸ¥å ±å°Žç­‰ã€‚

æ‰€ä»¥ç¾åœ¨çš„æœå°‹å·²ç¶“æ¯”ä¸€é–‹å§‹æ›´æŽ¥è¿‘ï¼š

- AI å¹«ä½ ç†è§£ä¸»é¡Œ
- AI å¹«ä½ æ”¾å¤§æœç´¢é¢ï¼ŒåŒ…å«æ¯å…¬å¸ã€å­å…¬å¸ã€é—œä¿‚ä¼æ¥­èˆ‡å…¬é–‹è³‡è¨Š
- å†æŠŠçµæžœé¤µé€²åˆ†æžèˆ‡å ±å‘Šæµç¨‹

---

## 10. n8n ç›®å‰æ€Žéº¼æŽ¥

repo å…§å·²æœ‰ï¼š

```text
n8n_tax_monitor_workflow.json
n8n_tax_monitor_obsidian_workflow.json
n8n_tax_monitor_alert_workflow.json
n8n_tax_monitor_gmail_alert_workflow.json
```

ä½†å¦‚æžœä½ ç¾åœ¨è¦å…ˆç¢ºèª FastAPI æœ¬èº«èƒ½è·‘ï¼Œå»ºè­°å…ˆå®Œæˆï¼š

1. `document/upload`
2. `analysis/run`
3. `analysis/report`
4. `pipeline/run`

ç­‰é€™å››æ­¥éƒ½ç©©ï¼Œå†å›žé ­æŽ¥ n8nã€‚

---

## 11. æˆ‘å»ºè­°ä½ ç¾åœ¨çš„å¯¦éš›æ“ä½œé †åº

### ç¬¬ä¸€éšŽæ®µï¼šç¢ºèªæœ¬æ©Ÿå®‰è£æ­£å¸¸

1. `python -m pip install -r requirements.txt`
2. `.\\.venv\\Scripts\\Activate.ps1`
3. `ollama pull qwen3:8b`
4. `.\\.venv\\Scripts\\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8010`
5. æ‰“é–‹ `/docs`
6. æ‰“é–‹ `/ui`

### ç¬¬äºŒéšŽæ®µï¼šç¢ºèªåˆ†æžåˆ° PPTX æ­£å¸¸

1. ä¸Šå‚³ `demo_tax_update.txt`
2. åŸ·è¡Œ `/api/analysis/run`
3. åŸ·è¡Œ `/api/analysis/report`
4. ç¢ºèª `data/reports/*.pptx`

### ç¬¬ä¸‰éšŽæ®µï¼šç¢ºèªæœå°‹ç®¡ç·šæ­£å¸¸

1. åœ¨ `/ui` è¼¸å…¥é—œéµå­—
2. `source_name` é¸ `all`
3. å‹¾é¸ `ç”¨ Ollama æ™ºæ…§æ“´å¯«æœå°‹æ„åœ–`
4. è¨­è¼ƒå¤§çš„ `max_results`
5. çœ‹æ˜¯å¦æœ‰ï¼š
   - åŒ¯å…¥æ–‡ä»¶
   - é—œéµå­—
   - é¢¨éšªç­‰ç´š
   - PPTX è·¯å¾‘

### ç¬¬å››éšŽæ®µï¼šæœ€å¾Œå†æŽ¥ n8n

---

## 12. ä¸€éµé©—è­‰ç¯„ä¾‹

å¦‚æžœä½ æƒ³ç¢ºèªã€Œæœå°‹çµæžœ â†’ åŒ¯å…¥æ–‡ä»¶ â†’ åˆ†æž â†’ ç”¢å‡º PPTXã€æ•´æ¢æµç¨‹æ˜¯å¦æ­£å¸¸ï¼Œå¯ä»¥ç›´æŽ¥è·‘ repo å…§å»ºçš„æœ¬æ©Ÿ smoke testã€‚

```powershell
.\\.venv\\Scripts\\python.exe -B examples\\run_pipeline_smoke_test.py
```

é€™æ”¯è…³æœ¬æœƒè‡ªå‹•ï¼š

1. å•Ÿå‹•ä¸€å€‹æœ¬æ©Ÿæš«æ™‚ HTTP server
2. æŠŠ `examples/sample_tax_update.html` ç•¶æˆæœå°‹çµæžœç¶²å€
3. å‘¼å« `PipelineService.run_pipeline()`
4. åŒ¯å…¥æ–‡ä»¶
5. åˆ†æžç¨…å‹™é¢¨éšª
6. ç”¢ç”Ÿ `.pptx`

æˆåŠŸæ™‚æœƒçœ‹åˆ°é¡žä¼¼ï¼š

```text
searched_result_count: 1
ingested_result_count: 1
processed_count: 1
report_file_path: ...\\data\\reports\\Sample 2026 Cross-Border Tax Filing Update.pptx
```

æœ¬æ©Ÿå·²é©—è­‰å¯ç”¢ç”Ÿï¼š

```text
data/reports/Sample 2026 Cross-Border Tax Filing Update.pptx
```

é€™å€‹ smoke test ä¸ä¾è³´å¤–éƒ¨ç¶²è·¯ï¼Œæ‰€ä»¥å¾ˆé©åˆç”¨ä¾†ç¢ºèªæ ¸å¿ƒç¨‹å¼æ²’æœ‰å£žã€‚

---

## 13. å·²çŸ¥é™åˆ¶

ç›®å‰é€™ç‰ˆå·²ç¶“èƒ½è·‘ï¼Œä½†é‚„ä¸æ˜¯å®Œæ•´ä¼æ¥­ç´šçˆ¬ç ”å¹³å°ã€‚

ç›®å‰é™åˆ¶åŒ…æ‹¬ï¼š

1. å¤–éƒ¨æœå°‹çµæžœä»å—æœå°‹å¼•æ“Žèˆ‡ç¶²ç«™å¯è¦‹åº¦å½±éŸ¿
2. DuckDuckGo HTML æœå°‹æœ‰æ™‚æœƒå›ž 403ï¼Œç¾åœ¨ç¨‹å¼æœƒè·³éŽå¤±æ•—æŸ¥è©¢ä¸¦ç¹¼çºŒè™•ç†å…¶ä»–ä¾†æº
3. Google News RSS æœ‰æ™‚æœƒå›žå‚³ Google News ä¸­ä»‹é ï¼Œæ¨™é¡Œå¯èƒ½é¡¯ç¤ºç‚º `Google News`
4. é‚„ä¸æ˜¯å®Œæ•´ agent å¼è‡ªä¸»ç€è¦½å™¨
5. å°šæœªåšå¤šæ­¥æ·±åº¦ç¶²é è¿½è¹¤èˆ‡ sitemap crawler
6. å°šæœªæŽ¥æ­£å¼å‘é‡è³‡æ–™åº«
7. å°šæœªåšå¤šè¼ªç ”ç©¶è¨˜æ†¶èˆ‡ä»»å‹™ç·¨æŽ’
8. ç›®å‰ SQLite é©åˆ PoCï¼Œä¸æ˜¯æœ€çµ‚æ­£å¼ç‰ˆè³‡æ–™åº«

---

## 14. é€™ç‰ˆæœ€é‡è¦çš„çµè«–

æ˜¯çš„ï¼Œç¾åœ¨é€™å€‹å°ˆæ¡ˆå·²ç¶“å¯ä»¥ï¼š

1. æŒ‰ README å®‰è£
2. å•Ÿå‹• FastAPI
3. å¾ž UI æˆ– Swagger åŸ·è¡Œæµç¨‹
4. å¾žæœå°‹ä¸€è·¯èµ°åˆ°åˆ†æžèˆ‡ PPTX ç”¢å‡º

è€Œä¸”ç¾åœ¨æœå°‹ç«¯ä¹Ÿå·²ç¶“ä¸å†åªå¡åœ¨å–®ä¸€ Google News æ€è·¯ï¼Œè€Œæ˜¯å¾€ã€ŒAI è‡ªå‹•ç ”ç©¶åŠ©æ‰‹ã€æ–¹å‘è£œå¼·äº†ã€‚

æŽ¥ä¸‹ä¾†æœ€å€¼å¾—åšçš„ä¸‹ä¸€æ­¥æœƒæ˜¯ï¼š

- æ­£å¼åŠ å…¥å¤šç«™é»ž crawler
- åŠ å…¥ç ”ç©¶ä»»å‹™è¨˜æ†¶
- æŠŠæœå°‹çµæžœåšæ›´å¼·çš„ç›¸é—œæ€§é‡æŽ’
- æŽ¥å›ž `n8n` åšå®šæ™‚è‡ªå‹•ç ”ç©¶èˆ‡é€šçŸ¥

---

## 15. ä¾æœ€æ–°åé¥‹æ–°å¢žçš„æ”¹è‰¯æ–¹å‘

### Tkinter æ¡Œé¢å‰ç«¯

ç›®å‰å·²æ–°å¢ž `desktop_app/`ï¼Œä½œç‚ºä¸ä¾è³´ç€è¦½å™¨çš„æ¡Œé¢ç‰ˆæ“ä½œä»‹é¢ã€‚

å•Ÿå‹•æ–¹å¼ï¼š

```powershell
.\\.venv\\Scripts\\python.exe -m desktop_app
```

æ¡Œé¢ç‰ˆç›®å‰åˆ†æˆå¤šå€‹æ¨¡çµ„ï¼š

- `desktop_app/app.py`
  - ä¸»è¦–çª—
- `desktop_app/input_panel.py`
  - æœå°‹èˆ‡ pipeline åƒæ•¸è¼¸å…¥
- `desktop_app/results_panel.py`
  - æ‘˜è¦ã€æœå°‹çµæžœã€åŒ¯å…¥æ–‡ä»¶ã€PPTX çµæžœé¡¯ç¤º
- `desktop_app/worker.py`
  - èƒŒæ™¯åŸ·è¡Œ pipelineï¼Œé¿å…è¦–çª—å¡ä½

æ¡Œé¢ç‰ˆæœƒç›´æŽ¥å‘¼å« `PipelineService`ï¼Œæ‰€ä»¥ä¸éœ€è¦å…ˆå•Ÿå‹• FastAPIã€‚

### MinerU æ–‡ä»¶è§£æž

ç›®å‰å·²æ–°å¢ž `services/document_parser_service.py`ã€‚

æ–‡ä»¶è§£æžæµç¨‹ç¾åœ¨æœƒï¼š

1. å„ªå…ˆå˜—è©¦å‘¼å«æœ¬æ©Ÿ `mineru` CLI
2. è‹¥ MinerU ä¸å­˜åœ¨æˆ–è§£æžå¤±æ•—ï¼ŒPDF æœƒ fallback åˆ° `pypdf`
3. ä¸€èˆ¬æ–‡å­—æª”æœƒä»¥ UTF-8 fallback è®€å–

MinerU å®‰è£å¯åƒè€ƒå®˜æ–¹ repoï¼š

```text
https://github.com/opendatalab/mineru
```

æœ¬å°ˆæ¡ˆæŽ¡å–ã€Œå¯é¸å®‰è£ã€æ–¹å¼ï¼ŒåŽŸå› æ˜¯ MinerU ä¾è³´è¼ƒé‡ï¼›æœªå®‰è£æ™‚ç³»çµ±ä»å¯ä½¿ç”¨æ—¢æœ‰ fallbackã€‚

### Web / PDF æœå°‹æ¨¡å¼

ç¾åœ¨ `source_name` å»ºè­°ä¾éœ€æ±‚é¸ï¼š

```text
duckduckgo
bing_web
all
```

å·®ç•°å¦‚ä¸‹ï¼š

- `duckduckgo`
  - DuckDuckGo ä¸€èˆ¬ç¶²é æœå°‹
  - DuckDuckGo PDF æœå°‹
  - å®˜æ–¹ / é¡§å• / ç¨…å‹™ç¶²ç«™å®šå‘ query
- `bing_web`
  - Bing ä¸€èˆ¬ç¶²é æœå°‹
  - Bing PDF æœå°‹
  - å°å…¬å¸å¹´å ±ã€è²¡å ±ã€IRã€å…¬é–‹è³‡è¨Šé æœ‰æ™‚æ¯” DuckDuckGo æ›´å®¹æ˜“å‘½ä¸­
- `all`
  - Google News / Bing News / Bing Web / DuckDuckGo èšåˆ
  - å…¬å¸èˆ‡å­å…¬å¸ç¨…å‹™é¢¨éšªç ”ç©¶å»ºè­°å„ªå…ˆç”¨é€™å€‹

Tkinter æ¡Œé¢ç‰ˆç›®å‰é è¨­å°±æ˜¯ `all`ã€‚

### PPTX æ ¼å¼æ”¹è‰¯

ç›®å‰ PPTX å·²ä¾ç…§ä½ æä¾›çš„ Colab ç°¡å ±æ¨¡æ¿é‚è¼¯ï¼Œæ”¹æˆæœ¬åœ° `python-pptx` ç‰ˆæœ¬ï¼Œä¸éœ€è¦å†é€² Google Colab æ‰èƒ½è¼¸å‡ºã€‚

å·²æ•´åˆçš„ç‰ˆåž‹é‚è¼¯ï¼š

- 10 x 5.625 inch çš„ 16:9 æŠ•å½±ç‰‡æ¯”ä¾‹
- å°é¢é ä½¿ç”¨ä¸­å¤®åœ“è§’ä¸»é¡Œè‰²æ¨™é¡Œæ¡†
- å…§å®¹é ä½¿ç”¨çµ±ä¸€é ‚éƒ¨æ¨™é¡Œåˆ—
- é å°¾åŒ…å«æ—¥æœŸã€ä¸­å¤®é ç¢¼ã€å³ä¸‹ç³»çµ±åç¨±
- é è¨­ä¸»é¡Œè‰²ç‚ºæ·±è— `#2C3E6B`
- ä¸­æ–‡å­—åž‹é è¨­ä½¿ç”¨ `Taipei Sans TC Beta`
- è‹±æ–‡å­—åž‹é è¨­ä½¿ç”¨ `Times New Roman`
- æ¯å€‹åˆ†æžå€å¡Šæœƒç¨ç«‹æˆé 
- ç¬¬ä¸€å¼µå…§å®¹é æœƒè‡ªå‹•ç”¢ç”Ÿ `Executive Snapshot`

ç›®å‰æœ¬åœ°ç‰ˆæ²’æœ‰æ¬å…¥ Colab çš„äº’å‹•å¼ `ipywidgets` ç·¨è¼¯å™¨èˆ‡ Gemini åœ–ç‰‡ç”ŸæˆåŠŸèƒ½ï¼Œå› ç‚ºæœ¬å°ˆæ¡ˆä¸»æµç¨‹æ˜¯è‡ªå‹•æœå°‹ã€åŒ¯å…¥ã€åˆ†æžã€è¼¸å‡ºå ±å‘Šï¼›ç°¡å ±å…§å®¹æœƒç›´æŽ¥ç”±åˆ†æžçµæžœèˆ‡ Ollama / API æ¨¡åž‹ç”¢ç”Ÿã€‚

### ç¾åœ¨å»ºè­°çš„å®Œæ•´ä½¿ç”¨æµç¨‹

#### æ–¹æ¡ˆ 1ï¼šæ¡Œé¢ç‰ˆæ“ä½œ

```powershell
.\\.venv\\Scripts\\python.exe -m desktop_app
```

æ¡Œé¢ç‰ˆé©åˆä¸€èˆ¬ä½¿ç”¨è€…ï¼š

1. è¼¸å…¥æœå°‹é—œéµå­—
2. è¼¸å…¥è£œå……ç ”ç©¶éœ€æ±‚
3. è¨­å®šè³‡æ–™æœŸé–“èˆ‡è³‡æ–™ç­†æ•¸ä¸Šé™
4. é¸æ“‡ `all`ï¼Œå¦‚æžœè¦å–®ç¨æ¸¬ç¶²é ä¾†æºå†åˆ‡ `duckduckgo` æˆ– `bing_web`
5. å‹¾é¸ AI æ™ºæ…§æ“´å¯«
6. å‹¾é¸ç”¢ç”Ÿ PPTX
7. æŒ‰ä¸‹åŸ·è¡Œ
8. åœ¨çµæžœé æŸ¥çœ‹ï¼š
   - æœå°‹çµæžœ
   - æˆåŠŸåŒ¯å…¥æ–‡ä»¶
   - é—œéµå­—è¨“ç·´çµæžœ
   - é¢¨éšªåˆ†æžçµæžœ
   - PPTX æª”æ¡ˆè·¯å¾‘

#### æ–¹æ¡ˆ 2ï¼šFastAPI Swagger ä¸€æ¬¡è·‘å®Œ

å•Ÿå‹•ï¼š

```powershell
.\\.venv\\Scripts\\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8010
```

æ‰“é–‹ï¼š

```text
http://127.0.0.1:8010/docs
```

ä½¿ç”¨ï¼š

```text
POST /api/pipeline/run
```

å»ºè­°æ¸¬è©¦ JSONï¼š

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

æˆåŠŸå¾Œçœ‹å›žå‚³çš„ï¼š

- `results`
- `ingested_documents`
- `analyses`
- `reports`
- `pptx_files`

ç”¢å‡ºçš„ç°¡å ±æœƒåœ¨ï¼š

```text
data/reports/
```

### AI è‡ªå‹•ç ”ç©¶åŠ©æ‰‹åŠ å¼·æ–¹å‘

ç›®å‰å·²ç¶“åŠ å¼·åˆ°ï¼š

1. ç”¨ Ollama ä¾ç…§ä½¿ç”¨è€…éœ€æ±‚æ“´å¯«æœå°‹ query
2. ç”¨ Google Newsã€Google News æ­·å²äº‹ä»¶è£œæœã€Bing Newsã€Bing Webã€DuckDuckGo æœå°‹ä¸€èˆ¬ç¶²é èˆ‡ PDF
3. å°å…¬å¸å¹´å ±ã€è²¡å ±ã€å…¬é–‹è³‡è¨Šã€å­å…¬å¸ã€é—œä¿‚ä¼æ¥­ã€è½‰æŠ•è³‡èˆ‡é—œä¿‚äººäº¤æ˜“åšå„ªå…ˆ query
4. ç”¨å®˜æ–¹ / é¡§å• / ç¨…å‹™ç¶²ç«™å®šå‘ query è£œå¼·ä¾†æºå¤šæ¨£æ€§
5. å°å·²çŸ¥å…¬å¸è£œå…¥å®˜æ–¹ IRã€å¹´å ±ã€è²¡å ±ã€å…¬å¸æ²»ç†èˆ‡é—œä¿‚äººäº¤æ˜“æ–‡ä»¶ä½œç‚º `official_seed`
6. å°å·²çŸ¥å…¬å¸è£œå…¥å®˜æ–¹ç¶²åŸŸä¿åº•è³‡æ–™ä½œç‚º `official_domain_seed`
7. å°è·¨åœ‹ç¨…å‹™è£œå…¥ OECDã€PwCã€Deloitte ç­‰åˆ¶åº¦åž‹åƒè€ƒä½œç‚º `reference_seed`
8. å°æŸ¥ç¨…ã€ç¨…å‹™èª¿æŸ¥ã€è£œç¨…ã€è£ç½°ã€é—œç¨…è¡æ“Šç­‰äº‹ä»¶åž‹é¢¨éšªåšå°ˆé–€ query expansion
9. åŒ¯å…¥ç¶²é æˆ– PDF å…§å®¹
10. è‹¥å®‰è£ MinerUï¼Œå„ªå…ˆç”¨ MinerU åšæ–‡ä»¶è§£æž
11. å°åŒ¯å…¥æ–‡ä»¶é‡è¨“é—œéµå­—æ¨¡åž‹
12. å°æ–‡ä»¶åšç¨…å‹™é¢¨éšªåˆ†æž
13. è¼¸å‡ºç®¡ç†å±¤ç°¡å ±æ ¼å¼ PPTX

ä¸‹ä¸€æ­¥å¦‚æžœè¦æ›´åƒçœŸæ­£çš„ AI ç ”ç©¶å“¡ï¼Œå¯ä»¥å†åŠ ï¼š

- å¤šå±¤ç¶²é è¿½è¹¤èˆ‡ sitemap crawler
- æœå°‹çµæžœèªžæ„ç›¸ä¼¼åº¦é‡æŽ’
- ä¾†æºå¯ä¿¡åº¦è©•åˆ†
- ç ”ç©¶ä»»å‹™è¨˜æ†¶
- PPTX åœ–è¡¨èˆ‡è³‡æ–™è¡¨è‡ªå‹•ç”Ÿæˆ

---

## 16. è³‡æ–™è’é›†å¼·åŒ–é€²åº¦ï¼ˆ2026-05 æ›´æ–°ï¼‰

é€™ä¸€è¼ªé‡é»žæ”¾åœ¨ã€ŒæŠŠè³‡æ–™ä¾†æºå¾žä¸€èˆ¬æœå°‹æ“´å¤§åˆ°å®˜æ–¹è³‡æ–™åº«ï¼‹å…¬å¸åŽŸå§‹æª”ã€ï¼Œè®“ AI ç ”ç©¶åŠ©ç†åœ¨é¢å°è·¨åœ‹ç¨…å‹™é¡Œææ™‚ä¸å†åªèƒ½ä»°è³´ Google Newsã€‚

### 16.1 æ–°å¢žçš„å®˜æ–¹ï¼ç›£ç®¡ï¼å…¬é–‹è³‡è¨Šä¾†æº

`services/search_service.py` æ–°å¢žä»¥ä¸‹è³‡æ–™æŠ“å–å™¨ï¼š

| æŠ“å–å™¨ | ä¾†æº | ç”¨é€” |
|--------|------|------|
| `_search_sec_edgar` | SEC EDGAR Full-Text Search JSON API | ç²¾æº–å‘½ä¸­ 10-K / 20-F / 10-Q / 8-K / 6-K / 40-F ç­‰æ­éœ²æ–‡ä»¶ï¼Œå…§å«æ‰€å¾—ç¨…ã€éžå»¶æ‰€å¾—ç¨…ã€å­å…¬å¸ã€é—œä¿‚äººäº¤æ˜“èˆ‡ä¸ç¢ºå®šç¨…å‹™éƒ¨ä½ |
| `_search_eur_lex` | EUR-Lex å®˜æ–¹æ³•è¦æª¢ç´¢ | è£œå…¥æ­ç›Ÿæ³•è¦ã€æŒ‡ä»¤ã€åˆ¤ä¾‹èˆ‡è·¨å¢ƒç¨…å‹™åˆ¶åº¦æ–‡ä»¶ |
| `_search_taiwan_law` | å…¨åœ‹æ³•è¦è³‡æ–™åº«ï¼ˆlaw.moj.gov.twï¼‰ | ä¸­è¯æ°‘åœ‹ç¨…æ³•ã€é—œç¨…ã€æ³•è¦æ¢æ–‡ï¼ˆæ‰€å¾—ç¨…æ³•ã€åŠ å€¼ç‡Ÿæ¥­ç¨…ã€è²¨ç‰©ç¨…ã€CFC ç­‰ï¼‰ |
| `_search_company_sitemap` | å…¬å¸å®˜æ–¹ `sitemap.xml` / `sitemap_index.xml` | å¾žå·²çŸ¥å…¬å¸ç¶²åŸŸï¼ˆè¯ç¢©ã€å°ç©é›»ã€é´»æµ·ã€Toyotaâ€¦ï¼‰çš„ sitemap ä¸»å‹•æ‰¾å‡ºå¹´å ±ã€æ°¸çºŒå ±å‘Šã€IRã€ç¨…å‹™æ²»ç†é é¢ |

æ–°ä¾†æºéƒ½æœƒï¼š

- æŽ’åºæ™‚å¾—åˆ°é¡å¤–åŠ æ¬Šï¼ˆEDGAR +1.8ã€EUR-Lex +1.5ã€Taiwan MOJ +1.5ã€Sitemap +1.2ï¼‰
- é€²å…¥æ—¢æœ‰çš„åŽ»é‡ / ä½Žè¨Šè™Ÿç¶²åŸŸéŽæ¿¾æµç¨‹
- åœ¨å‰ç«¯çš„ `match_reasons` é¡¯ç¤ºç‚ºå°æ‡‰ source

### 16.2 æ–°å¢ž `deep_research` æœå°‹æ¨¡å¼

æ–°æ¨¡å¼ `source_name = "deep_research"` æœƒèµ°ã€Œå…ˆå®˜æ–¹ã€å¾Œæ–°èžã€çš„ç ”ç©¶è·¯ç·šï¼š

1. å…ˆæ”¾å…¥ `official_seed` / `official_domain_seed` / `reference_seed`
2. è·‘å…¬å¸ sitemap probeï¼Œæ’ˆå‡ºå®˜æ–¹æ–‡ä»¶å…¥å£
3. å‘¼å« SEC EDGAR JSON APIï¼ˆä¾å…¬å¸ä¸»é«”åˆ¥åï¼‰
4. å‘¼å« EUR-Lex èˆ‡ Taiwan MOJ æ³•è¦æª¢ç´¢
5. ç”¨ `site:` å°å®˜æ–¹ç¨…å‹™ / é¡§å•ç«™åšå®šå‘æœå°‹
6. æœ€å¾Œå†è£œå°‘é‡ Google News RSS ä½œç‚ºæ–°èžè„ˆçµ¡

`source_name = "all"` ä¹Ÿå·²é †ä¾¿æ’å…¥ sitemap èˆ‡ SEC EDGAR è£œå¼·ï¼ŒåŽŸæœ¬çš„äº‹ä»¶åž‹ / å¤š locale æ–°èžæµç¨‹ä¸è®Šã€‚

æ¡Œé¢ç‰ˆï¼ˆTkinterï¼‰çš„ `Source` ä¸‹æ‹‰æ–°å¢ž `deep_research` é¸é …ï¼Œé è¨­ä»ä¿ç•™ `all`ï¼Œå¯æ‰‹å‹•åˆ‡æ›ã€‚

### 16.3 HTTP æŠ“å–å±¤çš„ç©©å®šæ€§èˆ‡æ•ˆèƒ½

éŽåŽ»æ¯å€‹æœå°‹å‘¼å«éƒ½æ˜¯ `requests.get(...)` ç›´æŽ¥ç”¨ï¼Œä¸”ç„¡ retryã€ç„¡ cacheã€ç„¡ UA è¼ªæ›¿ã€‚ç¾åœ¨å·²é‡æ§‹ç‚ºï¼š

- `requests.Session` + `HTTPAdapter`ï¼ˆretryï¼š429/5xx, backoff 0.6s, total=2ï¼‰
- é€£ç·šæ±  16 / pool_maxsize 32ï¼Œé‡ç”¨ TCP é€£ç·š
- ä¸‰çµ„æ¡Œé¢é¡ž User-Agent è¼ªæ›¿ï¼Œé¿å…å–®ä¸€ UA è¢«å°
- å…§å»º `Accept-Encoding: gzip, deflate` èˆ‡å¤šèªž `Accept-Language`
- åŠ å…¥ `_cached_request` TTL å¿«å–ï¼ˆé è¨­ 600 ç§’ã€æœ€å¤š 256 ç­†ï¼ŒLRU é€€å ´ï¼‰
- SEC EDGAR å‘¼å«ä½¿ç”¨ç¬¦åˆå®˜æ–¹ fair-use è¦ç¯„çš„ `User-Agent: Tax Monitor Research Bot acc.capstone.115@gmail.com`

æ•ˆç›Šï¼š

- åŒä¸€è¼ª pipeline é‡è¤‡è·‘ç›¸åŒ query variant æ™‚ä¸å†é‡è¤‡æ‰“å¤–éƒ¨
- å¤šå®¶æœå°‹å¼•æ“Žè¢«çŸ­æš«é¢¨æŽ§æ™‚æ•´æ‰¹ä¸å†ç‚¸é–‹
- é€£ç·šè¤‡ç”¨å¾Œ `all` / `deep_research` æ¨¡å¼æ•´é«”è€—æ™‚ä¸‹é™

### 16.4 å·²æ“´å¤§çš„å®˜æ–¹ç¨…å‹™ / ç›£ç®¡ç¶²åŸŸæ¸…å–®

`OFFICIAL_TAX_DOMAINS` èˆ‡ `DISCLOSURE_DOMAINS` è£œå…¥ï¼š

- äºžå¤ªï¼š`nta.go.jp`ã€`mof.go.jp`ã€`nts.go.kr`ã€`moef.go.kr`ã€`iras.gov.sg`ã€`ird.gov.hk`ã€`chinatax.gov.cn`ã€`mof.gov.cn`ã€`incometax.gov.in`ã€`gst.gov.in`ã€`ato.gov.au`ã€`ird.govt.nz`
- å°ç£ï¼š`law.moj.gov.tw`ã€`ntbt.gov.tw`ã€`ntbk.gov.tw`ã€`ntbsa.gov.tw`ã€`tax.gov.tw`ã€`fsc.gov.tw`ã€`tpex.org.tw`
- æ­ç¾Žï¼š`hmrc.gov.uk`ã€`treasury.gov`ã€`bundesfinanzministerium.de`ã€`impots.gouv.fr`ã€`agenziaentrate.gov.it`ã€`eur-lex.europa.eu`ã€`taxation-customs.ec.europa.eu`ã€`canada.ca`
- å…¶ä»–ï¼š`sars.gov.za`ã€`sat.gob.mx`ã€`rfb.gov.br`ã€`afip.gob.ar`
- å…¬é–‹è³‡è¨Šï¼š`efts.sec.gov`ã€`jpx.co.jp`ã€`release.tdnet.info`ã€`hkexnews.hk`ã€`krx.co.kr`ã€`sgx.com`ã€`asx.com.au`ã€`bseindia.com`ã€`nseindia.com`ã€`sse.com.cn`ã€`szse.cn`
- é¡§å•è£œå……ï¼š`bdo.global`ã€`grantthornton.global`ã€`tax.thomsonreuters.com`ã€`internationaltaxreview.com`

ä»»ä½•ä¾†è‡ªä¸Šè¿°ç¶²åŸŸçš„æœå°‹çµæžœéƒ½æœƒè‡ªå‹•æ‹¿åˆ° `official_bonus` / `disclosure_bonus`ã€‚

### 16.5 æ–‡ä»¶åŒ¯å…¥ï¼šè‡ªå‹•å›žæ”¶åµŒå…¥æ–‡ä»¶é€£çµ

`services/document_service.py` åœ¨ ingest ä¸€å¼µ HTML é é¢æ™‚ï¼Œç¾åœ¨æœƒé¡å¤–è§£æžé é¢å…§æ‰€æœ‰ `<a href="...">`ï¼Œä¸¦å›žå‚³ä¸€ä»½ `embedded_document_links`ï¼Œå…§å«ï¼š

- ç›´æŽ¥å‰¯æª”åæ˜¯ `.pdf` / `.docx` / `.xlsx` / `.pptx` çš„æª”æ¡ˆ
- URL æˆ–é€£çµæ–‡å­—å‘½ä¸­å¹´å ±ã€æ°¸çºŒã€ç¨…ã€è²¡å ±ã€æŠ•è³‡äººã€å­å…¬å¸ã€é—œä¿‚ä¼æ¥­ã€governanceã€investorã€ESG ç­‰é—œéµè©žçš„é é¢

`models/schemas.py` ä¹Ÿæ–°å¢ž `EmbeddedDocumentLink`ï¼Œä¸¦æŠŠå®ƒæ”¾å…¥ `UploadResponse`ã€‚

æ•ˆç›Šï¼šç•¶æœå°‹çµæžœä¸Ÿå›žä¸€å¼µ IR å…¥å£é ï¼Œä½¿ç”¨è€…ï¼ˆæˆ–ä¸‹ä¸€è¼ª pipelineï¼‰å¯ä»¥ç›´æŽ¥çœ‹åˆ°è©²é åˆ—å‡ºçš„æ‰€æœ‰å¹´å ±èˆ‡æ°¸çºŒå ±å‘Šä¸‹è¼‰é€£çµï¼Œä¸å†éœ€è¦æ‰‹å‹•ç¿»å®˜ç¶²ã€‚

### 16.6 è©¦ç”¨æ–¹å¼

```json
POST /api/pipeline/run
{
  "keywords": ["è¯ç¢© ASUS å…¨çƒç¨…å‹™æ²»ç†"],
  "user_prompt": "åŒ…å« ASUSã€è¯ç¢©é›»è…¦ã€å­å…¬å¸ã€é—œä¿‚ä¼æ¥­ã€å¹´å ±ã€æ°¸çºŒå ±å‘Šã€SECã€EUR-Lexã€Taiwan MOJ æ³•è¦æª¢ç´¢",
  "date_range": "1y",
  "max_results": 30,
  "source_name": "deep_research",
  "use_ai_query_expansion": true,
  "report_format": "pptx"
}
```

é æœŸå›žå‚³çš„ `results` ä¸­æœƒçœ‹åˆ°ï¼š

- `source = "company_sitemap"`ï¼šä¾†è‡ª `asus.com` sitemap æ’ˆåˆ°çš„å¹´å ± / IR é 
- `source = "sec_edgar"`ï¼šè‹¥å…¬å¸æœ‰ç¾Žè‚¡ ADR / å­å…¬å¸åœ¨ç¾Žç™»è¨˜æ­éœ²
- `source = "eur_lex"`ï¼šè·¨åœ‹ç¨…å‹™åˆ¶åº¦
- `source = "taiwan_law_moj"`ï¼šæ‰€å¾—ç¨…æ³•ã€åŠ å€¼ç‡Ÿæ¥­ç¨…æ³•ç­‰æ¢æ–‡
- æ—¢æœ‰ `official_seed` / `bing_web` / `duckduckgo_html` çµæžœ

æ¯ç­†çµæžœçš„ `match_reasons` æœƒæ˜Žç¢ºé¡¯ç¤ºã€Œå®˜æ–¹ / é¡§å• / ç¨…å‹™ç«™é»žåŠ æ¬Šã€èˆ‡ã€Œå¹´å ± / è²¡å ± / å…¬é–‹è³‡è¨Šä¾†æºåŠ æ¬Šã€ï¼Œæ–¹ä¾¿äººå·¥å¯©æ ¸è³‡æ–™ä¾†æºã€‚

---

## 17. LLM ä¾›æ‡‰å•†åˆ‡æ›ï¼ˆ2026-05 æ›´æ–°ï¼‰

### 17.1 æ¡Œé¢ç‰ˆç›´æŽ¥åˆ‡ä¾›æ‡‰å•†èˆ‡æ¨¡åž‹

`desktop_app/input_panel.py` æ–°å¢žã€ŒLLM providerã€èˆ‡ã€ŒLLM modelã€å…©å€‹ä¸‹æ‹‰é¸å–®ã€‚é è¨­ä»æ˜¯ Ollama + `qwen3:8b`ï¼Œä½†ç¾åœ¨å¯ä»¥ç›´æŽ¥åˆ‡åˆ°ï¼š

| Provider | é è¨­æ¨¡åž‹ | å…§å»ºå¿«é¸æ¸…å–® |
|----------|----------|---------------|
| `ollama` | `qwen3:8b` | qwen3 å…¨ç³»åˆ—ï¼ˆ0.6b/1.7b/4b/8b/14b/32bã€coder:30bï¼‰ã€qwen2.5 å…¨ç³»åˆ—ï¼ˆ1.5b/3b/7b/14b/32b/72bã€coder ç³»åˆ—ï¼‰ã€llama3.1/3.2ã€mistralã€mixtralã€deepseek-r1ã€phi3ã€gemma2 |
| `claude` | `claude-sonnet-4-6` | claude-opus-4-7ã€claude-sonnet-4-6ã€claude-haiku-4-5-20251001ã€claude-3-7-sonnet-latestã€claude-3-5-sonnet-latestã€claude-3-5-haiku-latestã€claude-3-opus-latest |
| `openai` | `gpt-4o-mini` | gpt-4oã€gpt-4o-miniã€gpt-4.1ã€gpt-4.1-miniã€gpt-4.1-nanoã€gpt-4-turboã€gpt-3.5-turboã€o1ã€o1-miniã€o3-mini |
| `gemini` | `gemini-2.5-flash` | gemini-2.5-proã€gemini-2.5-flashã€gemini-2.0-flashã€gemini-2.0-flash-liteã€gemini-1.5-proã€gemini-1.5-flash |
| `qwen` | `qwen3.6-plus` | qwen3.6-plusã€qwen3.6-max-previewã€qwen-maxã€qwen-max-latestã€qwen-plusã€qwen-turboã€qwen3.5-397b-a17b |

å…©å€‹ä¸‹æ‹‰çš†ç‚º `ttk.Combobox`ï¼š

- åˆ‡æ› provider æœƒè‡ªå‹•æŠŠ model ä¸‹æ‹‰çš„é¸é …æ›æˆè©² provider çš„å¿«é¸æ¸…å–®ï¼Œä¸¦æŠŠ model é‡è¨­ç‚ºè©² provider çš„å»ºè­°é è¨­å€¼
- model ä¸‹æ‹‰æ˜¯ `state="normal"`ï¼Œå¯ç›´æŽ¥è¼¸å…¥æ¸…å–®æ²’åˆ—å‡ºçš„å®¢è£½æ¨¡åž‹åç¨±ï¼ˆä¾‹å¦‚æ–°ç‰ˆ GGUF tagã€Bedrock model idã€Azure deployment name ç­‰ï¼‰

é¸å®šå¾Œçš„ provider / model æœƒåŒæ­¥å‚³é€² `PipelineService.search_ingest_and_train`ï¼Œå› æ­¤æœå°‹å±¤çš„ AI query expansionã€æ–‡ä»¶åˆ†æžã€å ±å‘Šç”¢å‡ºéƒ½æœƒç”¨åŒä¸€çµ„è¨­å®šã€‚

### 17.2 API key å³æ™‚è¦†å¯«

ä¸‹æ–¹çš„ `API key (optional, overrides env var for this session)` æ˜¯ä¸€å€‹é®ç½©è¼¸å…¥æ¬„ã€‚æµç¨‹ï¼š

1. åˆ‡åˆ° `claude` / `openai` / `gemini` / `qwen` ä»»ä¸€ provider
2. åœ¨ API key æ¬„è²¼å…¥é‡‘é‘°
3. æŒ‰ `Run research`

æ¡Œé¢ç‰ˆæœƒåœ¨é€å‡º payload ä¹‹å‰ `os.environ[env_var] = key`ï¼Œæ‰€ä»¥ `services/llm_service.py` çš„ `_call_claude` / `_call_openai` / `_call_gemini` / `_call_qwen` å¯ä»¥é€éŽç›¸å°æ‡‰çš„ç’°å¢ƒè®Šæ•¸æ‹¿åˆ°ã€‚é‡‘é‘°åªå­˜åœ¨æ–¼ç›®å‰ process è¨˜æ†¶é«”ï¼Œä¸æœƒå¯«å…¥ç£ç¢Ÿï¼Œè¦–çª—é—œé–‰å°±æ¶ˆå¤±ã€‚

å¦‚æžœ API key æ¬„ç•™ç©ºï¼Œå‰‡å›žé€€ä½¿ç”¨ shell / ç³»çµ±å±¤ç´šçš„ç’°å¢ƒè®Šæ•¸ï¼ˆ`ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `GEMINI_API_KEY` / `DASHSCOPE_API_KEY`ï¼‰ã€‚ä¾›æ‡‰å•†æ—é‚Šæœƒé¡¯ç¤ºä¸€è¡Œç‹€æ…‹æç¤ºï¼š

- ç¶ è‰²ï¼šã€Œ`OPENAI_API_KEY` detected. Ready to call openai.ã€
- ç´…è‰²ï¼šã€Œ`OPENAI_API_KEY` is not set. Set it in your shell before launching to call openai.ã€
- ç°è‰²ï¼šã€ŒLocal provider (Ollama). Make sure `ollama serve` is running.ã€

### 17.3 å°æ‡‰çš„ Provider è·¯ç”±

`services/llm_service.py` å·²å…§å»ºäº”å€‹ä¾›æ‡‰å•†å‘¼å«å™¨ï¼Œç¾åœ¨æ¡Œé¢ç‰ˆåªæ˜¯æŠŠé¸æ“‡æ¬Šæš´éœ²çµ¦ä½¿ç”¨è€…ï¼š

- `_call_ollama` â†’ `http://localhost:11434/api/generate`
- `_call_openai` â†’ `https://api.openai.com/v1/chat/completions`
- `_call_gemini` â†’ `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`
- `_call_claude` â†’ `https://api.anthropic.com/v1/messages`ï¼ˆ`anthropic-version: 2023-06-01`ï¼‰
- `_call_qwen` â†’ `https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions`ï¼ˆå¯ç”¨ `DASHSCOPE_BASE_URL` è¦†å¯«ï¼‰

æ‰€ä»¥å¾žæ¡Œé¢ç‰ˆé¸ `claude` + `claude-opus-4-7`ï¼Œæˆ– `qwen` + `qwen3.6-plus` / `qwen3.6-max-preview` / `qwen-max-latest`ï¼ŒAI query expansionã€`AnalysisService` çš„ LLM æ‘˜è¦ã€`ReportService` çš„ç°¡å ±å…§å®¹ç”Ÿæˆéƒ½æœƒèµ°åŒä¸€çµ„ provider/modelã€‚

### 17.4 é †å¸¶å„ªåŒ–çš„æ•ˆèƒ½é …ç›®

åˆ‡ä¾›æ‡‰å•†æœ‰æ™‚æœƒæ­åˆ°ä»˜è²» APIï¼Œå› æ­¤é€™ä¸€è¼ªä¹Ÿé †æ‰‹æŠŠ pipeline è·‘ä¸‹ä¾†æœ€æµªè²»çš„åœ°æ–¹ä¿®äº†ï¼š

- `services/document_service.process_url` / `process_upload` æ–°å¢ž `defer_keyword_training: bool` åƒæ•¸
- `services/pipeline_service` åœ¨æ‰¹æ¬¡ ingest æ™‚å°‡è©²åƒæ•¸è¨­ç‚º `True`ï¼Œä¸¦åœ¨æ‰€æœ‰æ–‡ä»¶ ingest å®Œä¹‹å¾Œ**åªè¨“ç·´ä¸€æ¬¡** TF-IDF æ¨¡åž‹
- ä¹‹å‰ä¸€æ¬¡ 30 ç¯‡å°±æœƒåš 30 æ¬¡å®Œæ•´ corpus é‡è¨“ï¼Œç¾åœ¨åªåš 1 æ¬¡ï¼›å° 1m+ å­—å…ƒçš„ç´¯ç©è³‡æ–™åº«å·®ç•°å¾ˆå¤§
- æ—¢æœ‰ `/api/document/upload`ã€`/api/document/ingest-url` å–®ç­† API ä¸å—å½±éŸ¿ï¼ˆé è¨­ä»æ˜¯ `False`ï¼‰

### 17.5 è©¦ç”¨æ–¹å¼

```powershell
# 1. å•Ÿå‹•æ¡Œé¢ç‰ˆ
.\.venv\Scripts\python.exe -m desktop_app

# 2. åœ¨ LLM provider é¸ "claude"
# 3. åœ¨ LLM model é¸ "claude-opus-4-7"ï¼ˆæˆ–è‡ªè¡Œè¼¸å…¥å…¶ä»– Claude model idï¼‰
# 4. åœ¨ API key æ¬„è²¼ä¸Š sk-ant-...
# 5. æŒ‰ Run research
```

æˆ–ç›´æŽ¥åœ¨ API ç«¯ï¼š

```json
POST /api/pipeline/run
{
  "keywords": ["è¯ç¢© ASUS å…¨çƒç¨…å‹™æ²»ç†"],
  "user_prompt": "åŒ…å«å­å…¬å¸ã€å¹´å ±ã€SECã€EUR-Lexã€Taiwan MOJ",
  "source_name": "deep_research",
  "provider": "claude",
  "model_name": "claude-opus-4-7",
  "report_format": "pptx"
}
```

åªè¦ç’°å¢ƒè®Šæ•¸ `ANTHROPIC_API_KEY` å·²è¨­å®šï¼Œæ•´æ¢ pipelineï¼ˆæœå°‹æ“´å¯«ã€é¢¨éšªåˆ†æžã€PPTX å…§å®¹ï¼‰éƒ½æœƒäº¤çµ¦ Claudeã€‚æ›æˆ `provider: "openai", model_name: "gpt-4o"`ã€`provider: "gemini", model_name: "gemini-2.5-pro"`ï¼Œæˆ– `provider: "qwen", model_name: "qwen3.6-plus"` ä¹Ÿæ˜¯åŒä¸€å€‹å¯«æ³•ã€‚

---

## 18. æŸ¥è©¢æ“´å¯«åŠ å¼·ï¼šæŠ“æŠ½æ¨£ï¼é¸æ¡ˆæŸ¥æ ¸é¢¨éšªï¼ˆ2026-05 æ›´æ–°ï¼‰

é€™ä¸€è¼ªè§£çš„æ ¸å¿ƒå•é¡Œï¼šæœå°‹ç¨…å‹™ã€ŒæŠ½æ¨£é¢¨éšªã€è³‡æ–™æ™‚ï¼Œç¶²è·¯ä¸Šå¹¾ä¹Žä¸æœƒç”¨ã€ŒæŠ½æ¨£é¢¨éšªã€å››å€‹å­—ç›´æŽ¥å¯«å‡ºä¾†ï¼ŒçœŸæ­£æœƒå¯«å‡ºä¾†çš„æ˜¯å„åœ‹åœ‹ç¨…å±€è‡ªå·±ç”¨èªžï¼Œä¾‹å¦‚å°ç£ã€Œé¸æ¡ˆæŸ¥æ ¸ã€ã€Œè£œå¾µç¨…æ¬¾ã€ã€æ—¥æœ¬ã€Œç¨Žå‹™èª¿æŸ»ã€ã€Œæ›´æ­£å‡¦åˆ†ã€ã€éŸ“åœ‹ã€Œì„¸ë¬´ì¡°ì‚¬ã€ã€ä¸­åœ‹å¤§é™¸ã€Œç¨ŽåŠ¡ç¨½æŸ¥ã€ã€ŒéšæœºæŠ½æŸ¥ã€ã€IRSã€ŒNotice of Deficiencyã€ã€Œrisk-based auditã€ã€‚æ‰€ä»¥å…‰é åŽŸå§‹å­—é¢æˆ–å–®ä¸€èªžè¨€æ“´å¯«æœƒæ¼æŽ‰ä¸€å¤§å¡Šã€‚

### 18.1 å¤šèªžè¨€ã€å¤šç®¡è½„å€ç¨…å‹™åŒç¾©è©žå…¸

`services/search_service.py` æ–°å¢žä¸‰å€‹å¸¸æ•¸ï¼š

| å¸¸æ•¸ | å…§å®¹ | ç”¨é€” |
|------|------|------|
| `AUDIT_SAMPLING_TERMS` | 58 å€‹æŠ½æ¨£ï¼é¸æ¡ˆæŸ¥æ ¸ç›¸é—œç”¨èªžï¼ˆä¸­ï¼è‹±ï¼æ—¥ï¼éŸ“ï¼ç°¡é«”ï¼‰ | ç›´æŽ¥é¤µå…¥æŸ¥è©¢èˆ‡æŽ’åºåŠ æ¬Š |
| `TAX_AUDIT_THESAURUS` | 10 å€‹æ¦‚å¿µï¼šaudit / sampling / penalty / transfer_pricing / pillar_two / cfc / permanent_establishment / withholding_tax / tariff / vat_gst | æ¦‚å¿µ â†’ å¤šèªžåŒç¾©è©ž |
| `JURISDICTION_PROFILE` | 9 å€‹ç®¡è½„å€ï¼ˆTW / JP / KR / CN / HK / SG / US / EU / INï¼‰çš„å¯©æŸ¥æ©Ÿé—œåˆ¥åã€æŸ¥æ ¸ç”¨èªžã€ç”³å ±ç”¨èªž | å‘½ä¸­ç®¡è½„å€å¾Œåšå°ˆå±¬æ“´å¯« |

ç‰¹è‰²ï¼š

- ä¸ä¾è³´ LLMã€é›¶å»¶é²ã€é›¶ token æˆæœ¬
- å³ä½¿ Ollama / é›²ç«¯ API å…¨å£žï¼Œé€™å±¤ä»èƒ½æ“´å¯«
- æœƒè‡ªå‹•æŠ“å‡ºè¼¸å…¥è£¡çš„ç®¡è½„å€æš—ç¤ºï¼ˆä¾‹å¦‚ `Taiwan`ã€`å›½ç¨Žåº`ã€`IRS`ã€`SEC.gov`ï¼‰ï¼Œå°æ‡‰åˆ° `JURISDICTION_PROFILE` è£œå‡ºç•¶åœ°æŸ¥æ ¸ç”¨èªž

### 18.2 çµæ§‹åŒ–æ„åœ–è§£æž

æ–°å¢ž `_extract_intent_with_llm`ï¼ŒæŠŠå–®æ¬¡ LLM å‘¼å«çš„è¼¸å‡ºå›ºå®šæˆ JSON schemaï¼š

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

`_build_intent_queries` æ‹¿åˆ°é€™ä»½ JSON å¾Œåšç¬›å¡çˆ¾ç©ï¼š`entity Ã— risk_category synonyms Ã— jurisdiction audit_terms Ã— must_have_terms`ï¼Œç”¢å‡ºæœ€é«˜ 60 å€‹å¸¶å¼•è™Ÿçš„ç²¾æº–æŸ¥è©¢ã€‚

ä¾‹å¦‚ä½¿ç”¨è€…è¼¸å…¥ã€Œè¯ç¢©è·¨åœ‹å­å…¬å¸ æŠ½æ¨£æŸ¥æ ¸é¢¨éšªã€ï¼Œæ„åœ–è§£æžæœƒæŠŠå®ƒæ‹†æˆï¼š

- entities: `è¯ç¢©`ã€`ASUS`ã€`ASUSTeK`
- jurisdictions: `TW`ã€`US`ã€`CN`ã€`HK`
- risk_categories: `audit`ã€`sampling`ã€`transfer_pricing`ã€`permanent_establishment`
- ç”¢å‡ºæŸ¥è©¢ä¾‹ï¼š`"ASUS" risk-based audit selection`ã€`"è¯ç¢©" é¸æ¡ˆæŸ¥æ ¸ 113å¹´åº¦`ã€`"ASUSTeK" Notice of Deficiency`ã€`"è¯ç¢©" ç§»è½‰è¨‚åƒ¹é¸æ¡ˆ`

### 18.3 å½ç›¸é—œå›žé¥‹ï¼ˆPseudo-Relevance Feedback, PRFï¼‰

æ–°å¢ž `_pseudo_relevance_feedback`ï¼Œé‚è¼¯ï¼š

1. ç¬¬ä¸€è¼ªæœå°‹æ‹¿å›žçš„ titles + snippets åš token åŒ–
2. è‹±æ–‡ï¼š`[A-Za-z][A-Za-z0-9.-]{3,}`
3. ä¸­æ–‡ï¼šå°é€£çºŒ CJK æ®µåš 4 / 3 / 2-gram æ»‘çª—ï¼ˆæ²’è£ jiebaï¼Œé€™æ¨£æœ€ç©©ï¼‰
4. éŽæ¿¾æŽ‰ä½Žè¨Šè™Ÿè©žèˆ‡å·²å­˜åœ¨æ–¼åŽŸæŸ¥è©¢çš„è©ž
5. æŽ’åºé »çŽ‡ï¼Œå– top-N èˆ‡ä¸»é«”åˆ¥å + `tax audit / ç¨…å‹™æŸ¥æ ¸ / ç¨Žå‹™èª¿æŸ»` é‡æ–°çµ„åˆ
6. æ‹¿é€™æ‰¹æ–° query å†è·‘ä¸€è¼ª DuckDuckGo / Bing

å¯¦æ¸¬ï¼šçµ¦ã€ŒASUS ç§»è½‰è¨‚åƒ¹æŸ¥æ ¸è£œå¾µç¨…æ¬¾ã€ç›¸é—œ snippetï¼ŒPRF æœƒå›žé¥‹å‡º `"ASUSTeK" ç§»è½‰è¨‚ tax audit` é€™é¡žæŸ¥è©¢ï¼ŒæŠŠç¬¬ä¸€è¼ªæ²’å‘½ä¸­çš„ç›¸é„°æ–‡ä»¶å¸¶å›žã€‚

### 18.4 æŽ’åºèˆ‡ç†ç”±æ›´æ–°

| åŠ æ¬Šé … | åˆ†æ•¸ |
|--------|------|
| `sampling_hits`ï¼ˆå‘½ä¸­ AUDIT_SAMPLING_TERMSï¼‰ | +1.4 / å‘½ä¸­ |
| match_reasons æ–°å¢ž | `å‘½ä¸­æŠ½æ¨£ï¼é¸æ¡ˆæŸ¥æ ¸ç·šç´¢ï¼š...` |

æ‰€ä»¥å‰ç«¯çµæžœåˆ—è¡¨æœƒç›´æŽ¥çœ‹åˆ°ã€Œç‚ºä»€éº¼é€™ç­†è¢«æŠ“å‡ºä¾†ã€ï¼Œä¾‹å¦‚ `å‘½ä¸­æŠ½æ¨£ï¼é¸æ¡ˆæŸ¥æ ¸ç·šç´¢ï¼šé¸æ¡ˆæŸ¥æ ¸, è£œå¾µç¨…æ¬¾`ã€‚

### 18.5 æŽ§åˆ¶åƒæ•¸

- `_search_deep_research` æ–°å¢ž `provider`ã€`model_name`ã€`use_intent_extraction` ä¸‰å€‹å…¥åƒ
- `search()` åœ¨ `source_name == "deep_research"` æ™‚è‡ªå‹•æŠŠé€™ä¸‰å€‹å€¼å‚³ä¸‹åŽ»
- ç•¶ `use_ai_query_expansion = False` æ™‚ï¼Œæ„åœ–è§£æžèˆ‡ LLM æ“´å¯«ä¸€èµ·è·³éŽï¼ŒPRF èˆ‡å¤šèªžåŒç¾©è©žå…¸ä»æœƒè·‘ï¼ˆç´”è¦å‰‡å¼ï¼‰

### 18.6 è©¦ç”¨

```json
POST /api/pipeline/run
{
  "keywords": ["è¯ç¢© ASUS"],
  "user_prompt": "åŒ…å«æ——ä¸‹å­å…¬å¸ã€è·¨åœ‹æŠ½æ¨£ï¼é¸æ¡ˆæŸ¥æ ¸é¢¨éšªã€ç§»è½‰è¨‚åƒ¹æŸ¥æ ¸ã€è£œå¾µç¨…æ¬¾ã€ç¨…å‹™è£ç½°æ›¸ã€ç¨…å‹™åŠç”¨åœ°èª¿æŸ¥",
  "date_range": "1y",
  "max_results": 30,
  "source_name": "deep_research",
  "provider": "ollama",
  "model_name": "qwen3:8b",
  "use_ai_query_expansion": true,
  "report_format": "pptx"
}
```

é æœŸè®ŠåŒ–ï¼š

- `query_variants` å¾žåŽŸæœ¬çš„ ~36 ä¸Šå‡åˆ° 48 ä¸Šé™ï¼Œä¸”æ–°å¢ž `_expand_with_thesaurus` ç”¢å‡ºçš„ 60 å€‹å¤šèªžæ“´å¯«
- å¤šä¸€è¼ª `intent_queries`ï¼ˆæœ€é«˜ 60 å€‹ï¼‰è·‘ DuckDuckGo + Bing
- æœ«ç«¯å¤šä¸€è¼ª `pseudo_relevance_feedback`ï¼ŒæŠŠç¬¬ä¸€è¼ªå‘½ä¸­çš„ snippet åé¥‹å›žæœå°‹
- çµæžœé çš„ `match_reasons` æœƒå‡ºç¾ã€Œå‘½ä¸­æŠ½æ¨£ï¼é¸æ¡ˆæŸ¥æ ¸ç·šç´¢ï¼šâ€¦ã€èˆ‡ã€Œå‘½ä¸­ç¨…å‹™äº‹ä»¶ç·šç´¢ï¼šâ€¦ã€

### 18.7 é‚„æ²’å‹•ä½†ä¸‹ä¸€æ­¥å¯ä»¥æŽ¥

1. **TF-IDF è‡ªèº«è©žå½™å›žæ”¶** â€” åœ¨ `_pseudo_relevance_feedback` è£¡ä¹Ÿè®€ä¸€æ¬¡ `KeywordService.feature_names`ï¼ŒæŠŠèˆ‡è¼¸å…¥åˆ¥åå…±ç¾é«˜é »çš„è©žè£œé€²åŽ»ï¼ˆè¦åšè·¨æœå‹™æ³¨å…¥ï¼‰
2. **Embedding ç›¸ä¼¼åº¦é‡æŽ’** â€” `sentence-transformers` æˆ– Ollama embedding æ¨¡åž‹ï¼ŒæŠŠæœå°‹çµæžœèªžæ„ç›¸ä¼¼åº¦ç•¶ç¬¬äºŒæŽ’åºè»¸
3. **Query negation** â€” æŠŠæ„åœ–è§£æžçš„ `exclude_terms` è½‰æˆ `-noise -term` çš„æœå°‹é‹ç®—å­
4. **Per-jurisdiction parallel fetch** â€” åµæ¸¬åˆ°å¤šç®¡è½„å€æ™‚é–‹ thread pool å¹³è¡Œæ‰“å„åœ‹æ–°èž RSS èˆ‡å®˜æ–¹æª¢ç´¢

---

## 19. æœå°‹å±¤ç¬¬äºŒè¼ªåŠ å¼·ï¼ˆ2026-05 æ›´æ–°ï¼‰

æŽ¥çºŒ Â§18ï¼ŒæŠŠä¸Šä¸€è¼ªã€Œä¸‹ä¸€æ­¥ã€æ¸…å–®è£¡çš„äº‹éƒ½åšäº†ï¼ŒåŠ ä¸Šå¹¾å€‹çµæ§‹æ€§æ•ˆèƒ½èˆ‡å“è³ªæ”¹é€ ã€‚

### 19.1 å¹³è¡ŒåŒ–æŠ“å–ï¼ˆconcurrent fan-outï¼‰

æ–°å¢ž `_run_parallel_searches`ï¼š

- åŒ…æˆ `concurrent.futures.ThreadPoolExecutor`ï¼Œé è¨­ 6 worker
- ä¾ task æ•¸é‡è‡ªå‹•ç¸®æ”¾ï¼ˆ`min(6, max(2, len(tasks)))`ï¼‰
- ä»»ä½•ä¸€å€‹ task æ‹‰æ»¿ `candidate_limit` å°±æœƒ `cancel()` é‚„åœ¨æŽ’éšŠçš„ futureï¼Œææ—©çµæŸ

`_search_deep_research` æ•´æ¢æµç¨‹å·²é‡å¯«æˆã€Œåˆ†çµ„å¹³è¡Œã€ï¼š

| éšŽæ®µ | å…§å®¹ | å¹³è¡ŒæŠ“å– |
|------|------|----------|
| 1. seed | `official_seed` / `reference_seed` / `official_domain_seed` | â€” |
| 2. official tasks | sitemapã€SEC EDGARã€EUR-Lexã€Taiwan MOJã€ï¼ˆåµæ¸¬åˆ° JPï¼‰EDINETã€ï¼ˆåµæ¸¬åˆ° KRï¼‰DART | âœ… |
| 3. intent tasks | ä¾†è‡ªæ„åœ–è§£æžçš„ 6 å€‹é«˜ç²¾åº¦æŸ¥è©¢ Ã— DuckDuckGo + Bing | âœ… |
| 4. targeted tasks | `site:` å®˜æ–¹ï¼é¡§å•å®šå‘æŸ¥è©¢ | âœ… |
| 5. news tasks | Google News RSSï¼ˆå¤š variantï¼‰ | âœ… |
| 6. PRF tasks | å¾žç¬¬ä¸€æ³¢çµæžœåé¥‹å‡ºçš„ query | âœ… |

å¯¦æ¸¬ï¼š5 å€‹å‡ä»»å‹™ï¼ˆserial ç´„ 0.35sï¼‰å¹³è¡Œç‰ˆåªèŠ± **0.118s**ï¼Œé€Ÿåº¦ç´„ 3Ã—ã€‚

### 19.2 ä¾†æºå¥åº·åº¦è¿½è¹¤

æ–°å¢ž `_source_stats`ï¼š

- æ¯å€‹ adapterï¼ˆ`_search_sec_edgar` / `_search_bing_web` ...ï¼‰ä»¥ function name ä½œ key
- è¿½è¹¤ `success / fail / consecutive_fail`
- `consecutive_fail >= 3` æ™‚è‡ªå‹•é€²å…¥ unhealthy ç‹€æ…‹ï¼Œ`_safe_search_call` ç›´æŽ¥ short-circuit å›žç©ºé™£åˆ—
- ä»»ä¸€æ¬¡ success å°±æŠŠé€£çºŒå¤±æ•—è¨ˆæ•¸æ­¸é›¶ï¼Œæ¢å¾©æ­£å¸¸æŽ’ç¨‹
- å…¬é–‹ `get_source_health_snapshot()` çµ¦ä¸Šå±¤ç”¨

æ•ˆç›Šï¼šDuckDuckGo æ•´è¼ªéƒ½ 403 çš„æƒ…æ³ä¸‹ï¼Œå‰©ä¸‹ 12 æ¬¡ query variant ä¸æœƒå†åŽ»æ•²å®ƒï¼Œçœä¸‹ç´„ 96 ç§’ï¼ˆ8s timeout Ã— 12ï¼‰ã€‚

### 19.3 æ¨™é¡Œç›¸ä¼¼åº¦ dedupï¼ˆJaccard n-gramï¼‰

`_dedup_by_title_similarity` åœ¨ `_rank_results` ä¹‹å¾ŒåŸ·è¡Œï¼š

- è‹±æ–‡ï¼šlowercase + alpha-num token
- ä¸­æ–‡ï¼šå°é€£çºŒ CJK æ®µåš 2/3-gram æ»‘çª—
- ç”¨ Jaccard ç›¸ä¼¼åº¦ â‰¥ **0.7** è¦–ç‚ºè¿‘é‡è¤‡
- é«˜åˆ†çµæžœä¿ç•™ï¼Œä½Žåˆ†çµæžœåˆä½µé€² `duplicate_titles`ï¼Œé¿å…å–®ä¸€æ–°èžç¨¿è¢«å¤šå®¶è½‰è¼‰çŒçˆ†æŽ’åº

### 19.4 æ„åœ–å±¤ must_have / exclude_terms æŽ¥åˆ°æŽ’åº

`_rank_results` æŽ¥å— `intent` åƒæ•¸ï¼š

- `must_have_bonus`ï¼šæ¯å‘½ä¸­ä¸€å€‹ `must_have_terms` +1.6
- `exclude_penalty`ï¼šæ¯å‘½ä¸­ä¸€å€‹ `exclude_terms` -2.5
- `match_reasons` é¡¯ç¤ºã€Œå‘½ä¸­æ„åœ–å¿…å«è©žï¼šâ€¦ã€èˆ‡ã€Œå‘½ä¸­æ„åœ–æŽ’é™¤è©ž (æ‰£åˆ†)ï¼šâ€¦ã€ï¼Œæ–¹ä¾¿äººå·¥æª¢æŸ¥ LLM æŠ½å‡ºçš„è©žæ˜¯å¦åˆç†

é€™ä¹Ÿä»£è¡¨ Â§18 åŠ çš„çµæ§‹åŒ–æ„åœ– JSONï¼ˆ`exclude_terms`ã€`must_have_terms`ï¼‰çµ‚æ–¼æœ‰å¯¦éš›æŽ’åºæ•ˆæžœï¼Œè€Œä¸åªæ˜¯è¢«æ‰“å°å‡ºä¾†ã€‚

### 19.5 æ–°å¢žæ—¥éŸ“å®˜æ–¹æ­éœ²ä¾†æº

| æŠ“å–å™¨ | ä¾†æº | å…§å®¹ |
|--------|------|------|
| `_search_edinet_jp` | é‡‘èžåº EDINETï¼ˆdisclosure2.edinet-fsa.go.jpï¼‰ | æœ‰ä¾¡è¨¼åˆ¸å ±å‘Šæ›¸ã€å››åŠæœŸå ±å‘Šæ›¸ã€è‡¨æ™‚å ±å‘Šæ›¸ï¼Œå«åˆä½µæ‰€å¾—ç¨…ã€é—œä¿‚äººäº¤æ˜“ã€å€æ®µç¨…å‹™æ­éœ² |
| `_search_dart_kr` | éŸ“åœ‹ FSS DARTï¼ˆdart.fss.or.krï¼‰ | ì‚¬ì—…ë³´ê³ ì„œã€ë¶„ê¸°ë³´ê³ ì„œã€ì£¼ìš”ì‚¬í•­ë³´ê³ ì„œï¼›í•œêµ­ ìƒìž¥ì‚¬ æ³•äººç¨Žã€ì´ì „ê°€ê²©ã€íŠ¹ìˆ˜ê´€ê³„ìž ê±°ëž˜ |

å•Ÿç”¨æ¢ä»¶ï¼š`_search_deep_research` åµæ¸¬åˆ° JP / KR jurisdictionï¼Œæˆ–å…¬å¸ç¶²åŸŸä»¥ `.jp`ï¼`.kr` çµå°¾ï¼ŒæœƒæŠŠ EDINET / DART è‡ªå‹•æŽ’å…¥ç¬¬ 2 éšŽæ®µå¹³è¡Œ taskã€‚

æŽ’åºåŠ æ¬Šï¼š`edinet_jp` / `dart_kr` å„ +1.6ï¼ˆä»‹æ–¼ SEC EDGAR +1.8 èˆ‡ EUR-Lex +1.5 ä¹‹é–“ï¼‰ã€‚å°æ‡‰ç¶²åŸŸåŠ å…¥ `DISCLOSURE_DOMAINS`ï¼Œè‡ªå‹•æ‹¿åˆ° `disclosure_bonus`ã€‚

### 19.6 PRF æŽ¥ KeywordService è©žå½™å›žæ”¶

`_pseudo_relevance_feedback` ç¾åœ¨æœƒåœ¨åš n-gram çµ±è¨ˆå¾Œï¼Œå†åŽ» `services/keyword_service.py` çš„ TF-IDF feature_namesï¼ˆæœ€å¤š 200 è©žï¼‰æ’ˆä¸€è¼ªï¼š

- å·²è¢« TF-IDF è¨“ç·´å‡ºä¾†çš„é ˜åŸŸè©žï¼Œå¦‚æžœåœ¨ç¬¬ä¸€æ³¢çµæžœçš„ title/snippet è£¡å‡ºç¾ï¼Œå°±åŠ é€²å€™é¸è©ž
- æŽ’é™¤æ—¢æœ‰ query / ä½Žè¨Šè™Ÿè©ž
- çµæžœèˆ‡ n-gram å€™é¸è©žåˆä½µæŽ’åºï¼Œåšç‚º PRF ç¬¬äºŒè¼ªæŸ¥è©¢çš„ç¨®å­

æ„ç¾©ï¼š`KeywordService` ç´¯ç©çš„é ˜åŸŸè©žåº«çµ‚æ–¼å›žæµåˆ°æœå°‹å±¤ï¼Œè®“æ¯æ¬¡ ingest å®Œçš„ã€Œé›†åœ˜æž¶æ§‹ã€åˆä½µè²¡å‹™å ±è¡¨ã€æ‰€å¾—ç¨…è²»ç”¨ã€ç§»è½‰è¨‚åƒ¹ã€æœ‰æ•ˆç¨…çŽ‡ã€é€™äº› TF-IDF é«˜åˆ†è©žè‡ªå‹•é€²åˆ°ä¸‹ä¸€è¼ªæŸ¥è©¢ã€‚

### 19.7 æŽ§åˆ¶èˆ‡è§€å¯Ÿ

- å¹³è¡Œ worker ä¸Šé™ï¼š`SearchService.PARALLEL_FETCH_WORKERS`ï¼ˆé è¨­ 6ï¼‰
- ä¾†æºå¥åº·åº¦é–€æª»ï¼š`SearchService.SOURCE_HEALTH_FAIL_THRESHOLD`ï¼ˆé è¨­ 3ï¼‰
- Dedup ç›¸ä¼¼åº¦é–€æª»ï¼š`_dedup_by_title_similarity(threshold=0.7)`
- è§€å¯Ÿç•¶å‰å¥åº·ç‹€æ…‹ï¼š`search_service.get_source_health_snapshot()`

### 19.8 è©¦ç”¨

```json
POST /api/pipeline/run
{
  "keywords": ["TSMC å°ç©é›» æŠ½æ¨£é¸æ¡ˆæŸ¥æ ¸é¢¨éšª"],
  "user_prompt": "åŒ…å«æ—¥æœ¬å­å…¬å¸ã€éŸ“åœ‹å­å…¬å¸ã€ç§»è½‰è¨‚åƒ¹ã€è£œå¾µç¨…æ¬¾ã€æœ‰æ•ˆç¨…çŽ‡ï¼Œä¸è¦æ–°èžç¨¿è½‰è¼‰",
  "date_range": "1y",
  "max_results": 30,
  "source_name": "deep_research",
  "provider": "claude",
  "model_name": "claude-sonnet-4-6",
  "use_ai_query_expansion": true
}
```

é æœŸè®ŠåŒ–ï¼š

- æ„åœ–è§£æžæœƒæŠŠ `jurisdictions: ["TW", "JP", "KR"]` æŠ½å‡ºä¾†
- ç¬¬ 2 éšŽæ®µå¹³è¡Œ fan-out æœƒåŒæ™‚æ‰“ **sitemapã€SEC EDGARã€EUR-Lexã€Taiwan MOJã€EDINETã€DART**ï¼ˆ6 å€‹ adapter ä¸¦è¡Œï¼‰
- `exclude_terms: ["press release", "æ–°èžç¨¿"]` æœƒçµ¦è½‰è¼‰ç¨¿æ‰£ -2.5
- Jaccard dedup æœƒæŠŠå¤šå®¶åª’é«”è½‰è¼‰åŒä¸€ç¯‡ TSMC æ–°èžåˆä½µ
- ç¬¬ä¸€è¼ªçµæžœè£¡è‹¥ TF-IDF å·²æœ‰ã€Œåˆä½µè²¡å‹™å ±è¡¨ã€ã€Œæœ‰æ•ˆç¨…çŽ‡ã€ï¼ŒPRF ç¬¬äºŒè¼ªæœƒè‡ªå‹•æŠŠé€™å…©å€‹è©žç•¶ç¨®å­æŸ¥è©¢
- çµæžœé çš„ `match_reasons` å¤šäº†ã€Œå‘½ä¸­æ„åœ–å¿…å«è©žã€ã€Œå‘½ä¸­æ„åœ–æŽ’é™¤è©ž (æ‰£åˆ†)ã€ã€Œå‘½ä¸­æŠ½æ¨£ï¼é¸æ¡ˆæŸ¥æ ¸ç·šç´¢ã€

---

## 20. è·¨å±¤åŠ å¼·ï¼šåŽ»é‡ã€æ­·å²ã€å…¨æ–‡æª¢ç´¢ã€LLM éŸŒæ€§ï¼ˆ2026-05 æ›´æ–°ï¼‰

é€™ä¸€è¼ªä¸å†åªå‹•æœå°‹å±¤ï¼ŒæŠŠ storage / LLM / pipeline ç­‰ä¹‹å‰æ²’ç¢°éŽçš„è–„å¼±ç’°ç¯€ä¸€æ¬¡è£œä¸Šã€‚

### 20.1 å…§å®¹é›œæ¹ŠåŽ»é‡ï¼ˆidempotent ingestionï¼‰

`services/storage_service.py` æ–°å¢ž `content_hash TEXT` æ¬„èˆ‡ç´¢å¼• `idx_documents_content_hash`ã€‚

`services/document_service.py` ingest æµç¨‹ç¾åœ¨æœƒï¼š

1. æŠ½å‡º `raw_text` å¾Œåš `re.sub(r"\s+", " ", text).lower()` æ­£è¦åŒ–
2. ç®— `sha256` å¾—åˆ° `content_hash`
3. å‘¼å« `storage_service.find_document_by_content_hash(hash)` æŸ¥é‡
4. è‹¥å·²å­˜åœ¨ï¼Œ**ç›´æŽ¥å›žå‚³æ—¢æœ‰ `doc_id` èˆ‡ `deduplicated: True`**ï¼Œä¸é‡å¯«è³‡æ–™åº«ã€ä¸é‡æŠ½é—œéµå­—

æ•ˆç›Šï¼š

- åŒä¸€ç¯‡ PDF è¢«ä¸åŒ URLï¼ˆIR å…¥å£ã€SEC é¡åƒã€media archiveï¼‰æŒ‡å‘æ™‚ï¼Œç¾åœ¨åªç®—ä¸€æ¬¡ï¼Œä¸æœƒåœ¨ DB èˆ‡å ±å‘Šæµç¨‹è£¡é‡åš
- åŒä¸€è¼ª `deep_research` å¹³è¡Œ fan-out å‘½ä¸­ç›¸åŒæª”æ¡ˆæ™‚ä¹Ÿæœƒè¢«æ””ä¸‹
- å°æ‡‰ LLM åˆ†æžã€PPTX ç”¢å‡ºçš„æˆæœ¬ä¸‹é™

### 20.2 SQLite FTS5 å…¨æ–‡ç´¢å¼•

`documents` åŒæ­¥å½±å­è¡¨ `documents_fts`ï¼ˆvirtual tableï¼Œ`unicode61 remove_diacritics 2` tokenizerï¼‰ã€‚

- `save_document()` è‡ªå‹•å¯«å…¥ / æ›´æ–° FTS
- æ–°å¢ž `storage_service.fts_search_documents(query, limit)`ï¼šç”¨ `bm25()` æŽ’åºï¼Œå›žå‚³å« `snippet(documents_fts, 2, 'Â«', 'Â»', ' â€¦ ', 12)` çš„é«˜äº®ç‰‡æ®µ
- æ–°å¢ž API `POST /api/document/fts-search` å›ž `FtsSearchResponse`ï¼ˆå« doc ä¸­ç¹¼è³‡æ–™ + é«˜äº® snippet + bm25 rankï¼‰

å°æ—¢æœ‰çš„ `LIKE %keyword%` æ˜¯ 100Ã—â€“1000Ã— ç´šçš„é€Ÿåº¦å·®è·ï¼›ä¸­æ–‡ä¹Ÿèƒ½å‘½ä¸­ï¼ˆunicode61 tokenizer åˆ‡å­—ï¼‰ã€‚

### 20.3 Pipeline åŸ·è¡Œæ­·å²æŒä¹…åŒ–

æ–°è¡¨ `pipeline_runs`ï¼š

```
run_id (PK), started_at, finished_at, status,
source_name, provider, model_name, keywords (JSON),
user_prompt, payload (JSON), result_summary (JSON), error
```

`services/pipeline_service.py` å…©å€‹å…¥å£éƒ½åŒ…äº† `_start_run` / `_finalize_run`ï¼š

- é€²å…¥ pipeline ç«‹å³å¯«ä¸€ç­† `status="running"` + å®Œæ•´ payload
- æˆåŠŸå¾Œå¯« `status="success"` + `_summarize_pipeline_result()`ï¼ˆåªå­˜ doc_id / title / risk_level / report_file_path çš„ç²¾ç°¡ç‰ˆï¼‰
- å¤±æ•—æœƒå¯« `status="failed"` + `error=str(exc)`ï¼Œä¾‹å¤–ç…§æ¨£å¾€ä¸Šæ‹‹

æ–° APIï¼š

| æ–¹æ³• | ç«¯é»ž | ç”¨é€” |
|------|------|------|
| GET | `/api/pipeline/history?limit=50` | åˆ—æœ€è¿‘åŸ·è¡Œ |
| GET | `/api/pipeline/history/{run_id}` | å–®ç­†å®Œæ•´ç´€éŒ„ï¼ˆå« payloadï¼‰ |

`PipelineRunResponse` / `SearchTrainResponse` ä¹Ÿéƒ½æ–°å¢ž `run_id` æ¬„ï¼Œå‰ç«¯å¯ä»¥ç›´æŽ¥æ‹¿ä¾†è¿½è¹¤ã€‚

### 20.4 LLM JSON ä¿®å¾© + è‡ªå‹• retry

ä¹‹å‰ `LLMService.generate_json` ä¸€é‡åˆ°æ¨¡åž‹å›ž markdown fence å°± `except Exception: pass` ç›´æŽ¥ fallback åˆ°ç©º schemaã€‚æ”¹æˆï¼š

1. `JSON_PARSE_RETRIES = 1`ï¼šç¬¬ä¸€æ¬¡å¤±æ•—å¾Œç­‰ 0.4s å†å‘¼å«ä¸€æ¬¡æ¨¡åž‹
2. `_safe_json_loads` ä¸‰æ®µä¿®å¾©ï¼š
   - ç´” `json.loads`
   - åŽ» ` ```json` / ``` ``` ``` åœæ¬„
   - ç”¨ `\{[\s\S]*\}` æˆªå‡ºç¬¬ä¸€æ®µç–‘ä¼¼ JSONã€å†ä¿® trailing comma èˆ‡å–®å¼•è™Ÿ
3. å…©æ¬¡éƒ½å¤±æ•—æ‰å›ž schema fallback

ç…™éœ§æ¸¬è©¦çµæžœï¼š

| è¼¸å…¥ | çµæžœ |
|------|------|
| `{"a":1}` | âœ“ |
| ` ```json\n{"a":2}\n``` ` | âœ“ |
| `Here is your output: {"a":3, "b":[1,2,3]}` | âœ“ |
| `{"a":4,}` | âœ“ |
| `not json at all` | Noneï¼ˆåˆç† fallbackï¼‰ |

å° Ollama ä¸Š qwen3 / deepseek-r1 é€™é¡žå¶çˆ¾å¤šåä¸€è¡Œ reasoning çš„æ¨¡åž‹ï¼Œå½±éŸ¿ç‰¹åˆ¥æ˜Žé¡¯ã€‚

### 20.5 Anthropic prompt caching

`services/llm_service.py._call_claude` æ”¹æˆæ¨™æº– system + user é›™å€å¡Šæ ¼å¼ï¼Œç•¶å€å¡Šé•·åº¦ â‰¥ `CACHE_PROMPT_THRESHOLD_CHARS = 1500` æ™‚è‡ªå‹•åŠ  `cache_control = {"type": "ephemeral"}`ï¼š

- `system` å€å¡Šï¼šå›ºå®šçš„ Tax Monitor é ˜åŸŸèƒŒæ™¯ï¼ˆç¨…å‹™åŒç¾©è©žé›†ã€ä¿ç•™åŽŸå…¬å¸åç­‰è¦å‰‡ï¼‰
- `user` å€å¡Šï¼šå¯¦éš› promptï¼ˆæœå°‹æ“´å¯« / é¢¨éšªåˆ†æž / å ±å‘Šå¤§ç¶±ï¼‰

å° Claude Opus 4.7 / Sonnet 4.6ï¼Œé‡è¤‡å‘¼å«åŒä¸€ä»½ system + å¤§æ®µ prompt å‘½ä¸­ cache å¾Œ input tokens è¨ˆè²» 0.1Ã— å·¦å³ï¼›åŒä¸€è¼ª pipeline å¤šç¯‡æ–‡ä»¶åˆ†æž â†’ ç›´æŽ¥é«”ç¾åœ¨å¸³å–®ä¸Šã€‚

### 20.6 è©¦ç”¨

```bash
# 1. FTS å°å·² ingest çš„ corpus åšå…¨æ–‡æª¢ç´¢
curl -s -X POST http://127.0.0.1:8010/api/document/fts-search \
  -H "Content-Type: application/json" \
  -d '{"query": "transfer pricing audit OR ç§»è½‰è¨‚åƒ¹ OR è£œå¾µç¨…æ¬¾", "limit": 10}'

# 2. çœ‹æ­·æ¬¡ pipeline run
curl -s http://127.0.0.1:8010/api/pipeline/history?limit=20

# 3. çœ‹å–®ç­†åŸ·è¡Œ payload + summary
curl -s http://127.0.0.1:8010/api/pipeline/history/<run_id>
```

### 20.7 é‚„æ²’åšã€åƒ¹å€¼é«˜çš„ä¸‹ä¸€è¼ªå€™é¸

- Pipeline é€²åº¦äº‹ä»¶ï¼ˆSSE / WebSocketï¼‰è®“ UI å³æ™‚é¡¯ç¤ºã€Œæœå°‹ä¸­ / åˆ†æžç¬¬ 2 ç¯‡ / ç”¢ PPTXã€
- desktop_app åŠ  History tab ç›´æŽ¥æ¶ˆè²» `/api/pipeline/history`
- PPTX è‡ªå‹•åŠ ã€Œè³‡æ–™ä¾†æºã€é ï¼Œå« URL + æŠ“å–æ™‚é–“ + å‘½ä¸­ç†ç”±
- æ¯åŸŸ polite rate limiterï¼ˆtoken bucketï¼‰+ HEAD precheck è·³ 404
- æ–‡ä»¶ ingest size cap + è¶…å¤§ PDF chunk è™•ç†
- æŠŠ `services/document_parser_service.py` æŽ¥ OCR fallbackï¼ˆæŽƒæ PDF ä¸æœƒç©ºç™½ï¼‰

---

## 21. éŸŒæ€§èˆ‡å¯è¿½æº¯æ€§å¼·åŒ–ï¼ˆ2026-05 æ›´æ–°ï¼‰

æŽ¥çºŒ Â§20 çš„æ¸…å–®ï¼Œé€™ä¸€è¼ªåšäº† 5 ä»¶ä¸éœ€è¦æ–°ä¾è³´ã€ä½†æ¯ä»¶éƒ½ç›´æŽ¥å½±éŸ¿ä½¿ç”¨è€…è§€æ„Ÿçš„äº‹ã€‚

### 21.1 æ¯åŸŸ polite rate limiter

`services/search_service.py` æ–°å¢ž `_respect_domain_rate_limit` / `_mark_domain_request`ï¼š

- é è¨­ `DOMAIN_MIN_INTERVAL_SECONDS = 0.7`
- å° SEC EDGARã€Taiwan MOJã€EUR-Lexã€EDINETã€DART ç­‰å…¬å‹™ / ç›£ç®¡ç«™åšæ›´åš´æ ¼çš„ overrideï¼ˆ0.9â€“1.2sï¼‰
- æ¯å€‹ domain å–®ç¨ lockï¼Œä¸æœƒè·¨åŸŸäº’ç›¸é˜»å¡ž
- èˆ‡æ—¢æœ‰çš„ `ThreadPoolExecutor` å¹³è¡Œ fan-out ç„¡è¡çªï¼šåŒ domain è‡ªå‹•æŽ’éšŠï¼Œä¸åŒ domain ä»ç„¶ä¸¦è¡Œ

æ•ˆç›Šï¼š

- SEC EDGAR éŽåŽ»æœ€å®¹æ˜“è¢« 429 bannedï¼Œå› ç‚º official rate guide æ˜¯ â‰¤10 req/sï¼›ç¾åœ¨åš´å®ˆ â‰¥1.1s å€é–“
- æ³•å‹™ / å…¬å‹™ç«™è‹¥åœ¨æŸè¼ªæŸ¥è©¢è¢« throttledï¼Œæ•´æ”¯ pipeline ä¸æœƒå† cascade å¤±æ•—

### 21.2 HEAD precheck

æ–°å¢ž `_head_precheck(url)`ï¼š

- èµ° `requests.Session.head(allow_redirects=True)`
- å‘½ä¸­ 404 / 410 / 451 â†’ å›ž `False`ï¼ˆä¸åŽ»æ‹‰å…¨æ–‡ï¼‰
- `Content-Length > 25 MB` â†’ å›ž `False`ï¼ˆé¿å…ä¸‹è¼‰ 200MB å¹´å ±åŽŸæª”ï¼‰
- `Content-Type` æ˜¯ video / audio / image â†’ å›ž `False`
- é€£ç·šå¤±æ•— fail-openï¼ˆå›ž `True`ï¼Œä¸èª¤æ®ºï¼‰

`pipeline_service.py` çš„ ingest loop åœ¨æŠ“ä»»ä½•æ–‡ä»¶å‰å…ˆ precheckï¼Œçœä¸‹ 404 èˆ‡è¶…å¤§æª”çš„å…¨æ–‡ä¸‹è¼‰ + parser é–‹éŠ·ã€‚

### 21.3 æ–‡ä»¶ ingest size cap + ä¸²æµä¸‹è¼‰

`services/document_service.py` æ–°å¢žå…©å€‹å¸¸æ•¸ï¼š

- `MAX_FETCH_BYTES = 25 * 1024 * 1024`ï¼ˆ25 MBï¼‰
- `MAX_RAW_TEXT_CHARS = 600_000`ï¼ˆâ‰ˆ Claude 4.x Opus context ä¸­æ®µï¼‰

`_fetch_url_content` æ”¹æˆï¼š

1. `requests.get(stream=True)`ï¼Œå…ˆçœ‹ `Content-Length`ï¼Œè¶… cap ç›´æŽ¥æ‹’çµ•
2. 64 KB chunk ä¸²æµä¸‹è¼‰ï¼ŒéŽç¨‹ä¸­ä¹Ÿæª¢æŸ¥ sizeï¼Œé¿å…å›žæ‡‰ header æ’’è¬Š
3. PDF / HTML éƒ½æœƒç¶“éŽ `_cap_text(text)` â€” è¶…éŽ 600k å­—å…ƒå°±æˆªæ–·ä¸¦é™„ `[...truncated by tax-monitor: original exceeded 600000 chars]`

æ•ˆç›Šï¼š

- ä¸æœƒå†å› ç‚ºä¸€ä»½ 200 MB çš„æŽƒæå¹´å ±æŠŠ Python process æ’çˆ†
- å¾ŒçºŒé€é€² LLM åˆ†æžçš„å­—æ•¸æœ‰ ceilingï¼Œé¿å… 1M context æ¨¡åž‹ä¹Ÿè¢«æ‰“åˆ° token ä¸Šé™

### 21.4 PPTX è‡ªå‹•ç”¢å‡ºã€Œè³‡æ–™ä¾†æº / Sources & Citationsã€é 

`services/report_service.py` æ–°å¢ž `_build_sources_slide`ï¼Œåœ¨ `output_format == "pptx"` æ™‚è‡ªå‹• append åˆ° slide_outlineï¼š

å›ºå®šæ¬„ä½ï¼ˆä¾ document / analysis ä¸­ç¹¼è³‡æ–™ï¼‰ï¼š

| æ¬„ä½ | å…§å®¹ |
|------|------|
| åŽŸå§‹æ–‡ä»¶ / Source title | document.title |
| ä¾†æºç¶²å€ / URL | document.url |
| åŽŸå§‹æª”å / File name | document.file_name |
| ä¾†æºé¡žåž‹ / Source | source_type via source_nameï¼ˆä¾‹ï¼š`pdf via sec_edgar`ï¼‰ |
| åŽŸæ–‡èªžè¨€ / Original language | document.language |
| åœ°å€ / ç”¢æ¥­ | country Â· industry |
| åŽŸå§‹ç™¼å¸ƒ / Published | document.published_date |
| åŒ¯å…¥æ™‚é–“ / Ingested at | document.created_at |
| é¢¨éšªåˆ¤æ–· / Risk | risk_level + risk_tags |
| åˆ†æžæ¨¡åž‹ / Generated by | provider / model / target language |
| å ±å‘Šæ™‚é–“ / Report timestamp | å ±å‘Š build ç•¶ä¸‹æ™‚é–“ |
| ä½¿ç”¨è€…æ„åœ– / Research intent | user_promptï¼ˆæˆª 240 å­—ï¼‰ |

å°ç¨…å‹™ç°¡å ±çš„å¯è¿½æº¯æ€§æ˜¯å¿…é ˆé …ï¼›ç®¡ç†å±¤ review æ™‚å¯ç›´æŽ¥å¾žé€™é åˆ¤æ–·è³‡æ–™æ–°é®®åº¦èˆ‡æ¨¡åž‹ç‰ˆæœ¬ã€‚

### 21.5 Desktop History Tab

`desktop_app/results_panel.py` æ–°å¢žç¬¬äº”å€‹ tab `History`ï¼š

- ç›´æŽ¥å‘¼å« `StorageService.list_pipeline_runs(limit=50)`ï¼Œä¸éœ€è¦å…ˆå•Ÿå‹• FastAPI
- åˆ‡åˆ°è©² tab æ™‚è‡ªå‹• refreshï¼ˆ`<<NotebookTabChanged>>`ï¼‰
- å·¥å…·åˆ—æœ‰ `Refresh` æŒ‰éˆ•æ‰‹å‹•é‡æŠ“
- æ¯ç­†é¡¯ç¤ºï¼šstatusã€run_idã€started/finished æ™‚é–“ã€provider/modelã€sourceã€keywordsã€prompt æ‘˜è¦ã€result summaryï¼ˆsearched / ingested / processedï¼‰ã€error

å°ä½¿ç”¨è€…ï¼šè·‘äº† 5 æ¬¡ pipeline ä¹‹å¾Œå¯ä»¥ç›´æŽ¥åœ¨æ¡Œé¢æ¯”å°å“ªä¸€çµ„é—œéµå­—å‘½ä¸­çŽ‡æœ€é«˜ã€PPTX è½åœ¨å“ªè£¡ï¼Œä¸éœ€è¦å†åŽ»ç¿» SQLiteã€‚

### 21.6 æŽ§åˆ¶èˆ‡è§€å¯Ÿ

- é€ŸçŽ‡é™åˆ¶ï¼š`SearchService.DOMAIN_MIN_INTERVAL_SECONDS`ã€`SearchService.DOMAIN_MIN_INTERVAL_OVERRIDES`
- HEAD ä¸Šé™ï¼š`SearchService.HEAD_PRECHECK_MAX_BYTES = 25 MB`
- æ–‡ä»¶å¤§å°ä¸Šé™ï¼š`document_service.MAX_FETCH_BYTES`ã€`MAX_RAW_TEXT_CHARS`
- æ¡Œé¢æ­·å²é åˆ‡æ›æ™‚è‡ªå‹• refreshï¼Œå¯ä»¥éš¨æ™‚æ‰‹å‹•æŒ‰ Refresh

### 21.7 é‚„æ²’åšã€ä¸‹ä¸€è¼ªå€™é¸

- Pipeline é€²åº¦äº‹ä»¶ï¼ˆSSE / WebSocketï¼‰ï¼š`run_pipeline` æ³¨å…¥ callbackï¼ŒUI å³æ™‚é¡¯ç¤ºã€Œå·²æœå°‹ 12 ç­† / åˆ†æžç¬¬ 2 ç¯‡ / ç”¢ PPTX ä¸­ã€
- OCR fallbackï¼ˆpytesseract / EasyOCRï¼‰ï¼šæŽƒæ PDF ä¸å†å›žç©ºå­—ä¸²
- PDF è¡¨æ ¼æŠ½å–ï¼ˆcamelot / pdfplumberï¼‰ï¼šå¹´å ±å¸¸æŠŠæ‰€å¾—ç¨…è²»ç”¨ã€ç§»è½‰è¨‚åƒ¹é‡‘é¡æ”¾è¡¨æ ¼å…§
- KeywordService å¢žé‡è¨“ç·´ï¼šè·¨ ingest batch reuse vectorizerï¼Œçœ fit time
- æ¡Œé¢ç‰ˆåŠ  dark mode + å­—åž‹åˆ‡æ›

---

## 22. å¹³è¡ŒåŒ¯å…¥ã€è¡¨æ ¼æŠ½å–ã€é€²åº¦å›žå‘¼ã€Markdown å ±å‘Šï¼ˆ2026-05 æ›´æ–°ï¼‰

æŽ¥çºŒ Â§21.7 çš„æ¸…å–®ï¼Œé€™ä¸€è¼ªåš 4 ä»¶ï¼šæŠŠ ingest å¾žåºåˆ—æ”¹å¹³è¡Œã€PDF è¡¨æ ¼ä¸å†è¢«ä¸ŸæŽ‰ã€æ¡Œé¢ UI å³æ™‚çœ‹åˆ°é€²åº¦ã€å ±å‘Šå¤šä¸€å€‹ç´” markdown æ ¼å¼ã€‚

### 22.1 å¹³è¡Œæ–‡ä»¶åŒ¯å…¥ï¼ˆasyncio.gather + Semaphoreï¼‰

ä¹‹å‰ `pipeline_service` æ˜¯ `for item in results: await process_url(...)`ï¼Œ5 ç¯‡æ–‡ä»¶ç­‰æ–¼ 5 æ¬¡åºåˆ— HTTP+parseã€‚

æ”¹é€ ï¼š

1. `services/document_service.py` æŠŠ `_fetch_url_content`ï¼ˆåŒæ­¥é˜»å¡žï¼‰åŒ…é€² `await asyncio.to_thread(self._fetch_url_content, url)`ï¼Œè®“ `process_url` çœŸçš„èƒ½åœ¨å¤š coroutine ä¸¦è¡Œ
2. `services/pipeline_service.py` æ–°å¢ž `_ingest_items_concurrently`ï¼š`asyncio.Semaphore(INGEST_CONCURRENCY=4)` æŽ§åˆ¶æœ€å¤š 4 å€‹åŒæ™‚ä¸‹è¼‰
3. å…©å€‹ pipeline å…¥å£ï¼ˆ`run_pipeline` / `search_ingest_and_train`ï¼‰çš„ ingest è¿´åœˆéƒ½æ”¹ç”¨é€™å€‹ helper

å¯¦æ¸¬ï¼ˆsynthetic 8 ç¯‡ Ã— 0.3sï¼‰ï¼š

```
serial estimate: 2.40s
concurrent actual: 0.633s   (â‰ˆ 3.8Ã— speedup, concurrency=4)
```

å°å¯¦éš› 30 ç¯‡ Ã— 1â€“3s çš„ HTTP æŠ“å–ï¼Œæ•´é«” wall-clock é€šå¸¸æœƒé™åˆ°åŽŸæœ¬çš„ 25â€“35%ã€‚

### 22.2 PDF è¡¨æ ¼æŠ½å–ï¼ˆpdfplumberï¼‰

ç¨…å‹™å¹´å ±æœ€é—œéµçš„æ•¸å­—ï¼ˆæ‰€å¾—ç¨…è²»ç”¨ã€æœ‰æ•ˆç¨…çŽ‡ã€ç§»è½‰è¨‚åƒ¹é‡‘é¡ã€å­å…¬å¸æ¸…å–®ï¼‰å¹¾ä¹Žéƒ½åœ¨è¡¨æ ¼è£¡ï¼Œpypdf æŠŠè¡¨æ ¼æ‰å¹³åŒ–æœƒç ´å£žæ¬„ä½å°é½Šã€‚

`services/document_parser_service.py` æ”¹æˆï¼š

1. å˜—è©¦ `import pdfplumber`ï¼Œæ²’è£å°± graceful skipï¼ˆ**pdfplumber æ˜¯é¸ç”¨**ï¼ŒåŠ é€² `requirements.txt` å°±æœƒå•Ÿç”¨ï¼‰
2. PDF è§£æžå®Œå¾Œå‘¼å« `_enrich_pdf_with_tables`ï¼šå°æ¯é è·‘ `extract_tables()`ï¼ŒæŠŠæ¯å¼µè¡¨ render æˆ `cell | cell | cell` è¡Œï¼Œé™„ `[Table extracted via pdfplumber] page=X table=Y` headerï¼Œappend åˆ° raw_text
3. ä¸Šé™ `PDFPLUMBER_MAX_PAGES=50`ã€`PDFPLUMBER_MAX_TABLES=30`ï¼Œé¿å…ç™¾é å¹´å ±å¡žçˆ† raw_text
4. éŽæ¿¾æŽ‰ã€Œè¡Œæ•¸ < 2 æˆ–æœ‰æ•ˆ cell < 4ã€çš„é›œè¨Šè¡¨æ ¼

æœªå®‰è£ pdfplumber æ™‚è¡Œç‚ºèˆ‡ä¹‹å‰å®Œå…¨ä¸€è‡´ï¼›å®‰è£å¾Œ raw_text æœ«æ®µæœƒå¤šå‡ºçµæ§‹åŒ–è¡¨æ ¼ï¼ŒKeywordService èˆ‡ LLM åˆ†æžéƒ½åƒå¾—åˆ°ã€‚

### 22.3 Pipeline é€²åº¦å›žå‘¼

`services/pipeline_service.py` æ–°å¢ž `progress_callback: Optional[PipelineProgressCallback]` åƒæ•¸ã€‚è§¸ç™¼é»žï¼š

| äº‹ä»¶ | å…§å®¹ |
|------|------|
| `run_started` | run_id + payload |
| `search_started` / `search_completed` | source_name, keywords / count |
| `ingest_phase_started` / `ingest_phase_completed` | total / ingested |
| `ingest_started` / `ingest_completed` / `ingest_failed` / `ingest_skipped` | index, url, deduplicated, error |
| `analysis_started` / `analysis_completed` | doc_id, risk_level |
| `report_started` / `report_completed` | format, file_path |
| `run_completed` / `run_failed` | run_id, processed/error |

`desktop_app/worker.py` æŽ¥å— `on_progress` å›žå‘¼ï¼›`desktop_app/app.py` æŠŠäº‹ä»¶ marshal åˆ°ä¸»åŸ·è¡Œç·’ï¼›`desktop_app/results_panel.py` æ–°å¢ž `update_progress` + `_format_progress_event`ï¼ŒæŠŠæ¯å€‹äº‹ä»¶è®Šæˆä¸€è¡Œäººé¡žçœ‹çš„å­—ï¼Œæ›´æ–°åˆ°åŽŸæœ¬çš„ `Status` labelã€‚

å¯¦éš›ä½¿ç”¨é«”æ„Ÿï¼š

```
Searching (deep_research): ASUS, æŸ¥ç¨…
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

ä¹‹å‰ä¸€ç›´åœåœ¨ `Running...`ï¼›ç¾åœ¨æ¯å¹¾ç§’å°±æœ‰ä¸€è¡Œæ–°çš„é€²åº¦ã€‚

### 22.4 Markdown å ±å‘Šè¼¸å‡º

ä¹‹å‰åªæœ‰ obsidian / slides / pptxã€‚æ–°å¢ž `markdown` æ ¼å¼ï¼š

- `models/schemas.py` `ReportRequest.output_format` / `PipelineRunRequest.report_format` çš„ regex åŠ ä¸Š `|markdown`
- `services/report_service.py` æ–°å¢ž `_build_markdown_report` + `_write_markdown_file`ï¼Œè¼¸å‡ºç´” GitHub-flavored markdown
- çµæ§‹ï¼šExecutive summary â†’ Risk level / tags â†’ Auto-extracted keywords â†’ Key evidence â†’ Notes â†’ Slide outline â†’ **Sources & metadata**ï¼ˆå« URLã€ç”Ÿæˆæ¨¡åž‹ã€å ±å‘Šæ™‚é–“ã€ä½¿ç”¨è€…æ„åœ–ï¼‰

å°å¤–åˆ†äº«æ¯” obsidian frontmatter ä¹¾æ·¨ï¼Œæ¯” PPTX è¼•é‡ï¼›å¯ç›´æŽ¥è²¼åˆ° GitHub Issue / Wiki / Notionã€‚

### 22.5 è©¦ç”¨

```json
POST /api/pipeline/run
{
  "keywords": ["TSMC æŠ½æ¨£é¸æ¡ˆæŸ¥æ ¸é¢¨éšª"],
  "source_name": "deep_research",
  "max_results": 30,
  "max_documents_to_process": 5,
  "report_format": "markdown",
  "provider": "claude",
  "model_name": "claude-sonnet-4-6",
  "use_ai_query_expansion": true
}
```

æˆ– desktopï¼š

1. `python -m desktop_app`
2. è¼¸å…¥é—œéµå­—ã€æŒ‰ `Run research`
3. ä¸Šæ–¹ Status label å³æ™‚è·³ï¼š`Searchingâ€¦ â†’ Ingested 3/12 â†’ Analyzing #1 â†’ Report ready: â€¦`
4. åœ¨ `data/reports/` å‡ºç¾ `.md` æª”ï¼ˆå¦‚æžœåˆ‡åˆ° markdownï¼‰ï¼Œæˆ– `.pptx`ï¼ˆé è¨­ï¼‰

é¸ç”¨å®‰è£ï¼š

```powershell
.\.venv\Scripts\python.exe -m pip install pdfplumber
```

è£å®Œä¹‹å¾Œ PDF ingest æœƒè‡ªå‹•æŠŠè¡¨æ ¼å¡žé€² raw_textã€‚

### 22.6 é‚„æ²’åšã€ä¸‹ä¸€è¼ªå€™é¸

- **OCR fallback**ï¼ˆpytesseract / EasyOCRï¼‰ï¼šæŽƒæåž‹ PDF ä¸æœƒå›žç©ºå­—ä¸²
- **CSV / XLSX åŒ¯å‡º**ï¼šæŠŠ search_resultsã€ingested_documentsã€analyses ä¸€éµåŒ¯å‡ºè¡¨æ ¼
- **Run comparison**ï¼š`/api/pipeline/runs/compare?a=...&b=...` å›žå‚³å…©æ¬¡åŸ·è¡Œçš„ doc å·®é›†
- **Pipeline cancel**ï¼šworker æš´éœ² cancel tokenï¼Œdesktop UI åŠ ç´…è‰²åœæ­¢éˆ•
- **Dark mode / å­—åž‹åˆ‡æ›**
- **Per-pipeline æˆæœ¬è¿½è¹¤**ï¼šç´¯ç© LLM tokens / ä¼°ç®— USDï¼Œå­˜é€² `pipeline_runs.cost_summary`

---

## 23. æˆæœ¬è¿½è¹¤ã€Pipeline ä¸­æ–·ã€è¡¨æ ¼åŒ¯å‡ºã€Dark Modeï¼ˆ2026-05 æ›´æ–°ï¼‰

é€™ä¸€è¼ªè§£ 4 å€‹å¾žç‡Ÿé‹é¢é•·å‡ºä¾†çš„éœ€æ±‚ï¼šåˆ‡åˆ°ä»˜è²» LLM å¾Œæƒ³çŸ¥é“èŠ±å¤šå°‘ã€é•· pipeline æƒ³ä¸­é€”åœã€çµ¦æ³•å‹™åŒäº‹çš„å ±å‘Šè¦è©¦ç®—è¡¨ã€æ¡Œé¢è¦ dark modeã€‚

### 23.1 LLM token ç”¨é‡è¿½è¹¤

`services/llm_service.py` æ¯å€‹ provider å‘¼å«å™¨æ”¹æˆå›žå‚³ `(text, usage)`ï¼Œä¸¦æŠŠæ¯æ¬¡ usage å¯«é€² thread-safe çš„ `_usage_records`ï¼š

| Provider | input | output | cache_read | cache_write |
|----------|-------|--------|------------|-------------|
| Claude | `usage.input_tokens` | `usage.output_tokens` | `usage.cache_read_input_tokens` | `usage.cache_creation_input_tokens` |
| OpenAI | `usage.prompt_tokens` | `usage.completion_tokens` | `prompt_tokens_details.cached_tokens` | â€” |
| Gemini | `usageMetadata.promptTokenCount` | `usageMetadata.candidatesTokenCount` | `cachedContentTokenCount` | â€” |
| Ollama | `prompt_eval_count` | `eval_count` | â€” | â€” |

æ–°å…¬é–‹æ–¹æ³•ï¼š

- `LLMService.consume_usage_records()` â€” å–èµ°ä¸¦æ¸…ç©ºï¼ˆpipeline çµæŸæ™‚å‘¼å«ï¼‰
- `LLMService.reset_usage_records()` â€” pipeline é–‹å§‹æ™‚æ¸…é›¶
- `LLMService.get_usage_summary()` â€” å³æ™‚çœ‹ç•¶ä¸‹ç´¯ç©

### 23.2 Per-pipeline cost summary

`services/pipeline_service.py`ï¼š

1. `_reset_token_counters()` åœ¨ pipeline é–‹å§‹æ™‚å° search / analysis / report / keyword å››å€‹ service çš„ `llm_service` å…¨éƒ¨ `reset_usage_records`
2. `_collect_token_usage()` èšåˆæ‰€æœ‰ service çš„ recordsï¼Œç”¢ç”Ÿ `{ totals, per_model }` çµæ§‹
3. æˆåŠŸ / å¤±æ•— / å–æ¶ˆ ä¸‰æ¢è·¯å¾‘éƒ½æœƒæŠŠ `cost` å­˜é€² `pipeline_runs.result_summary` ä¸¦é€éŽ progress callback æš´éœ²
4. `_summarize_pipeline_result()` ä¹Ÿå¸¶å…¥ `cost`ï¼Œé€™æ¨£ `/api/pipeline/history` ç›´æŽ¥çœ‹å¾—åˆ°

å¯¦æ¸¬ï¼ˆsyntheticï¼‰ï¼š

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

`cache_read_tokens` é¡¯ç¤º Â§20.5 çš„ Anthropic prompt caching çœŸçš„æœ‰å‘½ä¸­ï¼Œåœ¨é€£çºŒå‘¼å«åŒ system prompt æ™‚èƒ½ç›´æŽ¥çœ‹åˆ° token é‡ç”¨ã€‚

### 23.3 Pipeline å–æ¶ˆ

æ–°é¡žåˆ¥ `PipelineCancelled(Exception)`ã€‚`pipeline_service` æŽ¥å— `cancel_event: Optional[threading.Event]`ï¼š

- `_check_cancel(event)` æª¢æŸ¥ eventï¼Œset äº†å°± raise `PipelineCancelled`
- æª¢æŸ¥é»žï¼šsearch å‰å¾Œã€ingest éšŽæ®µå‰å¾Œã€analysis èˆ‡ report æ¯ç¯‡é–‹å§‹å‰
- ä¸¦è¡Œ ingest ä¹Ÿæœƒåœ¨æ¯å€‹ task é€²å…¥æ™‚æª¢æŸ¥ï¼›å·² in-flight çš„ HTTP æŠ“å–æœƒè‡ªç„¶å®Œæˆä¸æœƒä¸­æ–·ï¼ˆé¿å… partial stateï¼‰
- çµæŸè·¯å¾‘ï¼šå–æ¶ˆ â†’ `status="cancelled"` å¯«å…¥ `pipeline_runs`ï¼Œä¸¦æŠŠç•¶ä¸‹ç´¯ç©çš„ cost ä¸€èµ·å­˜

æ¡Œé¢æ•´åˆï¼š

- `desktop_app/worker.py` å…§å»º `threading.Event` cancel_eventï¼›å…¬é–‹ `cancel()` / `is_running()`
- æ–°å¢ž `on_cancelled` callback
- `desktop_app/input_panel.py` æ–°å¢ž **Stop** æŒ‰éˆ•ï¼ˆåŸ·è¡Œä¸­æ‰ enableï¼‰
- `desktop_app/app.py` æŠŠ Stop é€£åˆ° `worker.cancel()`ï¼ŒUI ä¸Šç«‹å³é¡¯ç¤º `Cancellation requested...`
- `desktop_app/results_panel.py` åŠ  `run_cancelled` äº‹ä»¶è™•ç†ï¼Œç‹€æ…‹åˆ—é¡¯ç¤º `Pipeline cancelled by user`

### 23.4 æ–‡ä»¶ CSV / XLSX åŒ¯å‡º

æ–° endpointï¼š

```
GET /api/document/export?format=csv&keyword=tax&country=TW&limit=500
GET /api/document/export?format=xlsx&industry=technology&limit=200
```

- CSV ç”¨æ¨™æº–å‡½å¼åº« `csv` + UTF-8 BOMï¼ˆExcel é–‹ç¹ä¸­ä¸äº‚ç¢¼ï¼‰
- XLSX èµ° `openpyxl`ï¼ˆé¸ç”¨ï¼‰ï¼Œæœªå®‰è£æ™‚å›ž 503 ä¸¦æç¤ºå®‰è£
- æ¬„ä½ï¼š`doc_id, title, source_type, source_name, language, country, industry, published_date, created_at, updated_at, url`
- éŽæ¿¾åƒæ•¸æ²¿ç”¨ `list_documents`ï¼škeyword / country / industry / language
- æª”åè‡ªå‹•åŠ æ™‚æˆ³ï¼š`tax_monitor_documents_20260507_163215.csv`

### 23.5 Dark Mode åˆ‡æ›

`desktop_app/app.py` æŠ½å‡º `LIGHT_THEME` / `DARK_THEME` palette èˆ‡ `apply_theme(dark)` æ–¹æ³•ã€‚åº•å±¤æ”¹ï¼š

- ttk çš„ TFrame / TLabel / TCheckbutton / TNotebook / TNotebook.Tab / TCombobox å…¨éƒ¨è·Ÿè‘—åˆ‡æ›
- é€éŽ `_apply_text_theme` éžè¿´æŠŠæ‰€æœ‰ `tk.Text` widget çš„ background / foreground / insertbackground ä¹Ÿæ›æŽ‰
- `desktop_app/input_panel.py` æ–°å¢ž `Dark mode` checkboxï¼Œåˆ‡æ›æ™‚å‘¼å« root window çš„ `apply_theme`
- é è¨­ lightï¼Œç‹€æ…‹å­˜åœ¨ `tk.BooleanVar`ï¼Œè¦–çª—é—œé–‰å°±å›žåˆ° lightï¼ˆä¸æŒä¹…åŒ–ï¼‰

### 23.6 è©¦ç”¨

```powershell
# æ¡Œé¢ï¼šè·‘ä¸€æ¬¡ â†’ çœ‹ status åˆ—å°¾å·´é¡¯ç¤º LLM tokens
.\.venv\Scripts\python.exe -m desktop_app
# åˆ‡åˆ° Dark modeï¼›æŒ‰ Stop ä¸­æ–·ï¼›é—œæŽ‰ Dark mode

# APIï¼šCSV åŒ¯å‡º
curl -o asus.csv "http://127.0.0.1:8010/api/document/export?format=csv&keyword=ASUS"

# APIï¼šXLSX åŒ¯å‡ºï¼ˆéœ€å…ˆ pip install openpyxlï¼‰
curl -o tw_tax.xlsx "http://127.0.0.1:8010/api/document/export?format=xlsx&country=TW&industry=technology"

# APIï¼šæ­·å²ç´€éŒ„çœ‹ cost
curl http://127.0.0.1:8010/api/pipeline/history?limit=10
```

é€²åº¦åˆ—å°¾å·´ç¯„ä¾‹ï¼š

```
Pipeline complete: ingested=8 processed=3 Â· LLM tokens in/out=42100/8200 cache_read=18400
```

### 23.7 é‚„æ²’åšã€ä¸‹ä¸€è¼ªå€™é¸

- **USD ä¼°åƒ¹å±¤**ï¼ˆper-provider per-model å–®åƒ¹è¡¨ï¼Œè‡ªå‹•æŠŠ tokens Ã— å–®åƒ¹ç®—æˆ USDï¼‰
- **OCR fallback**ï¼ˆpytesseractï¼‰
- **Run comparison**ï¼ˆå…©æ¬¡åŸ·è¡Œçš„ doc å·®é›†ã€æ–°å¢ž / ç§»é™¤æ–‡ä»¶ï¼‰
- **Pipeline retry on transient failure**ï¼ˆHTTP 5xx è‡ªå‹•é‡è·‘å–®ç¯‡ï¼‰
- **API èªè­‰**ï¼ˆFastAPI Bearer tokenï¼‰
- **Document age annotation**ï¼ˆæœå°‹çµæžœæ—é‚Šé¡¯ç¤º `30 days ago`ï¼‰

## 24. Windows 一鍵安裝包

建議交付一般使用者的檔案：

```text
release\TaxMonitor-Setup.exe
```

備用 ZIP 安裝包：

```text
release\TaxMonitor-Windows-Installer.zip
```

### 24.1 使用者安裝流程

建議方式：

1. 雙擊 `TaxMonitor-Setup.exe`。
2. 等待安裝器自動解壓並執行安裝。
3. 安裝完成後，從桌面捷徑 `Tax Monitor` 啟動。

備用方式：

1. 解壓縮 `TaxMonitor-Windows-Installer.zip`。
2. 雙擊 `install.bat`。
3. 安裝完成後，從桌面捷徑 `Tax Monitor` 啟動。

安裝包已包含 Python runtime、Tkinter 桌面程式與主要 Python 依賴；一般使用者不需要另外安裝 Python 或執行 `pip install`。

### 24.2 Ollama / Qwen 本地模型

安裝包內建 Tax Monitor 桌面程式與 Python 依賴，但不會把 Ollama 模型一起塞進安裝包，因為單一模型通常就有數 GB。

桌面版右側新增 `LLM Setup` 分頁，可直接：

- 檢查本機是否已安裝 Ollama
- 用 `winget` 嘗試安裝 Ollama
- 從清單選擇並下載 Ollama 模型，例如 `qwen3:8b`
- 查看本機已安裝模型

手動安裝模型也可以使用：

```powershell
ollama pull qwen3:8b
```

安裝完成後可用：

```powershell
ollama run qwen3:8b
```

看到可以對話後輸入 `/bye` 離開即可。

### 24.3 Release 內容

```text
release\
  TaxMonitor-Setup.exe                # 推薦交付：單檔一鍵安裝器
  TaxMonitor-Windows-Installer.zip    # 備用：解壓後雙擊 install.bat
  SHA256SUMS.txt                      # 檔案完整性驗證
```

ZIP 內部結構：

```text
TaxMonitor-Windows-Installer\
  install.bat              # 一鍵安裝
  install.ps1              # 複製程式並建立桌面/開始選單捷徑
  run_without_install.bat  # 不安裝，直接從解壓縮資料夾啟動
  uninstall.bat            # 解除安裝
  README_INSTALL.txt       # 給使用者看的簡短說明
  TaxMonitor\              # PyInstaller 打包後的桌面程式
```

雲端 LLM（OpenAI / Gemini / Claude / Qwen Cloud）不需要安裝模型；只要在左側輸入 API key，或事先設定環境變數 `OPENAI_API_KEY`、`GEMINI_API_KEY`、`ANTHROPIC_API_KEY`、`DASHSCOPE_API_KEY`。

### 24.4 Tkinter 桌面版研究助理

安裝後啟動桌面捷徑 `Tax Monitor`，右側結果區會有 `Assistant` 分頁。

使用情境：

1. 先在左側輸入公司、子公司或稅務風險關鍵字，執行 `Run research`。
2. 如果結果太少、太集中在單一來源、或沒有涵蓋子公司/跨國稅務議題，切到 `Assistant`。
3. 直接輸入你的不滿意點，例如：

```text
這次資料太少，請加入華碩所有子公司、英文來源、轉讓訂價、扣繳稅、常設機構與 Pillar Two 風險。
```

LLM 會產生下一輪搜尋建議，包含：

- 建議關鍵字
- 下一輪研究指令
- 搜尋來源
- 資料期間
- 搜尋筆數與 PPTX 處理筆數

可以按 `Apply settings` 套用到左側搜尋設定，也可以按 `Apply + rerun` 直接重新執行。

### 24.5 Tkinter n8n 自動化分頁

右側新增 `n8n Automation` 分頁，用來把目前左側的研究設定轉成 n8n workflow。

建議流程：

1. 在左側輸入公司、子公司、風險關鍵字、資料期間與模型。
2. 到 `n8n Automation` 分頁按 `Start API server`，讓 n8n 可以呼叫 Tax Monitor。
3. 按 `Check API` 確認 `http://127.0.0.1:8010` 可用。
4. 按 `Export n8n JSON` 產出可匯入 n8n 的 workflow。
5. 到 n8n 匯入該 JSON，或填入 n8n API key 後按 `Import via n8n API` 嘗試自動匯入。

匯出的 workflow 會呼叫：

```text
POST http://127.0.0.1:8010/api/pipeline/run
```

也就是一次完成：

- 搜尋資料
- 匯入文件
- 稅務風險分析
- 產出 PPTX
- 回傳 PPTX 路徑給 n8n

若電腦尚未安裝 n8n，可在該分頁按 `Start n8n with npx`。此功能需要先有 Node.js / npx；如果沒有，程式會引導到 Node.js 下載頁。

### 24.6 可安裝電腦範圍

目前的 `TaxMonitor-Setup.exe` 是 Windows 版安裝包，建議使用：

- Windows 10 / Windows 11
- 64-bit x86 電腦
- 一般使用者權限即可安裝到 `%LOCALAPPDATA%\Programs\TaxMonitor`

注意：

- 這不是 macOS / Linux 安裝包；那些系統需要另外打包。
- 若公司電腦封鎖未簽章 EXE、PowerShell、`winget` 或網路下載，安裝器仍可能被 IT 原則擋下。
- 若要使用本地 LLM，使用者電腦還需要能下載 Ollama 與模型。
- 若要使用 n8n，使用者電腦還需要 Node.js/npx、Docker，或已經有一台可連線的 n8n server。

### 24.7 檔案完整性驗證

可用 PowerShell 驗證 SHA256：

```powershell
Get-FileHash .\release\TaxMonitor-Setup.exe -Algorithm SHA256
Get-Content .\release\SHA256SUMS.txt
```

### 24.8 注意事項

- 此安裝包未做程式碼簽章，Windows SmartScreen 可能提示未知發行者。確認來源可信後，可選「其他資訊」→「仍要執行」。
- 首次啟動時若防毒軟體掃描，可能需要等待幾秒。
- 若要重新打包 Tkinter 桌面版，直接執行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\build_windows_installer.ps1
```

此腳本會自動重建 PyInstaller 桌面程式、ZIP 備用包、單檔 `TaxMonitor-Setup.exe` 與 `SHA256SUMS.txt`。內部使用 PyInstaller `--windowed`，避免使用者啟動時多出黑色命令視窗。


