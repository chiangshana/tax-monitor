import csv
import io
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import StreamingResponse
from models.schemas import (
    DocumentDetail,
    DocumentListRequest,
    UploadResponse,
    DocumentListResponse,
    DocumentUpdateRequest,
    UrlIngestRequest,
    SearchRequest,
    SearchResponse,
    KeywordTrainResponse,
    KeywordTrainRequest,
    KeywordProfileResponse,
    KeywordPreviewResponse,
    FtsSearchRequest,
    FtsSearchResponse,
)
from services.document_service import DocumentService
from services.keyword_service import KeywordService
from services.search_service import SearchService
from services.storage_service import StorageService


router = APIRouter()
document_service = DocumentService()
keyword_service = KeywordService()
search_service = SearchService()
storage_service = StorageService()


EXPORT_COLUMNS = [
    "doc_id",
    "title",
    "source_type",
    "source_name",
    "language",
    "country",
    "industry",
    "published_date",
    "created_at",
    "updated_at",
    "url",
]


@router.get("/export", summary="匯出已匯入文件為 CSV / XLSX")
async def export_documents(
    format: str = Query(default="csv", pattern="^(csv|xlsx)$"),
    keyword: str = Query(default=None),
    country: str = Query(default=None),
    industry: str = Query(default=None),
    language: str = Query(default=None),
    limit: int = Query(default=500, ge=1, le=5000),
):
    try:
        listing = document_service.list_documents(
            page=1,
            page_size=limit,
            country=country,
            industry=industry,
            language=language,
            keyword=keyword,
        )
        documents = listing.get("documents", []) if isinstance(listing, dict) else []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if format == "csv":
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(EXPORT_COLUMNS)
        for doc in documents:
            writer.writerow([doc.get(col) or "" for col in EXPORT_COLUMNS])
        buffer.seek(0)
        return StreamingResponse(
            iter([buffer.getvalue().encode("utf-8-sig")]),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename=tax_monitor_documents_{timestamp}.csv"},
        )

    try:
        from openpyxl import Workbook
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="XLSX export requires openpyxl. Install with: pip install openpyxl",
        )

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "documents"
    sheet.append(EXPORT_COLUMNS)
    for doc in documents:
        sheet.append([doc.get(col) or "" for col in EXPORT_COLUMNS])
    binary_buffer = io.BytesIO()
    workbook.save(binary_buffer)
    binary_buffer.seek(0)
    return StreamingResponse(
        iter([binary_buffer.getvalue()]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=tax_monitor_documents_{timestamp}.xlsx"},
    )


@router.post("/fts-search", response_model=FtsSearchResponse, summary="對已匯入文件執行全文檢索（FTS5）")
async def fts_search_documents(request: FtsSearchRequest):
    try:
        hits = storage_service.fts_search_documents(query=request.query, limit=request.limit)
        return FtsSearchResponse(query=request.query, total=len(hits), hits=hits)
    except Exception as e:
        print(f"[ERROR] /api/document/fts-search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload", response_model=UploadResponse, summary="上傳文件")
async def upload_document(file: UploadFile = File(...)):
    try:
        result = await document_service.process_upload(file)
        return result
    except Exception as e:
        print(f"[ERROR] /api/document/upload: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest-url", response_model=UploadResponse, summary="匯入網站內容")
async def ingest_url(request: UrlIngestRequest):
    try:
        result = await document_service.process_url(
            url=request.url,
            country=request.country,
            industry=request.industry,
            source_name=request.source_name,
            published_date=request.published_date
        )
        return result
    except Exception as e:
        print(f"[ERROR] /api/document/ingest-url: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/list", response_model=DocumentListResponse, summary="列出文件")
async def list_documents(request: DocumentListRequest):
    try:
        result = document_service.list_documents(
            page=request.page,
            page_size=request.page_size,
            country=request.country,
            industry=request.industry,
            language=request.language,
            source_name=request.source_name,
            keyword=request.keyword
        )
        return DocumentListResponse(**result)
    except Exception as e:
        print(f"[ERROR] /api/document/list: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/keyword-profiles", response_model=list[KeywordProfileResponse], summary="列出關鍵字設定檔")
async def list_keyword_profiles():
    try:
        profiles = keyword_service.list_keyword_profiles()
        return [KeywordProfileResponse(**profile) for profile in profiles]
    except Exception as e:
        print(f"[ERROR] /api/document/keyword-profiles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{doc_id}", response_model=DocumentDetail, summary="查看單篇文件詳情")
async def get_document_detail(doc_id: str):
    try:
        document = document_service.get_document(doc_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        return DocumentDetail(**document)
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] /api/document/{doc_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{doc_id}", response_model=DocumentDetail, summary="更新文件中繼資料")
async def update_document(doc_id: str, request: DocumentUpdateRequest):
    try:
        document = document_service.get_document(doc_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        updated = document_service.update_document(doc_id, request.model_dump(exclude_none=True))
        return DocumentDetail(**updated)
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] /api/document/{doc_id} [PATCH]: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=SearchResponse, summary="搜尋並可選擇匯入相關資料")
async def search_documents(request: SearchRequest):
    try:
        query = " ".join(request.keywords)
        results = search_service.search(
            keywords=request.keywords,
            user_prompt=request.user_prompt,
            mode=request.mode,
            date_range=request.date_range,
            start_date=request.start_date,
            end_date=request.end_date,
            max_results=request.max_results,
            candidate_urls=request.candidate_urls,
            source_name=request.source_name,
            use_ai_query_expansion=request.use_ai_query_expansion,
            provider=request.provider,
            model_name=request.model_name
        )

        normalized_results = []
        for item in results:
            ingested_doc_id = None
            if request.auto_ingest and item.get("url"):
                try:
                    ingest_result = await document_service.process_url(
                        url=item["url"],
                        country=request.country,
                        industry=request.industry,
                        source_name=request.source_name,
                        published_date=item.get("published_at")
                    )
                    ingested_doc_id = ingest_result["document"]["doc_id"]
                except Exception:
                    ingested_doc_id = None

            normalized_results.append({
                **item,
                "ingested_doc_id": ingested_doc_id
            })

        return {
            "query": query,
            "mode": request.mode,
            "date_range": request.date_range,
            "results": normalized_results
        }
    except Exception as e:
        print(f"[ERROR] /api/document/search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/train-keywords", response_model=KeywordTrainResponse, summary="重新訓練關鍵字模型")
async def train_keyword_model():
    try:
        result = keyword_service.train_from_database()
        return KeywordTrainResponse(**result)
    except Exception as e:
        print(f"[ERROR] /api/document/train-keywords: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/train-keyword-profile", response_model=KeywordProfileResponse, summary="訓練使用者需求與風險標籤關鍵字")
async def train_keyword_profile(request: KeywordTrainRequest):
    try:
        profile = keyword_service.train_keyword_profile(
            profile_name=request.profile_name,
            user_keywords=request.user_keywords,
            risk_labels=request.risk_labels,
            user_prompt=request.user_prompt,
            provider=request.provider,
            model_name=request.model_name
        )
        return KeywordProfileResponse(**profile)
    except Exception as e:
        print(f"[ERROR] /api/document/train-keyword-profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/keywords/{doc_id}", response_model=KeywordPreviewResponse, summary="查看文件自動關鍵字")
async def preview_keywords(doc_id: str):
    try:
        document = document_service.get_document(doc_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        keywords = keyword_service.extract_keywords_for_document(
            title=document["title"],
            text=document["raw_text"]
        )
        return KeywordPreviewResponse(
            doc_id=doc_id,
            title=document["title"],
            keywords=keywords
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] /api/document/keywords/{doc_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
