import re
from typing import Dict, List, Optional

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from services.storage_service import StorageService


class RAGService:
    """Lightweight retrieval over ingested documents.

    This intentionally avoids an external vector database so the Windows
    installer remains simple. It chunks the local SQLite corpus and reranks
    chunks with TF-IDF cosine similarity.
    """

    DEFAULT_RISK_TERMS = [
        "tax risk",
        "tax audit",
        "tax investigation",
        "transfer pricing",
        "withholding tax",
        "permanent establishment",
        "pillar two",
        "global minimum tax",
        "tax penalty",
        "tax reform",
        "filing obligation",
        "稅務風險",
        "稅務稽查",
        "查稅",
        "補稅",
        "轉讓訂價",
        "扣繳稅",
        "常設機構",
        "全球最低稅負",
        "申報義務",
    ]

    def __init__(self):
        self.storage_service = StorageService()

    def retrieve_context(
        self,
        query: str,
        exclude_doc_id: Optional[str] = None,
        top_k: int = 4,
        chunk_chars: int = 1400,
        max_context_chars: int = 4500,
    ) -> Dict:
        query = (query or "").strip()
        top_k = max(0, min(int(top_k or 0), 10))
        if not query or top_k <= 0:
            return {"query": query, "chunks": [], "context_text": ""}

        chunks = self._build_chunks(exclude_doc_id=exclude_doc_id, chunk_chars=chunk_chars)
        if not chunks:
            return {"query": query, "chunks": [], "context_text": ""}

        corpus = [chunk["text"] for chunk in chunks] + [self._augment_query(query)]
        try:
            vectorizer = TfidfVectorizer(
                tokenizer=self._tokenize,
                lowercase=True,
                token_pattern=None,
                ngram_range=(1, 2),
                max_features=12000,
            )
            matrix = vectorizer.fit_transform(corpus)
            scores = cosine_similarity(matrix[-1], matrix[:-1]).ravel()
        except ValueError:
            scores = [self._lexical_score(query, chunk["text"]) for chunk in chunks]

        ranked = []
        for chunk, score in zip(chunks, scores):
            score_value = float(score)
            if score_value <= 0:
                score_value = self._lexical_score(query, chunk["text"])
            if score_value <= 0:
                continue
            ranked.append((score_value, chunk))
        ranked.sort(key=lambda item: item[0], reverse=True)

        selected = []
        seen_doc_ids = set()
        for score, chunk in ranked:
            doc_id = chunk["doc_id"]
            # Prefer diversity across documents before allowing a second chunk.
            if doc_id in seen_doc_ids and len(seen_doc_ids) < top_k:
                continue
            enriched = dict(chunk)
            enriched["score"] = round(score, 4)
            selected.append(enriched)
            seen_doc_ids.add(doc_id)
            if len(selected) >= top_k:
                break

        if len(selected) < top_k:
            selected_ids = {(item["doc_id"], item["chunk_index"]) for item in selected}
            for score, chunk in ranked:
                key = (chunk["doc_id"], chunk["chunk_index"])
                if key in selected_ids:
                    continue
                enriched = dict(chunk)
                enriched["score"] = round(score, 4)
                selected.append(enriched)
                selected_ids.add(key)
                if len(selected) >= top_k:
                    break

        return {
            "query": query,
            "chunks": selected,
            "context_text": self._format_context(selected, max_context_chars=max_context_chars),
        }

    def _build_chunks(self, exclude_doc_id: Optional[str], chunk_chars: int) -> List[Dict]:
        rows = self.storage_service.get_all_texts()
        chunks: List[Dict] = []
        chunk_chars = max(600, min(int(chunk_chars or 1400), 3000))
        overlap = min(250, chunk_chars // 5)
        stride = chunk_chars - overlap

        for row in rows:
            doc_id = row.get("doc_id")
            if exclude_doc_id and doc_id == exclude_doc_id:
                continue
            raw_text = (row.get("raw_text") or "").strip()
            if not raw_text:
                continue
            title = row.get("title") or "Untitled"
            normalized_text = re.sub(r"\s+", " ", raw_text)
            for chunk_index, start in enumerate(range(0, len(normalized_text), stride)):
                text = normalized_text[start:start + chunk_chars].strip()
                if len(text) < 80:
                    continue
                chunks.append({
                    "doc_id": doc_id,
                    "title": title,
                    "url": row.get("url"),
                    "source_name": row.get("source_name"),
                    "published_date": row.get("published_date"),
                    "chunk_index": chunk_index,
                    "text": text,
                })
                if chunk_index >= 8:
                    break
        return chunks

    def _augment_query(self, query: str) -> str:
        return " ".join([query] + self.DEFAULT_RISK_TERMS)

    def _format_context(self, chunks: List[Dict], max_context_chars: int) -> str:
        if not chunks:
            return ""
        blocks = []
        used = 0
        max_context_chars = max(1000, min(int(max_context_chars or 4500), 12000))
        for index, chunk in enumerate(chunks, start=1):
            source_bits = [chunk.get("title") or "Untitled"]
            if chunk.get("published_date"):
                source_bits.append(str(chunk["published_date"]))
            if chunk.get("source_name"):
                source_bits.append(str(chunk["source_name"]))
            if chunk.get("url"):
                source_bits.append(str(chunk["url"]))
            header = f"[RAG {index}] score={chunk.get('score', 0)} source={' | '.join(source_bits)}"
            body = chunk.get("text", "")
            block = f"{header}\n{body}"
            if used + len(block) > max_context_chars:
                remaining = max_context_chars - used
                if remaining <= 200:
                    break
                block = block[:remaining].rstrip()
            blocks.append(block)
            used += len(block)
            if used >= max_context_chars:
                break
        return "\n\n".join(blocks)

    def _tokenize(self, text: str) -> List[str]:
        normalized = (text or "").lower()
        tokens = re.findall(r"[a-z0-9][a-z0-9_-]{1,}", normalized)
        for segment in re.findall(r"[\u4e00-\u9fff]{2,}", normalized):
            if len(segment) <= 8:
                tokens.append(segment)
            tokens.extend(segment[i:i + 2] for i in range(len(segment) - 1))
            tokens.extend(segment[i:i + 3] for i in range(len(segment) - 2))
        return tokens

    def _lexical_score(self, query: str, text: str) -> float:
        query_tokens = set(self._tokenize(query))
        text_tokens = set(self._tokenize(text))
        if not query_tokens or not text_tokens:
            return 0.0
        overlap = len(query_tokens & text_tokens)
        return overlap / max(len(query_tokens), 1)
