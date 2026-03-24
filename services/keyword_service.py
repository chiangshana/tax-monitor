from typing import List
from sklearn.feature_extraction.text import TfidfVectorizer

from services.storage_service import StorageService


class KeywordService:
    def __init__(self):
        self.storage_service = StorageService()
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
            stop_words="english"
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
            if len(term.strip()) <= 1:
                continue
            results.append(term)
            if len(results) >= top_k:
                break

        return results
