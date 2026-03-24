import json
import re
from typing import List

import requests

from services.document_service import DocumentService
from services.keyword_service import KeywordService
from services.language_service import LanguageService
from services.translator_service import TranslatorService


class AnalysisService:
    def __init__(self):
        self.document_service = DocumentService()
        self.keyword_service = KeywordService()
        self.language_service = LanguageService()
        self.translator_service = TranslatorService()

    async def analyze_document(
        self,
        doc_id: str,
        mode: str = "translate_first",
        target_language: str = "zh",
        use_llm: bool = False,
        model_name: str = "qwen2.5:7b"
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

        if mode == "translate_first":
            notes.append("先翻譯，再分析")
            working_text = await self.translator_service.translate_text(
                text=raw_text,
                source_language=detected_language,
                target_language=target_language,
                use_llm=use_llm,
                model_name=model_name
            )
            summary = await self._generate_summary(
                text=working_text,
                keywords=auto_keywords,
                target_language=target_language,
                use_llm=use_llm,
                model_name=model_name
            )
            translated_summary = None

        elif mode == "analyze_first":
            notes.append("先分析，再翻譯")
            summary = await self._generate_summary(
                text=raw_text,
                keywords=auto_keywords,
                target_language=detected_language,
                use_llm=use_llm,
                model_name=model_name
            )
            translated_summary = await self.translator_service.translate_text(
                text=summary,
                source_language=detected_language,
                target_language=target_language,
                use_llm=use_llm,
                model_name=model_name
            )
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
            "summary": summary,
            "translated_summary": translated_summary,
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
文本：
{text[:12000]}
"""
        try:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={"model": model_name, "prompt": prompt, "stream": False},
                timeout=90
            )
            response.raise_for_status()
            content = response.json().get("response", "").strip()
            data = json.loads(content)
            return data.get("summary", fallback)
        except Exception:
            return fallback

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
