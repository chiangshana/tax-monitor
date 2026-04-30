import tkinter as tk
from tkinter import ttk


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
        self.max_documents_to_process = tk.IntVar(value=3)

        self._combo("Source", self.source_name, ["duckduckgo", "bing_web", "all", "google_news_rss_global", "google_news_rss"], 4, 0)
        self._combo("Period", self.date_range, ["7d", "1m", "3m", "6m", "1y"], 4, 1)
        self._spinbox("Max results", self.max_results, 1, 100, 6, 0)
        self._spinbox("PPTX limit", self.max_documents_to_process, 1, 10, 6, 1)
        self._entry("Country", self.country, 8, 0)
        self._entry("Industry", self.industry, 8, 1)

        ttk.Checkbutton(self, text="Use Ollama query expansion", variable=self.use_ai_query_expansion).grid(
            row=10, column=0, columnspan=2, sticky="w", pady=(6, 0)
        )
        ttk.Checkbutton(self, text="Generate PPTX", variable=self.generate_pptx).grid(
            row=11, column=0, columnspan=2, sticky="w"
        )
        ttk.Checkbutton(self, text="Only generate PPTX for high-risk items", variable=self.high_risk_only).grid(
            row=12, column=0, columnspan=2, sticky="w"
        )

        self.run_button = ttk.Button(self, text="Run research", command=self.on_run)
        self.run_button.grid(row=13, column=0, columnspan=2, sticky="ew", pady=(12, 0))

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

    def get_payload(self):
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
            "provider": "ollama",
            "model_name": "qwen3:8b",
            "max_documents_to_process": int(self.max_documents_to_process.get()),
            "high_risk_only": bool(self.high_risk_only.get()),
        }

    def _parse_keywords(self, raw):
        separators = [",", "，", ";", "；", "|", "\n"]
        items = [raw]
        for separator in separators:
            items = [part for item in items for part in item.split(separator)]
        return [item.strip() for item in items if item.strip()]
