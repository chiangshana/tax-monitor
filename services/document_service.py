import asyncio
import hashlib
import re
import uuid
from datetime import datetime
from pathlib import Path
import tempfile

import requests
from bs4 import BeautifulSoup
from fastapi import UploadFile

from services.document_parser_service import DocumentParserService
from services.keyword_service import KeywordService
from services.language_service import LanguageService
from services.runtime_paths import output_dir
from services.storage_service import StorageService


BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = output_dir("uploads")
FALLBACK_UPLOAD_DIR = output_dir("upload_files")
SECONDARY_UPLOAD_DIR = BASE_DIR / "upload_files"
TEMP_UPLOAD_DIR = Path(tempfile.gettempdir()) / "tax_monitor_uploads"

MAX_RAW_TEXT_CHARS = 600_000
MAX_FETCH_BYTES = 25 * 1024 * 1024


class DocumentService:
    def __init__(self):
        self.storage_service = StorageService()
        self.keyword_service = KeywordService()
        self.language_service = LanguageService()
        self.parser_service = DocumentParserService()

    async def process_upload(self, file: UploadFile, defer_keyword_training: bool = False):
        raw_bytes = await file.read()
        file_path = self._write_upload_bytes(file.filename, raw_bytes)

        raw_text = self.parser_service.parse_file(file_path)

        language = self.language_service.detect_language(raw_text)
        content_hash = self._compute_content_hash(raw_text)
        existing = self.storage_service.find_document_by_content_hash(content_hash) if content_hash else None
        if existing:
            return self._duplicate_response(
                message="Identical document already ingested; reusing existing record.",
                existing=existing,
                embedded_links=[],
            )
        document = self._build_document(
            title=file.filename,
            source_type="file",
            source_name="upload",
            file_name=file.filename,
            raw_text=raw_text,
            language=language,
            content_hash=content_hash,
        )
        self.storage_service.save_document(document)
        if not defer_keyword_training:
            self.keyword_service.train_from_database()

        keywords = self.keyword_service.extract_keywords_for_document(
            title=document["title"],
            text=document["raw_text"]
        )

        return {
            "message": "Document uploaded successfully.",
            "document": {
                "doc_id": document["doc_id"],
                "title": document["title"],
                "source_type": document["source_type"],
                "language": document["language"],
                "country": document.get("country"),
                "industry": document.get("industry"),
                "published_date": document.get("published_date"),
                "created_at": document["created_at"],
                "updated_at": document.get("updated_at")
            },
            "extracted_keywords": keywords,
            "embedded_document_links": []
        }

    async def process_url(
        self,
        url: str,
        country: str = None,
        industry: str = None,
        source_name: str = "web",
        published_date: str = None,
        defer_keyword_training: bool = False
    ):
        title, raw_text, detected_source_type, embedded_links = await asyncio.to_thread(
            self._fetch_url_content, url
        )
        language = self.language_service.detect_language(raw_text)

        content_hash = self._compute_content_hash(raw_text)
        existing = self.storage_service.find_document_by_content_hash(content_hash) if content_hash else None
        if existing:
            return self._duplicate_response(
                message="Identical content already ingested; reusing existing record.",
                existing=existing,
                embedded_links=embedded_links,
            )

        document = self._build_document(
            title=title,
            source_type=detected_source_type,
            source_name=source_name,
            url=url,
            raw_text=raw_text,
            language=language,
            country=country,
            industry=industry,
            published_date=published_date,
            content_hash=content_hash,
        )
        self.storage_service.save_document(document)
        if not defer_keyword_training:
            self.keyword_service.train_from_database()

        keywords = self.keyword_service.extract_keywords_for_document(
            title=document["title"],
            text=document["raw_text"]
        )

        return {
            "message": "Web content ingested successfully.",
            "document": {
                "doc_id": document["doc_id"],
                "title": document["title"],
                "source_type": document["source_type"],
                "language": document["language"],
                "country": document.get("country"),
                "industry": document.get("industry"),
                "published_date": document.get("published_date"),
                "created_at": document["created_at"],
                "updated_at": document.get("updated_at")
            },
            "extracted_keywords": keywords,
            "embedded_document_links": embedded_links
        }

    def list_documents(self, **filters):
        return self.storage_service.list_documents(**filters)

    def get_document(self, doc_id: str):
        return self.storage_service.get_document(doc_id)

    def update_document(self, doc_id: str, updates: dict):
        return self.storage_service.update_document(doc_id, updates)

    def _build_document(
        self,
        title: str,
        source_type: str,
        source_name: str,
        raw_text: str,
        language: str,
        file_name: str = None,
        url: str = None,
        country: str = None,
        industry: str = None,
        published_date: str = None,
        content_hash: str = None,
    ):
        timestamp = datetime.now().isoformat(timespec="seconds")
        return {
            "doc_id": str(uuid.uuid4()),
            "title": title,
            "source_type": source_type,
            "source_name": source_name,
            "file_name": file_name,
            "url": url,
            "raw_text": raw_text,
            "language": language,
            "country": country,
            "industry": industry,
            "published_date": published_date,
            "content_hash": content_hash,
            "created_at": timestamp,
            "updated_at": timestamp
        }

    def _compute_content_hash(self, raw_text: str) -> str:
        if not raw_text:
            return ""
        normalized = re.sub(r"\s+", " ", raw_text).strip().lower()
        if not normalized:
            return ""
        return hashlib.sha256(normalized.encode("utf-8", errors="ignore")).hexdigest()

    def _duplicate_response(self, message: str, existing: dict, embedded_links: list) -> dict:
        keywords = self.keyword_service.extract_keywords_for_document(
            title=existing.get("title") or "",
            text=existing.get("raw_text") or "",
        )
        return {
            "message": message,
            "document": {
                "doc_id": existing["doc_id"],
                "title": existing.get("title"),
                "source_type": existing.get("source_type"),
                "language": existing.get("language"),
                "country": existing.get("country"),
                "industry": existing.get("industry"),
                "published_date": existing.get("published_date"),
                "created_at": existing.get("created_at"),
                "updated_at": existing.get("updated_at"),
            },
            "extracted_keywords": keywords,
            "embedded_document_links": embedded_links,
            "deduplicated": True,
        }

    def _get_upload_dir(self) -> Path:
        if UPLOAD_DIR.exists() and UPLOAD_DIR.is_file():
            for candidate in (FALLBACK_UPLOAD_DIR, SECONDARY_UPLOAD_DIR, TEMP_UPLOAD_DIR):
                try:
                    candidate.mkdir(parents=True, exist_ok=True)
                    return candidate
                except PermissionError:
                    continue
            raise PermissionError("No writable upload directory is available")

        try:
            UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
            return UPLOAD_DIR
        except PermissionError:
            for candidate in (SECONDARY_UPLOAD_DIR, TEMP_UPLOAD_DIR):
                try:
                    candidate.mkdir(parents=True, exist_ok=True)
                    return candidate
                except PermissionError:
                    continue
            raise PermissionError("No writable upload directory is available")

    def _write_upload_bytes(self, filename: str, raw_bytes: bytes) -> Path:
        candidate_dirs = []
        try:
            candidate_dirs.append(self._get_upload_dir())
        except PermissionError:
            pass
        candidate_dirs.extend([SECONDARY_UPLOAD_DIR, TEMP_UPLOAD_DIR])

        checked = set()
        for directory in candidate_dirs:
            if directory in checked:
                continue
            checked.add(directory)
            try:
                directory.mkdir(parents=True, exist_ok=True)
                file_path = directory / filename
                file_path.write_bytes(raw_bytes)
                return file_path
            except PermissionError:
                continue
        raise PermissionError("No writable upload file path is available")

    def _fetch_url_content(self, url: str):
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, timeout=20, headers=headers, stream=True)
        response.raise_for_status()

        content_length = response.headers.get("Content-Length")
        if content_length and content_length.isdigit() and int(content_length) > MAX_FETCH_BYTES:
            raise ValueError(
                f"Refusing to ingest {url}: declared size {int(content_length)} bytes exceeds cap {MAX_FETCH_BYTES}"
            )

        body = bytearray()
        for chunk in response.iter_content(chunk_size=64 * 1024):
            if not chunk:
                continue
            body.extend(chunk)
            if len(body) > MAX_FETCH_BYTES:
                raise ValueError(
                    f"Refusing to ingest {url}: streamed size exceeded cap {MAX_FETCH_BYTES} bytes"
                )

        body_bytes = bytes(body)
        content_type = (response.headers.get("Content-Type") or "").lower()
        if url.lower().endswith(".pdf") or "application/pdf" in content_type:
            title = self._infer_file_name_from_url(url)
            raw_text = self.parser_service.parse_bytes(body_bytes, title)
            return title, self._cap_text(raw_text), "pdf", []

        try:
            html_text = body_bytes.decode(response.encoding or "utf-8", errors="ignore")
        except Exception:
            html_text = body_bytes.decode("utf-8", errors="ignore")
        soup = BeautifulSoup(html_text, "html.parser")
        title = soup.title.text.strip() if soup.title else url

        embedded_links = self._collect_embedded_document_links(soup, base_url=url)

        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        text = soup.get_text(separator="\n")
        return title, self._cap_text(text), "web", embedded_links

    def _cap_text(self, text: str) -> str:
        if not text:
            return text
        if len(text) <= MAX_RAW_TEXT_CHARS:
            return text
        return text[:MAX_RAW_TEXT_CHARS] + "\n\n[...truncated by tax-monitor: original exceeded {} chars]".format(MAX_RAW_TEXT_CHARS)

    def _collect_embedded_document_links(self, soup: BeautifulSoup, base_url: str) -> list:
        from urllib.parse import urljoin

        keyword_pattern = (
            "annual",
            "report",
            "tax",
            "financial",
            "statement",
            "sustain",
            "esg",
            "investor",
            "ir/",
            "governance",
            "risk",
            "transfer",
            "subsidiar",
            "年報",
            "永續",
            "稅",
            "財報",
            "投資人",
            "公司治理",
            "風險",
            "關係企業",
            "子公司",
        )

        links = []
        seen = set()
        for anchor in soup.find_all("a", href=True):
            href = (anchor.get("href") or "").strip()
            if not href or href.startswith("#"):
                continue
            absolute = urljoin(base_url, href)
            lowered = absolute.lower()
            link_text = anchor.get_text(" ", strip=True) or ""
            haystack = f"{lowered} {link_text.lower()}"

            looks_like_doc = (
                lowered.endswith((".pdf", ".docx", ".xlsx", ".pptx"))
                or "filetype=pdf" in lowered
                or "/pdf/" in lowered
            )
            looks_relevant = any(needle in haystack for needle in keyword_pattern)

            if not (looks_like_doc or looks_relevant):
                continue
            if absolute in seen:
                continue
            seen.add(absolute)
            links.append({
                "url": absolute,
                "text": link_text[:120],
                "looks_like_document": looks_like_doc,
            })
            if len(links) >= 30:
                break
        return links

    def _infer_file_name_from_url(self, url: str) -> str:
        candidate = url.rstrip("/").split("/")[-1]
        return candidate or "downloaded_document.pdf"
