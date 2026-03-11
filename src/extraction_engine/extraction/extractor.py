import json
import time

import anthropic
import structlog
from pydantic import ValidationError

from extraction_engine.config import Settings
from extraction_engine.extraction.prompts import (
    SYSTEM_PROMPT,
    build_correction_prompt,
    build_extraction_prompt,
)
from extraction_engine.preprocessing.image import get_media_type, image_to_base64
from extraction_engine.schemas.base import BaseExtractionResult, ExtractionMetadata
from extraction_engine.schemas.registry import get_schema

logger = structlog.get_logger()


class ExtractionError(Exception):
    """Raised when extraction fails after all retries."""

    pass


class Extractor:
    """Extracts structured data from documents using Claude VLM."""

    def __init__(self, settings: Settings):
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.anthropic_model
        self.max_tokens = settings.anthropic_max_tokens
        self.max_retries = settings.max_extraction_retries

    def extract(
        self,
        doc_type: str,
        image_b64: str,
        ocr_text: str,
        source_filename: str,
        image_format: str = "PNG",
    ) -> BaseExtractionResult:
        """Extract structured data from a document image.

        Args:
            doc_type: Document type (e.g. "invoice")
            image_b64: Base64-encoded image
            ocr_text: OCR text from Azure Document Intelligence
            source_filename: Original filename
            image_format: Image format (PNG, JPEG)

        Returns:
            Validated Pydantic model with extracted data
        """
        schema_cls = get_schema(doc_type)
        extraction_prompt = build_extraction_prompt(doc_type, ocr_text)
        media_type = get_media_type(image_format)

        start_time = time.time()

        # Initial extraction
        raw_response = self._call_claude(image_b64, media_type, extraction_prompt)
        parsed_json = self._parse_json(raw_response)

        # Inject required base fields
        parsed_json["source_filename"] = source_filename
        parsed_json["doc_type"] = doc_type

        # Try to validate, retry on failure
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                # Use strict=False since JSON from Claude has strings for Decimal/date
                result = schema_cls.model_validate(parsed_json, strict=False)
                processing_time = int((time.time() - start_time) * 1000)
                result.metadata = ExtractionMetadata(
                    model_version=self.model,
                    processing_time_ms=processing_time,
                    page_count=1,
                )
                logger.info(
                    "extraction_success",
                    doc_type=doc_type,
                    attempt=attempt + 1,
                    processing_time_ms=processing_time,
                )
                return result
            except ValidationError as e:
                last_error = e
                if attempt < self.max_retries:
                    logger.warning(
                        "extraction_validation_failed",
                        attempt=attempt + 1,
                        errors=str(e),
                    )
                    correction_prompt = build_correction_prompt(
                        errors=str(e),
                        previous_output=json.dumps(parsed_json, default=str),
                    )
                    raw_response = self._call_claude(
                        image_b64, media_type, correction_prompt
                    )
                    parsed_json = self._parse_json(raw_response)
                    parsed_json["source_filename"] = source_filename
                    parsed_json["doc_type"] = doc_type

        raise ExtractionError(
            f"Extraction failed after {self.max_retries + 1} attempts. "
            f"Last error: {last_error}"
        )

    def _call_claude(
        self, image_b64: str, media_type: str, user_prompt: str
    ) -> str:
        """Make an API call to Claude with image and text."""
        message = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_b64,
                            },
                        },
                        {
                            "type": "text",
                            "text": user_prompt,
                        },
                    ],
                }
            ],
        )
        return message.content[0].text

    def _parse_json(self, raw_text: str) -> dict:
        """Parse JSON from Claude's response, handling markdown code blocks."""
        text = raw_text.strip()

        # Strip markdown code blocks if present
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first line (```json) and last line (```)
            lines = [l for l in lines[1:] if l.strip() != "```"]
            text = "\n".join(lines)

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise ExtractionError(f"Failed to parse JSON from Claude response: {e}")
