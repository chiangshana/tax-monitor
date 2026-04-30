import asyncio
import threading

from services.pipeline_service import PipelineService


class PipelineWorker:
    def __init__(self, on_success, on_error):
        self.on_success = on_success
        self.on_error = on_error

    def run(self, payload):
        thread = threading.Thread(target=self._run_thread, args=(payload,), daemon=True)
        thread.start()

    def _run_thread(self, payload):
        try:
            result = asyncio.run(self._run_pipeline(payload))
            self.on_success(result)
        except Exception as exc:
            self.on_error(str(exc))

    async def _run_pipeline(self, payload):
        service = PipelineService()
        return await service.search_ingest_and_train(**payload)
