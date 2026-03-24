from fastapi import APIRouter, HTTPException
from models.schemas import AnalysisRequest, AnalysisResponse, TranslationPreviewResponse
from services.analysis_service import AnalysisService
from services.document_service import DocumentService


router = APIRouter()
analysis_service = AnalysisService()
document_service = DocumentService()


@router.post("/run", response_model=AnalysisResponse, summary="執行文件分析")
async def run_analysis(request: AnalysisRequest):
    try:
        result = await analysis_service.analyze_document(
            doc_id=request.doc_id,
            mode=request.mode,
            target_language=request.target_language,
            use_llm=request.use_llm,
            model_name=request.model_name
        )
        return AnalysisResponse(**result)
    except Exception as e:
        print(f"[ERROR] /api/analysis/run: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/translation-preview/{doc_id}", response_model=TranslationPreviewResponse, summary="翻譯預覽")
async def translation_preview(doc_id: str, target_language: str = "zh"):
    try:
        document = document_service.get_document(doc_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        preview = await analysis_service.preview_translation(
            raw_text=document["raw_text"],
            original_language=document["language"],
            target_language=target_language
        )
        return TranslationPreviewResponse(
            doc_id=doc_id,
            original_language=document["language"],
            translated_language=target_language,
            translated_text_preview=preview
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] /api/analysis/translation-preview/{doc_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
