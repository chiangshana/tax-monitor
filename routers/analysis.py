from fastapi import APIRouter, HTTPException
from models.schemas import AnalysisRequest, AnalysisResponse, EvaluationRequest, EvaluationResponse, ReportRequest, ReportResponse, TranslationPreviewResponse
from services.analysis_service import AnalysisService
from services.document_service import DocumentService
from services.report_service import ReportService


router = APIRouter()
analysis_service = AnalysisService()
document_service = DocumentService()
report_service = ReportService()


@router.post("/run", response_model=AnalysisResponse, summary="執行文件分析")
async def run_analysis(request: AnalysisRequest):
    try:
        result = await analysis_service.analyze_document(
            doc_id=request.doc_id,
            mode=request.mode,
            target_language=request.target_language,
            use_llm=request.use_llm,
            provider=request.provider,
            user_prompt=request.user_prompt,
            model_name=request.model_name
        )
        return AnalysisResponse(**result)
    except Exception as e:
        print(f"[ERROR] /api/analysis/run: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/report", response_model=ReportResponse, summary="輸出 Obsidian 或投影片格式報告")
async def generate_report(request: ReportRequest):
    try:
        result = await report_service.generate_report(
            doc_id=request.doc_id,
            output_format=request.output_format,
            provider=request.provider,
            model_name=request.model_name,
            target_language=request.target_language,
            user_prompt=request.user_prompt
        )
        return ReportResponse(**result)
    except Exception as e:
        print(f"[ERROR] /api/analysis/report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evaluate", response_model=EvaluationResponse, summary="比較 rule-based 與 LLM 分析結果")
async def evaluate_analysis(request: EvaluationRequest):
    try:
        result = await analysis_service.evaluate_document(
            doc_id=request.doc_id,
            target_language=request.target_language,
            provider=request.provider,
            model_name=request.model_name,
            user_prompt=request.user_prompt
        )
        return EvaluationResponse(**result)
    except Exception as e:
        print(f"[ERROR] /api/analysis/evaluate: {e}")
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
