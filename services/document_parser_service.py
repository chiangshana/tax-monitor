import shutil
import subprocess
import tempfile
from pathlib import Path

from pypdf import PdfReader

try:
    import pdfplumber
except ImportError:  # pragma: no cover - optional dependency
    pdfplumber = None


BASE_DIR = Path(__file__).resolve().parent.parent
MINERU_OUTPUT_DIR = BASE_DIR / "data" / "mineru_output"


class DocumentParserService:
    MINERU_EXTENSIONS = {".pdf", ".docx", ".pptx", ".xlsx", ".png", ".jpg", ".jpeg"}
    PDFPLUMBER_MAX_PAGES = 50
    PDFPLUMBER_MAX_TABLES = 30

    def parse_file(self, file_path: Path) -> str:
        file_path = Path(file_path)
        if file_path.suffix.lower() in self.MINERU_EXTENSIONS:
            parsed_text = self._parse_with_mineru(file_path)
            if parsed_text.strip():
                return self._enrich_pdf_with_tables(file_path, parsed_text)

        if file_path.suffix.lower() == ".pdf":
            extracted = self._extract_text_from_pdf(file_path)
            return self._enrich_pdf_with_tables(file_path, extracted)

        return file_path.read_text(encoding="utf-8", errors="ignore")

    def parse_bytes(self, raw_bytes: bytes, file_name: str) -> str:
        suffix = Path(file_name).suffix or ".pdf"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(raw_bytes)

        try:
            return self.parse_file(temp_path)
        finally:
            try:
                temp_path.unlink(missing_ok=True)
            except PermissionError:
                pass

    def _parse_with_mineru(self, file_path: Path) -> str:
        mineru_executable = shutil.which("mineru")
        if not mineru_executable:
            return ""

        output_dir = MINERU_OUTPUT_DIR / file_path.stem
        output_dir.mkdir(parents=True, exist_ok=True)

        command = [
            mineru_executable,
            "-p",
            str(file_path),
            "-o",
            str(output_dir),
            "-m",
            "auto",
            "-b",
            "pipeline",
        ]

        try:
            subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                timeout=600,
            )
        except Exception:
            return ""

        return self._collect_mineru_text(output_dir)

    def _collect_mineru_text(self, output_dir: Path) -> str:
        texts = []
        for pattern in ("*.md", "*.json"):
            for path in output_dir.rglob(pattern):
                try:
                    texts.append(path.read_text(encoding="utf-8", errors="ignore"))
                except OSError:
                    continue
        return "\n\n".join(texts)

    def _extract_text_from_pdf(self, file_path: Path) -> str:
        reader = PdfReader(str(file_path))
        texts = []
        for page in reader.pages:
            texts.append(page.extract_text() or "")
        return "\n".join(texts)

    def _enrich_pdf_with_tables(self, file_path: Path, base_text: str) -> str:
        if pdfplumber is None:
            return base_text
        if file_path.suffix.lower() != ".pdf":
            return base_text
        try:
            extracted_tables = self._extract_pdf_tables(file_path)
        except Exception:
            return base_text
        if not extracted_tables:
            return base_text
        return base_text + "\n\n" + "\n\n".join(extracted_tables)

    def _extract_pdf_tables(self, file_path: Path) -> list:
        if pdfplumber is None:
            return []
        rendered_tables = []
        with pdfplumber.open(str(file_path)) as pdf:
            for page_index, page in enumerate(pdf.pages[: self.PDFPLUMBER_MAX_PAGES]):
                if len(rendered_tables) >= self.PDFPLUMBER_MAX_TABLES:
                    break
                try:
                    tables = page.extract_tables() or []
                except Exception:
                    continue
                for table_index, raw_table in enumerate(tables):
                    if len(rendered_tables) >= self.PDFPLUMBER_MAX_TABLES:
                        break
                    rendered = self._render_table(raw_table)
                    if not rendered:
                        continue
                    header = (
                        f"[Table extracted via pdfplumber] page={page_index + 1} table={table_index + 1}\n"
                    )
                    rendered_tables.append(header + rendered)
        return rendered_tables

    def _render_table(self, raw_table) -> str:
        if not raw_table:
            return ""
        rows = []
        meaningful_cells = 0
        for row in raw_table:
            if not row:
                continue
            cells = ["" if cell is None else str(cell).strip() for cell in row]
            if not any(cell for cell in cells):
                continue
            meaningful_cells += sum(1 for cell in cells if cell)
            rows.append(" | ".join(cells))
        if meaningful_cells < 4 or len(rows) < 2:
            return ""
        return "\n".join(rows)
