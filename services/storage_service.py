import sqlite3
from pathlib import Path
from typing import Dict, List, Optional


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "tax_monitor.db"


class StorageService:
    def __init__(self):
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                doc_id TEXT PRIMARY KEY,
                title TEXT,
                source_type TEXT,
                source_name TEXT,
                file_name TEXT,
                url TEXT,
                raw_text TEXT,
                language TEXT,
                country TEXT,
                industry TEXT,
                created_at TEXT
            )
        """)
        conn.commit()
        conn.close()

    def save_document(self, document: Dict):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO documents (
                doc_id, title, source_type, source_name, file_name, url,
                raw_text, language, country, industry, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            document["doc_id"],
            document["title"],
            document["source_type"],
            document.get("source_name"),
            document.get("file_name"),
            document.get("url"),
            document["raw_text"],
            document["language"],
            document.get("country"),
            document.get("industry"),
            document["created_at"]
        ))
        conn.commit()
        conn.close()

    def get_document(self, doc_id: str) -> Optional[Dict]:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM documents WHERE doc_id = ?", (doc_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    def list_documents(self) -> List[Dict]:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT doc_id, title, source_type, language, country, industry, created_at
            FROM documents
            ORDER BY created_at DESC
        """)
        rows = cur.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_all_texts(self) -> List[Dict]:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT doc_id, title, raw_text FROM documents")
        rows = cur.fetchall()
        conn.close()
        return [dict(row) for row in rows]
