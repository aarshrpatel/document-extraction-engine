"""DeepEval integration for document extraction evaluation."""

import json
from pathlib import Path

from deepeval import assert_test
from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase

from eval.metrics import field_exact_match, field_similarity, numeric_tolerance_match
from eval.scorer import score_document


class FieldAccuracyMetric(BaseMetric):
    """DeepEval metric: percentage of fields correctly extracted."""

    def __init__(self, threshold: float = 0.8):
        self.threshold = threshold
        self._score = 0.0
        self._reason = ""

    @property
    def __name__(self):
        return "Field Accuracy"

    async def a_measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        return self.measure(test_case)

    def measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        expected = json.loads(test_case.expected_output)
        extracted = json.loads(test_case.actual_output)

        doc_score = score_document(expected, extracted, "test")
        self._score = doc_score.field_accuracy
        self._reason = (
            f"{doc_score.correct_fields}/{doc_score.total_fields} fields correct"
        )
        self.success = self._score >= self.threshold
        return self._score

    def is_successful(self) -> bool:
        return self.success

    @property
    def score(self):
        return self._score

    @property
    def reason(self):
        return self._reason


class LevenshteinSimilarityMetric(BaseMetric):
    """DeepEval metric: average Levenshtein similarity across fields."""

    def __init__(self, threshold: float = 0.9):
        self.threshold = threshold
        self._score = 0.0
        self._reason = ""

    @property
    def __name__(self):
        return "Levenshtein Similarity"

    async def a_measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        return self.measure(test_case)

    def measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        expected = json.loads(test_case.expected_output)
        extracted = json.loads(test_case.actual_output)

        doc_score = score_document(expected, extracted, "test")
        self._score = doc_score.avg_similarity
        self._reason = f"Average similarity: {self._score:.3f}"
        self.success = self._score >= self.threshold
        return self._score

    def is_successful(self) -> bool:
        return self.success

    @property
    def score(self):
        return self._score

    @property
    def reason(self):
        return self._reason


def create_test_cases(
    ground_truth_dir: Path,
    extraction_results_dir: Path,
) -> list[LLMTestCase]:
    """Create DeepEval test cases from ground truth and extraction results."""
    test_cases = []

    for gt_file in sorted(ground_truth_dir.glob("*.json")):
        result_file = extraction_results_dir / gt_file.name
        if not result_file.exists():
            continue

        expected = gt_file.read_text()
        actual = result_file.read_text()

        test_cases.append(
            LLMTestCase(
                input=f"Extract data from {gt_file.stem}",
                actual_output=actual,
                expected_output=expected,
            )
        )

    return test_cases
