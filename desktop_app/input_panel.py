import os
import tkinter as tk
from tkinter import ttk

from models.schemas import RISK_THEME_OPTIONS


PROVIDER_MODEL_PRESETS = {
    "ollama": [
        "qwen3.5:latest",
        "qwen3.5:0.8b",
        "qwen3.5:2b",
        "qwen3.5:4b",
        "qwen3.5:9b",
        "qwen3.5:27b",
        "qwen3.5:35b",
        "qwen3.5:122b",
        "qwen3:0.6b",
        "qwen3:1.7b",
        "qwen3:4b",
        "qwen3:8b",
        "qwen3:14b",
        "qwen3:32b",
        "qwen3-coder:30b",
        "qwen2.5:1.5b",
        "qwen2.5:3b",
        "qwen2.5:7b",
        "qwen2.5:14b",
        "qwen2.5:32b",
        "qwen2.5:72b",
        "qwen2.5-coder:7b",
        "qwen2.5-coder:14b",
        "qwen2.5-coder:32b",
        "llama3.1:8b",
        "llama3.1:70b",
        "llama3.2:3b",
        "mistral:7b",
        "mixtral:8x7b",
        "deepseek-r1:7b",
        "deepseek-r1:14b",
        "phi3:14b",
        "gemma2:9b",
    ],
    "claude": [
        "claude-opus-4-7",
        "claude-sonnet-4-6",
        "claude-haiku-4-5-20251001",
        "claude-3-7-sonnet-latest",
        "claude-3-5-sonnet-latest",
        "claude-3-5-haiku-latest",
        "claude-3-opus-latest",
    ],
    "openai": [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4.1",
        "gpt-4.1-mini",
        "gpt-4.1-nano",
        "gpt-4-turbo",
        "gpt-3.5-turbo",
        "o1",
        "o1-mini",
        "o3-mini",
    ],
    "gemini": [
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
    ],
    "qwen": [
        "qwen3.6-plus",
        "qwen3.6-max-preview",
        "qwen-max",
        "qwen-max-latest",
        "qwen-plus",
        "qwen-turbo",
        "qwen3.5-397b-a17b",
    ],
}

PROVIDER_API_KEY_ENV = {
    "ollama": None,
    "claude": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "qwen": "DASHSCOPE_API_KEY",
}

PROVIDER_DEFAULT_MODEL = {
    "ollama": "qwen3:8b",
    "claude": "claude-sonnet-4-6",
    "openai": "gpt-4o-mini",
    "gemini": "gemini-2.5-flash",
    "qwen": "qwen3.6-plus",
}

SOURCE_OPTIONS = ["deep_research", "duckduckgo", "bing_web", "all", "google_news_rss_global", "google_news_rss"]
DATE_RANGE_OPTIONS = ["7d", "1m", "3m", "6m", "1y"]
MIN_TAX_FOCUS_OPTIONS = ["low", "medium", "high"]


class InputPanel(ttk.Frame):
    def __init__(self, master, on_run):
        super().__init__(master, padding=12)
        self.on_run = on_run
        self._build()

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        ttk.Label(self, text="Search keywords").grid(row=0, column=0, columnspan=2, sticky="w")
        self.keywords = tk.Text(self, height=4, wrap="word")
        self.keywords.insert("1.0", "penalty, tax reform, filing obligation")
        self.keywords.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(4, 10))

        ttk.Label(self, text="Research intent").grid(row=2, column=0, columnspan=2, sticky="w")
        self.user_prompt = tk.Text(self, height=4, wrap="word")
        self.user_prompt.insert("1.0", "focus on high-risk tax updates for management review")
        self.user_prompt.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=(4, 10))

        self.source_name = tk.StringVar(value="all")
        self.date_range = tk.StringVar(value="3m")
        self.max_results = tk.IntVar(value=30)
        self.country = tk.StringVar(value="")
        self.industry = tk.StringVar(value="technology")
        self.generate_pptx = tk.BooleanVar(value=True)
        self.high_risk_only = tk.BooleanVar(value=False)
        self.use_ai_query_expansion = tk.BooleanVar(value=True)
        self.use_rag_context = tk.BooleanVar(value=True)
        self.rag_top_k = tk.IntVar(value=4)
        self.max_documents_to_process = tk.IntVar(value=3)
        self.provider = tk.StringVar(value="ollama")
        self.model_name = tk.StringVar(value=PROVIDER_DEFAULT_MODEL["ollama"])
        self.api_key_status = tk.StringVar(value="")
        self.api_key_value = tk.StringVar(value="")

        self._combo(
            "Source",
            self.source_name,
            SOURCE_OPTIONS,
            4,
            0,
        )
        self._combo("Period", self.date_range, DATE_RANGE_OPTIONS, 4, 1)
        self._spinbox("Max results", self.max_results, 1, 100, 6, 0)
        self._spinbox("PPTX limit", self.max_documents_to_process, 1, 10, 6, 1)
        self._entry("Country", self.country, 8, 0)
        self._entry("Industry", self.industry, 8, 1)

        ttk.Label(self, text="LLM provider").grid(row=10, column=0, sticky="w")
        provider_box = ttk.Combobox(
            self,
            textvariable=self.provider,
            values=list(PROVIDER_MODEL_PRESETS.keys()),
            state="readonly",
        )
        provider_box.grid(row=11, column=0, sticky="ew", pady=(4, 8))
        provider_box.bind("<<ComboboxSelected>>", self._on_provider_changed)

        ttk.Label(self, text="LLM model").grid(row=10, column=1, sticky="w", padx=(6, 0))
        self.model_combo = ttk.Combobox(
            self,
            textvariable=self.model_name,
            values=PROVIDER_MODEL_PRESETS["ollama"],
            state="normal",
        )
        self.model_combo.grid(row=11, column=1, sticky="ew", padx=(6, 0), pady=(4, 8))

        ttk.Label(self, text="API key (optional, overrides env var for this session)").grid(
            row=12, column=0, columnspan=2, sticky="w", pady=(2, 0)
        )
        self.api_key_entry = ttk.Entry(self, textvariable=self.api_key_value, show="*")
        self.api_key_entry.grid(row=13, column=0, columnspan=2, sticky="ew", pady=(2, 4))

        self.api_key_label = ttk.Label(self, textvariable=self.api_key_status, foreground="#5a6573")
        self.api_key_label.grid(row=14, column=0, columnspan=2, sticky="w", pady=(0, 4))

        ttk.Checkbutton(self, text="Use AI query expansion (uses selected provider)", variable=self.use_ai_query_expansion).grid(
            row=15, column=0, columnspan=2, sticky="w", pady=(6, 0)
        )
        ttk.Checkbutton(self, text="Use RAG cross-document context", variable=self.use_rag_context).grid(
            row=16, column=0, columnspan=2, sticky="w"
        )
        self._spinbox("RAG chunks", self.rag_top_k, 0, 10, 17, 0)
        ttk.Checkbutton(self, text="Generate PPTX", variable=self.generate_pptx).grid(
            row=17, column=1, sticky="w", padx=(6, 0), pady=(4, 0)
        )
        ttk.Checkbutton(self, text="Only generate PPTX for high-risk items", variable=self.high_risk_only).grid(
            row=18, column=1, sticky="w", padx=(6, 0), pady=(4, 0)
        )

        self._build_risk_theme_section(start_row=22)
        self.min_tax_focus = tk.StringVar(value="low")
        self._combo("Min tax focus for PPTX", self.min_tax_focus, MIN_TAX_FOCUS_OPTIONS, 26, 0)

        button_row = ttk.Frame(self)
        button_row.grid(row=28, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        button_row.columnconfigure(0, weight=3)
        button_row.columnconfigure(1, weight=1)
        self.run_button = ttk.Button(button_row, text="Run research", command=self.on_run)
        self.run_button.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.stop_button = ttk.Button(button_row, text="Stop", command=self._on_stop, state="disabled")
        self.stop_button.grid(row=0, column=1, sticky="ew", padx=(4, 0))

        self.dark_mode = tk.BooleanVar(value=False)
        ttk.Checkbutton(self, text="Dark mode", variable=self.dark_mode, command=self._on_theme_toggle).grid(
            row=29, column=0, columnspan=2, sticky="w", pady=(8, 0)
        )

        self._refresh_api_key_status()
        self._stop_handler = None

    def _on_provider_changed(self, _event=None):
        provider = self.provider.get()
        presets = PROVIDER_MODEL_PRESETS.get(provider, [])
        self.model_combo.configure(values=presets)
        default_model = PROVIDER_DEFAULT_MODEL.get(provider, "")
        if default_model:
            self.model_name.set(default_model)
        self._refresh_api_key_status()

    def _apply_api_key_override(self, provider: str):
        env_var = PROVIDER_API_KEY_ENV.get(provider)
        if not env_var:
            return
        value = (self.api_key_value.get() or "").strip()
        if value:
            os.environ[env_var] = value

    def _refresh_api_key_status(self):
        provider = self.provider.get()
        env_var = PROVIDER_API_KEY_ENV.get(provider)
        if not env_var:
            self.api_key_status.set("Local provider (Ollama). Make sure `ollama serve` is running.")
            self.api_key_label.configure(foreground="#5a6573")
            return
        if os.getenv(env_var):
            self.api_key_status.set(f"{env_var} detected. Ready to call {provider}.")
            self.api_key_label.configure(foreground="#1f6f3a")
        else:
            self.api_key_status.set(
                f"{env_var} is not set. Set it in your shell before launching to call {provider}."
            )
            self.api_key_label.configure(foreground="#a63a3a")

    def _build_risk_theme_section(self, start_row: int):
        ttk.Label(self, text="Risk themes (optional — lock search to these tax topics)").grid(
            row=start_row, column=0, columnspan=2, sticky="w", pady=(8, 2)
        )
        self.risk_theme_vars = {}
        theme_frame = ttk.Frame(self)
        theme_frame.grid(row=start_row + 1, column=0, columnspan=2, sticky="ew")
        theme_frame.columnconfigure(0, weight=1)
        theme_frame.columnconfigure(1, weight=1)
        for index, (key, label) in enumerate(RISK_THEME_OPTIONS):
            var = tk.BooleanVar(value=False)
            self.risk_theme_vars[key] = var
            row = index // 2
            column = index % 2
            ttk.Checkbutton(theme_frame, text=label, variable=var).grid(
                row=row, column=column, sticky="w", padx=(0, 8), pady=1
            )

    def _selected_risk_themes(self):
        if not getattr(self, "risk_theme_vars", None):
            return []
        return [key for key, var in self.risk_theme_vars.items() if var.get()]

    def _combo(self, label, variable, values, row, column):
        ttk.Label(self, text=label).grid(row=row, column=column, sticky="w")
        box = ttk.Combobox(self, textvariable=variable, values=values, state="readonly")
        box.grid(row=row + 1, column=column, sticky="ew", padx=(0 if column == 0 else 6, 0), pady=(4, 8))

    def _spinbox(self, label, variable, minimum, maximum, row, column):
        ttk.Label(self, text=label).grid(row=row, column=column, sticky="w")
        spin = ttk.Spinbox(self, from_=minimum, to=maximum, textvariable=variable)
        spin.grid(row=row + 1, column=column, sticky="ew", padx=(0 if column == 0 else 6, 0), pady=(4, 8))

    def _entry(self, label, variable, row, column):
        ttk.Label(self, text=label).grid(row=row, column=column, sticky="w")
        entry = ttk.Entry(self, textvariable=variable)
        entry.grid(row=row + 1, column=column, sticky="ew", padx=(0 if column == 0 else 6, 0), pady=(4, 8))

    def set_running(self, running):
        self.run_button.configure(text="Running..." if running else "Run research", state="disabled" if running else "normal")
        self.stop_button.configure(state="normal" if running else "disabled")

    def bind_stop_handler(self, handler):
        self._stop_handler = handler

    def _on_stop(self):
        if self._stop_handler:
            self._stop_handler()

    def _on_theme_toggle(self):
        root = self.winfo_toplevel()
        apply_theme = getattr(root, "apply_theme", None)
        if callable(apply_theme):
            apply_theme(dark=bool(self.dark_mode.get()))

    def get_payload(self):
        provider = (self.provider.get() or "ollama").strip().lower()
        model_name = (self.model_name.get() or PROVIDER_DEFAULT_MODEL.get(provider, "qwen3:8b")).strip()
        self._apply_api_key_override(provider)
        self._refresh_api_key_status()
        min_tax_focus = (self.min_tax_focus.get() or "low").strip().lower()
        if min_tax_focus not in MIN_TAX_FOCUS_OPTIONS:
            min_tax_focus = "low"
        return {
            "keywords": self._parse_keywords(self.keywords.get("1.0", "end")),
            "user_prompt": self.user_prompt.get("1.0", "end").strip() or None,
            "mode": "auto",
            "date_range": self.date_range.get(),
            "max_results": int(self.max_results.get()),
            "country": self.country.get().strip() or None,
            "industry": self.industry.get().strip() or None,
            "source_name": self.source_name.get(),
            "candidate_urls": [],
            "auto_ingest": True,
            "use_ai_query_expansion": bool(self.use_ai_query_expansion.get()),
            "generate_pptx": bool(self.generate_pptx.get()),
            "target_language": "zh",
            "provider": provider,
            "model_name": model_name,
            "max_documents_to_process": int(self.max_documents_to_process.get()),
            "high_risk_only": bool(self.high_risk_only.get()),
            "use_rag_context": bool(self.use_rag_context.get()),
            "rag_top_k": int(self.rag_top_k.get()),
            "risk_theme_labels": self._selected_risk_themes(),
            "min_tax_focus": min_tax_focus,
        }

    def apply_suggestions(self, suggestion):
        """Apply LLM research assistant suggestions to the search form."""
        if not isinstance(suggestion, dict):
            return

        keywords = suggestion.get("suggested_keywords") or suggestion.get("keywords") or []
        if isinstance(keywords, str):
            keywords = [part.strip() for part in keywords.replace("，", ",").split(",") if part.strip()]
        if keywords:
            self._replace_text(self.keywords, ", ".join(str(item).strip() for item in keywords if str(item).strip()))

        user_prompt = suggestion.get("suggested_user_prompt") or suggestion.get("user_prompt")
        if user_prompt:
            self._replace_text(self.user_prompt, str(user_prompt).strip())

        source_name = str(suggestion.get("source_name") or "").strip()
        if source_name in SOURCE_OPTIONS:
            self.source_name.set(source_name)

        date_range = str(suggestion.get("date_range") or "").strip()
        if date_range in DATE_RANGE_OPTIONS:
            self.date_range.set(date_range)

        if "max_results" in suggestion:
            self.max_results.set(self._clamp_int(suggestion.get("max_results"), 1, 100, self.max_results.get()))
        if "max_documents_to_process" in suggestion:
            self.max_documents_to_process.set(
                self._clamp_int(suggestion.get("max_documents_to_process"), 1, 10, self.max_documents_to_process.get())
            )

        if "country" in suggestion:
            self.country.set(str(suggestion.get("country") or "").strip())
        if "industry" in suggestion:
            self.industry.set(str(suggestion.get("industry") or "").strip())

        self.use_ai_query_expansion.set(True)
        if "use_rag_context" in suggestion:
            self.use_rag_context.set(bool(suggestion.get("use_rag_context")))
        if "rag_top_k" in suggestion:
            self.rag_top_k.set(self._clamp_int(suggestion.get("rag_top_k"), 0, 10, self.rag_top_k.get()))

    def _replace_text(self, widget, value):
        widget.delete("1.0", "end")
        widget.insert("1.0", value)

    def _clamp_int(self, value, minimum, maximum, default):
        try:
            number = int(value)
        except (TypeError, ValueError, tk.TclError):
            number = int(default)
        return max(minimum, min(maximum, number))

    def _parse_keywords(self, raw):
        separators = [",", "，", ";", "；", "|", "\n"]
        items = [raw]
        for separator in separators:
            items = [part for item in items for part in item.split(separator)]
        return [item.strip() for item in items if item.strip()]
