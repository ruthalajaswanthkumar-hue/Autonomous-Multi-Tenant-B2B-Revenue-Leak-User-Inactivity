from __future__ import annotations

import json
import platform
from pathlib import Path

from revenue_leakage.models import Outcome
from revenue_leakage.synthetic import evaluate_variant

ROOT = Path(__file__).parents[1]


def run() -> dict[str, object]:
    dataset = json.loads((ROOT / "benchmarks/synthetic_cases.json").read_text())
    rows = []
    tp = fp = fn = tn = 0
    outcome_mismatches = 0
    for case in dataset["cases"]:
        result = evaluate_variant(case["variant"])
        predicted = result.outcome is Outcome.FINDING
        expected = case["expected_finding"]
        tp += int(expected and predicted)
        fp += int(not expected and predicted)
        fn += int(expected and not predicted)
        tn += int(not expected and not predicted)
        expected_outcome = case.get("expected_outcome", "finding" if expected else "clear")
        outcome_match = result.outcome.value == expected_outcome
        outcome_mismatches += int(not outcome_match)
        rows.append(
            {
                "case_id": case["case_id"],
                "expected_finding": expected,
                "predicted_outcome": result.outcome.value,
                "expected_outcome": expected_outcome,
                "outcome_match": outcome_match,
                "rule_id": result.rule_id,
                "finding_key": result.finding_key,
            }
        )
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {
        "evidence_label": "synthetic_benchmark",
        "dataset": "benchmarks/synthetic_cases.json",
        "environment": {"python": platform.python_version()},
        "case_count": len(rows),
        "metrics": {
            "true_positives": tp,
            "true_negatives": tn,
            "false_positives": fp,
            "false_negatives": fn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "outcome_mismatches": outcome_mismatches,
        },
        "cases": rows,
        "claim_boundary": (
            "Synthetic fixtures validate these encoded rules only; they do not establish "
            "production recovery or generalization."
        ),
    }


if __name__ == "__main__":
    output = run()
    destination = ROOT / "results/synthetic_benchmark.json"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(output, indent=2) + "\n")
    print(destination.relative_to(ROOT))
