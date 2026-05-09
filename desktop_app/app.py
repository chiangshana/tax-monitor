import tkinter as tk
from tkinter import messagebox, ttk

from desktop_app.input_panel import InputPanel
from desktop_app.results_panel import ResultsPanel
from desktop_app.worker import PipelineWorker
from services.runtime_paths import output_dir
from services.storage_service import StorageService


class TaxMonitorDesktopApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Tax Monitor Research Workbench")
        self.geometry("1180x760")
        self.minsize(980, 620)
        self._configure_style()
        self._build()
        self._mark_previous_interrupted_runs()

    LIGHT_THEME = {
        "bg": "#f5f7fb",
        "fg": "#18212b",
        "tab_bg": "#f5f7fb",
        "text_bg": "#ffffff",
        "text_fg": "#18212b",
        "select_bg": "#cfd8dc",
    }
    DARK_THEME = {
        "bg": "#1e1f24",
        "fg": "#e6e9ef",
        "tab_bg": "#1e1f24",
        "text_bg": "#252730",
        "text_fg": "#e6e9ef",
        "select_bg": "#3a3d4a",
    }

    def _configure_style(self):
        self._style = ttk.Style(self)
        if "clam" in self._style.theme_names():
            self._style.theme_use("clam")
        self._style.configure("TButton", padding=8)
        self._style.configure("TNotebook.Tab", padding=(12, 6))
        self.apply_theme(dark=False)

    def apply_theme(self, dark: bool = False):
        palette = self.DARK_THEME if dark else self.LIGHT_THEME
        style = self._style
        style.configure("TFrame", background=palette["bg"])
        style.configure("TLabel", background=palette["bg"], foreground=palette["fg"])
        style.configure("TCheckbutton", background=palette["bg"], foreground=palette["fg"])
        style.configure("TNotebook", background=palette["tab_bg"])
        style.configure("TNotebook.Tab", background=palette["tab_bg"], foreground=palette["fg"])
        style.map("TNotebook.Tab", background=[("selected", palette["select_bg"])])
        style.configure("TCombobox", fieldbackground=palette["text_bg"], foreground=palette["text_fg"])
        self.configure(background=palette["bg"])
        self._apply_text_theme(self, palette)

    def _apply_text_theme(self, widget, palette):
        for child in widget.winfo_children():
            try:
                if isinstance(child, tk.Text):
                    child.configure(
                        background=palette["text_bg"],
                        foreground=palette["text_fg"],
                        insertbackground=palette["text_fg"],
                    )
                elif isinstance(child, tk.Tk) or isinstance(child, ttk.Frame):
                    pass
            except tk.TclError:
                pass
            self._apply_text_theme(child, palette)

    def _build(self):
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self.input_panel = InputPanel(self, on_run=self._run)
        self.input_panel.grid(row=0, column=0, sticky="nsw")

        self.results_panel = ResultsPanel(
            self,
            get_payload=self.input_panel.get_payload,
            on_apply_recommendation=self.input_panel.apply_suggestions,
            on_apply_and_run=self._run,
        )
        self.results_panel.grid(row=0, column=1, sticky="nsew")

        self.worker = PipelineWorker(
            on_success=lambda result: self.after(0, self._handle_success, result),
            on_error=lambda message: self.after(0, self._handle_error, message),
            on_progress=lambda event: self.after(0, self._handle_progress, event),
            on_cancelled=lambda message: self.after(0, self._handle_cancelled, message),
        )
        self.input_panel.bind_stop_handler(self._cancel)

    def _mark_previous_interrupted_runs(self):
        try:
            updated = StorageService().mark_stale_running_runs()
        except Exception:
            updated = 0
        if updated:
            self.results_panel.set_status(f"Recovered {updated} interrupted run(s) from the previous session.")

    def _run(self):
        if hasattr(self, "worker") and self.worker.is_running():
            messagebox.showinfo("Already running", "A research run is already in progress.")
            return
        payload = self.input_panel.get_payload()
        if not payload["keywords"]:
            messagebox.showwarning("Missing keywords", "Please enter at least one search keyword.")
            return
        cleanup = payload.pop("cleanup", {})
        if not self._maybe_cleanup_before_run(cleanup):
            return
        self.input_panel.set_running(True)
        self.results_panel.set_status("Running research pipeline...")
        self.worker.run(payload)

    def _maybe_cleanup_before_run(self, cleanup):
        if not cleanup or not cleanup.get("clear_before_run"):
            return True

        selected = []
        if cleanup.get("documents"):
            selected.append("documents and keyword model")
        if cleanup.get("pipeline_runs"):
            selected.append("run history")
        if cleanup.get("reports"):
            selected.append("generated PPTX/reports")
        if not selected:
            messagebox.showwarning("No cleanup target", "Please select at least one data type to clear, or turn off cleanup.")
            return False

        confirmed = messagebox.askyesno(
            "Confirm cleanup",
            "Before this run, Tax Monitor will clear:\n\n"
            + "\n".join(f"- {item}" for item in selected)
            + "\n\nThis cannot be undone. Continue?",
        )
        if not confirmed:
            return False

        deleted = StorageService().clear_runtime_data(
            documents=bool(cleanup.get("documents")),
            keyword_profiles=bool(cleanup.get("keyword_profiles")),
            pipeline_runs=bool(cleanup.get("pipeline_runs")),
        )
        report_count = self._clear_report_files() if cleanup.get("reports") else 0
        self.results_panel.set_status(
            "Cleaned before run: "
            f"documents={deleted.get('documents', 0)}, "
            f"keyword_profiles={deleted.get('keyword_profiles', 0)}, "
            f"history={deleted.get('pipeline_runs', 0)}, "
            f"reports={report_count}"
        )
        return True

    def _clear_report_files(self):
        reports_dir = output_dir("reports").resolve()
        reports_dir.mkdir(parents=True, exist_ok=True)
        deleted = 0
        for path in reports_dir.iterdir():
            try:
                if path.is_file() and path.resolve().parent == reports_dir:
                    path.unlink()
                    deleted += 1
            except OSError:
                continue
        return deleted

    def _cancel(self):
        if self.worker.is_running():
            self.worker.cancel()
            self.results_panel.set_status("Cancellation requested...")

    def _handle_success(self, result):
        self.input_panel.set_running(False)
        self.results_panel.set_status("Completed")
        self.results_panel.render_result(result)

    def _handle_error(self, message):
        self.input_panel.set_running(False)
        self.results_panel.render_error(message)

    def _handle_cancelled(self, message):
        self.input_panel.set_running(False)
        self.results_panel.set_status(f"Cancelled: {message}")

    def _handle_progress(self, event):
        self.results_panel.update_progress(event)


def main():
    app = TaxMonitorDesktopApp()
    app.mainloop()


if __name__ == "__main__":
    main()
