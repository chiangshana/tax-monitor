from services.llm_service import LLMService


class TranslatorService:
    def __init__(self):
        self.llm_service = LLMService()

    async def translate_text(
        self,
        text: str,
        source_language: str,
        target_language: str,
        use_llm: bool = False,
        provider: str = "ollama",
        model_name: str = "qwen3:8b"
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
        data = self.llm_service.generate_json(
            prompt=prompt,
            schema_hint={"translated_text": self._fallback_translate(text, source_language, target_language)},
            provider=provider,
            model_name=model_name
        )
        return data.get("translated_text", self._fallback_translate(text, source_language, target_language))

    def _fallback_translate(self, text: str, source_language: str, target_language: str) -> str:
        header = f"[Translation preview only | {source_language} -> {target_language}]\n"
        return header + text[:2500]
