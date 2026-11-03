import os
from datetime import date

from conftest import AS_OF, FRESH
from fastapi.testclient import TestClient

from revenue_leakage.service import app

client = TestClient(app)


def test_health_exposes_ruleset_version():
    assert client.get("/health").json() == {
        "status": "ok",
        "ruleset": "revenue-leakage-v1",
    }


def test_service_returns_structured_pricing_evidence():
    response = client.post(
        "/v1/evaluate",
        json={
            "rule": "outdated_pricing",
            "as_of": AS_OF.isoformat(),
            "customer": {
                "customer_id": "customer-1",
                "currency": "USD",
                "plan_name": "pro",
            },
            "charge": {
                "event_id": "invoice-1",
                "customer_id": "customer-1",
                "period_start": "2025-01-01",
                "period_end": "2025-01-31",
                "base_charge": "99.99",
                "currency": "USD",
                "source_updated_at": FRESH.isoformat(),
            },
            "terms": [
                {
                    "term_id": "catalog-v1",
                    "plan_name": "pro",
                    "base_price": "149.00",
                    "currency": "USD",
                    "effective_date": date(2025, 1, 1).isoformat(),
                    "source_updated_at": FRESH.isoformat(),
                }
            ],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["outcome"] == "finding"
    assert body["expected_value"] == "149.00"
    assert body["actual_value"] == "99.99"
    assert body["rule_version"] == "pricing.v1"


def test_service_rejects_unknown_rule_and_extra_fields():
    assert (
        client.post(
            "/v1/evaluate",
            json={"rule": "unknown", "as_of": AS_OF.isoformat(), "customer": {}, "extra": True},
        ).status_code
        == 422
    )


def test_service_token_is_required_when_configured(monkeypatch):
    monkeypatch.setenv("LEAKAGE_ENGINE_TOKEN", "test-secret")
    request = {"rule": "unknown", "as_of": AS_OF.isoformat(), "customer": {}}
    assert client.post("/v1/evaluate", json=request).status_code == 401
    response = client.post(
        "/v1/evaluate",
        json=request,
        headers={"Authorization": f"Bearer {os.environ['LEAKAGE_ENGINE_TOKEN']}"},
    )
    assert response.status_code == 422
