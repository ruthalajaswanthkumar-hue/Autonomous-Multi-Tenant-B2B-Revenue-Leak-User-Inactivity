from scripts.run_synthetic_benchmark import run


def test_synthetic_benchmark_is_perfect_on_labeled_fixtures():
    result = run()
    assert result["evidence_label"] == "synthetic_benchmark"
    assert result["case_count"] == 11
    assert result["metrics"] == {
        "true_positives": 4,
        "true_negatives": 7,
        "false_positives": 0,
        "false_negatives": 0,
        "precision": 1.0,
        "recall": 1.0,
        "outcome_mismatches": 0,
    }
