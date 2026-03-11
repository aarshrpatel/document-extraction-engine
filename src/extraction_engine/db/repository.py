from sqlalchemy.orm import Session

from extraction_engine.db.models import (
    Document,
    DocumentStatus,
    EvalResult,
    EvalRun,
    ExtractionResult,
)


class DocumentRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, filename: str, doc_type: str, file_path: str | None = None) -> Document:
        doc = Document(filename=filename, doc_type=doc_type, file_path=file_path)
        self.session.add(doc)
        self.session.commit()
        self.session.refresh(doc)
        return doc

    def get(self, doc_id: int) -> Document | None:
        return self.session.query(Document).filter(Document.id == doc_id).first()

    def update_status(self, doc_id: int, status: DocumentStatus) -> None:
        self.session.query(Document).filter(Document.id == doc_id).update({"status": status})
        self.session.commit()

    def list_recent(self, limit: int = 20, doc_type: str | None = None) -> list[Document]:
        q = self.session.query(Document)
        if doc_type:
            q = q.filter(Document.doc_type == doc_type)
        return q.order_by(Document.created_at.desc()).limit(limit).all()


class ExtractionResultRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        document_id: int,
        extracted_data: dict,
        raw_llm_response: str | None = None,
        ocr_text: str | None = None,
        ocr_confidence: float | None = None,
        model_version: str | None = None,
        processing_time_ms: int | None = None,
    ) -> ExtractionResult:
        result = ExtractionResult(
            document_id=document_id,
            extracted_data=extracted_data,
            raw_llm_response=raw_llm_response,
            ocr_text=ocr_text,
            ocr_confidence=ocr_confidence,
            model_version=model_version,
            processing_time_ms=processing_time_ms,
        )
        self.session.add(result)
        self.session.commit()
        self.session.refresh(result)
        return result

    def get_by_document(self, document_id: int) -> ExtractionResult | None:
        return (
            self.session.query(ExtractionResult)
            .filter(ExtractionResult.document_id == document_id)
            .order_by(ExtractionResult.created_at.desc())
            .first()
        )


class EvalRunRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, doc_type: str, total_documents: int, report: dict) -> EvalRun:
        run = EvalRun(
            doc_type=doc_type,
            total_documents=total_documents,
            avg_field_accuracy=report.get("avg_field_accuracy"),
            avg_levenshtein_score=report.get("avg_similarity"),
            report_json=report,
        )
        self.session.add(run)
        self.session.commit()
        self.session.refresh(run)
        return run

    def get(self, run_id: int) -> EvalRun | None:
        return self.session.query(EvalRun).filter(EvalRun.id == run_id).first()

    def save_field_results(self, eval_run_id: int, scores: list) -> None:
        for doc_score in scores:
            for fs in doc_score.field_scores:
                result = EvalResult(
                    eval_run_id=eval_run_id,
                    document_id=doc_score.document_id,
                    field_name=fs.field_name,
                    expected_value=fs.expected,
                    extracted_value=fs.extracted,
                    is_correct=fs.is_correct,
                    levenshtein_distance=fs.levenshtein_dist,
                    similarity_score=fs.similarity,
                )
                self.session.add(result)
        self.session.commit()
