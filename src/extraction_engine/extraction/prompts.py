from extraction_engine.schemas.registry import get_schema

SYSTEM_PROMPT = """You are a precise document extraction assistant. Your task is to extract structured data from document images.

CRITICAL RULES:
1. Only extract information that is clearly visible in the document.
2. If a field is not visible or unclear, set it to null. NEVER guess or fabricate values.
3. For monetary values, extract the exact number without currency symbols.
4. For dates, use ISO 8601 format (YYYY-MM-DD).
5. Maintain the exact spelling and formatting of text as it appears in the document.
6. Cross-reference your extraction with the provided OCR text to ensure accuracy.
7. If the OCR text and image disagree, prefer what you see in the image but note the discrepancy."""

EXTRACTION_PROMPT_TEMPLATE = """Extract the structured data from this {doc_type} document.

## OCR Text (for reference - cross-check against the image)
{ocr_text}

## Required Output Format
Return a JSON object matching this exact schema:
{json_schema}

## Instructions
- Extract all visible fields from the document image above.
- Use the OCR text as a reference to verify your extraction.
- Set any field that is not clearly visible to null.
- For line items, extract each item as a separate entry in the array.
- Ensure all monetary amounts are numeric values (no currency symbols).
- Ensure all dates are in YYYY-MM-DD format.
- Return ONLY the JSON object, no other text."""

CORRECTION_PROMPT_TEMPLATE = """Your previous extraction had validation errors. Please fix them.

## Validation Errors
{errors}

## Previous Extraction
{previous_output}

## Instructions
Fix the errors above and return the corrected JSON object.
Return ONLY the corrected JSON object, no other text."""


def build_extraction_prompt(doc_type: str, ocr_text: str) -> str:
    """Build the extraction prompt with the correct schema for the document type."""
    schema_cls = get_schema(doc_type)
    json_schema = schema_cls.model_json_schema()

    return EXTRACTION_PROMPT_TEMPLATE.format(
        doc_type=doc_type,
        ocr_text=ocr_text or "(No OCR text available)",
        json_schema=json_schema,
    )


def build_correction_prompt(errors: str, previous_output: str) -> str:
    """Build a correction prompt when validation fails."""
    return CORRECTION_PROMPT_TEMPLATE.format(
        errors=errors,
        previous_output=previous_output,
    )
