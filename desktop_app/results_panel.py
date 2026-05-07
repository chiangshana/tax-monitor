import tkinter as tk
from tkinter import ttk

from services.storage_service import StorageService


class ResultsPanel(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self._storage = StorageService()
        self._build()

    def _build(self):
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        self.status = tk.StringVar(value="Ready")
        ttk.Label(self, textvariable=self.status).grid(row=0, column=0, sticky="ew", pady=(0, 8))

        self.notebook = ttk.Notebook(self)
        self.notebook.grid(row=1, column=0, sticky="nsew")

        self.summary_text = self._text_tab("Summary")
        self.search_text = self._text_tab("Search results")
        self.document_text = self._text_tab("Documents")
        self.pptx_text = self._text_tab("PPTX")
        self.history_text = self._build_history_tab()
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

    def _text_tab(self, title):
        frame = ttk.Frame(self.notebook)
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        text = tk.Text(frame, wrap="word", height=20)
        scroll = ttk.Scrollbar(frame, command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        text.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        self.notebook.add(frame, text=title)
        return text

    def _build_history_tab(self):
        frame = ttk.Frame(self.notebook)
        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(0, weight=1)

        toolbar = ttk.Frame(frame)
        toolbar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        ttk.Button(toolbar, text="Refresh", command=self.refresh_history).pack(side="left")
        ttk.Label(toolbar, text="Most recent pipeline runs (auto-refresh on tab open)").pack(side="left", padx=(8, 0))

        text = tk.Text(frame, wrap="word", height=20)
        scroll = ttk.Scrollbar(frame, command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        text.grid(row=1, column=0, sticky="nsew")
        scroll.grid(row=1, column=1, sticky="ns")
        self.notebook.add(frame, text="History")
        return text

    def _on_tab_changed(self, _event=None):
        try:
            current_tab = self.notebook.tab(self.notebook.select(), "text")
        except tk.TclError:
            return
        if current_tab == "History":
            self.refresh_history()

    def refresh_history(self):
        try:
            runs = self._storage.list_pipeline_runs(limit=50)
        except Exception as exc:
            self._write(self.history_text, f"Failed to load history: {exc}")
            return
        if not runs:
            self._write(self.history_text, "No pipeline runs recorded yet.")
            return
        blocks = []
        for index, run in enumerate(runs, start=1):
            keywords = run.get("keywords") or []
            if isinstance(keywords, list):
                keywords_str = ", ".join(keywords)
            else:
                keywords_str = str(keywords)
            summary = run.get("result_summary") or {}
            if isinstance(summary, dict):
                summary_line = (
                    f"searched={summary.get('searched_result_count', 0)} "
                    f"ingested={summary.get('ingested_result_count', 0)} "
                    f"processed={summary.get('processed_count', 0)}"
                )
            else:
                summary_line = str(summary)
            blocks.append(
                "\n".join([
                    f"{index}. [{run.get('status', '?').upper()}] {run.get('run_id', '')}",
                    f"   started: {run.get('started_at', '')}   finished: {run.get('finished_at', '')}",
                    f"   provider: {run.get('provider', '')}/{run.get('model_name', '')}   source: {run.get('source_name', '')}",
                    f"   keywords: {keywords_str}",
                    f"   prompt: {(run.get('user_prompt') or '')[:160]}",
                    f"   summary: {summary_line}",
                    f"   error: {run.get('error') or '-'}",
                ])
            )
        self._write(self.history_text, "\n\n".join(blocks))

    def set_status(self, message):
        self.status.set(message)

    def update_progress(self, event):
        if not isinstance(event, dict):
            return
        kind = event.get("event", "")
        text = self._format_progress_event(kind, event)
        if text:
            self.set_status(text)

    def _format_progress_event(self, kind, event):
        if kind == "run_started":
            return "Run started"
        if kind == "search_started":
            keywords = event.get("keywords") or []
            return f"Searching ({event.get('source_name', 'n/a')}): {', '.join(keywords[:3])}"
        if kind == "search_completed":
            return f"Search returned {event.get('count', 0)} candidates"
        if kind == "ingest_phase_started":
            return f"Ingesting {event.get('total', 0)} candidates (concurrent={4})..."
        if kind == "ingest_started":
            return f"Ingesting #{event.get('index', '?')}: {(event.get('title') or event.get('url') or '')[:80]}"
        if kind == "ingest_completed":
            tail = " (deduplicated)" if event.get("deduplicated") else ""
            return f"Ingested {event.get('completed', '?')}/{event.get('total', '?')}{tail}"
        if kind == "ingest_failed":
            return f"Ingest failed: {(event.get('error') or '')[:120]}"
        if kind == "ingest_skipped":
            return f"Skipped (precheck): {(event.get('url') or '')[:80]}"
        if kind == "ingest_phase_completed":
            return f"Ingest phase done: {event.get('ingested', 0)} documents"
        if kind == "analysis_started":
            return f"Analyzing #{event.get('index', '?')}: {(event.get('title') or '')[:80]}"
        if kind == "analysis_completed":
            return f"Analysis #{event.get('index', '?')} done: risk={event.get('risk_level', 'n/a')}"
        if kind == "report_started":
            return f"Generating {event.get('format', '')} report for #{event.get('index', '?')}"
        if kind == "report_completed":
            path = event.get("file_path") or ""
            return f"Report ready: {path[-80:]}" if path else "Report generated"
        if kind == "run_completed":
            cost = event.get("cost") or {}
            totals = (cost.get("totals") or {}) if isinstance(cost, dict) else {}
            cost_tail = ""
            if totals:
                cost_tail = (
                    f" · LLM tokens in/out={totals.get('input_tokens', 0)}/{totals.get('output_tokens', 0)}"
                    f" cache_read={totals.get('cache_read_tokens', 0)}"
                )
            return (
                f"Pipeline complete: ingested={event.get('ingested', '?')}"
                f" processed={event.get('processed', '?')}{cost_tail}"
            )
        if kind == "run_cancelled":
            return "Pipeline cancelled by user"
        if kind == "run_failed":
            return f"Pipeline failed: {(event.get('error') or '')[:200]}"
        return f"{kind}"

    def render_result(self, result):
        self._write(self.summary_text, self._format_summary(result))
        self._write(self.search_text, self._format_search_results(result.get("search_results", [])))
        self._write(self.document_text, self._format_documents(result.get("documents", [])))
        self._write(self.pptx_text, self._format_pptx(result.get("documents", [])))

    def render_error(self, message):
        self.set_status("Failed")
        self._write(self.summary_text, message)

    def _write(self, widget, text):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    def _format_summary(self, result):
        model = result.get("trained_keyword_model", {})
        lines = [
            f"Query: {result.get('query', '')}",
            f"Keywords: {', '.join(result.get('normalized_keywords', []))}",
            f"Search results: {result.get('searched_result_count', 0)}",
            f"Ingested: {result.get('ingested_result_count', 0)}",
            f"PPTX generated: {result.get('generated_report_count', 0)}",
            f"Training documents: {model.get('document_count', 0)}",
            f"Vocabulary size: {model.get('vocabulary_size', 0)}",
            "",
            model.get("message", ""),
        ]
        return "\n".join(lines)

    def _format_search_results(self, results):
        if not results:
            return "No search results."
        blocks = []
        for index, item in enumerate(results, start=1):
            reasons = "\n".join(f"  - {reason}" for reason in item.get("match_reasons", []))
            blocks.append(
                "\n".join([
                    f"{index}. {item.get('title', '')}",
                    f"   URL: {item.get('url', '')}",
                    f"   Domain: {item.get('domain', '')}",
                    f"   Type: {item.get('result_type', '')}",
                    f"   Source: {item.get('source', '')}",
                    f"   Score: {item.get('relevance_score', 0)}",
                    f"   Reasons:\n{reasons or '  - N/A'}",
                ])
            )
        return "\n\n".join(blocks)

    def _format_documents(self, documents):
        if not documents:
            return "No documents ingested."
        blocks = []
        for index, doc in enumerate(documents, start=1):
            blocks.append(
                "\n".join([
                    f"{index}. {doc.get('title', '')}",
                    f"   doc_id: {doc.get('doc_id', '')}",
                    f"   url: {doc.get('url', '')}",
                    f"   risk: {doc.get('risk_level') or 'not analyzed'}",
                    f"   tags: {', '.join(doc.get('risk_tags', []))}",
                    f"   keywords: {', '.join(doc.get('extracted_keywords', []))}",
                ])
            )
        return "\n\n".join(blocks)

    def _format_pptx(self, documents):
        generated = [doc for doc in documents if doc.get("pptx_file_path")]
        if not generated:
            return "No PPTX generated."
        return "\n\n".join(
            f"{index}. {doc.get('title', '')}\n   {doc.get('pptx_file_path', '')}"
            for index, doc in enumerate(generated, start=1)
        )
