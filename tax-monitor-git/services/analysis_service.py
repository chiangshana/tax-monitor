import json
import re
from typing import List

from services.document_service import DocumentService
from services.keyword_service import KeywordService
from services.language_service import LanguageService
from services.llm_service import LLMService
from services.translator_service import TranslatorService


class AnalysisService:
    def __init__(self):
        self.document_service = DocumentService()
        self.keyword_service = KeywordService()
        self.language_service = LanguageService()
        self.translator_service = TranslatorService()
        self.llm_service = LLMService()

    async def analyze_document(
        self,
        doc_id: str,
        mode: str = "translate_first",
        target_language: str = "zh",
        use_llm: bool = False,
        provider: str = "ollama",
        user_prompt: str = None,
        model_name: str = "qwen3:8b"
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
                model_name=model_name
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
                model_name=model_name
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
            "notes": notes
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
        model_name: str
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
