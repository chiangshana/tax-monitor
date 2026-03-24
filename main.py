from fastapi import FastAPI
from routers.document import router as document_router
from routers.analysis import router as analysis_router


app = FastAPI(
    title="Tax Monitor API",
    description="跨國法令與稅務風險監測原型",
    version="1.0.0"
)

app.include_router(document_router, prefix="/api/document", tags=["document"])
app.include_router(analysis_router, prefix="/api/analysis", tags=["analysis"])


@app.get("/", summary="Health check")
async def root():
    return {"message": "Tax Monitor API is running"}
