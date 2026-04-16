import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "tax_monitor.db"
FALLBACK_DB_PATH = BASE_DIR / "tax_monitor_runtime.db"
MEMORY_DB_URI = "file:tax_monitor_shared?mode=memory&cache=shared"


class StorageService:
    _shared_db_path = None
    _shared_use_uri = False
    _shared_memory_conn = None

    def __init__(self):
        self.db_path = self.__class__._shared_db_path or self._resolve_db_path()
        self.use_uri = self.__class__._shared_use_uri
        self._memory_conn = self.__class__._shared_memory_conn
        self._init_db()
        self._sync_shared_state()

    def _resolve_db_path(self) -> Path:
        if DB_PATH.exists():
            return DB_PATH
        return FALLBACK_DB_PATH

    def _init_db(self):
        try:
            self._create_tables(self.db_path)
        except sqlite3.OperationalError:
            try:
                self.db_path = FALLBACK_DB_PATH
                self._create_tables(self.db_path)
            except sqlite3.OperationalError:
                self._switch_to_memory()

    def _create_tables(self, db_path: Path):
        if not self.use_uri:
            db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = self._connect()
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
                published_date TEXT,
                created_at TEXT
            )
        """)
        self._ensure_column(cur, "documents", "updated_at", "TEXT")
        self._ensure_column(cur, "documents", "published_date", "TEXT")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS keyword_profiles (
                profile_name TEXT PRIMARY KEY,
                user_keywords TEXT,
                expanded_keywords TEXT,
                risk_labels TEXT,
                updated_at TEXT
            )
        """)
        conn.commit()
        if conn is not self._memory_conn:
            conn.close()

    def _ensure_column(self, cur, table_name: str, column_name: str, column_type: str):
        cur.execute(f"PRAGMA table_info({table_name})")
        columns = {row[1] for row in cur.fetchall()}
        if column_name not in columns:
            cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")

    def _connect(self):
        self._refresh_from_shared_state()
        if self.use_uri:
            if self._memory_conn is None:
                self._memory_conn = sqlite3.connect(self.db_path, uri=True, check_same_thread=False)
                self._sync_shared_state()
            return self._memory_conn
        return sqlite3.connect(self.db_path)

    def _switch_to_memory(self):
        self.db_path = MEMORY_DB_URI
        self.use_uri = True
        if self.__class__._shared_memory_conn is None:
            self.__class__._shared_memory_conn = sqlite3.connect(
                self.db_path,
                uri=True,
                check_same_thread=False
            )
        self._memory_conn = self.__class__._shared_memory_conn
        self._sync_shared_state()
        self._create_tables(self.db_path)

    def _sync_shared_state(self):
        self.__class__._shared_db_path = self.db_path
        self.__class__._shared_use_uri = self.use_uri
        self.__class__._shared_memory_conn = self._memory_conn

    def _refresh_from_shared_state(self):
        if self.__class__._shared_db_path is not None:
            self.db_path = self.__class__._shared_db_path
        self.use_uri = self.__class__._shared_use_uri
        self._memory_conn = self.__class__._shared_memory_conn

    def _retry_on_readonly(self, operation):
        try:
            return operation()
        except sqlite3.OperationalError as exc:
            error_text = str(exc).lower()
            if "readonly" not in error_text and "disk i/o" not in error_text and "unable to open database file" not in error_text:
                raise
            self._switch_to_memory()
            return operation()

    def save_document(self, document: Dict):
        def operation():
            conn = self._connect()
            cur = conn.cursor()
            cur.execute("""
                INSERT OR REPLACE INTO documents (
                    doc_id, title, source_type, source_name, file_name, url,
                    raw_text, language, country, industry, published_date, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                document.get("published_date"),
                document["created_at"],
                document.get("updated_at", document["created_at"])
            ))
            conn.commit()
            if conn is not self._memory_conn:
                conn.close()
        self._retry_on_readonly(operation)

    def get_document(self, doc_id: str) -> Optional[Dict]:
        conn = self._connect()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM documents WHERE doc_id = ?", (doc_id,))
        row = cur.fetchone()
        if conn is not self._memory_conn:
            conn.close()
        return dict(row) if row else None

    def list_documents(
        self,
        page: int = 1,
        page_size: int = 10,
        country: str = None,
        industry: str = None,
        language: str = None,
        source_name: str = None,
        keyword: str = None
    ) -> Dict:
        conn = self._connect()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        filters = []
        params = []
        if country:
            filters.append("country = ?")
            params.append(country)
        if industry:
            filters.append("industry = ?")
            params.append(industry)
        if language:
            filters.append("language = ?")
            params.append(language)
        if source_name:
            filters.append("source_name = ?")
            params.append(source_name)
        if keyword:
            filters.append("(title LIKE ? OR raw_text LIKE ?)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])

        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
        cur.execute(f"SELECT COUNT(*) FROM documents {where_clause}", params)
        total = cur.fetchone()[0]

        offset = (page - 1) * page_size
        cur.execute(f"""
            SELECT doc_id, title, source_type, source_name, language, country, industry,
                   published_date, created_at, updated_at
            FROM documents
            {where_clause}
            ORDER BY COALESCE(published_date, created_at) DESC
            LIMIT ? OFFSET ?
        """, params + [page_size, offset])
        rows = cur.fetchall()
        if conn is not self._memory_conn:
            conn.close()
        return {
            "documents": [dict(row) for row in rows],
            "page": page,
            "page_size": page_size,
            "total": total
        }

    def get_all_texts(self) -> List[Dict]:
        conn = self._connect()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT doc_id, title, raw_text FROM documents")
        rows = cur.fetchall()
        if conn is not self._memory_conn:
            conn.close()
        return [dict(row) for row in rows]

    def update_document(self, doc_id: str, updates: Dict) -> Optional[Dict]:
        allowed_fields = ["title", "country", "industry", "source_name", "published_date"]
        set_clauses = []
        params = []
        for field in allowed_fields:
            if field in updates and updates[field] is not None:
                set_clauses.append(f"{field} = ?")
                params.append(updates[field])

        if not set_clauses:
            return self.get_document(doc_id)

        set_clauses.append("updated_at = ?")
        params.append(datetime.now().isoformat(timespec="seconds"))
        params.append(doc_id)

        def operation():
            conn = self._connect()
            cur = conn.cursor()
            cur.execute(f"UPDATE documents SET {', '.join(set_clauses)} WHERE doc_id = ?", params)
            conn.commit()
            if conn is not self._memory_conn:
                conn.close()
        self._retry_on_readonly(operation)
        return self.get_document(doc_id)

    def save_keyword_profile(
        self,
        profile_name: str,
        user_keywords: List[str],
        expanded_keywords: List[str],
        risk_labels: List[str]
    ):
        def operation():
            conn = self._connect()
            cur = conn.cursor()
            cur.execute("""
                INSERT OR REPLACE INTO keyword_profiles (
                    profile_name, user_keywords, expanded_keywords, risk_labels, updated_at
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                profile_name,
                ",".join(user_keywords),
                ",".join(expanded_keywords),
                ",".join(risk_labels),
                datetime.now().isoformat(timespec="seconds")
            ))
            conn.commit()
            if conn is not self._memory_conn:
                conn.close()
        self._retry_on_readonly(operation)

    def get_keyword_profile(self, profile_name: str) -> Optional[Dict]:
        conn = self._connect()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM keyword_profiles WHERE profile_name = ?", (profile_name,))
        row = cur.fetchone()
        if conn is not self._memory_conn:
            conn.close()
        if not row:
            return None
        data = dict(row)
        data["user_keywords"] = self._split_csv(data.get("user_keywords"))
        data["expanded_keywords"] = self._split_csv(data.get("expanded_keywords"))
        data["risk_labels"] = self._split_csv(data.get("risk_labels"))
        return data

    def list_keyword_profiles(self) -> List[Dict]:
        conn = self._connect()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM keyword_profiles ORDER BY updated_at DESC")
        rows = cur.fetchall()
        if conn is not self._memory_conn:
            conn.close()

        profiles = []
        for row in rows:
            data = dict(row)
            data["user_keywords"] = self._split_csv(data.get("user_keywords"))
            data["expanded_keywords"] = self._split_csv(data.get("expanded_keywords"))
            data["risk_labels"] = self._split_csv(data.get("risk_labels"))
            profiles.append(data)
        return profiles

    def _split_csv(self, value: Optional[str]) -> List[str]:
        if not value:
            return []
        return [item for item in value.split(",") if item]
