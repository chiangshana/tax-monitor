import json
import re
from typing import List

from services.document_service import DocumentService
from services.keyword_service import KeywordService
from services.language_service import LanguageService
from services.llm_service import LLMService
from services.rag_service import RAGService
from services.translator_service import TranslatorService


class AnalysisService:
    def __init__(self):
        self.document_service = DocumentService()
        self.keyword_service = KeywordService()
        self.language_service = LanguageService()
        self.translator_service = TranslatorService()
        self.llm_service = LLMService()
        self.rag_service = RAGService()

    async def analyze_document(
        self,
        doc_id: str,
        mode: str = "translate_first",
        target_language: str = "zh",
        use_llm: bool = False,
        provider: str = "ollama",
        user_prompt: str = None,
        model_name: str = "qwen3:8b",
        use_rag_context: bool = True,
        rag_top_k: int = 4,
        rag_query: str = None
    ):
        document = self.document_service.get_document(doc_id)
        if not document:
            raise ValueError("Document not found")

        title = document["title"]
        raw_text = document["raw_text"]
        detected_language = document["language"]

        auto_keywords = self.keyword_service.extract_keywords_for_document(
            title=title,
            text=raw_text
        )

        notes = []
        evidence = self._extract_evidence(raw_text, auto_keywords)
        risk_tags = self._extract_risk_tags(raw_text, auto_keywords)
        bilingual_summary = {}
        rag_context = {"query": "", "chunks": [], "context_text": ""}
        if use_rag_context:
            rag_context = self.rag_service.retrieve_context(
                query=self._build_rag_query(
                    title=title,
                    auto_keywords=auto_keywords,
                    user_prompt=user_prompt,
                    rag_query=rag_query,
                ),
                exclude_doc_id=doc_id,
                top_k=rag_top_k,
            )
            if rag_context.get("chunks"):
                notes.append(f"RAG context used: {len(rag_context['chunks'])} related chunks")

        if mode == "translate_first":
            notes.append("先翻譯，再分析")
            working_text = await self.translator_service.translate_text(
                text=raw_text,
                source_language=detected_language,
                target_language=target_language,
                use_llm=use_llm,
                provider=provider,
                model_name=model_name
            )
            summary = await self._generate_summary(
                text=working_text,
                keywords=auto_keywords,
                target_language=target_language,
                use_llm=use_llm,
                provider=provider,
                user_prompt=user_prompt,
                model_name=model_name,
                rag_context=rag_context.get("context_text", "")
            )
            translated_summary = None
            bilingual_summary = {
                detected_language: raw_text[:400],
                target_language: summary
            }

        elif mode == "analyze_first":
            notes.append("先分析，再翻譯")
            summary = await self._generate_summary(
                text=raw_text,
                keywords=auto_keywords,
                target_language=detected_language,
                use_llm=use_llm,
                provider=provider,
                user_prompt=user_prompt,
                model_name=model_name,
                rag_context=rag_context.get("context_text", "")
            )
            translated_summary = await self.translator_service.translate_text(
                text=summary,
                source_language=detected_language,
                target_language=target_language,
                use_llm=use_llm,
                provider=provider,
                model_name=model_name
            )
            bilingual_summary = {
                detected_language: summary,
                target_language: translated_summary
            }
        else:
            raise ValueError("Unsupported mode")

        risk_level = self._detect_risk_level(raw_text)

        return {
            "doc_id": doc_id,
            "title": title,
            "detected_language": detected_language,
            "mode": mode,
            "target_language": target_language,
            "auto_keywords": auto_keywords,
            "risk_level": risk_level,
            "risk_tags": risk_tags,
            "summary": summary,
            "translated_summary": translated_summary,
            "bilingual_summary": bilingual_summary,
            "evidence": evidence,
            "notes": notes,
            "rag_context": {
                "query": rag_context.get("query", ""),
                "chunks": [
                    {
                        "doc_id": chunk.get("doc_id"),
                        "title": chunk.get("title"),
                        "url": chunk.get("url"),
                        "source_name": chunk.get("source_name"),
                        "published_date": chunk.get("published_date"),
                        "score": chunk.get("score"),
                        "chunk_index": chunk.get("chunk_index"),
                    }
                    for chunk in rag_context.get("chunks", [])
                ],
            }
        }

    async def preview_translation(self, raw_text: str, original_language: str, target_language: str):
        return await self.translator_service.translate_text(
            text=raw_text,
            source_language=original_language,
            target_language=target_language,
            use_llm=False
        )

    async def _generate_summary(
        self,
        text: str,
        keywords: List[str],
        target_language: str,
        use_llm: bool,
        provider: str,
        user_prompt: str,
        model_name: str,
        rag_context: str = ""
    ) -> str:
        fallback = self._fallback_summary(text, keywords)

        if not use_llm:
            return fallback

        prompt = f"""
你是一位稅務研究助理。
請根據以下文本做摘要，重點放在：
1. 修法或政策重點
2. 可能受影響對象
3. 生效日或時間資訊
4. 可能風險或管理重點

請用 {target_language} 輸出，語氣簡單、明確。
只輸出 JSON：
{{
  "summary": "摘要內容"
}}

關鍵字：{keywords}
使用者需求：{user_prompt or ""}
RAG 相關背景（供交叉比對，不可把沒有證據的推測寫成事實）：
{rag_context or "N/A"}

文本：
{text[:12000]}
"""
        data = self.llm_service.generate_json(
            prompt=prompt,
            schema_hint={"summary": fallback},
            provider=provider,
            model_name=model_name
        )
        return data.get("summary", fallback)

    def _build_rag_query(
        self,
        title: str,
        auto_keywords: List[str],
        user_prompt: str = None,
        rag_query: str = None,
    ) -> str:
        parts = [
            title or "",
            user_prompt or "",
            rag_query or "",
            " ".join(auto_keywords or []),
            "tax risk transfer pricing withholding tax permanent establishment pillar two audit penalty filing obligation",
            "稅務風險 轉讓訂價 扣繳稅 常設機構 全球最低稅負 稅務稽查 補稅 申報義務",
        ]
        return " ".join(part for part in parts if part).strip()

    def _fallback_summary(self, text: str, keywords: List[str]) -> str:
        sentences = self.language_service.split_sentences(text)
        scored = []

        for sentence in sentences:
            score = sum(1 for keyword in keywords if keyword.lower() in sentence.lower())
            score += len(sentence) / 500
            scored.append((score, sentence))

        scored.sort(key=lambda item: item[0], reverse=True)
        selected = [sentence for _, sentence in scored[:4]]

        if not selected:
            return text[:400]
        return "；".join(selected[:3])

    def _extract_evidence(self, text: str, keywords: List[str], top_k: int = 3):
        sentences = self.language_service.split_sentences(text)
        scored = []

        for sentence in sentences:
            score = sum(1 for keyword in keywords if keyword.lower() in sentence.lower())
            if re.search(r"20\d{2}|生效|effective|draft|草案", sentence, flags=re.IGNORECASE):
                score += 2
            scored.append((score, sentence))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [sentence for _, sentence in scored[:top_k] if sentence]

    def _detect_risk_level(self, text: str) -> str:
        text_lower = text.lower()
        high_terms = [
            "penalty", "audit", "investigation", "mandatory", "effective date",
            "draft", "compliance", "罰則", "查核", "草案", "生效", "申報義務"
        ]
        medium_terms = [
            "clarification", "filing", "threshold", "guidance",
            "申報", "門檻", "解釋", "通知"
        ]

        high_score = sum(1 for term in high_terms if term.lower() in text_lower)
        medium_score = sum(1 for term in medium_terms if term.lower() in text_lower)

        if high_score >= 3:
            return "High"
        if high_score >= 1 or medium_score >= 2:
            return "Medium"
        return "Low"

    def _extract_risk_tags(self, text: str, keywords: List[str]) -> List[str]:
        mapping = {
            "penalty": ["penalty", "罰則", "fine"],
            "audit": ["audit", "查核", "investigation"],
            "filing_obligation": ["filing", "申報", "declaration"],
            "effective_date": ["effective", "生效", "implementation"],
            "draft_regulation": ["draft", "草案", "proposal"],
            "compliance_change": ["compliance", "合規", "obligation"]
        }
        haystack = f"{text}\n{' '.join(keywords)}".lower()
        tags = []
        for tag, terms in mapping.items():
            if any(term.lower() in haystack for term in terms):
                tags.append(tag)
        return tags

    async def evaluate_document(
        self,
        doc_id: str,
        target_language: str = "zh",
        provider: str = "ollama",
        model_name: str = "qwen3:8b",
        user_prompt: str = None
    ):
        rule_result = await self.analyze_document(
            doc_id=doc_id,
            mode="translate_first",
            target_language=target_language,
            use_llm=False,
            provider=provider,
            user_prompt=user_prompt,
            model_name=model_name
        )
        llm_result = await self.analyze_document(
            doc_id=doc_id,
            mode="translate_first",
            target_language=target_language,
            use_llm=True,
            provider=provider,
            user_prompt=user_prompt,
            model_name=model_name
        )
        overlap_score = self._calculate_overlap(
            rule_result["summary"],
            llm_result["summary"]
        )
        notes = [
            f"rule_keywords={len(rule_result.get('auto_keywords', []))}",
            f"llm_risk_tags={','.join(llm_result.get('risk_tags', []))}"
        ]
        return {
            "doc_id": doc_id,
            "compare_mode": "rule_vs_llm",
            "rule_based_summary": rule_result["summary"],
            "llm_summary": llm_result["summary"],
            "overlap_score": overlap_score,
            "risk_level_rule": rule_result["risk_level"],
            "risk_level_llm": llm_result["risk_level"],
            "notes": notes
        }

    def _calculate_overlap(self, text_a: str, text_b: str) -> float:
        tokens_a = set(re.findall(r"[\u4e00-\u9fff]{2,}|[a-z0-9_]{2,}", text_a.lower()))
        tokens_b = set(re.findall(r"[\u4e00-\u9fff]{2,}|[a-z0-9_]{2,}", text_b.lower()))
        if not tokens_a or not tokens_b:
            return 0.0
        score = len(tokens_a & tokens_b) / len(tokens_a | tokens_b)
        return round(score, 3)
