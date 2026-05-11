import os
import queue
import shutil
import subprocess
import threading
import tkinter as tk
import webbrowser
from tkinter import messagebox, ttk

import requests

from desktop_app.input_panel import PROVIDER_MODEL_PRESETS


class LLMSetupPanel(ttk.Frame):
    """Ollama helper for non-technical desktop users."""

    def __init__(self, master):
        super().__init__(master, padding=10)
        self._queue = queue.Queue()
        self._busy = False
        self._build()
        self.after(300, self.check_ollama)

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(4, weight=1)

        header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        header.columnconfigure(1, weight=1)
        ttk.Label(header, text="Local LLM setup").grid(row=0, column=0, sticky="w")
        ttk.Button(header, text="Check Ollama", command=self.check_ollama).grid(row=0, column=2, padx=(8, 0))

        self.status = tk.StringVar(value="Checking Ollama...")
        ttk.Label(self, textvariable=self.status).grid(row=1, column=0, sticky="ew", pady=(0, 8))

        controls = ttk.Frame(self)
        controls.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        controls.columnconfigure(1, weight=1)

        ttk.Label(controls, text="Install local model").grid(row=0, column=0, sticky="w")
        self.model_name = tk.StringVar(value="qwen3:8b")
        self.model_box = ttk.Combobox(
            controls,
            textvariable=self.model_name,
            values=PROVIDER_MODEL_PRESETS.get("ollama", []),
            state="normal",
        )
        self.model_box.grid(row=0, column=1, sticky="ew", padx=(8, 8))
        ttk.Button(controls, text="Pull model", command=self.pull_selected_model).grid(row=0, column=2)
        ttk.Button(
            controls,
            text="One-click setup selected model",
            command=self.setup_selected_model,
        ).grid(row=1, column=1, columnspan=2, sticky="ew", padx=(8, 0), pady=(6, 0))

        quick = ttk.Frame(self)
        quick.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(quick, text="Quick Qwen install").pack(side="left")
        ttk.Button(
            quick,
            text="Qwen 3 8B",
            command=lambda: self.setup_quick_model("qwen3:8b"),
        ).pack(side="left", padx=(8, 0))
        ttk.Button(
            quick,
            text="Qwen 3.5 9B",
            command=lambda: self.setup_quick_model("qwen3.5:9b"),
        ).pack(side="left", padx=(8, 0))
        ttk.Button(
            quick,
            text="Qwen 3.5 27B",
            command=lambda: self.setup_quick_model("qwen3.5:27b"),
        ).pack(side="left", padx=(8, 0))

        actions = ttk.Frame(self)
        actions.grid(row=5, column=0, sticky="ew", pady=(8, 0))
        ttk.Button(actions, text="Install Ollama with winget", command=self.install_ollama_with_winget).pack(side="left")
        ttk.Button(actions, text="Open Ollama download page", command=self.open_ollama_download).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="Refresh installed models", command=self.list_models).pack(side="left", padx=(8, 0))

        self.output = tk.Text(self, wrap="word", height=18)
        scroll = ttk.Scrollbar(self, command=self.output.yview)
        self.output.configure(yscrollcommand=scroll.set)
        self.output.grid(row=4, column=0, sticky="nsew")
        scroll.grid(row=4, column=1, sticky="ns")

        self._write(
            "Cloud models such as OpenAI, Gemini, Claude, and Qwen Cloud are not installed locally. "
            "They use API keys in the left panel. This tab installs Ollama models only.\n\n"
            "For non-technical users, choose a model and press `One-click setup selected model`. "
            "Tax Monitor will try to install or locate Ollama, start the local service, then pull the model.\n\n"
        )

    def check_ollama(self):
        self._check_ollama_status(refresh_list=True)

    def _check_ollama_status(self, refresh_list=False):
        path = self._ollama_executable()
        if not path:
            self.status.set("Ollama is not installed or not on PATH.")
            self._write("Ollama was not found. Install it first, then pull a model such as qwen3:8b or qwen3.5:9b.\n")
            return

        server_ok = False
        try:
            response = requests.get("http://127.0.0.1:11434/api/tags", timeout=2)
            server_ok = response.ok
        except requests.RequestException:
            server_ok = False

        if server_ok:
            self.status.set(f"Ollama is ready: {path}")
            if refresh_list:
                self.list_models()
        else:
            self.status.set("Ollama is installed, but the local server is not responding.")
            self._write(
                "Ollama command exists, but http://127.0.0.1:11434 is not ready. "
                "Open Ollama once from the Start Menu, or run: ollama serve\n"
            )

    def list_models(self):
        ollama = self._ollama_executable() or "ollama"
        self._run_command("ollama list", [ollama, "list"])

    def pull_selected_model(self):
        model = (self.model_name.get() or "").strip()
        if not model:
            messagebox.showwarning("Missing model", "Please choose or type an Ollama model name.")
            return
        ollama = self._ollama_executable() or "ollama"
        self._run_command(f"ollama pull {model}", [ollama, "pull", model])

    def pull_quick_model(self, model: str):
        self.model_name.set(model)
        ollama = self._ollama_executable() or "ollama"
        self._run_command(f"ollama pull {model}", [ollama, "pull", model])

    def setup_selected_model(self):
        model = (self.model_name.get() or "").strip()
        if not model:
            messagebox.showwarning("Missing model", "Please choose or type an Ollama model name.")
            return
        self._run_model_setup(model)

    def setup_quick_model(self, model: str):
        self.model_name.set(model)
        self._run_model_setup(model)

    def install_ollama_with_winget(self):
        if not shutil.which("winget"):
            messagebox.showinfo(
                "winget not found",
                "Windows Package Manager was not found. Use the download page instead.",
            )
            return
        self._run_command(
            "winget install Ollama.Ollama",
            ["winget", "install", "--id", "Ollama.Ollama", "-e"],
        )

    def open_ollama_download(self):
        webbrowser.open("https://ollama.com/download")

    def _ollama_executable(self):
        path = shutil.which("ollama")
        if path:
            return path
        candidates = [
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", "ollama.exe"),
            os.path.join(os.environ.get("ProgramFiles", ""), "Ollama", "ollama.exe"),
            os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Ollama", "ollama.exe"),
        ]
        return next((candidate for candidate in candidates if candidate and os.path.exists(candidate)), None)

    def _ollama_server_ready(self):
        try:
            response = requests.get("http://127.0.0.1:11434/api/tags", timeout=2)
            return response.ok
        except requests.RequestException:
            return False

    def _run_model_setup(self, model: str):
        if self._busy:
            messagebox.showinfo("Busy", "Another LLM setup task is still running.")
            return
        self._busy = True
        self._write(f"\n$ one-click setup local model: {model}\n")
        thread = threading.Thread(target=self._model_setup_thread, args=(model,), daemon=True)
        thread.start()
        self.after(100, self._drain_queue)

    def _model_setup_thread(self, model: str):
        try:
            ollama = self._ollama_executable()
            if not ollama:
                if not shutil.which("winget"):
                    self._queue.put(
                        "Ollama was not found, and winget is not available. "
                        "Please use `Open Ollama download page`, install Ollama, then run setup again.\n"
                    )
                    return
                self._queue.put("Ollama was not found. Installing Ollama with winget...\n")
                self._run_subprocess(
                    [
                        "winget",
                        "install",
                        "--id",
                        "Ollama.Ollama",
                        "-e",
                        "--accept-source-agreements",
                        "--accept-package-agreements",
                    ]
                )
                ollama = self._ollama_executable()
                if not ollama:
                    self._queue.put(
                        "Ollama install command finished, but Tax Monitor cannot find ollama.exe yet. "
                        "Please reopen Tax Monitor or Windows, then press setup again.\n"
                    )
                    return

            if not self._ollama_server_ready():
                self._queue.put("Starting Ollama local service...\n")
                creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                subprocess.Popen(
                    [ollama, "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=creationflags,
                )
                for _ in range(30):
                    if self._ollama_server_ready():
                        break
                    threading.Event().wait(1)
                if not self._ollama_server_ready():
                    self._queue.put(
                        "Ollama is installed, but the local service did not become ready. "
                        "Open Ollama once from the Start Menu, then press setup again.\n"
                    )
                    return

            self._queue.put(f"Pulling local model: {model}\n")
            self._run_subprocess([ollama, "pull", model])
            self._queue.put(f"\nLocal LLM is ready: {model}\n")
        except Exception as exc:
            self._queue.put(f"\nOne-click setup failed: {exc}\n")
        finally:
            self._queue.put(None)

    def _run_subprocess(self, command):
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        proc = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creationflags,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            self._queue.put(line)
        code = proc.wait()
        if code != 0:
            raise RuntimeError(f"Command failed with exit code {code}: {' '.join(command)}")

    def _run_command(self, title, command):
        if self._busy:
            messagebox.showinfo("Busy", "Another LLM setup task is still running.")
            return
        if not shutil.which(command[0]):
            self._write(f"{command[0]} was not found on PATH.\n")
            return

        self._busy = True
        self._write(f"\n$ {title}\n")
        thread = threading.Thread(target=self._command_thread, args=(command,), daemon=True)
        thread.start()
        self.after(100, self._drain_queue)

    def _command_thread(self, command):
        try:
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            proc = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=creationflags,
            )
            assert proc.stdout is not None
            for line in proc.stdout:
                self._queue.put(line)
            code = proc.wait()
            self._queue.put(f"\nCommand finished with exit code {code}.\n")
        except Exception as exc:
            self._queue.put(f"\nCommand failed: {exc}\n")
        finally:
            self._queue.put(None)

    def _drain_queue(self):
        while True:
            try:
                item = self._queue.get_nowait()
            except queue.Empty:
                break
            if item is None:
                self._busy = False
                self._check_ollama_status(refresh_list=False)
                return
            self._write(item)
        self.after(100, self._drain_queue)

    def _write(self, text):
        self.output.configure(state="normal")
        self.output.insert("end", text)
        self.output.see("end")
        self.output.configure(state="disabled")
