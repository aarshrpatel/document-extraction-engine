from decimal import Decimal

from eval.metrics import (
    date_match,
    field_exact_match,
    field_levenshtein_distance,
    field_similarity,
    numeric_tolerance_match,
)


class TestFieldExactMatch:
    def test_both_none(self):
        assert field_exact_match(None, None) is True

    def test_one_none(self):
        assert field_exact_match("abc", None) is False
        assert field_exact_match(None, "abc") is False

    def test_exact_match(self):
        assert field_exact_match("INV-001", "INV-001") is True

    def test_no_match(self):
        assert field_exact_match("INV-001", "INV-002") is False

    def test_whitespace_stripped(self):
        assert field_exact_match(" INV-001 ", "INV-001") is True


class TestFieldSimilarity:
    def test_identical(self):
        assert field_similarity("hello", "hello") == 1.0

    def test_both_none(self):
        assert field_similarity(None, None) == 1.0

    def test_one_none(self):
        assert field_similarity("hello", None) == 0.0

    def test_similar(self):
        score = field_similarity("INV-001", "INV-002")
        assert 0.5 < score < 1.0


class TestNumericTolerance:
    def test_exact_match(self):
        assert numeric_tolerance_match(Decimal("100.00"), Decimal("100.00")) is True

    def test_within_tolerance(self):
        assert numeric_tolerance_match(Decimal("100.00"), Decimal("100.005")) is True

    def test_outside_tolerance(self):
        assert numeric_tolerance_match(Decimal("100.00"), Decimal("100.02")) is False

    def test_none_handling(self):
        assert numeric_tolerance_match(None, None) is True
        assert numeric_tolerance_match(Decimal("1"), None) is False


class TestDateMatch:
    def test_same_format(self):
        assert date_match("2024-01-15", "2024-01-15") is True

    def test_different_separators(self):
        assert date_match("2024/01/15", "2024-01-15") is True

    def test_none_handling(self):
        assert date_match(None, None) is True
        assert date_match("2024-01-15", None) is False
