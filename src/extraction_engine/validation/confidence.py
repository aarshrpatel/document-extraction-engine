from decimal import Decimal

from extraction_engine.schemas.base import FieldConfidence
from extraction_engine.schemas.invoice import InvoiceSchema


def score_field_confidence(
    field_name: str,
    extracted_value: str | None,
    ocr_text: str,
) -> FieldConfidence:
    """Score confidence for a single field by checking if the value appears in OCR text.

    Simple presence-based scoring:
    - 1.0 if exact match found in OCR text
    - 0.7 if case-insensitive match found
    - 0.3 if not found (may still be correct - OCR might have missed it)
    """
    if extracted_value is None:
        return FieldConfidence(
            field_name=field_name,
            value=None,
            confidence=Decimal("1.0"),
            ocr_matched=True,
            notes="Field is null (not extracted)",
        )

    value_str = str(extracted_value).strip()
    if not value_str:
        return FieldConfidence(
            field_name=field_name,
            value=extracted_value,
            confidence=Decimal("1.0"),
            ocr_matched=True,
        )

    # Check exact match
    if value_str in ocr_text:
        return FieldConfidence(
            field_name=field_name,
            value=extracted_value,
            confidence=Decimal("1.0"),
            ocr_matched=True,
        )

    # Check case-insensitive match
    if value_str.lower() in ocr_text.lower():
        return FieldConfidence(
            field_name=field_name,
            value=extracted_value,
            confidence=Decimal("0.7"),
            ocr_matched=True,
            notes="Case-insensitive OCR match",
        )

    # Not found in OCR text
    return FieldConfidence(
        field_name=field_name,
        value=extracted_value,
        confidence=Decimal("0.3"),
        ocr_matched=False,
        notes="Value not found in OCR text",
    )


def compute_invoice_confidence(
    invoice: InvoiceSchema, ocr_text: str
) -> list[FieldConfidence]:
    """Compute confidence scores for all key fields of an invoice."""
    key_fields = {
        "invoice_number": invoice.invoice_number,
        "invoice_date": str(invoice.invoice_date) if invoice.invoice_date else None,
        "vendor_name": invoice.vendor_name,
        "customer_name": invoice.customer_name,
        "total_amount": str(invoice.total_amount) if invoice.total_amount else None,
        "subtotal": str(invoice.subtotal) if invoice.subtotal else None,
        "tax_amount": str(invoice.tax_amount) if invoice.tax_amount else None,
        "currency": invoice.currency,
    }

    return [
        score_field_confidence(name, value, ocr_text)
        for name, value in key_fields.items()
    ]
