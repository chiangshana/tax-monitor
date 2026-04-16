# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 專案概述

**跨國法令與稅務風險監測系統** — 以 FastAPI 建構的後端服務，支援法規文件的匯入（PDF 上傳或網址擷取）、關鍵字提取與稅務風險分析。目前為原型系統。

## 常用指令

```bash
# 安裝相依套件
pip install -r requirements.txt

# 啟動開發伺服器
python -m uvicorn main:app --reload

# API 文件（伺服器啟動後）
# http://127.0.0.1:8000/docs
```

目前尚未設定測試套件或 linter。

## 系統架構

三層式管線架構：

1. **文件層**（`services/document_service.py`）— PDF 文字擷取（pypdf）、網頁爬取（BeautifulSoup）、語言偵測，最後透過 `storage_service.py` 存入 SQLite。
2. **分析層**（`services/analysis_service.py`）— TF-IDF 關鍵字提取（`keyword_service.py`）、句子級摘要、風險等級判斷、可選的 LLM 翻譯（`translator_service.py`）。
3. **儲存層**（`services/storage_service.py`）— SQLite 資料庫位於 `data/tax_monitor.db`，僅有單一 `documents` 資料表。

### 核心設計理念

- **情境優化：** 分析前先提取關鍵字與重要句子，降低 LLM 輸入雜訊。
- **逆向驗證：** 將分析結論與原始文本比對，減少錯誤。
- **雙模式分析**（於 `POST /api/analysis/run` 傳入）：
  - `translate_first` — 先翻譯文件，再進行分析
  - `analyze_first` — 先分析，再翻譯摘要

### LLM 整合

選用性功能，透過本地 Ollama 服務呼叫（`http://localhost:11434/api/generate`），預設模型為 `qwen2.5:7b`。若 Ollama 無法使用，系統會退回規則式翻譯。

### API 端點

| 方法 | 端點 | 說明 |
|------|------|------|
| POST | `/api/document/upload` | 上傳 PDF 或文字檔 |
| POST | `/api/document/ingest-url` | 擷取網頁內容 |
| GET | `/api/document/list` | 列出所有文件 |
| GET | `/api/document/keywords/{doc_id}` | 預覽自動提取的關鍵字 |
| POST | `/api/document/train-keywords` | 重新訓練 TF-IDF 模型 |
| POST | `/api/analysis/run` | 執行分析（`translate_first` 或 `analyze_first`） |
| GET | `/api/analysis/translation-preview/{doc_id}` | 預覽翻譯結果 |

### 檔案結構

```
main.py              # FastAPI 應用程式與路由註冊
models/schemas.py    # 所有 Pydantic 請求／回應模型
routers/             # HTTP 端點處理（委派給 services）
services/            # 核心業務邏輯
data/uploads/        # 上傳檔案目錄（已加入 .gitignore）
data/tax_monitor.db  # SQLite 資料庫（已加入 .gitignore）
```
