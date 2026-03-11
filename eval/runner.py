"""Batch evaluation runner for document extraction accuracy."""

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from eval.scorer import DocumentScore, score_document


GROUND_TRUTH_DIR = Path(__file__).parent / "ground_truth"


def load_ground_truth(doc_type: str) -> list[tuple[Path, dict]]:
    """Load ground truth JSON files for a document type.

    Expects pairs: <name>.pdf + <name>.json in the ground truth directory.
    """
    gt_dir = GROUND_TRUTH_DIR / f"{doc_type}s"
    if not gt_dir.exists():
        raise FileNotFoundError(f"Ground truth directory not found: {gt_dir}")

    pairs = []
    for json_file in sorted(gt_dir.glob("*.json")):
        # Look for matching PDF
        pdf_file = json_file.with_suffix(".pdf")
        if not pdf_file.exists():
            # Try image formats
            for ext in (".jpg", ".jpeg", ".png"):
                img_file = json_file.with_suffix(ext)
                if img_file.exists():
                    pdf_file = img_file
                    break

        with open(json_file) as f:
            ground_truth = json.load(f)

        pairs.append((pdf_file, ground_truth))

    return pairs


def run_eval_offline(
    doc_type: str,
    extraction_results_dir: Path | None = None,
) -> list[DocumentScore]:
    """Run evaluation comparing extraction results against ground truth.

    If extraction_results_dir is provided, load pre-computed results from there.
    Otherwise, this function just validates ground truth format.
    """
    pairs = load_ground_truth(doc_type)
    scores = []

    for doc_path, ground_truth in pairs:
        doc_id = doc_path.stem

        if extraction_results_dir:
            result_file = extraction_results_dir / f"{doc_id}.json"
            if not result_file.exists():
                print(f"  SKIP {doc_id} (no extraction result)")
                continue
            with open(result_file) as f:
                extracted = json.load(f)
        else:
            # Self-test: compare ground truth to itself (should be 100%)
            extracted = ground_truth

        doc_score = score_document(ground_truth, extracted, doc_id)
        scores.append(doc_score)

        print(f"  {doc_id}: accuracy={doc_score.field_accuracy:.1%} "
              f"similarity={doc_score.avg_similarity:.3f} "
              f"({doc_score.correct_fields}/{doc_score.total_fields} fields)")

    return scores


def print_summary(scores: list[DocumentScore]) -> None:
    """Print aggregate summary of evaluation results."""
    if not scores:
        print("\nNo documents evaluated.")
        return

    total_fields = sum(s.total_fields for s in scores)
    correct_fields = sum(s.correct_fields for s in scores)
    avg_accuracy = correct_fields / total_fields if total_fields > 0 else 0.0
    avg_similarity = sum(s.avg_similarity for s in scores) / len(scores)

    print(f"\n{'=' * 50}")
    print(f"EVALUATION SUMMARY ({len(scores)} documents)")
    print(f"{'=' * 50}")
    print(f"  Field accuracy:  {avg_accuracy:.1%} ({correct_fields}/{total_fields})")
    print(f"  Avg similarity:  {avg_similarity:.3f}")
    print(f"{'=' * 50}")


def generate_report(scores: list[DocumentScore], doc_type: str) -> dict:
    """Generate a JSON report from evaluation scores."""
    total_fields = sum(s.total_fields for s in scores)
    correct_fields = sum(s.correct_fields for s in scores)

    return {
        "doc_type": doc_type,
        "total_documents": len(scores),
        "total_fields": total_fields,
        "correct_fields": correct_fields,
        "avg_field_accuracy": correct_fields / total_fields if total_fields > 0 else 0.0,
        "avg_similarity": sum(s.avg_similarity for s in scores) / len(scores) if scores else 0.0,
        "documents": [asdict(s) for s in scores],
    }


def main():
    parser = argparse.ArgumentParser(description="Run extraction evaluation")
    parser.add_argument("--doc-type", required=True, help="Document type (e.g. invoice)")
    parser.add_argument("--results-dir", help="Directory with extraction result JSON files")
    parser.add_argument("--output", help="Output report JSON file")
    args = parser.parse_args()

    print(f"Running evaluation for doc_type={args.doc_type}")

    results_dir = Path(args.results_dir) if args.results_dir else None
    scores = run_eval_offline(args.doc_type, results_dir)
    print_summary(scores)

    if args.output:
        report = generate_report(scores, args.doc_type)
        Path(args.output).write_text(json.dumps(report, indent=2, default=str))
        print(f"\nReport saved to {args.output}")


if __name__ == "__main__":
    main()
