import re
from typing import List

from sklearn.feature_extraction.text import TfidfVectorizer

from services.llm_service import LLMService
from services.storage_service import StorageService


class KeywordService:
    STOPWORDS = {
        "a", "an", "and", "are", "as", "at", "be", "been", "by", "for", "from",
        "in", "into", "is", "it", "its", "of", "on", "or", "that", "the",
        "their", "this", "to", "was", "were", "with", "will", "may", "need",
        "you", "your", "our", "we", "they", "them", "he", "she", "his", "her",
        "not", "than", "then", "there", "here", "about", "after", "before",
        "also", "only", "such", "using", "used", "use"
    }

    def __init__(self):
        self.storage_service = StorageService()
        self.llm_service = LLMService()
        self.vectorizer = None
        self.feature_names = []

    def train_from_database(self):
        rows = self.storage_service.get_all_texts()
        corpus = []

        for row in rows:
            title = row.get("title", "")
            raw_text = row.get("raw_text", "")
            corpus.append(f"{title}\n{raw_text}")

        if not corpus:
            self.vectorizer = None
            self.feature_names = []
            return {
                "message": "No documents found. Keyword model not trained.",
                "document_count": 0,
                "vocabulary_size": 0
            }

        self.vectorizer = TfidfVectorizer(
            max_features=3000,
            ngram_range=(1, 2),
            tokenizer=self._tokenize,
            lowercase=True,
            token_pattern=None
        )
        self.vectorizer.fit(corpus)
        self.feature_names = list(self.vectorizer.get_feature_names_out())

        return {
            "message": "Keyword model trained successfully.",
            "document_count": len(corpus),
            "vocabulary_size": len(self.feature_names)
        }

    def extract_keywords_for_document(self, title: str, text: str, top_k: int = 12) -> List[str]:
        if self.vectorizer is None:
            self.train_from_database()

        content = f"{title}\n{text}"
        if self.vectorizer is None:
            return []

        matrix = self.vectorizer.transform([content])
        scores = matrix.toarray()[0]

        pairs = list(zip(self.feature_names, scores))
        pairs.sort(key=lambda item: item[1], reverse=True)

        results = []
        for term, score in pairs:
            if score <= 0:
                continue
            if not self._is_valid_keyword(term):
                continue
            results.append(term)
            if len(results) >= top_k:
                break

        return results

    def train_keyword_profile(
        self,
        profile_name: str,
        user_keywords: List[str],
        risk_labels: List[str],
        user_prompt: str = None,
        provider: str = "ollama",
        model_name: str = "qwen3:8b"
    ):
        rows = self.storage_service.get_all_texts()
        corpus_sample = "\n".join(
            f"{row.get('title', '')}\n{row.get('raw_text', '')[:1200]}"
            for row in rows[:5]
        )
        fallback_keywords = self._fallback_expand_keywords(user_keywords, risk_labels)
        prompt = f"""
你是一位稅務監測系統的關鍵字設計助手。
請根據使用者需求、風險標籤與樣本文本，產出可用於自動搜尋的關鍵字。
請混合主題詞、法規詞、風險詞、制度變動詞與同義詞。
請只輸出 JSON：
{{
  "expanded_keywords": ["keyword1", "keyword2", "keyword3"]
}}

使用者原始關鍵字：{user_keywords}
風險標籤：{risk_labels}
使用者補充需求：{user_prompt or ""}
樣本文本：
{corpus_sample[:4000]}
"""
        data = self.llm_service.generate_json(
            prompt=prompt,
            schema_hint={"expanded_keywords": fallback_keywords},
            provider=provider,
            model_name=model_name
        )
        expanded_keywords = self._deduplicate_keywords(
            user_keywords + risk_labels + data.get("expanded_keywords", [])
        )
        self.storage_service.save_keyword_profile(
            profile_name=profile_name,
            user_keywords=user_keywords,
            expanded_keywords=expanded_keywords,
            risk_labels=risk_labels
        )
        return self.storage_service.get_keyword_profile(profile_name)

    def list_keyword_profiles(self):
        return self.storage_service.list_keyword_profiles()

    def get_keyword_profile(self, profile_name: str):
        return self.storage_service.get_keyword_profile(profile_name)

    def _fallback_expand_keywords(self, user_keywords: List[str], risk_labels: List[str]) -> List[str]:
        seed_terms = user_keywords + risk_labels
        expanded = []
        for term in seed_terms:
            expanded.extend([term, f"{term} tax", f"{term} regulation", f"{term} reform"])
            if re.search(r"稅|tax", term, flags=re.IGNORECASE):
                expanded.extend(["稅務風險", "稅制改革", "tax risk", "tax reform"])
        return self._deduplicate_keywords(expanded)

    def _deduplicate_keywords(self, keywords: List[str]) -> List[str]:
        results = []
        seen = set()
        for keyword in keywords:
            cleaned = keyword.strip()
            if not cleaned:
                continue
            normalized = cleaned.lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            results.append(cleaned)
        return results

    def _tokenize(self, text: str) -> List[str]:
        normalized = text.lower()
        tokens = re.findall(r"[\u4e00-\u9fff]{2,}|[a-z0-9][a-z0-9_-]{1,}", normalized)
        bigrams = [f"{tokens[i]} {tokens[i + 1]}" for i in range(len(tokens) - 1)]
        return tokens + bigrams

    def _is_valid_keyword(self, term: str) -> bool:
        cleaned = term.strip().lower()
        if len(cleaned) <= 1:
            return False
        if cleaned in self.STOPWORDS:
            return False

        parts = cleaned.split()
        if all(part in self.STOPWORDS for part in parts):
            return False
        if any(len(part) <= 1 for part in parts):
            return False
        if len(parts) > 1 and (parts[0] in self.STOPWORDS or parts[-1] in self.STOPWORDS):
            return False

        if re.fullmatch(r"[0-9]+", cleaned):
            return False

        return True
