import json
import os
import queue
import re
import shutil
import subprocess
import threading
import tkinter as tk
import webbrowser
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import requests


ALERT_FREQUENCY_PRESETS = {
    "每月一次 (每月 1 號 09:00)": {
        "cron": "0 9 1 * *",
        "trigger_label": "每月 1 號 09:00",
        "high_risk_only": False,
    },
    "每週一次 (週一 09:00)": {
        "cron": "0 9 * * 1",
        "trigger_label": "每週一 09:00",
        "high_risk_only": False,
    },
    "每天一次 (每天 09:00)": {
        "cron": "0 9 * * *",
        "trigger_label": "每天 09:00",
        "high_risk_only": False,
    },
    "有新資訊時 (每 6 小時掃，只在 High Risk 才寄)": {
        "cron": "0 */6 * * *",
        "trigger_label": "每 6 小時掃描，僅 High Risk 通知",
        "high_risk_only": True,
    },
}
DEFAULT_ALERT_FREQUENCY = "每月一次 (每月 1 號 09:00)"


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
        self.rowconfigure(7, weight=1)

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

        workflow_box = ttk.LabelFrame(self, text="Workflow export (進階：給工程師用)")
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

        alert_box = ttk.LabelFrame(self, text="自動寄信通知 (填完就能用，不用懂程式)")
        alert_box.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        alert_box.columnconfigure(1, weight=1)
        alert_box.columnconfigure(3, weight=1)
        self.alert_email_to = tk.StringVar(value="")
        self.alert_email_from = tk.StringVar(value="")
        self.alert_frequency = tk.StringVar(value=DEFAULT_ALERT_FREQUENCY)
        self.alert_workflow_name = tk.StringVar(value="Tax Monitor 稅務風險定期通知")
        ttk.Label(alert_box, text="收件 Email").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(alert_box, textvariable=self.alert_email_to).grid(row=0, column=1, sticky="ew", padx=8, pady=6)
        ttk.Label(alert_box, text="寄件 Gmail").grid(row=0, column=2, sticky="w", padx=8, pady=6)
        ttk.Entry(alert_box, textvariable=self.alert_email_from).grid(row=0, column=3, sticky="ew", padx=8, pady=6)
        ttk.Label(alert_box, text="觸發頻率").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        ttk.Combobox(
            alert_box,
            textvariable=self.alert_frequency,
            values=list(ALERT_FREQUENCY_PRESETS.keys()),
            state="readonly",
        ).grid(row=1, column=1, columnspan=3, sticky="ew", padx=8, pady=6)
        ttk.Label(alert_box, text="Workflow 名稱").grid(row=2, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(alert_box, textvariable=self.alert_workflow_name).grid(row=2, column=1, columnspan=3, sticky="ew", padx=8, pady=6)
        ttk.Button(
            alert_box,
            text="一鍵匯出自動通知包 (JSON + 操作說明)",
            command=self.export_alert_bundle,
        ).grid(row=3, column=0, columnspan=4, sticky="ew", padx=8, pady=(2, 8))

        n8n_box = ttk.LabelFrame(self, text="n8n app")
        n8n_box.grid(row=4, column=0, sticky="ew", pady=(0, 8))
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
            value="提示：填完上面的 Email 欄位，按「一鍵匯出自動通知包」即可。"
        )
        ttk.Label(self, textvariable=self.status).grid(row=5, column=0, sticky="ew", pady=(0, 8))

        quick_help = (
            "「自動寄信通知」會匯出一個 n8n workflow + 一份操作說明。"
            "把 workflow 拖到 n8n 視窗，按操作說明設定一次 Gmail SMTP credential，之後系統就會"
            "按你選的頻率自動執行、把 PPTX 報告寄到收件信箱。請保持 Tax Monitor 桌面程式開啟。"
        )
        ttk.Label(self, text=quick_help, wraplength=920).grid(row=6, column=0, sticky="ew", pady=(0, 8))

        self.output = tk.Text(self, wrap="word", height=18)
        scroll = ttk.Scrollbar(self, command=self.output.yview)
        self.output.configure(yscrollcommand=scroll.set)
        self.output.grid(row=7, column=0, sticky="nsew")
        scroll.grid(row=7, column=1, sticky="ns")
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

    def export_alert_bundle(self):
        email_to = (self.alert_email_to.get() or "").strip()
        email_from = (self.alert_email_from.get() or "").strip()
        frequency_label = self.alert_frequency.get() or DEFAULT_ALERT_FREQUENCY
        preset = ALERT_FREQUENCY_PRESETS.get(frequency_label)
        if preset is None:
            messagebox.showwarning("頻率錯誤", "請從下拉選單選一個觸發頻率。")
            return
        if not self._looks_like_email(email_to):
            messagebox.showwarning("收件信箱無效", "請輸入收件 Email，例如 yourname@gmail.com")
            return
        if not self._looks_like_email(email_from):
            messagebox.showwarning("寄件信箱無效", "請輸入寄件 Gmail，例如 yourname@gmail.com")
            return

        directory = filedialog.askdirectory(title="選擇要存放自動通知包的資料夾")
        if not directory:
            return
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_dir = Path(directory) / f"tax_monitor_alert_{timestamp}"
        target_dir.mkdir(parents=True, exist_ok=True)

        workflow_name = (self.alert_workflow_name.get() or "Tax Monitor 稅務風險定期通知").strip()
        workflow = self._build_alert_workflow(
            workflow_name=workflow_name,
            email_to=email_to,
            email_from=email_from,
            cron=preset["cron"],
            high_risk_only=preset["high_risk_only"],
        )
        json_path = target_dir / "tax_monitor_n8n_alert_workflow.json"
        with open(json_path, "w", encoding="utf-8") as handle:
            json.dump(workflow, handle, ensure_ascii=False, indent=2)

        card = self._build_setup_card(
            workflow_name=workflow_name,
            email_to=email_to,
            email_from=email_from,
            frequency_label=frequency_label,
            trigger_label=preset["trigger_label"],
            json_filename=json_path.name,
            api_base_url=self.api_base_url.get(),
        )
        card_path = target_dir / "三步驟設定卡.txt"
        with open(card_path, "w", encoding="utf-8") as handle:
            handle.write(card)

        self.status.set(f"已產出自動通知包：{target_dir}")
        self._write(
            "已產出自動通知包：\n"
            f"  資料夾：{target_dir}\n"
            f"  - {json_path.name}（匯入 n8n 用）\n"
            f"  - {card_path.name}（員工照這份做就好）\n"
        )
        messagebox.showinfo(
            "完成",
            f"已產出自動通知包：\n{target_dir}\n\n請打開「三步驟設定卡.txt」，照著三個步驟做完一次，之後系統就會自動寄信。",
        )

    def _build_alert_workflow(self, workflow_name, email_to, email_from, cron, high_risk_only):
        self.api_base_url.set(f"http://{self.api_host.get()}:{int(self.api_port.get())}")
        payload = self._pipeline_payload()
        payload["high_risk_only"] = high_risk_only
        payload_json = json.dumps(payload, ensure_ascii=False, indent=2)
        api_url = self.api_base_url.get().rstrip("/") + "/api/pipeline/run"
        body_template = (
            "以下是 Tax Monitor 在 {{ $now }} 自動偵測到的稅務風險摘要。\\n\\n"
            "標題：{{ $json.title }}\\n"
            "風險等級：{{ $json.risk_level }}\\n"
            "稅務焦點：{{ $json.tax_focus_label }} (score {{ $json.tax_focus_score }})\\n"
            "風險標籤：{{ $json.risk_tags ? $json.risk_tags.join(', ') : '' }}\\n"
            "來源：{{ $json.source_url }}\\n\\n"
            "完整 PPTX 報告請見附件。"
        )
        only_when_results_filter = (
            "" if not high_risk_only else
            " const hasResult = (Array.isArray($json.documents) && $json.documents.length > 0);"
            " if (!hasResult) { return []; }"
        )

        return {
            "name": workflow_name,
            "nodes": [
                {
                    "parameters": {
                        "rule": {
                            "interval": [
                                {
                                    "field": "cronExpression",
                                    "expression": cron,
                                }
                            ]
                        }
                    },
                    "id": "alert-cron",
                    "name": "排程觸發",
                    "type": "n8n-nodes-base.scheduleTrigger",
                    "typeVersion": 1.2,
                    "position": [220, 300],
                },
                {
                    "parameters": {
                        "jsCode": (
                            "return [{ json: { payload: "
                            + payload_json
                            + ", email_to: '"
                            + email_to.replace("'", "\\'")
                            + "', email_from: '"
                            + email_from.replace("'", "\\'")
                            + "' } }];"
                        )
                    },
                    "id": "alert-prepare-payload",
                    "name": "準備 Pipeline Payload",
                    "type": "n8n-nodes-base.code",
                    "typeVersion": 2,
                    "position": [480, 300],
                },
                {
                    "parameters": {
                        "method": "POST",
                        "url": api_url,
                        "sendBody": True,
                        "contentType": "json",
                        "specifyBody": "json",
                        "jsonBody": "={{ $json.payload }}",
                        "options": {
                            "response": {"response": {"responseFormat": "json"}},
                            "timeout": 1800000,
                        },
                    },
                    "id": "alert-run-pipeline",
                    "name": "執行 Tax Monitor Pipeline",
                    "type": "n8n-nodes-base.httpRequest",
                    "typeVersion": 4.2,
                    "position": [760, 300],
                },
                {
                    "parameters": {
                        "jsCode": (
                            "const docs = $json.documents || [];"
                            + only_when_results_filter
                            + " const config = $('準備 Pipeline Payload').first().json;"
                            " return docs"
                            " .filter(doc => doc.report_file_path)"
                            " .map(doc => ({ json: {"
                            "   doc_id: doc.doc_id,"
                            "   title: doc.title,"
                            "   risk_level: doc.risk_level,"
                            "   risk_tags: doc.risk_tags || [],"
                            "   tax_focus_label: doc.tax_focus_label,"
                            "   tax_focus_score: doc.tax_focus_score,"
                            "   source_url: doc.source_url || '',"
                            "   report_file_path: doc.report_file_path,"
                            "   email_to: config.email_to,"
                            "   email_from: config.email_from"
                            " } }));"
                        )
                    },
                    "id": "alert-fanout",
                    "name": "展開每份報告",
                    "type": "n8n-nodes-base.code",
                    "typeVersion": 2,
                    "position": [1020, 300],
                },
                {
                    "parameters": {
                        "filePath": "={{ $json.report_file_path }}",
                        "dataPropertyName": "pptx_attachment",
                    },
                    "id": "alert-read-pptx",
                    "name": "讀取 PPTX 附件",
                    "type": "n8n-nodes-base.readBinaryFile",
                    "typeVersion": 1,
                    "position": [1280, 300],
                },
                {
                    "parameters": {
                        "fromEmail": "={{ $json.email_from }}",
                        "toEmail": "={{ $json.email_to }}",
                        "subject": "=[Tax Monitor] {{ $json.risk_level }} - {{ $json.title }}",
                        "emailType": "text",
                        "message": "=" + body_template,
                        "attachments": "pptx_attachment",
                        "options": {},
                    },
                    "id": "alert-send-gmail",
                    "name": "寄送 Gmail",
                    "type": "n8n-nodes-base.emailSend",
                    "typeVersion": 2.1,
                    "position": [1540, 300],
                    "credentials": {
                        "smtp": {
                            "id": "REPLACE_WITH_YOUR_SMTP_CREDENTIAL_ID",
                            "name": "Gmail SMTP (Tax Monitor)",
                        }
                    },
                },
            ],
            "connections": {
                "排程觸發": {"main": [[{"node": "準備 Pipeline Payload", "type": "main", "index": 0}]]},
                "準備 Pipeline Payload": {"main": [[{"node": "執行 Tax Monitor Pipeline", "type": "main", "index": 0}]]},
                "執行 Tax Monitor Pipeline": {"main": [[{"node": "展開每份報告", "type": "main", "index": 0}]]},
                "展開每份報告": {"main": [[{"node": "讀取 PPTX 附件", "type": "main", "index": 0}]]},
                "讀取 PPTX 附件": {"main": [[{"node": "寄送 Gmail", "type": "main", "index": 0}]]},
            },
            "active": False,
            "settings": {"executionOrder": "v1"},
            "versionId": "tax-monitor-alert-v1",
            "meta": {"templateCredsSetupCompleted": False},
        }

    def _build_setup_card(self, workflow_name, email_to, email_from, frequency_label, trigger_label, json_filename, api_base_url):
        lines = [
            "Tax Monitor 自動通知 - 三步驟設定卡",
            "=" * 60,
            "",
            f"產生時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Workflow 名稱：{workflow_name}",
            f"收件信箱：{email_to}",
            f"寄件 Gmail：{email_from}",
            f"觸發頻率：{frequency_label}",
            f"實際排程：{trigger_label}",
            "",
            "完成下面三步驟，之後系統會自動把稅務風險 PPTX 寄到你的信箱。",
            "你只要在使用 Tax Monitor 桌面程式時保持它開著就好。",
            "",
            "------------------------------------------------------------",
            "步驟 1：在桌面程式按下「Start API server」",
            "------------------------------------------------------------",
            "1) 回到「n8n automation」分頁上方的「Tax Monitor API for n8n」區塊。",
            "2) 按「Start API server」按鈕。",
            "3) 按旁邊的「Check API」確認狀態顯示 reachable。",
            f"   - 預期網址：{api_base_url}",
            "   - 之後每次要讓 n8n 自動跑，這支 API server 都必須是開著的。",
            "   - 提示：最簡單就是不要關閉 Tax Monitor 桌面程式。",
            "",
            "------------------------------------------------------------",
            "步驟 2：把 workflow 匯入 n8n",
            "------------------------------------------------------------",
            "如果你還沒有 n8n：",
            "  - 桌面程式「n8n app」區塊有「Start n8n with npx」按鈕，按一下就會自動啟動。",
            "  - 第一次啟動會花幾分鐘下載；完成後瀏覽器會打開 http://127.0.0.1:5678。",
            "",
            "匯入 workflow：",
            f"  1) 打開 n8n（http://127.0.0.1:5678），登入或建立帳號。",
            f"  2) 左上角 Workflows -> 右上角「+」按鈕 -> 選「Import from File」。",
            f"  3) 選這份檔案：{json_filename}",
            f"  4) 看到名為「{workflow_name}」的 workflow 被打開。",
            "",
            "------------------------------------------------------------",
            "步驟 3：設定一次 Gmail 寄件 (僅第一次需要)",
            "------------------------------------------------------------",
            "為什麼需要：n8n 要用你的 Gmail 帳號幫你寄信，所以要拿到一組「應用程式密碼」。",
            "(這比你的 Gmail 登入密碼安全，撤銷也方便)",
            "",
            "A. 開啟 Gmail App Password (每個 Gmail 帳號只要做一次)：",
            "   1) 用你的「寄件 Gmail」登入 Google 帳號。",
            "   2) 開啟兩步驟驗證 (如果還沒開)：",
            "      https://myaccount.google.com/security",
            "   3) 開啟 App Password 頁面：",
            "      https://myaccount.google.com/apppasswords",
            "   4) App 選「Mail」，Device 選「Other」並輸入 Tax Monitor，按「Generate」。",
            "   5) 把畫面上 16 碼密碼（含空白可直接複製）整段複製起來。",
            "",
            "B. 在 n8n 設定 SMTP credential：",
            "   1) 在 n8n 開好的 workflow 裡，找到名為「寄送 Gmail」的節點，點兩下打開。",
            "   2) 在右側「Credential for SMTP account」按「Create New」。",
            "   3) 填入：",
            "      - User：你的寄件 Gmail (例如 yourname@gmail.com)",
            "      - Password：剛剛 Google 給你的 16 碼 App Password",
            "      - Host：smtp.gmail.com",
            "      - Port：465",
            "      - SSL/TLS：開啟 (打勾)",
            "      - Name：Gmail SMTP (Tax Monitor) ← 名稱用這個就好",
            "   4) 按「Save」。",
            "   5) 關掉節點視窗。",
            "",
            "C. 啟動 workflow：",
            "   1) 在 n8n workflow 編輯畫面右上角，找到「Active」開關。",
            "   2) 把它打開 (變綠色 / On)。",
            "   3) 完成！系統會依照你選的頻率自動執行。",
            "",
            "------------------------------------------------------------",
            "想要先測試一次嗎？",
            "------------------------------------------------------------",
            "1) 在 workflow 畫面，右下角按「Execute Workflow」(三角形播放按鈕)。",
            "2) 等所有節點變綠色或紅色 (大約 1-5 分鐘，取決於有沒有用 LLM)。",
            "3) 如果有偵測到風險文章，你的信箱會收到一封含 PPTX 附件的信。",
            "4) 如果一封都沒收到、且所有節點都是綠色，代表本次掃描沒有發現高風險的內容；",
            "   下次觸發再試。",
            "",
            "------------------------------------------------------------",
            "常見問題",
            "------------------------------------------------------------",
            "Q：每次都要開著 Tax Monitor 桌面程式嗎？",
            "  A：是。n8n 會打 API 給桌面程式，桌面程式關掉 API 就沒了。",
            "     可以把 Tax Monitor 加到 Windows 開機啟動，或最小化到系統列。",
            "",
            "Q：可以改頻率嗎？",
            "  A：可以。在 n8n 打開這個 workflow，點「排程觸發」節點修改 Cron Expression。",
            "     或者回 Tax Monitor 桌面程式重新匯出一份新的，蓋掉舊的。",
            "",
            "Q：「執行 Tax Monitor Pipeline」節點 timeout？",
            "  A：跑 LLM 分析比較久。已經設成 30 分鐘 timeout，通常夠。",
            "     如果還是不夠，把桌面程式左側的「Max results」與「PPTX limit」調小一點再重出。",
            "",
            "Q：收信延遲？",
            "  A：n8n 是依排程觸發的，介於兩次排程之間不會立即寄信。",
            "     想要更頻繁，請選「有新資訊時 (每 6 小時掃)」。",
            "",
            "Q：不想用 Gmail，公司用 Outlook 怎麼辦？",
            "  A：步驟 3 的 SMTP credential 改填 Outlook 的 smtp.office365.com / port 587，",
            "     User/Password 用 Outlook 的 App Password (或公司 IT 給的應用密碼)。",
            "",
            "=" * 60,
            "如需協助，請把這份設定卡 + n8n 畫面的錯誤訊息截圖一起傳給管理員。",
        ]
        return "\n".join(lines) + "\n"

    @staticmethod
    def _looks_like_email(value):
        return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value or ""))

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
            "risk_theme_labels": raw.get("risk_theme_labels") or [],
            "min_tax_focus": raw.get("min_tax_focus") or "low",
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
