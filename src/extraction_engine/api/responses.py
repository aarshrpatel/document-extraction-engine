from datetime import datetime

from pydantic import BaseModel


class JobResponse(BaseModel):
    job_id: int
    status: str
    filename: str
    doc_type: str
    created_at: datetime


class JobDetailResponse(JobResponse):
    extracted_data: dict | None = None
    processing_time_ms: int | None = None
    ocr_confidence: float | None = None


class JobListResponse(BaseModel):
    jobs: list[JobResponse]
    total: int


class EvalRunResponse(BaseModel):
    id: int
    doc_type: str
    total_documents: int
    avg_field_accuracy: float | None
    avg_levenshtein_score: float | None
    report: dict | None = None
    run_timestamp: datetime


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
