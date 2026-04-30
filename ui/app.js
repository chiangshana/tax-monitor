const form = document.getElementById("searchTrainForm");
const modeSelect = document.getElementById("mode");
const manualUrlsWrap = document.getElementById("manualUrlsWrap");
const submitBtn = document.getElementById("submitBtn");
const globalScope = document.getElementById("globalScope");
const countryInput = document.getElementById("country");
const sourceSelect = document.getElementById("sourceName");
const keywordsInput = document.getElementById("keywords");
const keywordPreview = document.getElementById("keywordPreview");

const statusText = document.getElementById("statusText");
const searchedCount = document.getElementById("searchedCount");
const ingestedCount = document.getElementById("ingestedCount");
const trainedDocCount = document.getElementById("trainedDocCount");
const vocabSize = document.getElementById("vocabSize");
const pptxCount = document.getElementById("pptxCount");
const trainMessage = document.getElementById("trainMessage");
const searchResultsList = document.getElementById("searchResultsList");
const documentsList = document.getElementById("documentsList");
const pptxList = document.getElementById("pptxList");

function toggleManualUrls() {
  manualUrlsWrap.classList.toggle("hidden", modeSelect.value !== "manual");
}

function toggleGlobalScope() {
  const isGlobal = globalScope.checked;
  countryInput.disabled = isGlobal;
  if (isGlobal) {
    countryInput.dataset.previousValue = countryInput.value;
    countryInput.value = "";
  } else if (!countryInput.value) {
    countryInput.value = countryInput.dataset.previousValue || "TW";
  }
}

function parseKeywords(rawValue) {
  return rawValue
    .split(/[\n,，;；|]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function renderKeywordPreview() {
  const parsed = parseKeywords(keywordsInput.value);
  if (!parsed.length) {
    keywordPreview.textContent = "可直接貼逗號、分號、換行混合格式，系統會自動整理成搜尋關鍵字。";
    return;
  }
  keywordPreview.textContent = `系統會用這 ${parsed.length} 個關鍵字去研究：${parsed.join("、")}`;
}

function parseCandidateUrls(rawValue) {
  return rawValue
    .split(/\n+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function renderDocuments(documents) {
  if (!documents.length) {
    documentsList.innerHTML = '<p class="empty-text">這次沒有成功匯入任何文件。</p>';
    return;
  }

  documentsList.innerHTML = documents
    .map((doc) => {
      const chips = (doc.extracted_keywords || [])
        .map((keyword) => `<span class="chip">${keyword}</span>`)
        .join("");

      return `
        <article class="document-item">
          <h4>${doc.title || "未命名文件"}</h4>
          <p class="document-meta">doc_id: ${doc.doc_id}</p>
          <p class="document-meta">來源: ${doc.url || "N/A"}</p>
          <p class="document-meta">發布時間: ${doc.published_at || "N/A"}</p>
          <p class="document-meta">風險等級: ${doc.risk_level || "尚未分析"}</p>
          <div class="keyword-chips">${chips || '<span class="chip">目前沒有抽到關鍵字</span>'}</div>
        </article>
      `;
    })
    .join("");
}

function renderSearchResults(results) {
  if (!results.length) {
    searchResultsList.innerHTML = '<p class="empty-text">這次沒有可顯示的搜尋線索。</p>';
    return;
  }

  searchResultsList.innerHTML = results
    .map((item) => {
      const reasons = (item.match_reasons || [])
        .map((reason) => `<span class="chip">${reason}</span>`)
        .join("");

      return `
        <article class="document-item">
          <h4>${item.title || "未命名搜尋結果"}</h4>
          <p class="document-meta">來源：${item.source || "N/A"}</p>
          <p class="document-meta">網域：${item.domain || "N/A"} | 類型：${item.result_type || "N/A"} | 分數：${item.relevance_score ?? 0}</p>
          <p class="document-meta">時間：${item.published_at || "N/A"}</p>
          <p class="document-meta">連結：${item.url || "N/A"}</p>
          <div class="keyword-chips">${reasons || '<span class="chip">目前沒有排序理由</span>'}</div>
        </article>
      `;
    })
    .join("");
}

function renderPptxResults(documents) {
  const generated = documents.filter((doc) => doc.pptx_file_path);
  if (!generated.length) {
    pptxList.innerHTML = '<p class="empty-text">這次沒有產出 PPTX。</p>';
    return;
  }

  pptxList.innerHTML = generated
    .map((doc) => {
      const tags = (doc.risk_tags || [])
        .map((tag) => `<span class="chip">${tag}</span>`)
        .join("");

      return `
        <article class="document-item">
          <h4>${doc.title || "未命名文件"}</h4>
          <p class="document-meta">風險等級: ${doc.risk_level || "N/A"}</p>
          <p class="document-meta">PPTX 路徑: ${doc.pptx_file_path}</p>
          <div class="keyword-chips">${tags || '<span class="chip">目前沒有風險標籤</span>'}</div>
        </article>
      `;
    })
    .join("");
}

async function runSearchTrain(payload) {
  const response = await fetch("/api/pipeline/search-train", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Request failed");
  }

  return response.json();
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const keywords = parseKeywords(document.getElementById("keywords").value);
  if (!keywords.length) {
    statusText.textContent = "請至少輸入一個搜尋關鍵字。";
    statusText.classList.add("error-text");
    return;
  }

  statusText.classList.remove("error-text");
  submitBtn.disabled = true;
  submitBtn.textContent = "系統執行中...";
  statusText.textContent = "正在批量搜尋、匯入資料並重訓關鍵字模型...";

  try {
    const payload = {
      keywords,
      user_prompt: document.getElementById("userPrompt").value.trim() || null,
      mode: modeSelect.value,
      date_range: document.getElementById("dateRange").value,
      max_results: Number(document.getElementById("maxResults").value || 5),
      country: globalScope.checked ? null : (document.getElementById("country").value.trim() || null),
      industry: document.getElementById("industry").value.trim() || null,
      source_name: document.getElementById("sourceName").value.trim() || (globalScope.checked ? "google_news_rss_global" : "google_news_rss"),
      candidate_urls: parseCandidateUrls(document.getElementById("candidateUrls").value),
      auto_ingest: document.getElementById("autoIngest").checked,
      use_ai_query_expansion: document.getElementById("useAiQueryExpansion").checked,
      generate_pptx: document.getElementById("generatePptx").checked,
      target_language: document.getElementById("targetLanguage").value,
      provider: "ollama",
      model_name: "qwen3:8b",
      max_documents_to_process: Number(document.getElementById("maxDocumentsToProcess").value || 3),
      high_risk_only: document.getElementById("highRiskOnly").checked
    };

    const result = await runSearchTrain(payload);

    searchedCount.textContent = String(result.searched_result_count ?? 0);
    ingestedCount.textContent = String(result.ingested_result_count ?? 0);
    trainedDocCount.textContent = String(result.trained_keyword_model?.document_count ?? 0);
    vocabSize.textContent = String(result.trained_keyword_model?.vocabulary_size ?? 0);
    pptxCount.textContent = String(result.generated_report_count ?? 0);
    trainMessage.textContent = result.trained_keyword_model?.message || "完成。";
    statusText.textContent = `完成：查到 ${result.searched_result_count} 筆，成功匯入 ${result.ingested_result_count} 筆，產出 ${result.generated_report_count ?? 0} 份 PPTX。`;
    keywordPreview.textContent = (result.normalized_keywords || []).length
      ? `本次實際送出的關鍵字：${result.normalized_keywords.join("、")}`
      : keywordPreview.textContent;

    renderSearchResults(result.search_results || []);
    renderDocuments(result.documents || []);
    renderPptxResults(result.documents || []);
  } catch (error) {
    statusText.textContent = `執行失敗：${error.message}`;
    statusText.classList.add("error-text");
    trainMessage.textContent = "請調整關鍵字、資料期間或手動網址後再試一次。";
    searchResultsList.innerHTML = '<p class="empty-text">這次沒有可顯示的搜尋線索。</p>';
    documentsList.innerHTML = '<p class="empty-text">這次沒有成功結果。</p>';
    pptxList.innerHTML = '<p class="empty-text">這次沒有產出 PPTX。</p>';
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "開始批量搜尋與訓練";
  }
});

modeSelect.addEventListener("change", toggleManualUrls);
globalScope.addEventListener("change", toggleGlobalScope);
keywordsInput.addEventListener("input", renderKeywordPreview);
toggleManualUrls();
toggleGlobalScope();
renderKeywordPreview();
