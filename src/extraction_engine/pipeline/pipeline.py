import time
from pathlib import Path

import structlog

from extraction_engine.config import Settings
from extraction_engine.extraction.extractor import Extractor
from extraction_engine.preprocessing.image import image_to_base64, image_to_bytes, preprocess_image
from extraction_engine.preprocessing.loader import load_document, load_document_from_bytes
from extraction_engine.preprocessing.ocr import OCRResult, create_ocr_client
from extraction_engine.schemas.invoice import InvoiceSchema
from extraction_engine.validation.confidence import compute_invoice_confidence
from extraction_engine.validation.validators import validate_invoice

logger = structlog.get_logger()


class PipelineResult:
    """Complete result from the extraction pipeline."""

    def __init__(
        self,
        extraction: BaseExtractionResult,
        ocr_result: OCRResult,
        validation_warnings: list[str],
        total_time_ms: int,
    ):
        self.extraction = extraction
        self.ocr_result = ocr_result
        self.validation_warnings = validation_warnings
        self.total_time_ms = total_time_ms


class ExtractionPipeline:
    """Orchestrates: load -> preprocess -> OCR -> extract -> validate."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.ocr_client = create_ocr_client(settings)
        self.extractor = Extractor(settings)

    def run(
        self,
        file_path: str | Path,
        doc_type: str,
    ) -> PipelineResult:
        """Run the full extraction pipeline on a file."""
        start_time = time.time()
        filename = Path(file_path).name

        logger.info("pipeline_start", filename=filename, doc_type=doc_type)

        # 1. Load document
        pages = load_document(file_path)
        logger.info("document_loaded", pages=len(pages))

        return self._process_pages(pages, filename, doc_type, start_time)

    def run_from_bytes(
        self,
        file_bytes: bytes,
        filename: str,
        doc_type: str,
    ) -> PipelineResult:
        """Run the full extraction pipeline on file bytes."""
        start_time = time.time()

        logger.info("pipeline_start", filename=filename, doc_type=doc_type)

        pages = load_document_from_bytes(file_bytes, filename)
        logger.info("document_loaded", pages=len(pages))

        return self._process_pages(pages, filename, doc_type, start_time)

    def _process_pages(
        self,
        pages: list,
        filename: str,
        doc_type: str,
        start_time: float,
    ) -> PipelineResult:
        # 2. Preprocess first page (multi-page extraction is future work)
        img, page_num = pages[0]
        img = preprocess_image(img)

        # 3. OCR via Azure
        img_bytes = image_to_bytes(img)
        ocr_result = self.ocr_client.analyze_document(img_bytes)
        logger.info(
            "ocr_complete",
            confidence=str(ocr_result.confidence),
            text_length=len(ocr_result.text),
        )

        # 4. Extract via Claude VLM
        image_b64 = image_to_base64(img)
        extraction = self.extractor.extract(
            doc_type=doc_type,
            image_b64=image_b64,
            ocr_text=ocr_result.text,
            source_filename=filename,
        )

        # 5. Update metadata
        total_time = int((time.time() - start_time) * 1000)
        if extraction.metadata:
            extraction.metadata.ocr_confidence = ocr_result.confidence
            extraction.metadata.page_count = len(pages)

        # 6. Run validation and confidence scoring
        validation_warnings: list[str] = []
        if doc_type == "invoice" and isinstance(extraction, InvoiceSchema):
            val_result = validate_invoice(extraction)
            validation_warnings = val_result.warnings

            confidences = compute_invoice_confidence(extraction, ocr_result.text)
            if extraction.metadata:
                extraction.metadata.field_confidences = confidences

        logger.info(
            "pipeline_complete",
            total_time_ms=total_time,
            warnings=len(validation_warnings),
        )

        return PipelineResult(
            extraction=extraction,
            ocr_result=ocr_result,
            validation_warnings=validation_warnings,
            total_time_ms=total_time,
        )
