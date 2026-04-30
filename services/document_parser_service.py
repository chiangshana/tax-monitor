import shutil
import subprocess
import tempfile
from pathlib import Path

from pypdf import PdfReader


BASE_DIR = Path(__file__).resolve().parent.parent
MINERU_OUTPUT_DIR = BASE_DIR / "data" / "mineru_output"


class DocumentParserService:
    MINERU_EXTENSIONS = {".pdf", ".docx", ".pptx", ".xlsx", ".png", ".jpg", ".jpeg"}

    def parse_file(self, file_path: Path) -> str:
        file_path = Path(file_path)
        if file_path.suffix.lower() in self.MINERU_EXTENSIONS:
            parsed_text = self._parse_with_mineru(file_path)
            if parsed_text.strip():
                return parsed_text

        if file_path.suffix.lower() == ".pdf":
            return self._extract_text_from_pdf(file_path)

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
