import asyncio
import threading
import uuid
from datetime import datetime
from typing import Awaitable, Callable, Dict, List, Optional

from services.analysis_service import AnalysisService
from services.document_service import DocumentService
from services.keyword_service import KeywordService
from services.llm_service import LLMService
from services.report_service import ReportService
from services.search_service import SearchService
from services.storage_service import StorageService


PipelineProgressCallback = Callable[[Dict], None]


class PipelineCancelled(Exception):
    pass


class PipelineService:
    INGEST_CONCURRENCY = 4
    def __init__(self):
        self.search_service = SearchService()
        self.document_service = DocumentService()
        self.analysis_service = AnalysisService()
        self.report_service = ReportService()
        self.keyword_service = KeywordService()
        self.storage_service = StorageService()

    def _start_run(self, payload: Dict) -> str:
        run_id = str(uuid.uuid4())
        try:
            self.storage_service.record_pipeline_run(
                run_id=run_id,
                started_at=datetime.now().isoformat(timespec="seconds"),
                status="running",
                source_name=payload.get("source_name"),
                provider=payload.get("provider"),
                model_name=payload.get("model_name"),
                keywords=payload.get("keywords"),
                user_prompt=payload.get("user_prompt"),
                payload=payload,
            )
        except Exception:
            pass
        return run_id

    def _finalize_run(self, run_id: str, status: str, summary: Optional[Dict] = None, error: Optional[str] = None):
        try:
            self.storage_service.finalize_pipeline_run(
                run_id=run_id,
                finished_at=datetime.now().isoformat(timespec="seconds"),
                status=status,
                result_summary=summary,
                error=error,
            )
        except Exception:
            pass

    def _check_cancel(self, cancel_event: Optional[threading.Event]):
        if cancel_event is not None and cancel_event.is_set():
            raise PipelineCancelled("Cancelled by user")

    def _shared_llm_service(self) -> Optional[LLMService]:
        candidates = [
            getattr(self.search_service, "llm_service", None),
            getattr(self.analysis_service, "llm_service", None),
            getattr(self.report_service, "llm_service", None),
            getattr(self.keyword_service, "llm_service", None),
        ]
        return next((service for service in candidates if isinstance(service, LLMService)), None)

    def _reset_token_counters(self):
        for service in (self.search_service, self.analysis_service, self.report_service, self.keyword_service):
            llm = getattr(service, "llm_service", None)
            if isinstance(llm, LLMService):
                try:
                    llm.reset_usage_records()
                except Exception:
                    pass

    def _collect_token_usage(self) -> Dict:
        records: List[Dict] = []
        seen_ids = set()
        for service in (self.search_service, self.analysis_service, self.report_service, self.keyword_service):
            llm = getattr(service, "llm_service", None)
            if not isinstance(llm, LLMService) or id(llm) in seen_ids:
                continue
            seen_ids.add(id(llm))
            try:
                records.extend(llm.consume_usage_records())
            except Exception:
                continue
        helper = LLMService()
        return helper._summarize_usage_records(records)

    def _emit_progress(self, callback: Optional[PipelineProgressCallback], event: str, **fields):
        if not callback:
            return
        payload = {"event": event, "timestamp": datetime.now().isoformat(timespec="seconds"), **fields}
        try:
            callback(payload)
        except Exception:
            pass

    async def _ingest_items_concurrently(
        self,
        items: List[Dict],
        country: Optional[str],
        industry: Optional[str],
        source_name: str,
        progress_callback: Optional[PipelineProgressCallback] = None,
        cancel_event: Optional[threading.Event] = None,
    ) -> List[Dict]:
        semaphore = asyncio.Semaphore(self.INGEST_CONCURRENCY)
        completed_count = {"value": 0}
        total = sum(1 for item in items if item.get("url"))

        async def _ingest_one(index: int, item: Dict):
            if cancel_event is not None and cancel_event.is_set():
                return None
            url = item.get("url")
            if not url:
                return None
            try:
                if not self.search_service._head_precheck(url):
                    self._emit_progress(
                        progress_callback,
                        "ingest_skipped",
                        index=index,
                        url=url,
                        reason="head_precheck_rejected",
                    )
                    return None
            except Exception:
                pass
            async with semaphore:
                try:
                    self._emit_progress(
                        progress_callback,
                        "ingest_started",
                        index=index,
                        url=url,
                        title=item.get("title"),
                    )
                    result = await self.document_service.process_url(
                        url=url,
                        country=country,
                        industry=industry,
                        source_name=source_name,
                        published_date=item.get("published_at"),
                        defer_keyword_training=True,
                    )
                except Exception as exc:
                    self._emit_progress(
                        progress_callback,
                        "ingest_failed",
                        index=index,
                        url=url,
                        error=str(exc),
                    )
                    return None
                completed_count["value"] += 1
                self._emit_progress(
                    progress_callback,
                    "ingest_completed",
                    index=index,
                    url=url,
                    completed=completed_count["value"],
                    total=total,
                    deduplicated=result.get("deduplicated", False),
                )
                return {"item": item, "ingest_result": result}

        gathered = await asyncio.gather(*[_ingest_one(i, it) for i, it in enumerate(items)])
        return [entry for entry in gathered if entry is not None]

    def _summarize_pipeline_result(self, payload: Dict, result: Dict) -> Dict:
        return {
            "query": result.get("query"),
            "searched_result_count": result.get("searched_result_count"),
            "ingested_result_count": result.get("ingested_result_count"),
            "processed_count": result.get("processed_count") or result.get("generated_report_count"),
            "report_format": result.get("report_format"),
            "documents": [
                {
                    "doc_id": doc.get("doc_id"),
                    "title": doc.get("title"),
                    "risk_level": doc.get("risk_level"),
                    "report_file_path": doc.get("report_file_path") or doc.get("pptx_file_path"),
                }
                for doc in (result.get("documents") or [])
            ],
            "source_name": payload.get("source_name"),
            "provider": payload.get("provider"),
            "model_name": payload.get("model_name"),
        }

    async def run_pipeline(
        self,
        keywords: List[str],
        user_prompt: str = None,
        mode: str = "auto",
        date_range: str = "1m",
        start_date: str = None,
        end_date: str = None,
        max_results: int = 10,
        country: str = None,
        industry: str = None,
        source_name: str = "google_news_rss",
        candidate_urls: List[str] = None,
        use_ai_query_expansion: bool = True,
        target_language: str = "zh",
        analysis_mode: str = "translate_first",
        provider: str = "ollama",
        model_name: str = "qwen3:8b",
        report_format: str = "pptx",
        max_documents_to_process: int = 3,
        high_risk_only: bool = False,
        progress_callback: Optional[PipelineProgressCallback] = None,
        cancel_event: Optional[threading.Event] = None
    ) -> Dict:
        run_payload = {
            "keywords": keywords,
            "user_prompt": user_prompt,
            "mode": mode,
            "date_range": date_range,
            "max_results": max_results,
            "country": country,
            "industry": industry,
            "source_name": source_name,
            "use_ai_query_expansion": use_ai_query_expansion,
            "target_language": target_language,
            "analysis_mode": analysis_mode,
            "provider": provider,
            "model_name": model_name,
            "report_format": report_format,
            "max_documents_to_process": max_documents_to_process,
            "high_risk_only": high_risk_only,
        }
        self._reset_token_counters()
        run_id = self._start_run(run_payload)
        self._emit_progress(progress_callback, "run_started", run_id=run_id, payload=run_payload)
        try:
            response = await self._run_pipeline_inner(
                keywords=keywords,
                user_prompt=user_prompt,
                mode=mode,
                date_range=date_range,
                start_date=start_date,
                end_date=end_date,
                max_results=max_results,
                country=country,
                industry=industry,
                source_name=source_name,
                candidate_urls=candidate_urls,
                use_ai_query_expansion=use_ai_query_expansion,
                target_language=target_language,
                analysis_mode=analysis_mode,
                provider=provider,
                model_name=model_name,
                report_format=report_format,
                max_documents_to_process=max_documents_to_process,
                high_risk_only=high_risk_only,
                progress_callback=progress_callback,
                cancel_event=cancel_event,
            )
        except PipelineCancelled as exc:
            cost_summary = self._collect_token_usage()
            self._finalize_run(run_id, status="cancelled", error=str(exc), summary={"cost": cost_summary})
            self._emit_progress(progress_callback, "run_cancelled", run_id=run_id, cost=cost_summary)
            raise
        except Exception as exc:
            cost_summary = self._collect_token_usage()
            self._finalize_run(run_id, status="failed", error=str(exc), summary={"cost": cost_summary})
            self._emit_progress(progress_callback, "run_failed", run_id=run_id, error=str(exc), cost=cost_summary)
            raise
        cost_summary = self._collect_token_usage()
        response["run_id"] = run_id
        response["cost"] = cost_summary
        summary_payload = self._summarize_pipeline_result(run_payload, response)
        summary_payload["cost"] = cost_summary
        self._finalize_run(
            run_id,
            status="success",
            summary=summary_payload,
        )
        self._emit_progress(
            progress_callback,
            "run_completed",
            run_id=run_id,
            processed=response.get("processed_count"),
            cost=cost_summary,
        )
        return response

    async def _run_pipeline_inner(
        self,
        keywords: List[str],
        user_prompt: str = None,
        mode: str = "auto",
        date_range: str = "1m",
        start_date: str = None,
        end_date: str = None,
        max_results: int = 10,
        country: str = None,
        industry: str = None,
        source_name: str = "google_news_rss",
        candidate_urls: List[str] = None,
        use_ai_query_expansion: bool = True,
        target_language: str = "zh",
        analysis_mode: str = "translate_first",
        provider: str = "ollama",
        model_name: str = "qwen3:8b",
        report_format: str = "pptx",
        max_documents_to_process: int = 3,
        high_risk_only: bool = False,
        progress_callback: Optional[PipelineProgressCallback] = None,
        cancel_event: Optional[threading.Event] = None
    ) -> Dict:
        self._check_cancel(cancel_event)
        self._emit_progress(progress_callback, "search_started", source_name=source_name, keywords=keywords)
        results = self.search_service.search(
            keywords=keywords,
            user_prompt=user_prompt,
            mode=mode,
            date_range=date_range,
            start_date=start_date,
            end_date=end_date,
            max_results=max_results,
            candidate_urls=candidate_urls,
            source_name=source_name,
            use_ai_query_expansion=use_ai_query_expansion,
            provider=provider,
            model_name=model_name
        )
        self._emit_progress(progress_callback, "search_completed", count=len(results))
        self._check_cancel(cancel_event)

        ingest_targets = results[:max(max_documents_to_process * 2, max_documents_to_process + 4)]
        self._emit_progress(progress_callback, "ingest_phase_started", total=len(ingest_targets))
        ingested = await self._ingest_items_concurrently(
            items=ingest_targets,
            country=country,
            industry=industry,
            source_name=source_name,
            progress_callback=progress_callback,
            cancel_event=cancel_event,
        )
        ingested_count = len(ingested)
        self._emit_progress(progress_callback, "ingest_phase_completed", ingested=ingested_count)
        self._check_cancel(cancel_event)

        processed_documents = []

        for index, entry in enumerate(ingested):
            self._check_cancel(cancel_event)
            if len(processed_documents) >= max_documents_to_process:
                break
            item = entry["item"]
            ingest_result = entry["ingest_result"]
            doc_id = ingest_result["document"]["doc_id"]
            self._emit_progress(
                progress_callback,
                "analysis_started",
                index=index,
                doc_id=doc_id,
                title=ingest_result["document"].get("title"),
            )

            try:
                analysis = await self.analysis_service.analyze_document(
                    doc_id=doc_id,
                    mode=analysis_mode,
                    target_language=target_language,
                    use_llm=True,
                    provider=provider,
                    user_prompt=user_prompt,
                    model_name=model_name
                )
            except Exception:
                analysis = await self.analysis_service.analyze_document(
                    doc_id=doc_id,
                    mode=analysis_mode,
                    target_language=target_language,
                    use_llm=False,
                    provider=provider,
                    user_prompt=user_prompt,
                    model_name=model_name
                )

            self._emit_progress(
                progress_callback,
                "analysis_completed",
                index=index,
                doc_id=doc_id,
                risk_level=analysis.get("risk_level"),
            )

            if high_risk_only and analysis["risk_level"] != "High":
                continue

            self._emit_progress(progress_callback, "report_started", index=index, doc_id=doc_id, format=report_format)
            report = await self.report_service.generate_report(
                doc_id=doc_id,
                output_format=report_format,
                provider=provider,
                model_name=model_name,
                target_language=target_language,
                user_prompt=user_prompt
            )
            self._emit_progress(
                progress_callback,
                "report_completed",
                index=index,
                doc_id=doc_id,
                file_path=report.get("file_path"),
            )

            processed_documents.append({
                "doc_id": doc_id,
                "title": analysis["title"],
                "source_url": item.get("url"),
                "risk_level": analysis["risk_level"],
                "risk_tags": analysis.get("risk_tags", []),
                "report_format": report_format,
                "report_file_path": report.get("file_path")
            })

        if ingested_count:
            try:
                self.keyword_service.train_from_database()
            except Exception:
                pass

        return {
            "query": " ".join(keywords),
            "searched_result_count": len(results),
            "ingested_result_count": ingested_count,
            "processed_count": len(processed_documents),
            "report_format": report_format,
            "documents": processed_documents
        }

    def _normalize_search_results(self, results: List[Dict]) -> List[Dict]:
        normalized = []
        for item in results:
            normalized.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "source": item.get("source", ""),
                "published_at": item.get("published_at"),
                "relevance_score": item.get("relevance_score", 0.0),
                "domain": item.get("domain"),
                "result_type": item.get("result_type"),
                "match_reasons": item.get("match_reasons", [])
            })
        return normalized

    async def search_ingest_and_train(
        self,
        keywords: List[str],
        user_prompt: str = None,
        mode: str = "auto",
        date_range: str = "1m",
        start_date: str = None,
        end_date: str = None,
        max_results: int = 10,
        country: str = None,
        industry: str = None,
        source_name: str = "google_news_rss",
        candidate_urls: List[str] = None,
        auto_ingest: bool = True,
        use_ai_query_expansion: bool = True,
        generate_pptx: bool = True,
        target_language: str = "zh",
        provider: str = "ollama",
        model_name: str = "qwen3:8b",
        max_documents_to_process: int = 3,
        high_risk_only: bool = False,
        progress_callback: Optional[PipelineProgressCallback] = None,
        cancel_event: Optional[threading.Event] = None
    ) -> Dict:
        run_payload = {
            "keywords": keywords,
            "user_prompt": user_prompt,
            "source_name": source_name,
            "provider": provider,
            "model_name": model_name,
            "date_range": date_range,
            "max_results": max_results,
            "auto_ingest": auto_ingest,
            "generate_pptx": generate_pptx,
            "target_language": target_language,
            "max_documents_to_process": max_documents_to_process,
            "high_risk_only": high_risk_only,
        }
        self._reset_token_counters()
        run_id = self._start_run(run_payload)
        self._emit_progress(progress_callback, "run_started", run_id=run_id, payload=run_payload)
        try:
            response = await self._search_ingest_and_train_inner(
                keywords=keywords,
                user_prompt=user_prompt,
                mode=mode,
                date_range=date_range,
                start_date=start_date,
                end_date=end_date,
                max_results=max_results,
                country=country,
                industry=industry,
                source_name=source_name,
                candidate_urls=candidate_urls,
                auto_ingest=auto_ingest,
                use_ai_query_expansion=use_ai_query_expansion,
                generate_pptx=generate_pptx,
                target_language=target_language,
                provider=provider,
                model_name=model_name,
                max_documents_to_process=max_documents_to_process,
                high_risk_only=high_risk_only,
                progress_callback=progress_callback,
                cancel_event=cancel_event,
            )
        except PipelineCancelled as exc:
            cost_summary = self._collect_token_usage()
            self._finalize_run(run_id, status="cancelled", error=str(exc), summary={"cost": cost_summary})
            self._emit_progress(progress_callback, "run_cancelled", run_id=run_id, cost=cost_summary)
            raise
        except Exception as exc:
            cost_summary = self._collect_token_usage()
            self._finalize_run(run_id, status="failed", error=str(exc), summary={"cost": cost_summary})
            self._emit_progress(progress_callback, "run_failed", run_id=run_id, error=str(exc), cost=cost_summary)
            raise
        cost_summary = self._collect_token_usage()
        response["run_id"] = run_id
        response["cost"] = cost_summary
        summary_payload = self._summarize_pipeline_result(run_payload, response)
        summary_payload["cost"] = cost_summary
        self._finalize_run(
            run_id,
            status="success",
            summary=summary_payload,
        )
        self._emit_progress(
            progress_callback,
            "run_completed",
            run_id=run_id,
            ingested=response.get("ingested_result_count"),
            cost=cost_summary,
        )
        return response

    async def _search_ingest_and_train_inner(
        self,
        keywords: List[str],
        user_prompt: str = None,
        mode: str = "auto",
        date_range: str = "1m",
        start_date: str = None,
        end_date: str = None,
        max_results: int = 10,
        country: str = None,
        industry: str = None,
        source_name: str = "google_news_rss",
        candidate_urls: List[str] = None,
        auto_ingest: bool = True,
        use_ai_query_expansion: bool = True,
        generate_pptx: bool = True,
        target_language: str = "zh",
        provider: str = "ollama",
        model_name: str = "qwen3:8b",
        max_documents_to_process: int = 3,
        high_risk_only: bool = False,
        progress_callback: Optional[PipelineProgressCallback] = None,
        cancel_event: Optional[threading.Event] = None
    ) -> Dict:
        self._check_cancel(cancel_event)
        normalized_keywords = self.search_service._normalize_keywords(keywords)
        self._emit_progress(progress_callback, "search_started", source_name=source_name, keywords=normalized_keywords)
        results = self.search_service.search(
            keywords=normalized_keywords,
            user_prompt=user_prompt,
            mode=mode,
            date_range=date_range,
            start_date=start_date,
            end_date=end_date,
            max_results=max_results,
            candidate_urls=candidate_urls,
            source_name=source_name,
            use_ai_query_expansion=use_ai_query_expansion,
            provider=provider,
            model_name=model_name
        )
        self._emit_progress(progress_callback, "search_completed", count=len(results))

        ingested_documents: List[Dict] = []
        generated_report_count = 0

        if not auto_ingest:
            ingested_count = 0
            ingested_pairs: List[Dict] = []
        else:
            self._emit_progress(progress_callback, "ingest_phase_started", total=len(results))
            ingested_pairs = await self._ingest_items_concurrently(
                items=results,
                country=country,
                industry=industry,
                source_name=source_name,
                progress_callback=progress_callback,
                cancel_event=cancel_event,
            )
            ingested_count = len(ingested_pairs)
            self._emit_progress(progress_callback, "ingest_phase_completed", ingested=ingested_count)

        for entry in ingested_pairs:
            self._check_cancel(cancel_event)
            item = entry["item"]
            ingest_result = entry["ingest_result"]
            doc_summary = ingest_result["document"]
            document_result = {
                "doc_id": doc_summary["doc_id"],
                "title": doc_summary["title"],
                "url": item.get("url"),
                "published_at": item.get("published_at"),
                "extracted_keywords": ingest_result.get("extracted_keywords", []),
                "risk_level": None,
                "risk_tags": [],
                "pptx_file_path": None
            }

            if generate_pptx and generated_report_count < max_documents_to_process:
                try:
                    analysis = await self.analysis_service.analyze_document(
                        doc_id=doc_summary["doc_id"],
                        mode="translate_first",
                        target_language=target_language,
                        use_llm=True,
                        provider=provider,
                        user_prompt=user_prompt,
                        model_name=model_name
                    )
                except Exception:
                    analysis = await self.analysis_service.analyze_document(
                        doc_id=doc_summary["doc_id"],
                        mode="translate_first",
                        target_language=target_language,
                        use_llm=False,
                        provider=provider,
                        user_prompt=user_prompt,
                        model_name=model_name
                    )

                document_result["risk_level"] = analysis.get("risk_level")
                document_result["risk_tags"] = analysis.get("risk_tags", [])

                if not high_risk_only or analysis.get("risk_level") == "High":
                    report = await self.report_service.generate_report(
                        doc_id=doc_summary["doc_id"],
                        output_format="pptx",
                        provider=provider,
                        model_name=model_name,
                        target_language=target_language,
                        user_prompt=user_prompt
                    )
                    document_result["pptx_file_path"] = report.get("file_path")
                    if report.get("file_path"):
                        generated_report_count += 1

            ingested_documents.append(document_result)

        train_result = self.keyword_service.train_from_database()

        return {
            "query": " ".join(normalized_keywords),
            "normalized_keywords": normalized_keywords,
            "searched_result_count": len(results),
            "ingested_result_count": ingested_count,
            "generated_report_count": generated_report_count,
            "trained_keyword_model": {
                "message": train_result["message"],
                "document_count": train_result["document_count"],
                "vocabulary_size": train_result["vocabulary_size"]
            },
            "search_results": self._normalize_search_results(results),
            "documents": ingested_documents
        }
