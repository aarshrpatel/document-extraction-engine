from fastapi import FastAPI

from extraction_engine.api.routes import router

app = FastAPI(
    title="Document Extraction Engine",
    description="Eval-first document extraction using OCR + VLM two-pass approach",
    version="0.1.0",
)

app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("extraction_engine.main:app", host="0.0.0.0", port=8000, reload=True)
