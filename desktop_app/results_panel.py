import tkinter as tk
from tkinter import ttk


class ResultsPanel(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
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

    def set_status(self, message):
        self.status.set(message)

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
