from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from routers.document import router as document_router
from routers.analysis import router as analysis_router
from routers.pipeline import router as pipeline_router

BASE_DIR = Path(__file__).resolve().parent


app = FastAPI(
    title="Tax Monitor API",
    description="跨國法令與稅務風險監測原型",
    version="1.0.0"
)

app.include_router(document_router, prefix="/api/document", tags=["document"])
app.include_router(analysis_router, prefix="/api/analysis", tags=["analysis"])
app.include_router(pipeline_router, prefix="/api/pipeline", tags=["pipeline"])


@app.get("/", summary="Health check")
async def root():
    return {"message": "Tax Monitor API is running"}


@app.get("/ui", include_in_schema=False)
async def workbench():
    return FileResponse(BASE_DIR / "ui" / "index.html")


@app.get("/ui/app.js", include_in_schema=False)
async def workbench_script():
    return FileResponse(BASE_DIR / "ui" / "app.js", media_type="application/javascript")


@app.get("/ui/styles.css", include_in_schema=False)
async def workbench_styles():
    return FileResponse(BASE_DIR / "ui" / "styles.css", media_type="text/css")
