from pydantic import BaseModel, Field
from typing import Optional, List


class DocumentSummary(BaseModel):
    doc_id: str
    title: str
    source_type: str
    language: str
    country: Optional[str] = None
    industry: Optional[str] = None
    created_at: str


class UploadResponse(BaseModel):
    message: str
    document: DocumentSummary
    extracted_keywords: List[str]


class UrlIngestRequest(BaseModel):
    url: str
    country: Optional[str] = None
    industry: Optional[str] = None
    source_name: Optional[str] = "web"


class DocumentListResponse(BaseModel):
    documents: List[DocumentSummary]


class AnalysisRequest(BaseModel):
    doc_id: str = Field(..., min_length=1)
    mode: str = Field(default="translate_first", pattern="^(translate_first|analyze_first)$")
    target_language: str = Field(default="zh", pattern="^(zh|en)$")
    use_llm: bool = False
    model_name: str = "qwen2.5:7b"


class AnalysisResponse(BaseModel):
    doc_id: str
    title: str
    detected_language: str
    mode: str
    target_language: str
    auto_keywords: List[str]
    risk_level: str
    summary: str
    translated_summary: Optional[str] = None
    evidence: List[str] = []
    notes: List[str] = []


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
