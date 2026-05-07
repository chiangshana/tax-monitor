import json
import os
import re
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

import requests


class LLMService:
    JSON_PARSE_RETRIES = 1
    CACHE_PROMPT_THRESHOLD_CHARS = 1500

    def __init__(self):
        self._usage_lock = threading.Lock()
        self._usage_records: List[Dict[str, Any]] = []

    def generate_json(
        self,
        prompt: str,
        schema_hint: Dict[str, Any],
        provider: str = "ollama",
        model_name: str = "qwen3:8b"
    ) -> Dict[str, Any]:
        fallback = schema_hint.copy()

        attempts = self.JSON_PARSE_RETRIES + 1
        last_content = ""
        for attempt in range(attempts):
            try:
                content = self._generate_text(
                    prompt=prompt,
                    provider=provider,
                    model_name=model_name,
                ).strip()
                last_content = content
                data = self._safe_json_loads(content)
                if isinstance(data, dict):
                    merged = fallback.copy()
                    merged.update(data)
                    return merged
            except Exception:
                pass
            if attempt + 1 < attempts:
                time.sleep(0.4)

        repaired = self._safe_json_loads(last_content) if last_content else None
        if isinstance(repaired, dict):
            merged = fallback.copy()
            merged.update(repaired)
            return merged
        return fallback

    def _safe_json_loads(self, content: str) -> Optional[Dict[str, Any]]:
        if not content:
            return None
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        cleaned = content.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```\s*$", "", cleaned)
        cleaned = cleaned.strip()
        if cleaned:
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass

        match = re.search(r"\{[\s\S]*\}", cleaned)
        if match:
            snippet = match.group(0)
            try:
                return json.loads(snippet)
            except json.JSONDecodeError:
                snippet = re.sub(r",(\s*[}\]])", r"\1", snippet)
                snippet = re.sub(r"(?<!\\)'", '"', snippet)
                try:
                    return json.loads(snippet)
                except json.JSONDecodeError:
                    return None
        return None

    def generate_text(
        self,
        prompt: str,
        provider: str = "ollama",
        model_name: str = "qwen3:8b"
    ) -> str:
        try:
            return self._generate_text(
                prompt=prompt,
                provider=provider,
                model_name=model_name
            ).strip()
        except Exception:
            return ""

    # ---------- Usage tracking ----------

    def reset_usage_records(self):
        with self._usage_lock:
            self._usage_records.clear()

    def consume_usage_records(self) -> List[Dict[str, Any]]:
        with self._usage_lock:
            records = list(self._usage_records)
            self._usage_records.clear()
        return records

    def get_usage_summary(self) -> Dict[str, Any]:
        with self._usage_lock:
            records = list(self._usage_records)
        return self._summarize_usage_records(records)

    def _summarize_usage_records(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        per_model: Dict[str, Dict[str, int]] = {}
        totals = {"calls": 0, "input_tokens": 0, "output_tokens": 0, "cache_read_tokens": 0, "cache_write_tokens": 0}
        for rec in records:
            key = f"{rec.get('provider', '?')}::{rec.get('model', '?')}"
            slot = per_model.setdefault(
                key,
                {"calls": 0, "input_tokens": 0, "output_tokens": 0, "cache_read_tokens": 0, "cache_write_tokens": 0},
            )
            for field in ("input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens"):
                value = int(rec.get(field) or 0)
                slot[field] += value
                totals[field] += value
            slot["calls"] += 1
            totals["calls"] += 1
        return {"totals": totals, "per_model": per_model}

    def _record_usage(
        self,
        provider: str,
        model_name: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cache_read_tokens: int = 0,
        cache_write_tokens: int = 0,
    ):
        record = {
            "provider": provider,
            "model": model_name,
            "input_tokens": int(input_tokens or 0),
            "output_tokens": int(output_tokens or 0),
            "cache_read_tokens": int(cache_read_tokens or 0),
            "cache_write_tokens": int(cache_write_tokens or 0),
            "timestamp": time.time(),
        }
        with self._usage_lock:
            self._usage_records.append(record)

    # ---------- Provider dispatch ----------

    def _generate_text(self, prompt: str, provider: str, model_name: str) -> str:
        provider_lower = provider.lower()
        if provider_lower == "ollama":
            text, usage = self._call_ollama(prompt, model_name)
        elif provider_lower == "openai":
            text, usage = self._call_openai(prompt, model_name)
        elif provider_lower == "gemini":
            text, usage = self._call_gemini(prompt, model_name)
        elif provider_lower == "claude":
            text, usage = self._call_claude(prompt, model_name)
        else:
            raise ValueError(f"Unsupported provider: {provider}")
        self._record_usage(
            provider=provider_lower,
            model_name=model_name,
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            cache_read_tokens=usage.get("cache_read_tokens", 0),
            cache_write_tokens=usage.get("cache_write_tokens", 0),
        )
        return text

    def _call_ollama(self, prompt: str, model_name: str) -> Tuple[str, Dict[str, int]]:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": model_name, "prompt": prompt, "stream": False},
            timeout=120
        )
        response.raise_for_status()
        body = response.json()
        usage = {
            "input_tokens": int(body.get("prompt_eval_count") or 0),
            "output_tokens": int(body.get("eval_count") or 0),
        }
        return body.get("response", ""), usage

    def _call_openai(self, prompt: str, model_name: str) -> Tuple[str, Dict[str, int]]:
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
        body = response.json()
        text = body["choices"][0]["message"]["content"]
        u = body.get("usage") or {}
        usage = {
            "input_tokens": int(u.get("prompt_tokens") or 0),
            "output_tokens": int(u.get("completion_tokens") or 0),
            "cache_read_tokens": int(((u.get("prompt_tokens_details") or {}).get("cached_tokens")) or 0),
        }
        return text, usage

    def _call_gemini(self, prompt: str, model_name: str) -> Tuple[str, Dict[str, int]]:
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
        text = ""
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            text = "".join(part.get("text", "") for part in parts)
        meta = data.get("usageMetadata") or {}
        usage = {
            "input_tokens": int(meta.get("promptTokenCount") or 0),
            "output_tokens": int(meta.get("candidatesTokenCount") or 0),
            "cache_read_tokens": int(meta.get("cachedContentTokenCount") or 0),
        }
        return text, usage

    def _call_claude(self, prompt: str, model_name: str) -> Tuple[str, Dict[str, int]]:
        api_key = self._require_env("ANTHROPIC_API_KEY")
        system_prompt = (
            "You are the Tax Monitor research assistant. You receive cross-border "
            "regulatory and tax-risk research tasks. Default to concise, well-structured "
            "JSON when the user asks for JSON. Lean on the tax domain vocabulary already "
            "embedded in the user's prompts (audit, sampling, transfer pricing, Pillar Two, "
            "permanent establishment, withholding tax, CFC, customs / tariff, VAT/GST, "
            "annual report, sustainability report, related party transactions, group "
            "structure). Preserve original company / subsidiary names verbatim including "
            "non-Latin scripts."
        )
        system_blocks: list = [{"type": "text", "text": system_prompt}]
        if len(system_prompt) >= self.CACHE_PROMPT_THRESHOLD_CHARS:
            system_blocks[0]["cache_control"] = {"type": "ephemeral"}

        user_blocks: list = [{"type": "text", "text": prompt}]
        if len(prompt) >= self.CACHE_PROMPT_THRESHOLD_CHARS:
            user_blocks[0]["cache_control"] = {"type": "ephemeral"}

        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": model_name,
                "max_tokens": 1500,
                "temperature": 0.2,
                "system": system_blocks,
                "messages": [{"role": "user", "content": user_blocks}],
            },
            timeout=120,
        )
        response.raise_for_status()
        body = response.json()
        items = body.get("content", [])
        text = "".join(item.get("text", "") for item in items if item.get("type") == "text")
        u = body.get("usage") or {}
        usage = {
            "input_tokens": int(u.get("input_tokens") or 0),
            "output_tokens": int(u.get("output_tokens") or 0),
            "cache_read_tokens": int(u.get("cache_read_input_tokens") or 0),
            "cache_write_tokens": int(u.get("cache_creation_input_tokens") or 0),
        }
        return text, usage

    def _require_env(self, name: str) -> str:
        value = os.getenv(name)
        if not value:
            raise ValueError(f"Missing environment variable: {name}")
        return value
