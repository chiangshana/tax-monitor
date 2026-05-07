from fastapi import APIRouter, HTTPException, Query

from models.schemas import (
    PipelineHistoryResponse,
    PipelineRunRecord,
    PipelineRunRequest,
    PipelineRunResponse,
    SearchTrainRequest,
    SearchTrainResponse,
)
from services.pipeline_service import PipelineService
from services.storage_service import StorageService


router = APIRouter()
pipeline_service = PipelineService()
storage_service = StorageService()


@router.get("/history", response_model=PipelineHistoryResponse, summary="列出最近的 pipeline 執行紀錄")
async def list_pipeline_runs(limit: int = Query(default=50, ge=1, le=200)):
    try:
        runs = storage_service.list_pipeline_runs(limit=limit)
        return PipelineHistoryResponse(total=len(runs), runs=[PipelineRunRecord(**run) for run in runs])
    except Exception as e:
        print(f"[ERROR] /api/pipeline/history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{run_id}", response_model=PipelineRunRecord, summary="取得單筆 pipeline 執行紀錄")
async def get_pipeline_run(run_id: str):
    try:
        run = storage_service.get_pipeline_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        return PipelineRunRecord(**run)
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] /api/pipeline/history/{run_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
            high_risk_only=request.high_risk_only,
            use_rag_context=request.use_rag_context,
            rag_top_k=request.rag_top_k
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
            high_risk_only=request.high_risk_only,
            use_rag_context=request.use_rag_context,
            rag_top_k=request.rag_top_k
        )
        return SearchTrainResponse(**result)
    except Exception as e:
        print(f"[ERROR] /api/pipeline/search-train: {e}")
        raise HTTPException(status_code=500, detail=str(e))
