import json
import threading
import tkinter as tk
from tkinter import ttk

from services.llm_service import LLMService


class ResearchChatPanel(ttk.Frame):
    """LLM-assisted refinement panel for unhappy search outcomes."""

    SOURCE_OPTIONS = {
        "deep_research",
        "duckduckgo",
        "bing_web",
        "all",
        "google_news_rss_global",
        "google_news_rss",
    }
    DATE_RANGE_OPTIONS = {"7d", "1m", "3m", "6m", "1y"}

    def __init__(self, master, get_payload, get_result, on_apply, on_apply_and_run):
        super().__init__(master)
        self.get_payload = get_payload
        self.get_result = get_result
        self.on_apply = on_apply
        self.on_apply_and_run = on_apply_and_run
        self.llm_service = LLMService()
        self.last_suggestion = None
        self._build()

    def _build(self):
        self.rowconfigure(1, weight=1)
        self.rowconfigure(3, weight=0)
        self.columnconfigure(0, weight=1)

        intro = (
            "Ask the LLM how to improve the next research run. "
            "Example: include subsidiaries, broaden English sources, or focus on transfer pricing."
        )
        ttk.Label(self, text=intro, wraplength=760, justify="left").grid(
            row=0, column=0, sticky="ew", pady=(0, 6)
        )

        self.transcript = tk.Text(self, wrap="word", height=18, state="disabled")
        transcript_scroll = ttk.Scrollbar(self, command=self.transcript.yview)
        self.transcript.configure(yscrollcommand=transcript_scroll.set)
        self.transcript.grid(row=1, column=0, sticky="nsew")
        transcript_scroll.grid(row=1, column=1, sticky="ns")

        ttk.Label(self, text="Message to research assistant").grid(row=2, column=0, sticky="w", pady=(8, 2))
        self.message = tk.Text(self, wrap="word", height=4)
        self.message.insert(
            "1.0",
            "這次資料太少，請幫我規劃下一輪搜尋：要包含公司子公司、英文與中文來源、跨國稅務風險。",
        )
        self.message.grid(row=3, column=0, columnspan=2, sticky="ew")

        button_row = ttk.Frame(self)
        button_row.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        button_row.columnconfigure(0, weight=1)
        button_row.columnconfigure(1, weight=1)
        button_row.columnconfigure(2, weight=1)

        self.send_button = ttk.Button(button_row, text="Ask LLM", command=self._send)
        self.send_button.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        self.apply_button = ttk.Button(
            button_row,
            text="Apply settings",
            command=self._apply,
            state="disabled",
        )
        self.apply_button.grid(row=0, column=1, sticky="ew", padx=4)

        self.apply_run_button = ttk.Button(
            button_row,
            text="Apply + rerun",
            command=self._apply_and_run,
            state="disabled",
        )
        self.apply_run_button.grid(row=0, column=2, sticky="ew", padx=(4, 0))

        self.status = tk.StringVar(value="Ready")
        ttk.Label(self, textvariable=self.status).grid(row=5, column=0, columnspan=2, sticky="w", pady=(6, 0))

        self._append(
            "Assistant",
            "跑完一次後，如果搜尋量太少或方向不對，可以直接告訴我哪裡不滿意。"
            "我會產生下一輪可套用的搜尋關鍵字、資料來源、期間與筆數建議。",
        )

    def _send(self):
        user_message = self.message.get("1.0", "end").strip()
        if not user_message:
            return
        self.message.delete("1.0", "end")
        self._append("User", user_message)
        self._set_busy(True)
        thread = threading.Thread(target=self._ask_llm_thread, args=(user_message,), daemon=True)
        thread.start()

    def _ask_llm_thread(self, user_message):
        try:
            payload = self.get_payload() or {}
            result = self.get_result() or {}
            suggestion = self._ask_llm(user_message, payload, result)
            self.after(0, self._handle_suggestion, suggestion)
        except Exception as exc:
            self.after(0, self._handle_error, str(exc))

    def _ask_llm(self, user_message, payload, result):
        provider = (payload.get("provider") or "ollama").strip().lower()
        model_name = (payload.get("model_name") or "qwen3:8b").strip()
        current_context = self._compact_context(payload, result)

        schema_hint = {
            "reply": "我會幫你擴大下一輪搜尋，並補上更精準的風險詞。",
            "suggested_keywords": payload.get("keywords") or [],
            "suggested_user_prompt": payload.get("user_prompt") or "",
            "source_name": payload.get("source_name") or "deep_research",
            "date_range": payload.get("date_range") or "3m",
            "max_results": int(payload.get("max_results") or 50),
            "max_documents_to_process": int(payload.get("max_documents_to_process") or 5),
            "use_rag_context": True,
            "rag_top_k": int(payload.get("rag_top_k") or 4),
            "country": payload.get("country") or "",
            "industry": payload.get("industry") or "",
            "should_rerun": True,
            "reasoning": [],
        }

        prompt = f"""
You are the Tax Monitor desktop research assistant.
The user is refining a tax-risk web research run after seeing the collected results.

Return valid JSON only. Use Traditional Chinese in the "reply" and "reasoning" fields.
The JSON must match this shape:
{json.dumps(schema_hint, ensure_ascii=False, indent=2)}

Rules:
- Improve recall without making the query meaningless.
- Include company aliases, subsidiaries, English names, and tax-risk vocabulary when useful.
- Prefer "deep_research" or "all" when the user complains that search results are too few.
- Use date_range only from: 7d, 1m, 3m, 6m, 1y.
- Use source_name only from: deep_research, duckduckgo, bing_web, all, google_news_rss_global, google_news_rss.
- suggested_keywords should be a concise list of search phrases, not a paragraph.
- suggested_user_prompt should be a stronger research instruction for the next pipeline run.

Current context:
{json.dumps(current_context, ensure_ascii=False, indent=2)}

User message:
{user_message}
""".strip()

        suggestion = self.llm_service.generate_json(
            prompt=prompt,
            schema_hint=schema_hint,
            provider=provider,
            model_name=model_name,
        )
        return self._sanitize_suggestion(suggestion, schema_hint)

    def _compact_context(self, payload, result):
        search_results = result.get("search_results") or []
        documents = result.get("documents") or []
        return {
            "current_settings": payload,
            "run_summary": {
                "searched_result_count": result.get("searched_result_count"),
                "ingested_result_count": result.get("ingested_result_count"),
                "generated_report_count": result.get("generated_report_count"),
                "normalized_keywords": result.get("normalized_keywords"),
            },
            "top_search_results": [
                {
                    "title": item.get("title"),
                    "domain": item.get("domain"),
                    "source": item.get("source"),
                    "score": item.get("relevance_score"),
                    "url": item.get("url"),
                }
                for item in search_results[:8]
            ],
            "documents": [
                {
                    "title": doc.get("title"),
                    "risk_level": doc.get("risk_level"),
                    "risk_tags": doc.get("risk_tags"),
                    "url": doc.get("url") or doc.get("source_url"),
                }
                for doc in documents[:8]
            ],
        }

    def _sanitize_suggestion(self, suggestion, fallback):
        clean = fallback.copy()
        clean.update(suggestion or {})

        keywords = clean.get("suggested_keywords") or []
        if isinstance(keywords, str):
            keywords = [part.strip() for part in keywords.replace("，", ",").split(",") if part.strip()]
        clean["suggested_keywords"] = [str(item).strip() for item in keywords if str(item).strip()][:20]

        source_name = str(clean.get("source_name") or "deep_research").strip()
        clean["source_name"] = source_name if source_name in self.SOURCE_OPTIONS else "deep_research"

        date_range = str(clean.get("date_range") or "3m").strip()
        clean["date_range"] = date_range if date_range in self.DATE_RANGE_OPTIONS else "3m"

        clean["max_results"] = self._clamp_int(clean.get("max_results"), 1, 200, 50)
        clean["max_documents_to_process"] = self._clamp_int(clean.get("max_documents_to_process"), 1, 10, 5)
        clean["use_rag_context"] = bool(clean.get("use_rag_context", True))
        clean["rag_top_k"] = self._clamp_int(clean.get("rag_top_k"), 0, 10, 4)
        clean["suggested_user_prompt"] = str(clean.get("suggested_user_prompt") or "").strip()
        clean["country"] = str(clean.get("country") or "").strip()
        clean["industry"] = str(clean.get("industry") or "").strip()
        clean["reply"] = str(clean.get("reply") or "我已產生下一輪搜尋建議。").strip()
        return clean

    def _clamp_int(self, value, minimum, maximum, default):
        try:
            number = int(value)
        except (TypeError, ValueError):
            number = default
        return max(minimum, min(maximum, number))

    def _handle_suggestion(self, suggestion):
        self.last_suggestion = suggestion
        self._set_busy(False)
        self.apply_button.configure(state="normal")
        self.apply_run_button.configure(state="normal")
        self._append("Assistant", self._format_suggestion(suggestion))

    def _handle_error(self, message):
        self._set_busy(False)
        self._append("Assistant", f"LLM 對話暫時失敗：{message}")

    def _format_suggestion(self, suggestion):
        reasoning = suggestion.get("reasoning") or []
        if isinstance(reasoning, list):
            reasoning_text = "\n".join(f"- {item}" for item in reasoning if item)
        else:
            reasoning_text = str(reasoning)

        keywords = "\n".join(f"- {item}" for item in suggestion.get("suggested_keywords", []))
        return "\n".join(
            [
                suggestion.get("reply", ""),
                "",
                "建議關鍵字：",
                keywords or "- 無",
                "",
                "建議設定：",
                f"- source_name: {suggestion.get('source_name')}",
                f"- date_range: {suggestion.get('date_range')}",
                f"- max_results: {suggestion.get('max_results')}",
                f"- max_documents_to_process: {suggestion.get('max_documents_to_process')}",
                f"- use_rag_context: {suggestion.get('use_rag_context')}",
                f"- rag_top_k: {suggestion.get('rag_top_k')}",
                f"- country: {suggestion.get('country') or '(不限)'}",
                f"- industry: {suggestion.get('industry') or '(不限)'}",
                "",
                "下一輪研究指令：",
                suggestion.get("suggested_user_prompt", ""),
                "",
                "理由：",
                reasoning_text or "- 無",
            ]
        )

    def _apply(self):
        if self.last_suggestion and callable(self.on_apply):
            self.on_apply(self.last_suggestion)
            self._append("System", "已套用建議到左側搜尋設定。你可以再手動微調，或按 Run research。")

    def _apply_and_run(self):
        if self.last_suggestion and callable(self.on_apply):
            self.on_apply(self.last_suggestion)
            self._append("System", "已套用建議並準備重新執行。")
        if callable(self.on_apply_and_run):
            self.on_apply_and_run()

    def _set_busy(self, busy):
        self.send_button.configure(text="Thinking..." if busy else "Ask LLM", state="disabled" if busy else "normal")
        self.status.set("Calling LLM..." if busy else "Ready")

    def _append(self, speaker, message):
        self.transcript.configure(state="normal")
        self.transcript.insert("end", f"{speaker}:\n{message.strip()}\n\n")
        self.transcript.see("end")
        self.transcript.configure(state="disabled")
