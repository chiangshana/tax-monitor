import asyncio
import json
import os
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
EXAMPLE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        return


def start_example_server():
    handler = partial(QuietHandler, directory=str(EXAMPLE_DIR))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


async def run_smoke_test():
    from services.pipeline_service import PipelineService

    server = start_example_server()
    port = server.server_address[1]
    sample_url = f"http://127.0.0.1:{port}/sample_tax_update.html"

    try:
        service = PipelineService()
        result = await service.run_pipeline(
            keywords=["cross-border tax", "filing obligation", "penalty"],
            user_prompt="verify one-click pipeline from search result to pptx report",
            mode="manual",
            date_range="3m",
            max_results=1,
            country="TW",
            industry="technology",
            source_name="local_smoke_test",
            candidate_urls=[sample_url],
            use_ai_query_expansion=False,
            target_language="zh",
            analysis_mode="translate_first",
            provider=os.getenv("TAX_MONITOR_SMOKE_PROVIDER", "ollama"),
            model_name=os.getenv("TAX_MONITOR_SMOKE_MODEL", "qwen3:8b"),
            report_format="pptx",
            max_documents_to_process=1,
            high_risk_only=False,
        )
    finally:
        server.shutdown()

    print(json.dumps(result, ensure_ascii=False, indent=2))
    pptx_paths = [
        item.get("report_file_path")
        for item in result.get("documents", [])
        if item.get("report_file_path")
    ]
    if not pptx_paths:
        raise SystemExit("Smoke test failed: no PPTX file was generated.")
    print("\nGenerated PPTX:")
    for path in pptx_paths:
        print(path)


if __name__ == "__main__":
    asyncio.run(run_smoke_test())
