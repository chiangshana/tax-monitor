from fastapi import APIRouter, UploadFile, File, HTTPException
from models.schemas import (
    UploadResponse,
    DocumentListResponse,
    UrlIngestRequest,
    KeywordTrainResponse,
    KeywordPreviewResponse
)
from services.document_service import DocumentService
from services.keyword_service import KeywordService


router = APIRouter()
document_service = DocumentService()
keyword_service = KeywordService()


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
            source_name=request.source_name
        )
        return result
    except Exception as e:
        print(f"[ERROR] /api/document/ingest-url: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list", response_model=DocumentListResponse, summary="列出文件")
async def list_documents():
    try:
        documents = document_service.list_documents()
        return DocumentListResponse(documents=documents)
    except Exception as e:
        print(f"[ERROR] /api/document/list: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/train-keywords", response_model=KeywordTrainResponse, summary="重新訓練關鍵字模型")
async def train_keyword_model():
    try:
        result = keyword_service.train_from_database()
        return KeywordTrainResponse(**result)
    except Exception as e:
        print(f"[ERROR] /api/document/train-keywords: {e}")
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
