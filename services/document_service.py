import uuid
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from fastapi import UploadFile
from pypdf import PdfReader

from services.keyword_service import KeywordService
from services.language_service import LanguageService
from services.storage_service import StorageService


BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "data" / "uploads"


class DocumentService:
    def __init__(self):
        self.storage_service = StorageService()
        self.keyword_service = KeywordService()
        self.language_service = LanguageService()

    async def process_upload(self, file: UploadFile):
        raw_bytes = await file.read()
        file_path = UPLOAD_DIR / file.filename
        file_path.write_bytes(raw_bytes)

        if file.filename.lower().endswith(".pdf"):
            raw_text = self._extract_text_from_pdf(file_path)
        else:
            raw_text = raw_bytes.decode("utf-8", errors="ignore")

        language = self.language_service.detect_language(raw_text)
        document = self._build_document(
            title=file.filename,
            source_type="file",
            source_name="upload",
            file_name=file.filename,
            raw_text=raw_text,
            language=language
        )
        self.storage_service.save_document(document)
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
                "created_at": document["created_at"]
            },
            "extracted_keywords": keywords
        }

    async def process_url(self, url: str, country: str = None, industry: str = None, source_name: str = "web"):
        title, raw_text = self._fetch_web_text(url)
        language = self.language_service.detect_language(raw_text)

        document = self._build_document(
            title=title,
            source_type="web",
            source_name=source_name,
            url=url,
            raw_text=raw_text,
            language=language,
            country=country,
            industry=industry
        )
        self.storage_service.save_document(document)
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
                "created_at": document["created_at"]
            },
            "extracted_keywords": keywords
        }

    def list_documents(self):
        return self.storage_service.list_documents()

    def get_document(self, doc_id: str):
        return self.storage_service.get_document(doc_id)

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
        industry: str = None
    ):
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
            "created_at": datetime.now().isoformat(timespec="seconds")
        }

    def _extract_text_from_pdf(self, file_path: Path) -> str:
        reader = PdfReader(str(file_path))
        texts = []
        for page in reader.pages:
            texts.append(page.extract_text() or "")
        return "\n".join(texts)

    def _fetch_web_text(self, url: str):
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, timeout=20, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.title.text.strip() if soup.title else url

        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        text = soup.get_text(separator="\n")
        return title, text
