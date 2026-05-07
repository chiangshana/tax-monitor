import re
from typing import List


class LanguageService:
    def detect_language(self, text: str) -> str:
        sample = text[:2000]

        zh_count = len(re.findall(r"[\u4e00-\u9fff]", sample))
        ja_count = len(re.findall(r"[\u3040-\u30ff]", sample))
        ko_count = len(re.findall(r"[\uac00-\ud7af]", sample))
        th_count = len(re.findall(r"[\u0E00-\u0E7F]", sample))
        latin_count = len(re.findall(r"[A-Za-z]", sample))

        scores = {
            "zh": zh_count,
            "ja": ja_count,
            "ko": ko_count,
            "th": th_count,
            "en": latin_count
        }

        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else "unknown"

    def split_sentences(self, text: str) -> List[str]:
        parts = re.split(r"(?<=[。.!?])\s+|\n+", text)
        return [part.strip() for part in parts if len(part.strip()) > 20]
