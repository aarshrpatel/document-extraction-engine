import json

import structlog
from celery import Task

from extraction_engine.config import get_settings
from extraction_engine.db.models import DocumentStatus
from extraction_engine.db.repository import DocumentRepository, ExtractionResultRepository
from extraction_engine.db.session import get_session_factory
from extraction_engine.pipeline.pipeline import ExtractionPipeline
from extraction_engine.worker.celery_app import celery_app

logger = structlog.get_logger()


class ExtractionTask(Task):
    """Base task with shared resources."""

    _pipeline = None
    _session_factory = None

    @property
    def pipeline(self) -> ExtractionPipeline:
        if self._pipeline is None:
            self._pipeline = ExtractionPipeline(get_settings())
        return self._pipeline

    @property
    def session_factory(self):
        if self._session_factory is None:
            self._session_factory = get_session_factory(get_settings())
        return self._session_factory


@celery_app.task(
    bind=True,
    base=ExtractionTask,
    name="extraction_engine.extract_document",
    max_retries=3,
    default_retry_delay=30,
)
def extract_document(self, document_id: int, file_path: str, doc_type: str) -> dict:
    """Extract structured data from a document.

    This task is idempotent - re-running will create a new extraction result.
    """
    session = self.session_factory()
    doc_repo = DocumentRepository(session)
    result_repo = ExtractionResultRepository(session)

    try:
        doc_repo.update_status(document_id, DocumentStatus.PROCESSING)

        pipeline_result = self.pipeline.run(file_path, doc_type)

        extracted_data = pipeline_result.extraction.model_dump(mode="json")
        result_repo.create(
            document_id=document_id,
            extracted_data=extracted_data,
            ocr_text=pipeline_result.ocr_result.text,
            ocr_confidence=float(pipeline_result.ocr_result.confidence),
            model_version=pipeline_result.extraction.metadata.model_version
            if pipeline_result.extraction.metadata
            else None,
            processing_time_ms=pipeline_result.total_time_ms,
        )

        doc_repo.update_status(document_id, DocumentStatus.COMPLETED)

        logger.info("extraction_task_complete", document_id=document_id)
        return extracted_data

    except Exception as exc:
        doc_repo.update_status(document_id, DocumentStatus.FAILED)
        logger.error("extraction_task_failed", document_id=document_id, error=str(exc))
        raise self.retry(exc=exc) if self.request.retries < self.max_retries else exc
    finally:
        session.close()
