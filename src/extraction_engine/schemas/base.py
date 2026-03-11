from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FieldConfidence(BaseModel):
    """Confidence score for an individual extracted field."""

    model_config = ConfigDict(strict=True)

    field_name: str
    value: Any
    confidence: Decimal = Field(ge=Decimal("0"), le=Decimal("1"))
    ocr_matched: bool = False
    notes: str | None = None


class ExtractionMetadata(BaseModel):
    """Metadata about the extraction process."""

    model_config = ConfigDict(strict=True)

    model_version: str
    processing_time_ms: int
    ocr_confidence: Decimal | None = None
    page_count: int
    field_confidences: list[FieldConfidence] = Field(default_factory=list)


class BaseExtractionResult(BaseModel):
    """Base class for all extraction results."""

    model_config = ConfigDict(strict=True)

    doc_type: str
    source_filename: str
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: ExtractionMetadata | None = None
