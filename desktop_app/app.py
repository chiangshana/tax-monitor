import tkinter as tk
from tkinter import messagebox, ttk

from desktop_app.input_panel import InputPanel
from desktop_app.results_panel import ResultsPanel
from desktop_app.worker import PipelineWorker


class TaxMonitorDesktopApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Tax Monitor Research Workbench")
        self.geometry("1180x760")
        self.minsize(980, 620)
        self._configure_style()
        self._build()

    def _configure_style(self):
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("TFrame", background="#f5f7fb")
        style.configure("TLabel", background="#f5f7fb", foreground="#18212b")
        style.configure("TButton", padding=8)
        style.configure("TNotebook", background="#f5f7fb")
        style.configure("TNotebook.Tab", padding=(12, 6))

    def _build(self):
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self.input_panel = InputPanel(self, on_run=self._run)
        self.input_panel.grid(row=0, column=0, sticky="nsw")

        self.results_panel = ResultsPanel(self)
        self.results_panel.grid(row=0, column=1, sticky="nsew")

        self.worker = PipelineWorker(
            on_success=lambda result: self.after(0, self._handle_success, result),
            on_error=lambda message: self.after(0, self._handle_error, message),
        )

    def _run(self):
        payload = self.input_panel.get_payload()
        if not payload["keywords"]:
            messagebox.showwarning("Missing keywords", "Please enter at least one search keyword.")
            return
        self.input_panel.set_running(True)
        self.results_panel.set_status("Running research pipeline...")
        self.worker.run(payload)

    def _handle_success(self, result):
        self.input_panel.set_running(False)
        self.results_panel.set_status("Completed")
        self.results_panel.render_result(result)

    def _handle_error(self, message):
        self.input_panel.set_running(False)
        self.results_panel.render_error(message)


def main():
    app = TaxMonitorDesktopApp()
    app.mainloop()


if __name__ == "__main__":
    main()
