import json
from pathlib import Path

WORKFLOWS = Path(__file__).parents[1] / "n8n-workflows"


def load(name: str) -> dict[str, object]:
    return json.loads((WORKFLOWS / name).read_text())


def test_all_workflow_exports_parse_and_are_inactive():
    paths = sorted(WORKFLOWS.glob("*.json"))
    assert len(paths) == 5
    for path in paths:
        workflow = json.loads(path.read_text())
        assert workflow["active"] is False
        assert workflow["nodes"]
        assert "connections" in workflow


def test_detection_workflows_delegate_rules_to_service():
    for name, rule in (
        ("03-detect-outdated-pricing.json", "outdated_pricing"),
        ("04-detect-missing-overages.json", "missing_overage"),
    ):
        serialized = json.dumps(load(name))
        assert "LEAKAGE_ENGINE_URL" in serialized
        assert "/v1/evaluate" in serialized
        assert rule in serialized
        assert "jsCode" not in serialized
        assert "persist_leakage_evaluation" in serialized


def test_usage_workflow_has_no_random_fixture_generation():
    serialized = json.dumps(load("02-usage-collection.json"))
    assert "Math.random" not in serialized
    assert "external_event_id" in serialized
    assert "ON CONFLICT" in serialized


def test_workflows_do_not_embed_secret_values():
    forbidden = ("sk_live_", "sk_test_51", "ghp_", "github_pat_", "eyJhbGciOi")
    for path in WORKFLOWS.glob("*.json"):
        content = path.read_text()
        assert not any(marker in content for marker in forbidden)
