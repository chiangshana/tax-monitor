import json
import os
from typing import Any, Dict, Optional

import requests


class LLMService:
    def generate_json(
        self,
        prompt: str,
        schema_hint: Dict[str, Any],
        provider: str = "ollama",
        model_name: str = "qwen3:8b"
    ) -> Dict[str, Any]:
        fallback = schema_hint.copy()

        try:
            content = self._generate_text(
                prompt=prompt,
                provider=provider,
                model_name=model_name
            ).strip()
            data = json.loads(content)
            if isinstance(data, dict):
                merged = fallback.copy()
                merged.update(data)
                return merged
        except Exception:
            pass

        return fallback

    def _generate_text(self, prompt: str, provider: str, model_name: str) -> str:
        provider = provider.lower()
        if provider == "ollama":
            return self._call_ollama(prompt, model_name)
        if provider == "openai":
            return self._call_openai(prompt, model_name)
        if provider == "gemini":
            return self._call_gemini(prompt, model_name)
        if provider == "claude":
            return self._call_claude(prompt, model_name)
        raise ValueError(f"Unsupported provider: {provider}")

    def _call_ollama(self, prompt: str, model_name: str) -> str:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": model_name, "prompt": prompt, "stream": False},
            timeout=120
        )
        response.raise_for_status()
        return response.json().get("response", "")

    def _call_openai(self, prompt: str, model_name: str) -> str:
        api_key = self._require_env("OPENAI_API_KEY")
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model_name,
                "messages": [
                    {"role": "system", "content": "Return concise, valid JSON only when asked."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.2
            },
            timeout=120
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    def _call_gemini(self, prompt: str, model_name: str) -> str:
        api_key = self._require_env("GEMINI_API_KEY")
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.2}
            },
            timeout=120
        )
        response.raise_for_status()
        data = response.json()
        candidates = data.get("candidates", [])
        if not candidates:
            return ""
        parts = candidates[0].get("content", {}).get("parts", [])
        return "".join(part.get("text", "") for part in parts)

    def _call_claude(self, prompt: str, model_name: str) -> str:
        api_key = self._require_env("ANTHROPIC_API_KEY")
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            },
            json={
                "model": model_name,
                "max_tokens": 1200,
                "temperature": 0.2,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=120
        )
        response.raise_for_status()
        items = response.json().get("content", [])
        return "".join(item.get("text", "") for item in items if item.get("type") == "text")

    def _require_env(self, name: str) -> str:
        value = os.getenv(name)
        if not value:
            raise ValueError(f"Missing environment variable: {name}")
        return value
