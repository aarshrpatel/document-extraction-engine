import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from extraction_engine.api.deps import get_db, get_pipeline
from extraction_engine.api.responses import (
    EvalRunResponse,
    HealthResponse,
    JobDetailResponse,
    JobListResponse,
    JobResponse,
)
from extraction_engine.db.models import DocumentStatus
from extraction_engine.db.repository import (
    DocumentRepository,
    EvalRunRepository,
    ExtractionResultRepository,
)
from extraction_engine.schemas.registry import list_doc_types
from extraction_engine.worker.tasks import extract_document

router = APIRouter(prefix="/api/v1")


@router.get("/health", response_model=HealthResponse)
def health_check():
    return HealthResponse()


@router.post("/extract", response_model=JobResponse)
async def create_extraction_job(
    file: UploadFile = File(...),
    doc_type: str = Query(..., description="Document type (e.g. invoice)"),
    db: Session = Depends(get_db),
):
    """Upload a document and start extraction."""
    if doc_type not in list_doc_types():
        raise HTTPException(
            status_code=400,
            detail=f"Unknown doc_type: {doc_type}. Available: {list_doc_types()}",
        )

    # Validate file type
    suffix = Path(file.filename or "unknown").suffix.lower()
    if suffix not in (".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".tif"):
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}")

    # Save uploaded file
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)

    file_bytes = await file.read()
    file_path = upload_dir / file.filename
    file_path.write_bytes(file_bytes)

    # Create DB record
    doc_repo = DocumentRepository(db)
    doc = doc_repo.create(
        filename=file.filename,
        doc_type=doc_type,
        file_path=str(file_path),
    )

    # Submit Celery task (async processing)
    extract_document.delay(doc.id, str(file_path), doc_type)

    return JobResponse(
        job_id=doc.id,
        status=doc.status.value,
        filename=doc.filename,
        doc_type=doc.doc_type,
        created_at=doc.created_at,
    )


@router.post("/extract/sync", response_model=JobDetailResponse)
async def extract_sync(
    file: UploadFile = File(...),
    doc_type: str = Query(..., description="Document type (e.g. invoice)"),
    db: Session = Depends(get_db),
):
    """Upload and extract synchronously (no Celery needed). Good for testing."""
    if doc_type not in list_doc_types():
        raise HTTPException(status_code=400, detail=f"Unknown doc_type: {doc_type}")

    suffix = Path(file.filename or "unknown").suffix.lower()
    if suffix not in (".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".tif"):
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}")

    file_bytes = await file.read()

    # Create DB record
    doc_repo = DocumentRepository(db)
    result_repo = ExtractionResultRepository(db)
    doc = doc_repo.create(filename=file.filename, doc_type=doc_type)
    doc_repo.update_status(doc.id, DocumentStatus.PROCESSING)

    try:
        pipeline = get_pipeline()
        pipeline_result = pipeline.run_from_bytes(file_bytes, file.filename, doc_type)
        extracted_data = pipeline_result.extraction.model_dump(mode="json")

        result_repo.create(
            document_id=doc.id,
            extracted_data=extracted_data,
            ocr_text=pipeline_result.ocr_result.text,
            ocr_confidence=float(pipeline_result.ocr_result.confidence),
            model_version=pipeline_result.extraction.metadata.model_version
            if pipeline_result.extraction.metadata else None,
            processing_time_ms=pipeline_result.total_time_ms,
        )
        doc_repo.update_status(doc.id, DocumentStatus.COMPLETED)

        return JobDetailResponse(
            job_id=doc.id,
            status="completed",
            filename=doc.filename,
            doc_type=doc.doc_type,
            created_at=doc.created_at,
            extracted_data=extracted_data,
            processing_time_ms=pipeline_result.total_time_ms,
            ocr_confidence=float(pipeline_result.ocr_result.confidence),
        )
    except Exception as e:
        doc_repo.update_status(doc.id, DocumentStatus.FAILED)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}", response_model=JobDetailResponse)
def get_job(job_id: int, db: Session = Depends(get_db)):
    """Get extraction job status and results."""
    doc_repo = DocumentRepository(db)
    result_repo = ExtractionResultRepository(db)

    doc = doc_repo.get(job_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Job not found")

    extraction = result_repo.get_by_document(job_id)

    return JobDetailResponse(
        job_id=doc.id,
        status=doc.status.value,
        filename=doc.filename,
        doc_type=doc.doc_type,
        created_at=doc.created_at,
        extracted_data=extraction.extracted_data if extraction else None,
        processing_time_ms=extraction.processing_time_ms if extraction else None,
        ocr_confidence=extraction.ocr_confidence if extraction else None,
    )


@router.get("/jobs", response_model=JobListResponse)
def list_jobs(
    limit: int = Query(20, ge=1, le=100),
    doc_type: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """List recent extraction jobs."""
    doc_repo = DocumentRepository(db)
    docs = doc_repo.list_recent(limit=limit, doc_type=doc_type)

    jobs = [
        JobResponse(
            job_id=doc.id,
            status=doc.status.value,
            filename=doc.filename,
            doc_type=doc.doc_type,
            created_at=doc.created_at,
        )
        for doc in docs
    ]

    return JobListResponse(jobs=jobs, total=len(jobs))


@router.post("/eval/run", response_model=EvalRunResponse)
def trigger_eval_run(
    doc_type: str = Query(...),
    db: Session = Depends(get_db),
):
    """Trigger an evaluation run against ground truth data."""
    from eval.runner import generate_report, run_eval_offline

    if doc_type not in list_doc_types():
        raise HTTPException(
            status_code=400,
            detail=f"Unknown doc_type: {doc_type}",
        )

    scores = run_eval_offline(doc_type)
    report = generate_report(scores, doc_type)

    eval_repo = EvalRunRepository(db)
    run = eval_repo.create(
        doc_type=doc_type,
        total_documents=len(scores),
        report=report,
    )
    eval_repo.save_field_results(run.id, scores)

    return EvalRunResponse(
        id=run.id,
        doc_type=run.doc_type,
        total_documents=run.total_documents,
        avg_field_accuracy=run.avg_field_accuracy,
        avg_levenshtein_score=run.avg_levenshtein_score,
        report=run.report_json,
        run_timestamp=run.run_timestamp,
    )


@router.get("/eval/runs/{run_id}", response_model=EvalRunResponse)
def get_eval_run(run_id: int, db: Session = Depends(get_db)):
    """Get evaluation run results."""
    eval_repo = EvalRunRepository(db)
    run = eval_repo.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Eval run not found")

    return EvalRunResponse(
        id=run.id,
        doc_type=run.doc_type,
        total_documents=run.total_documents,
        avg_field_accuracy=run.avg_field_accuracy,
        avg_levenshtein_score=run.avg_levenshtein_score,
        report=run.report_json,
        run_timestamp=run.run_timestamp,
    )
