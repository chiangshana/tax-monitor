import json
import os
import queue
import shutil
import subprocess
import threading
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox, ttk

import requests


class N8nAutomationPanel(ttk.Frame):
    """Create and test n8n workflows from the current desktop payload."""

    def __init__(self, master, get_payload):
        super().__init__(master, padding=10)
        self._get_payload = get_payload or (lambda: {})
        self._api_server = None
        self._api_thread = None
        self._queue = queue.Queue()
        self._build()

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(6, weight=1)

        ttk.Label(self, text="n8n automation").grid(row=0, column=0, sticky="w", pady=(0, 8))

        api_box = ttk.LabelFrame(self, text="Tax Monitor API for n8n")
        api_box.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        api_box.columnconfigure(1, weight=1)
        self.api_host = tk.StringVar(value="127.0.0.1")
        self.api_port = tk.IntVar(value=8010)
        self.api_base_url = tk.StringVar(value="http://127.0.0.1:8010")
        ttk.Label(api_box, text="Host").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(api_box, textvariable=self.api_host, width=16).grid(row=0, column=1, sticky="w", padx=8, pady=6)
        ttk.Label(api_box, text="Port").grid(row=0, column=2, sticky="w", padx=8, pady=6)
        ttk.Spinbox(api_box, from_=1024, to=65535, textvariable=self.api_port, width=8).grid(row=0, column=3, sticky="w", padx=8, pady=6)
        ttk.Button(api_box, text="Start API server", command=self.start_api_server).grid(row=0, column=4, padx=8, pady=6)
        ttk.Button(api_box, text="Check API", command=self.check_api).grid(row=0, column=5, padx=8, pady=6)
        ttk.Button(api_box, text="Open API docs", command=self.open_api_docs).grid(row=0, column=6, padx=8, pady=6)

        workflow_box = ttk.LabelFrame(self, text="Workflow export")
        workflow_box.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        workflow_box.columnconfigure(1, weight=1)
        self.schedule_hours = tk.IntVar(value=24)
        self.workflow_name = tk.StringVar(value="Tax Monitor - Automated PPTX Pipeline")
        ttk.Label(workflow_box, text="Name").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(workflow_box, textvariable=self.workflow_name).grid(row=0, column=1, sticky="ew", padx=8, pady=6)
        ttk.Label(workflow_box, text="Every N hours").grid(row=0, column=2, sticky="w", padx=8, pady=6)
        ttk.Spinbox(workflow_box, from_=1, to=168, textvariable=self.schedule_hours, width=8).grid(row=0, column=3, sticky="w", padx=8, pady=6)
        ttk.Button(workflow_box, text="Export n8n JSON", command=self.export_workflow).grid(row=0, column=4, padx=8, pady=6)
        ttk.Button(workflow_box, text="Copy JSON", command=self.copy_workflow_json).grid(row=0, column=5, padx=8, pady=6)

        n8n_box = ttk.LabelFrame(self, text="n8n app")
        n8n_box.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        n8n_box.columnconfigure(1, weight=1)
        self.n8n_url = tk.StringVar(value="http://127.0.0.1:5678")
        self.n8n_api_key = tk.StringVar(value="")
        ttk.Label(n8n_box, text="n8n URL").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(n8n_box, textvariable=self.n8n_url).grid(row=0, column=1, sticky="ew", padx=8, pady=6)
        ttk.Button(n8n_box, text="Open n8n", command=self.open_n8n).grid(row=0, column=2, padx=8, pady=6)
        ttk.Button(n8n_box, text="Start n8n with npx", command=self.start_n8n_with_npx).grid(row=0, column=3, padx=8, pady=6)
        ttk.Label(n8n_box, text="API key").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(n8n_box, textvariable=self.n8n_api_key, show="*").grid(row=1, column=1, sticky="ew", padx=8, pady=6)
        ttk.Button(n8n_box, text="Import via n8n API", command=self.import_to_n8n_api).grid(row=1, column=2, padx=8, pady=6)

        self.status = tk.StringVar(
            value="Tip: start the Tax Monitor API, export JSON, then import it in n8n."
        )
        ttk.Label(self, textvariable=self.status).grid(row=4, column=0, sticky="ew", pady=(0, 8))

        quick_help = (
            "The workflow calls POST /api/pipeline/run with the current left-panel settings. "
            "n8n can run it on a schedule and the result contains generated PPTX file paths."
        )
        ttk.Label(self, text=quick_help, wraplength=920).grid(row=5, column=0, sticky="ew", pady=(0, 8))

        self.output = tk.Text(self, wrap="word", height=18)
        scroll = ttk.Scrollbar(self, command=self.output.yview)
        self.output.configure(yscrollcommand=scroll.set)
        self.output.grid(row=6, column=0, sticky="nsew")
        scroll.grid(row=6, column=1, sticky="ns")
        self._write("Ready.\n")

    def start_api_server(self):
        if self._api_thread and self._api_thread.is_alive():
            self.status.set("Tax Monitor API is already running from this app.")
            return
        try:
            host = (self.api_host.get() or "127.0.0.1").strip()
            port = int(self.api_port.get())
        except (TypeError, ValueError, tk.TclError):
            messagebox.showwarning("Invalid port", "Please enter a valid API port.")
            return

        self.api_base_url.set(f"http://{host}:{port}")
        self._write(f"Starting API server at {self.api_base_url.get()}...\n")
        self._api_thread = threading.Thread(target=self._run_api_server, args=(host, port), daemon=True)
        self._api_thread.start()
        self.after(1200, self.check_api)

    def _run_api_server(self, host, port):
        try:
            import uvicorn
            from main import app as fastapi_app

            config = uvicorn.Config(fastapi_app, host=host, port=port, log_level="warning")
            self._api_server = uvicorn.Server(config)
            self._api_server.run()
        except Exception as exc:
            self._queue.put(f"API server failed: {exc}\n")
            self.after(0, self._drain_queue)

    def check_api(self):
        self.api_base_url.set(f"http://{self.api_host.get()}:{int(self.api_port.get())}")
        url = self.api_base_url.get().rstrip("/") + "/"
        try:
            response = requests.get(url, timeout=3)
            if response.ok:
                self.status.set(f"Tax Monitor API is reachable: {url}")
                self._write(f"API check OK: {response.text}\n")
            else:
                self.status.set(f"API responded with HTTP {response.status_code}")
                self._write(f"API check failed: HTTP {response.status_code}\n")
        except requests.RequestException as exc:
            self.status.set("Tax Monitor API is not reachable yet.")
            self._write(f"API check failed: {exc}\n")

    def open_api_docs(self):
        self.api_base_url.set(f"http://{self.api_host.get()}:{int(self.api_port.get())}")
        webbrowser.open(self.api_base_url.get().rstrip("/") + "/docs")

    def open_n8n(self):
        webbrowser.open((self.n8n_url.get() or "http://127.0.0.1:5678").rstrip("/"))

    def start_n8n_with_npx(self):
        if not shutil.which("npx"):
            messagebox.showinfo("npx not found", "Install Node.js first, then use this button again.")
            webbrowser.open("https://nodejs.org/")
            return
        self._write("Starting n8n with npx. The first launch may download n8n.\n")
        try:
            creationflags = subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0
            subprocess.Popen(["npx", "n8n"], creationflags=creationflags)
            self.status.set("n8n launch requested. Open http://127.0.0.1:5678 when it is ready.")
        except Exception as exc:
            self._write(f"Failed to start n8n: {exc}\n")

    def export_workflow(self):
        workflow = self._build_workflow()
        path = filedialog.asksaveasfilename(
            title="Save n8n workflow JSON",
            defaultextension=".json",
            initialfile="tax_monitor_n8n_pipeline_workflow.json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(workflow, handle, ensure_ascii=False, indent=2)
        self.status.set(f"Workflow exported: {path}")
        self._write(f"Workflow exported to: {path}\n")

    def copy_workflow_json(self):
        workflow = self._build_workflow()
        text = json.dumps(workflow, ensure_ascii=False, indent=2)
        root = self.winfo_toplevel()
        root.clipboard_clear()
        root.clipboard_append(text)
        self.status.set("Workflow JSON copied to clipboard.")
        self._write("Workflow JSON copied to clipboard.\n")

    def import_to_n8n_api(self):
        api_key = (self.n8n_api_key.get() or "").strip()
        if not api_key:
            messagebox.showwarning("Missing API key", "Paste an n8n API key first, or export JSON and import manually.")
            return
        endpoint = (self.n8n_url.get() or "http://127.0.0.1:5678").rstrip("/") + "/api/v1/workflows"
        try:
            response = requests.post(
                endpoint,
                headers={"X-N8N-API-KEY": api_key, "Content-Type": "application/json"},
                json=self._build_workflow(),
                timeout=20,
            )
            if response.status_code in (200, 201):
                self.status.set("Workflow imported to n8n.")
                self._write(f"n8n import OK: {response.text[:500]}\n")
            else:
                self.status.set(f"n8n import failed: HTTP {response.status_code}")
                self._write(f"n8n import failed: HTTP {response.status_code}\n{response.text[:1000]}\n")
        except requests.RequestException as exc:
            self.status.set("n8n import failed.")
            self._write(f"n8n import failed: {exc}\n")

    def _build_workflow(self):
        self.api_base_url.set(f"http://{self.api_host.get()}:{int(self.api_port.get())}")
        payload = self._pipeline_payload()
        payload_json = json.dumps(payload, ensure_ascii=False, indent=2)
        api_url = self.api_base_url.get().rstrip("/") + "/api/pipeline/run"
        hours = max(1, min(168, int(self.schedule_hours.get())))

        return {
            "name": self.workflow_name.get().strip() or "Tax Monitor - Automated PPTX Pipeline",
            "nodes": [
                {
                    "parameters": {},
                    "id": "manual-trigger",
                    "name": "Manual Trigger",
                    "type": "n8n-nodes-base.manualTrigger",
                    "typeVersion": 1,
                    "position": [220, 220],
                },
                {
                    "parameters": {"rule": {"interval": [{"field": "hours", "hoursInterval": hours}]}},
                    "id": "schedule-trigger",
                    "name": "Scheduled Trigger",
                    "type": "n8n-nodes-base.scheduleTrigger",
                    "typeVersion": 1.2,
                    "position": [220, 420],
                },
                {
                    "parameters": {
                        "jsCode": "return [{ json: { payload: " + payload_json + " } }];"
                    },
                    "id": "prepare-payload",
                    "name": "Prepare Tax Monitor Payload",
                    "type": "n8n-nodes-base.code",
                    "typeVersion": 2,
                    "position": [520, 320],
                },
                {
                    "parameters": {
                        "method": "POST",
                        "url": api_url,
                        "sendBody": True,
                        "contentType": "json",
                        "specifyBody": "json",
                        "jsonBody": "={{ $json.payload }}",
                    },
                    "id": "run-tax-monitor",
                    "name": "Run Tax Monitor Pipeline",
                    "type": "n8n-nodes-base.httpRequest",
                    "typeVersion": 4.2,
                    "position": [820, 320],
                },
                {
                    "parameters": {
                        "jsCode": (
                            "const docs = $json.documents || [];\n"
                            "return [{ json: {\n"
                            "  run_id: $json.run_id,\n"
                            "  searched_result_count: $json.searched_result_count,\n"
                            "  ingested_result_count: $json.ingested_result_count,\n"
                            "  processed_count: $json.processed_count,\n"
                            "  pptx_files: docs.map(d => d.report_file_path).filter(Boolean),\n"
                            "  high_risk_docs: docs.filter(d => String(d.risk_level || '').toLowerCase() === 'high')\n"
                            "} }];"
                        )
                    },
                    "id": "summarize-output",
                    "name": "Summarize PPTX Output",
                    "type": "n8n-nodes-base.code",
                    "typeVersion": 2,
                    "position": [1110, 320],
                },
            ],
            "connections": {
                "Manual Trigger": {"main": [[{"node": "Prepare Tax Monitor Payload", "type": "main", "index": 0}]]},
                "Scheduled Trigger": {"main": [[{"node": "Prepare Tax Monitor Payload", "type": "main", "index": 0}]]},
                "Prepare Tax Monitor Payload": {"main": [[{"node": "Run Tax Monitor Pipeline", "type": "main", "index": 0}]]},
                "Run Tax Monitor Pipeline": {"main": [[{"node": "Summarize PPTX Output", "type": "main", "index": 0}]]},
            },
            "settings": {"executionOrder": "v1"},
        }

    def _pipeline_payload(self):
        raw = dict(self._get_payload() or {})
        return {
            "keywords": raw.get("keywords") or [],
            "user_prompt": raw.get("user_prompt"),
            "mode": raw.get("mode") or "auto",
            "date_range": raw.get("date_range") or "3m",
            "max_results": int(raw.get("max_results") or 30),
            "country": raw.get("country"),
            "industry": raw.get("industry"),
            "source_name": raw.get("source_name") or "all",
            "candidate_urls": raw.get("candidate_urls") or [],
            "use_ai_query_expansion": bool(raw.get("use_ai_query_expansion", True)),
            "target_language": raw.get("target_language") or "zh",
            "analysis_mode": raw.get("analysis_mode") or "translate_first",
            "provider": raw.get("provider") or "ollama",
            "model_name": raw.get("model_name") or "qwen3:8b",
            "report_format": "pptx",
            "max_documents_to_process": int(raw.get("max_documents_to_process") or 3),
            "high_risk_only": bool(raw.get("high_risk_only", False)),
            "use_rag_context": bool(raw.get("use_rag_context", True)),
            "rag_top_k": int(raw.get("rag_top_k") or 4),
        }

    def _drain_queue(self):
        while True:
            try:
                item = self._queue.get_nowait()
            except queue.Empty:
                return
            self._write(item)

    def _write(self, text):
        self.output.configure(state="normal")
        self.output.insert("end", text)
        self.output.see("end")
        self.output.configure(state="disabled")
