import json
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from eval.metrics import (
    date_match,
    field_exact_match,
    field_similarity,
    field_levenshtein_distance,
    numeric_tolerance_match,
)

# Fields that should use numeric comparison
NUMERIC_FIELDS = {"subtotal", "tax_amount", "tax_rate", "total_amount", "discount_amount",
                  "shipping_amount", "quantity", "unit_price", "amount"}

# Fields that should use date comparison
DATE_FIELDS = {"invoice_date", "due_date"}


@dataclass
class FieldScore:
    """Score for a single field."""
    field_name: str
    expected: str | None
    extracted: str | None
    is_correct: bool
    similarity: float
    levenshtein_dist: int


@dataclass
class DocumentScore:
    """Aggregate score for a single document."""
    document_id: str
    field_scores: list[FieldScore] = field(default_factory=list)
    total_fields: int = 0
    correct_fields: int = 0
    field_accuracy: float = 0.0
    avg_similarity: float = 0.0


def score_document(
    expected_data: dict,
    extracted_data: dict,
    document_id: str,
) -> DocumentScore:
    """Score extraction results against ground truth for a single document."""
    doc_score = DocumentScore(document_id=document_id)
    similarities = []

    for field_name, expected_value in expected_data.items():
        # Skip metadata fields
        if field_name in ("doc_type", "source_filename", "extracted_at", "metadata"):
            continue

        # Handle nested objects (like addresses) by flattening
        if isinstance(expected_value, dict):
            for sub_key, sub_val in expected_value.items():
                full_key = f"{field_name}.{sub_key}"
                extracted_sub = (extracted_data.get(field_name) or {}).get(sub_key)
                fs = _score_field(full_key, sub_val, extracted_sub)
                doc_score.field_scores.append(fs)
                similarities.append(fs.similarity)
            continue

        # Handle line items separately
        if field_name == "line_items":
            line_scores = _score_line_items(
                expected_value or [], extracted_data.get("line_items") or []
            )
            doc_score.field_scores.extend(line_scores)
            similarities.extend(s.similarity for s in line_scores)
            continue

        extracted_value = extracted_data.get(field_name)
        fs = _score_field(field_name, expected_value, extracted_value)
        doc_score.field_scores.append(fs)
        similarities.append(fs.similarity)

    doc_score.total_fields = len(doc_score.field_scores)
    doc_score.correct_fields = sum(1 for fs in doc_score.field_scores if fs.is_correct)
    doc_score.field_accuracy = (
        doc_score.correct_fields / doc_score.total_fields if doc_score.total_fields > 0 else 0.0
    )
    doc_score.avg_similarity = (
        sum(similarities) / len(similarities) if similarities else 0.0
    )

    return doc_score


def _score_field(field_name: str, expected: object, extracted: object) -> FieldScore:
    """Score a single field."""
    exp_str = str(expected) if expected is not None else None
    ext_str = str(extracted) if extracted is not None else None

    # Choose comparison method based on field type
    if field_name.split(".")[-1] in NUMERIC_FIELDS:
        is_correct = numeric_tolerance_match(
            Decimal(str(expected)) if expected is not None else None,
            Decimal(str(extracted)) if extracted is not None else None,
        )
    elif field_name.split(".")[-1] in DATE_FIELDS:
        is_correct = date_match(exp_str, ext_str)
    else:
        is_correct = field_exact_match(exp_str, ext_str)

    return FieldScore(
        field_name=field_name,
        expected=exp_str,
        extracted=ext_str,
        is_correct=is_correct,
        similarity=field_similarity(exp_str, ext_str),
        levenshtein_dist=field_levenshtein_distance(exp_str, ext_str),
    )


def _score_line_items(
    expected_items: list[dict], extracted_items: list[dict]
) -> list[FieldScore]:
    """Score line items by matching in order."""
    scores = []
    max_len = max(len(expected_items), len(extracted_items))

    for i in range(max_len):
        expected = expected_items[i] if i < len(expected_items) else {}
        extracted = extracted_items[i] if i < len(extracted_items) else {}

        all_keys = set(list(expected.keys()) + list(extracted.keys()))
        for key in all_keys:
            fs = _score_field(
                f"line_items[{i}].{key}",
                expected.get(key),
                extracted.get(key),
            )
            scores.append(fs)

    return scores
