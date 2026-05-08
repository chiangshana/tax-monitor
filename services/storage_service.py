import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from services.runtime_paths import data_dir


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = data_dir() / "tax_monitor.db"
FALLBACK_DB_PATH = data_dir() / "tax_monitor_runtime.db"
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
        return DB_PATH

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
        self._ensure_column(cur, "documents", "content_hash", "TEXT")
        try:
            cur.execute("CREATE INDEX IF NOT EXISTS idx_documents_content_hash ON documents(content_hash)")
        except sqlite3.OperationalError:
            pass
        cur.execute("""
            CREATE TABLE IF NOT EXISTS keyword_profiles (
                profile_name TEXT PRIMARY KEY,
                user_keywords TEXT,
                expanded_keywords TEXT,
                risk_labels TEXT,
                updated_at TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pipeline_runs (
                run_id TEXT PRIMARY KEY,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT NOT NULL,
                source_name TEXT,
                provider TEXT,
                model_name TEXT,
                keywords TEXT,
                user_prompt TEXT,
                payload TEXT,
                result_summary TEXT,
                error TEXT
            )
        """)
        try:
            cur.execute("CREATE INDEX IF NOT EXISTS idx_pipeline_runs_started_at ON pipeline_runs(started_at DESC)")
        except sqlite3.OperationalError:
            pass

        try:
            cur.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
                    doc_id UNINDEXED,
                    title,
                    raw_text,
                    tokenize = 'unicode61 remove_diacritics 2'
                )
            """)
        except sqlite3.OperationalError:
            pass
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
                    raw_text, language, country, industry, published_date,
                    content_hash, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                document.get("content_hash"),
                document["created_at"],
                document.get("updated_at", document["created_at"])
            ))
            try:
                cur.execute("DELETE FROM documents_fts WHERE doc_id = ?", (document["doc_id"],))
                cur.execute(
                    "INSERT INTO documents_fts (doc_id, title, raw_text) VALUES (?, ?, ?)",
                    (document["doc_id"], document.get("title", ""), document.get("raw_text", "")),
                )
            except sqlite3.OperationalError:
                pass
            conn.commit()
            if conn is not self._memory_conn:
                conn.close()
        self._retry_on_readonly(operation)

    def find_document_by_content_hash(self, content_hash: str) -> Optional[Dict]:
        if not content_hash:
            return None
        conn = self._connect()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM documents WHERE content_hash = ? ORDER BY created_at DESC LIMIT 1",
            (content_hash,),
        )
        row = cur.fetchone()
        if conn is not self._memory_conn:
            conn.close()
        return dict(row) if row else None

    def fts_search_documents(self, query: str, limit: int = 20) -> List[Dict]:
        if not query or not query.strip():
            return []
        conn = self._connect()
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT d.doc_id, d.title, d.source_type, d.source_name, d.language,
                       d.country, d.industry, d.published_date, d.created_at, d.updated_at,
                       snippet(documents_fts, 2, '«', '»', ' … ', 12) AS snippet,
                       bm25(documents_fts) AS rank
                FROM documents_fts
                JOIN documents d ON d.doc_id = documents_fts.doc_id
                WHERE documents_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (query, limit),
            )
            rows = cur.fetchall()
        except sqlite3.OperationalError:
            rows = []
        if conn is not self._memory_conn:
            conn.close()
        return [dict(row) for row in rows]

    def record_pipeline_run(
        self,
        run_id: str,
        started_at: str,
        status: str,
        source_name: Optional[str] = None,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        user_prompt: Optional[str] = None,
        payload: Optional[Dict] = None,
    ):
        def operation():
            conn = self._connect()
            cur = conn.cursor()
            cur.execute(
                """
                INSERT OR REPLACE INTO pipeline_runs (
                    run_id, started_at, status, source_name, provider, model_name,
                    keywords, user_prompt, payload, result_summary, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?,
                    COALESCE((SELECT result_summary FROM pipeline_runs WHERE run_id = ?), NULL),
                    COALESCE((SELECT error FROM pipeline_runs WHERE run_id = ?), NULL)
                )
                """,
                (
                    run_id,
                    started_at,
                    status,
                    source_name,
                    provider,
                    model_name,
                    json.dumps(keywords or [], ensure_ascii=False),
                    user_prompt,
                    json.dumps(payload or {}, ensure_ascii=False, default=str),
                    run_id,
                    run_id,
                ),
            )
            conn.commit()
            if conn is not self._memory_conn:
                conn.close()
        self._retry_on_readonly(operation)

    def finalize_pipeline_run(
        self,
        run_id: str,
        finished_at: str,
        status: str,
        result_summary: Optional[Dict] = None,
        error: Optional[str] = None,
    ):
        def operation():
            conn = self._connect()
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE pipeline_runs
                SET finished_at = ?, status = ?, result_summary = ?, error = ?
                WHERE run_id = ?
                """,
                (
                    finished_at,
                    status,
                    json.dumps(result_summary or {}, ensure_ascii=False, default=str),
                    error,
                    run_id,
                ),
            )
            conn.commit()
            if conn is not self._memory_conn:
                conn.close()
        self._retry_on_readonly(operation)

    def list_pipeline_runs(self, limit: int = 50) -> List[Dict]:
        conn = self._connect()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            """
            SELECT run_id, started_at, finished_at, status, source_name, provider,
                   model_name, keywords, user_prompt, result_summary, error
            FROM pipeline_runs
            ORDER BY started_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cur.fetchall()
        if conn is not self._memory_conn:
            conn.close()
        runs: List[Dict] = []
        for row in rows:
            data = dict(row)
            for key in ("keywords", "result_summary"):
                if data.get(key):
                    try:
                        data[key] = json.loads(data[key])
                    except (TypeError, ValueError):
                        pass
            runs.append(data)
        return runs

    def clear_runtime_data(
        self,
        documents: bool = False,
        keyword_profiles: bool = False,
        pipeline_runs: bool = False,
    ) -> Dict:
        """Clear selected runtime tables without deleting the database file."""
        deleted = {"documents": 0, "keyword_profiles": 0, "pipeline_runs": 0}

        def operation():
            conn = self._connect()
            cur = conn.cursor()
            if documents:
                try:
                    cur.execute("SELECT COUNT(*) FROM documents")
                    deleted["documents"] = cur.fetchone()[0]
                except sqlite3.OperationalError:
                    deleted["documents"] = 0
                cur.execute("DELETE FROM documents")
                try:
                    cur.execute("DELETE FROM documents_fts")
                except sqlite3.OperationalError:
                    pass
            if keyword_profiles:
                try:
                    cur.execute("SELECT COUNT(*) FROM keyword_profiles")
                    deleted["keyword_profiles"] = cur.fetchone()[0]
                except sqlite3.OperationalError:
                    deleted["keyword_profiles"] = 0
                cur.execute("DELETE FROM keyword_profiles")
            if pipeline_runs:
                try:
                    cur.execute("SELECT COUNT(*) FROM pipeline_runs")
                    deleted["pipeline_runs"] = cur.fetchone()[0]
                except sqlite3.OperationalError:
                    deleted["pipeline_runs"] = 0
                cur.execute("DELETE FROM pipeline_runs")
            conn.commit()
            if conn is not self._memory_conn:
                conn.close()

        self._retry_on_readonly(operation)
        return deleted

    def get_pipeline_run(self, run_id: str) -> Optional[Dict]:
        conn = self._connect()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM pipeline_runs WHERE run_id = ?",
            (run_id,),
        )
        row = cur.fetchone()
        if conn is not self._memory_conn:
            conn.close()
        if not row:
            return None
        data = dict(row)
        for key in ("keywords", "payload", "result_summary"):
            if data.get(key):
                try:
                    data[key] = json.loads(data[key])
                except (TypeError, ValueError):
                    pass
        return data

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
        cur.execute("""
            SELECT doc_id, title, raw_text, url, source_type, source_name,
                   language, country, industry, published_date, created_at, updated_at
            FROM documents
        """)
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
