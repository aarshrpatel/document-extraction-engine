from decimal import Decimal
from abc import ABC, abstractmethod

from PIL import Image

from extraction_engine.config import Settings


class OCRResult:
    """Structured OCR output."""

    def __init__(self, text: str, confidence: Decimal, pages: int):
        self.text = text
        self.confidence = confidence
        self.pages = pages

    def __repr__(self) -> str:
        return (
            f"OCRResult(pages={self.pages}, confidence={self.confidence}, "
            f"text_length={len(self.text)})"
        )


class BaseOCRClient(ABC):
    """Abstract base for OCR clients."""

    @abstractmethod
    def analyze_document(self, file_bytes: bytes) -> OCRResult:
        ...


class TesseractOCRClient(BaseOCRClient):
    """Local OCR using Tesseract (pytesseract). Free, no API key needed."""

    def analyze_document(self, file_bytes: bytes) -> OCRResult:
        import io
        import pytesseract

        img = Image.open(io.BytesIO(file_bytes))
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)

        # Build full text from words
        words = []
        confidences = []
        for i, text in enumerate(data["text"]):
            text = text.strip()
            if text:
                words.append(text)
                conf = data["conf"][i]
                if isinstance(conf, (int, float)) and conf >= 0:
                    confidences.append(conf / 100.0)  # Tesseract gives 0-100

        full_text = " ".join(words)
        avg_confidence = Decimal("0")
        if confidences:
            avg_confidence = Decimal(str(sum(confidences) / len(confidences))).quantize(
                Decimal("0.001")
            )

        return OCRResult(text=full_text, confidence=avg_confidence, pages=1)


class AzureOCRClient(BaseOCRClient):
    """Client for Azure AI Document Intelligence. Higher accuracy on degraded scans."""

    def __init__(self, settings: Settings):
        from azure.ai.documentintelligence import DocumentIntelligenceClient
        from azure.core.credentials import AzureKeyCredential

        self.client = DocumentIntelligenceClient(
            endpoint=settings.azure_doc_intel_endpoint,
            credential=AzureKeyCredential(settings.azure_doc_intel_key),
        )

    def analyze_document(self, file_bytes: bytes) -> OCRResult:
        from azure.ai.documentintelligence.models import (
            AnalyzeDocumentRequest,
            DocumentAnalysisFeature,
        )

        poller = self.client.begin_analyze_document(
            model_id="prebuilt-layout",
            body=AnalyzeDocumentRequest(bytes_source=file_bytes),
            features=[DocumentAnalysisFeature.KEY_VALUE_PAIRS],
        )
        result = poller.result()

        text = result.content or ""

        confidences = []
        page_count = 0
        if result.pages:
            page_count = len(result.pages)
            for page in result.pages:
                if page.words:
                    for word in page.words:
                        if word.confidence is not None:
                            confidences.append(word.confidence)

        avg_confidence = Decimal("0")
        if confidences:
            avg_confidence = Decimal(str(sum(confidences) / len(confidences))).quantize(
                Decimal("0.001")
            )

        return OCRResult(text=text, confidence=avg_confidence, pages=page_count)


def create_ocr_client(settings: Settings) -> BaseOCRClient:
    """Factory: returns Azure client if configured, otherwise Tesseract."""
    if settings.azure_doc_intel_endpoint and settings.azure_doc_intel_key:
        return AzureOCRClient(settings)
    return TesseractOCRClient()
