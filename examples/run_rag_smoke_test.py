from datetime import UTC, datetime
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from services.rag_service import RAGService
from services.storage_service import MEMORY_DB_URI, StorageService


def seed_document(storage, doc_id, title, raw_text):
    now = datetime.now(UTC).isoformat()
    storage.save_document(
        {
            "doc_id": doc_id,
            "title": title,
            "source_type": "html",
            "source_name": "rag_smoke_test",
            "url": f"https://example.com/{doc_id}",
            "raw_text": raw_text,
            "language": "en",
            "created_at": now,
            "updated_at": now,
        }
    )


def main():
    StorageService._shared_db_path = MEMORY_DB_URI
    StorageService._shared_use_uri = True
    StorageService._shared_memory_conn = None

    storage = StorageService()
    seed_document(
        storage,
        "asus-tax-risk",
        "ASUS cross-border tax risk",
        (
            "ASUS and overseas subsidiaries should review transfer pricing, "
            "withholding tax, Pillar Two global minimum tax, and permanent "
            "establishment exposure in cross-border operations."
        ),
    )
    seed_document(
        storage,
        "consumer-product",
        "Consumer product launch",
        "A consumer product launch with no material tax compliance issue.",
    )

    result = RAGService().retrieve_context(
        "ASUS tax risk transfer pricing Pillar Two",
        top_k=2,
    )

    print(f"rag_chunk_count: {len(result['chunks'])}")
    for index, chunk in enumerate(result["chunks"], start=1):
        print(f"{index}. {chunk['title']} | score={chunk['score']}")

    assert result["chunks"], "Expected at least one RAG chunk"
    assert result["chunks"][0]["doc_id"] == "asus-tax-risk"
    print("rag_smoke_test: ok")


if __name__ == "__main__":
    main()
