from fastapi import APIRouter, HTTPException

from models.schemas import PipelineRunRequest, PipelineRunResponse, SearchTrainRequest, SearchTrainResponse
from services.pipeline_service import PipelineService


router = APIRouter()
pipeline_service = PipelineService()


@router.post("/run", response_model=PipelineRunResponse, summary="單次執行搜尋、匯入、分析與報告輸出")
async def run_pipeline(request: PipelineRunRequest):
    try:
        result = await pipeline_service.run_pipeline(
            keywords=request.keywords,
            user_prompt=request.user_prompt,
            mode=request.mode,
            date_range=request.date_range,
            start_date=request.start_date,
            end_date=request.end_date,
            max_results=request.max_results,
            country=request.country,
            industry=request.industry,
            source_name=request.source_name,
            candidate_urls=request.candidate_urls,
            use_ai_query_expansion=request.use_ai_query_expansion,
            target_language=request.target_language,
            analysis_mode=request.analysis_mode,
            provider=request.provider,
            model_name=request.model_name,
            report_format=request.report_format,
            max_documents_to_process=request.max_documents_to_process,
            high_risk_only=request.high_risk_only
        )
        return PipelineRunResponse(**result)
    except Exception as e:
        print(f"[ERROR] /api/pipeline/run: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search-train", response_model=SearchTrainResponse, summary="批量搜尋匯入並重訓關鍵字模型")
async def run_search_train(request: SearchTrainRequest):
    try:
        result = await pipeline_service.search_ingest_and_train(
            keywords=request.keywords,
            user_prompt=request.user_prompt,
            mode=request.mode,
            date_range=request.date_range,
            start_date=request.start_date,
            end_date=request.end_date,
            max_results=request.max_results,
            country=request.country,
            industry=request.industry,
            source_name=request.source_name,
            candidate_urls=request.candidate_urls,
            auto_ingest=request.auto_ingest,
            use_ai_query_expansion=request.use_ai_query_expansion,
            generate_pptx=request.generate_pptx,
            target_language=request.target_language,
            provider=request.provider,
            model_name=request.model_name,
            max_documents_to_process=request.max_documents_to_process,
            high_risk_only=request.high_risk_only
        )
        return SearchTrainResponse(**result)
    except Exception as e:
        print(f"[ERROR] /api/pipeline/search-train: {e}")
        raise HTTPException(status_code=500, detail=str(e))
