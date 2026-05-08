from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DocumentSummary(BaseModel):
    doc_id: str
    title: str
    source_type: str
    source_name: Optional[str] = None
    language: str
    country: Optional[str] = None
    industry: Optional[str] = None
    published_date: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None


class DocumentDetail(DocumentSummary):
    file_name: Optional[str] = None
    url: Optional[str] = None
    raw_text: str


class DocumentUpdateRequest(BaseModel):
    title: Optional[str] = None
    country: Optional[str] = None
    industry: Optional[str] = None
    source_name: Optional[str] = None
    published_date: Optional[str] = None


class DocumentListRequest(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)
    country: Optional[str] = None
    industry: Optional[str] = None
    language: Optional[str] = None
    source_name: Optional[str] = None
    keyword: Optional[str] = None


class EmbeddedDocumentLink(BaseModel):
    url: str
    text: Optional[str] = None
    looks_like_document: bool = False


class UploadResponse(BaseModel):
    message: str
    document: DocumentSummary
    extracted_keywords: List[str]
    embedded_document_links: List[EmbeddedDocumentLink] = Field(default_factory=list)


class UrlIngestRequest(BaseModel):
    url: str
    country: Optional[str] = None
    industry: Optional[str] = None
    source_name: Optional[str] = "web"
    published_date: Optional[str] = None


class DocumentListResponse(BaseModel):
    documents: List[DocumentSummary]
    page: int = 1
    page_size: int = 10
    total: int = 0


class AnalysisRequest(BaseModel):
    doc_id: str = Field(..., min_length=1)
    mode: str = Field(default="translate_first", pattern="^(translate_first|analyze_first)$")
    target_language: str = Field(default="zh", pattern="^(zh|en)$")
    use_llm: bool = False
    provider: str = Field(default="ollama", pattern="^(ollama|openai|gemini|claude|qwen)$")
    model_name: str = "qwen3:8b"
    user_prompt: Optional[str] = None
    use_rag_context: bool = True
    rag_top_k: int = Field(default=4, ge=0, le=10)


class AnalysisResponse(BaseModel):
    doc_id: str
    title: str
    detected_language: str
    mode: str
    target_language: str
    auto_keywords: List[str]
    risk_level: str
    risk_tags: List[str] = []
    summary: str
    translated_summary: Optional[str] = None
    bilingual_summary: Dict[str, str] = Field(default_factory=dict)
    evidence: List[str] = []
    notes: List[str] = []
    rag_context: Dict = Field(default_factory=dict)


class KeywordTrainResponse(BaseModel):
    message: str
    document_count: int
    vocabulary_size: int


class KeywordPreviewResponse(BaseModel):
    doc_id: str
    title: str
    keywords: List[str]


class TranslationPreviewResponse(BaseModel):
    doc_id: str
    original_language: str
    translated_language: str
    translated_text_preview: str


class SearchRequest(BaseModel):
    keywords: List[str] = Field(..., min_length=1)
    user_prompt: Optional[str] = None
    mode: str = Field(default="auto", pattern="^(auto|manual)$")
    date_range: str = Field(default="1m", pattern="^(7d|1m|3m|6m|1y|custom)$")
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    max_results: int = Field(default=10, ge=1, le=100)
    country: Optional[str] = None
    industry: Optional[str] = None
    source_name: str = "google_news_rss"
    candidate_urls: List[str] = Field(default_factory=list)
    auto_ingest: bool = True
    use_ai_query_expansion: bool = True
    provider: str = Field(default="ollama", pattern="^(ollama|openai|gemini|claude|qwen)$")
    model_name: str = "qwen3:8b"


class SearchResultItem(BaseModel):
    title: str
    url: str
    snippet: str = ""
    source: str
    published_at: Optional[str] = None
    relevance_score: float
    domain: Optional[str] = None
    result_type: Optional[str] = None
    match_reasons: List[str] = Field(default_factory=list)
    ingested_doc_id: Optional[str] = None


class SearchResponse(BaseModel):
    query: str
    mode: str
    date_range: str
    results: List[SearchResultItem]


class KeywordTrainRequest(BaseModel):
    profile_name: str = Field(default="default", min_length=1)
    user_keywords: List[str] = Field(default_factory=list)
    risk_labels: List[str] = Field(default_factory=list)
    user_prompt: Optional[str] = None
    provider: str = Field(default="ollama", pattern="^(ollama|openai|gemini|claude|qwen)$")
    model_name: str = "qwen3:8b"


class KeywordProfileResponse(BaseModel):
    profile_name: str
    user_keywords: List[str]
    expanded_keywords: List[str]
    risk_labels: List[str]
    updated_at: str


class SlideSection(BaseModel):
    title: str
    bullets: List[str]


class ReportRequest(BaseModel):
    doc_id: str = Field(..., min_length=1)
    output_format: str = Field(default="obsidian", pattern="^(obsidian|slides|pptx|markdown)$")
    provider: str = Field(default="ollama", pattern="^(ollama|openai|gemini|claude|qwen)$")
    model_name: str = "qwen3:8b"
    target_language: str = Field(default="zh", pattern="^(zh|en)$")
    user_prompt: Optional[str] = None
    use_rag_context: bool = True
    rag_top_k: int = Field(default=4, ge=0, le=10)


class ReportResponse(BaseModel):
    doc_id: str
    output_format: str
    title: str
    content: str
    slide_outline: List[SlideSection] = Field(default_factory=list)
    file_path: Optional[str] = None
    metadata: Dict[str, str] = Field(default_factory=dict)


class EvaluationRequest(BaseModel):
    doc_id: str = Field(..., min_length=1)
    target_language: str = Field(default="zh", pattern="^(zh|en)$")
    provider: str = Field(default="ollama", pattern="^(ollama|openai|gemini|claude|qwen)$")
    model_name: str = "qwen3:8b"
    compare_mode: str = Field(default="rule_vs_llm", pattern="^(rule_vs_llm)$")
    user_prompt: Optional[str] = None


class EvaluationResponse(BaseModel):
    doc_id: str
    compare_mode: str
    rule_based_summary: str
    llm_summary: str
    overlap_score: float
    risk_level_rule: str
    risk_level_llm: str
    notes: List[str] = Field(default_factory=list)


class PipelineRunRequest(BaseModel):
    keywords: List[str] = Field(..., min_length=1)
    user_prompt: Optional[str] = None
    mode: str = Field(default="auto", pattern="^(auto|manual)$")
    date_range: str = Field(default="1m", pattern="^(7d|1m|3m|6m|1y|custom)$")
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    max_results: int = Field(default=10, ge=1, le=100)
    country: Optional[str] = None
    industry: Optional[str] = None
    source_name: str = "google_news_rss"
    candidate_urls: List[str] = Field(default_factory=list)
    use_ai_query_expansion: bool = True
    target_language: str = Field(default="zh", pattern="^(zh|en)$")
    analysis_mode: str = Field(default="translate_first", pattern="^(translate_first|analyze_first)$")
    provider: str = Field(default="ollama", pattern="^(ollama|openai|gemini|claude|qwen)$")
    model_name: str = "qwen3:8b"
    report_format: str = Field(default="pptx", pattern="^(obsidian|slides|pptx|markdown)$")
    max_documents_to_process: int = Field(default=3, ge=1, le=10)
    high_risk_only: bool = False
    use_rag_context: bool = True
    rag_top_k: int = Field(default=4, ge=0, le=10)


class PipelineDocumentResult(BaseModel):
    doc_id: str
    title: str
    source_url: Optional[str] = None
    risk_level: str
    risk_tags: List[str] = Field(default_factory=list)
    rag_source_count: int = 0
    report_format: str
    report_file_path: Optional[str] = None


class PipelineRunResponse(BaseModel):
    query: str
    searched_result_count: int
    ingested_result_count: int
    processed_count: int
    report_format: str
    documents: List[PipelineDocumentResult] = Field(default_factory=list)
    run_id: Optional[str] = None


class SearchTrainRequest(BaseModel):
    keywords: List[str] = Field(..., min_length=1)
    user_prompt: Optional[str] = None
    mode: str = Field(default="auto", pattern="^(auto|manual)$")
    date_range: str = Field(default="1m", pattern="^(7d|1m|3m|6m|1y|custom)$")
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    max_results: int = Field(default=10, ge=1, le=100)
    country: Optional[str] = None
    industry: Optional[str] = None
    source_name: str = "google_news_rss"
    candidate_urls: List[str] = Field(default_factory=list)
    auto_ingest: bool = True
    use_ai_query_expansion: bool = True
    generate_pptx: bool = True
    target_language: str = Field(default="zh", pattern="^(zh|en)$")
    provider: str = Field(default="ollama", pattern="^(ollama|openai|gemini|claude|qwen)$")
    model_name: str = "qwen3:8b"
    max_documents_to_process: int = Field(default=3, ge=1, le=10)
    high_risk_only: bool = False
    use_rag_context: bool = True
    rag_top_k: int = Field(default=4, ge=0, le=10)


class SearchTrainDocumentResult(BaseModel):
    doc_id: str
    title: str
    url: Optional[str] = None
    published_at: Optional[str] = None
    extracted_keywords: List[str] = Field(default_factory=list)
    risk_level: Optional[str] = None
    risk_tags: List[str] = Field(default_factory=list)
    rag_source_count: int = 0
    pptx_file_path: Optional[str] = None


class SearchTrainSearchResult(BaseModel):
    title: str
    url: str
    source: str
    published_at: Optional[str] = None
    relevance_score: float
    domain: Optional[str] = None
    result_type: Optional[str] = None
    match_reasons: List[str] = Field(default_factory=list)


class FtsSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    limit: int = Field(default=20, ge=1, le=100)


class FtsSearchHit(BaseModel):
    doc_id: str
    title: Optional[str] = None
    source_type: Optional[str] = None
    source_name: Optional[str] = None
    language: Optional[str] = None
    country: Optional[str] = None
    industry: Optional[str] = None
    published_date: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    snippet: Optional[str] = None
    rank: Optional[float] = None


class FtsSearchResponse(BaseModel):
    query: str
    total: int
    hits: List[FtsSearchHit] = Field(default_factory=list)


class PipelineRunRecord(BaseModel):
    run_id: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    status: str
    source_name: Optional[str] = None
    provider: Optional[str] = None
    model_name: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    user_prompt: Optional[str] = None
    result_summary: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class PipelineHistoryResponse(BaseModel):
    total: int
    runs: List[PipelineRunRecord] = Field(default_factory=list)


class SearchTrainResponse(BaseModel):
    query: str
    normalized_keywords: List[str] = Field(default_factory=list)
    searched_result_count: int
    ingested_result_count: int
    generated_report_count: int
    trained_keyword_model: Dict[str, str | int]
    search_results: List[SearchTrainSearchResult] = Field(default_factory=list)
    documents: List[SearchTrainDocumentResult] = Field(default_factory=list)
    run_id: Optional[str] = None
