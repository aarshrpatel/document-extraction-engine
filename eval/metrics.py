from decimal import Decimal

from Levenshtein import distance as levenshtein_distance
from Levenshtein import ratio as levenshtein_ratio


def field_exact_match(expected: str | None, extracted: str | None) -> bool:
    """Check if two field values match exactly."""
    if expected is None and extracted is None:
        return True
    if expected is None or extracted is None:
        return False
    return str(expected).strip() == str(extracted).strip()


def field_similarity(expected: str | None, extracted: str | None) -> float:
    """Compute Levenshtein similarity ratio between two strings (0.0 to 1.0)."""
    if expected is None and extracted is None:
        return 1.0
    if expected is None or extracted is None:
        return 0.0
    return levenshtein_ratio(str(expected).strip(), str(extracted).strip())


def field_levenshtein_distance(expected: str | None, extracted: str | None) -> int:
    """Compute Levenshtein edit distance between two strings."""
    if expected is None and extracted is None:
        return 0
    if expected is None or extracted is None:
        return len(str(expected or extracted))
    return levenshtein_distance(str(expected).strip(), str(extracted).strip())


def numeric_tolerance_match(
    expected: Decimal | float | None,
    extracted: Decimal | float | None,
    tolerance: Decimal = Decimal("0.01"),
) -> bool:
    """Check if two numeric values match within a tolerance."""
    if expected is None and extracted is None:
        return True
    if expected is None or extracted is None:
        return False
    return abs(Decimal(str(expected)) - Decimal(str(extracted))) <= tolerance


def date_match(expected: str | None, extracted: str | None) -> bool:
    """Check if two date strings match (handles different formats)."""
    if expected is None and extracted is None:
        return True
    if expected is None or extracted is None:
        return False
    # Normalize common date separators
    e = str(expected).strip().replace("/", "-").replace(".", "-")
    x = str(extracted).strip().replace("/", "-").replace(".", "-")
    return e == x
