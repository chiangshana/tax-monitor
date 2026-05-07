import asyncio
import threading

from services.pipeline_service import PipelineCancelled, PipelineService


class PipelineWorker:
    def __init__(self, on_success, on_error, on_progress=None, on_cancelled=None):
        self.on_success = on_success
        self.on_error = on_error
        self.on_progress = on_progress
        self.on_cancelled = on_cancelled
        self.cancel_event = threading.Event()
        self._active = False

    def run(self, payload):
        self.cancel_event.clear()
        self._active = True
        thread = threading.Thread(target=self._run_thread, args=(payload,), daemon=True)
        thread.start()

    def cancel(self):
        if self._active:
            self.cancel_event.set()

    def is_running(self) -> bool:
        return self._active

    def _run_thread(self, payload):
        try:
            result = asyncio.run(self._run_pipeline(payload))
            self._active = False
            self.on_success(result)
        except PipelineCancelled as exc:
            self._active = False
            if self.on_cancelled:
                self.on_cancelled(str(exc))
            else:
                self.on_error(str(exc))
        except Exception as exc:
            self._active = False
            self.on_error(str(exc))

    async def _run_pipeline(self, payload):
        service = PipelineService()
        return await service.search_ingest_and_train(
            progress_callback=self.on_progress,
            cancel_event=self.cancel_event,
            **payload,
        )
