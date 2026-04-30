from typing import Dict, List

from services.analysis_service import AnalysisService
from services.document_service import DocumentService
from services.keyword_service import KeywordService
from services.report_service import ReportService
from services.search_service import SearchService


class PipelineService:
    def __init__(self):
        self.search_service = SearchService()
        self.document_service = DocumentService()
        self.analysis_service = AnalysisService()
        self.report_service = ReportService()
        self.keyword_service = KeywordService()

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
        high_risk_only: bool = False
    ) -> Dict:
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

        processed_documents = []
        ingested_count = 0

        for item in results:
            if len(processed_documents) >= max_documents_to_process:
                break

            if not item.get("url"):
                continue

            try:
                ingest_result = await self.document_service.process_url(
                    url=item["url"],
                    country=country,
                    industry=industry,
                    source_name=source_name,
                    published_date=item.get("published_at")
                )
            except Exception:
                continue

            ingested_count += 1
            doc_id = ingest_result["document"]["doc_id"]

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

            if high_risk_only and analysis["risk_level"] != "High":
                continue

            report = await self.report_service.generate_report(
                doc_id=doc_id,
                output_format=report_format,
                provider=provider,
                model_name=model_name,
                target_language=target_language,
                user_prompt=user_prompt
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
        high_risk_only: bool = False
    ) -> Dict:
        normalized_keywords = self.search_service._normalize_keywords(keywords)
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

        ingested_documents = []
        ingested_count = 0
        generated_report_count = 0

        for item in results:
            if not auto_ingest or not item.get("url"):
                continue

            try:
                ingest_result = await self.document_service.process_url(
                    url=item["url"],
                    country=country,
                    industry=industry,
                    source_name=source_name,
                    published_date=item.get("published_at")
                )
            except Exception:
                continue

            ingested_count += 1
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
