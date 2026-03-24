import json
import requests


class TranslatorService:
    async def translate_text(
        self,
        text: str,
        source_language: str,
        target_language: str,
        use_llm: bool = False,
        model_name: str = "qwen2.5:7b"
    ) -> str:
        if source_language == target_language:
            return text

        if not use_llm:
            return self._fallback_translate(text, source_language, target_language)

        prompt = f"""
你是一位專業翻譯助理。
請將以下內容從 {source_language} 翻譯成 {target_language}。
請保留法令、稅務、日期與數字資訊。
只輸出 JSON：
{{
  "translated_text": "翻譯結果"
}}

原文：
{text[:12000]}
"""
        try:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={"model": model_name, "prompt": prompt, "stream": False},
                timeout=90
            )
            response.raise_for_status()
            content = response.json().get("response", "").strip()
            data = json.loads(content)
            return data.get("translated_text", self._fallback_translate(text, source_language, target_language))
        except Exception:
            return self._fallback_translate(text, source_language, target_language)

    def _fallback_translate(self, text: str, source_language: str, target_language: str) -> str:
        header = f"[Translation preview only | {source_language} -> {target_language}]\n"
        return header + text[:2500]
