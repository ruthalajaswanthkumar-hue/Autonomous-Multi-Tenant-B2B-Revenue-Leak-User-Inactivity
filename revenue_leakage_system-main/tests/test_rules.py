from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal

import pytest
from conftest import AS_OF, CUSTOMER_ID, FRESH

from revenue_leakage.engine import LeakageEngine
from revenue_leakage.models import Charge, Customer, Outcome, Usage


def test_outdated_catalog_price_returns_structured_finding(customer, charge, catalog):
    result = LeakageEngine(as_of=AS_OF).pricing(customer, charge, [catalog])
    assert result.outcome is Outcome.FINDING
    assert result.as_dict() == {
        "rule_id": "outdated_pricing",
        "customer_id": CUSTOMER_ID,
        "outcome": "finding",
        "expected_value": "120.00",
        "actual_value": "100.00",
        "difference": "20.00",
        "impact_estimate": "20.00",
        "currency": "USD",
        "severity": "low",
        "evidence": {"term_id": "catalog-pro-v2", "precedence": "catalog"},
        "rule_version": "pricing.v1",
        "finding_key": result.finding_key,
    }


def test_negotiated_customer_price_overrides_catalog(customer, charge, catalog):
    negotiated = replace(
        catalog, term_id="contract-1", base_price=Decimal("100"), customer_id=CUSTOMER_ID
    )
    result = LeakageEngine(as_of=AS_OF).pricing(customer, charge, [catalog, negotiated])
    assert result.outcome is Outcome.CLEAR
    assert result.evidence["precedence"] == "negotiated"


def test_effective_and_end_dates_select_only_valid_term(customer, charge, catalog):
    expired = replace(
        catalog,
        term_id="expired",
        base_price=Decimal("200"),
        effective_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
    )
    future = replace(
        catalog, term_id="future", base_price=Decimal("300"), effective_date=date(2025, 2, 1)
    )
    assert LeakageEngine(as_of=AS_OF).pricing(
        customer, charge, [expired, catalog, future]
    ).expected_value == Decimal("120.00")
    boundary = replace(
        catalog, term_id="boundary", base_price=Decimal("100"), effective_date=charge.period_end
    )
    assert (
        LeakageEngine(as_of=AS_OF).pricing(customer, charge, [catalog, boundary]).outcome
        is Outcome.CLEAR
    )
    stale_expired = replace(expired, source_updated_at=FRESH - timedelta(days=10))
    result = LeakageEngine(as_of=AS_OF).pricing(
        customer, charge, (term for term in [stale_expired, catalog])
    )
    assert result.expected_value == Decimal("120.00")


def test_missing_and_correctly_billed_overages(customer, charge, catalog, usage):
    engine = LeakageEngine(as_of=AS_OF)
    missing = engine.overage(
        customer, replace(charge, overage_charge=Decimal("0")), [usage], [catalog]
    )
    assert missing.outcome is Outcome.FINDING
    assert missing.expected_value == Decimal("10.00")  # 3 API blocks + 2 storage GB
    correct = engine.overage(customer, charge, [usage], [catalog])
    assert correct.outcome is Outcome.CLEAR


def test_overage_grace_period_and_window_alignment(customer, charge, catalog, usage):
    engine = LeakageEngine(as_of=AS_OF)
    assert (
        engine.overage(customer, charge, [usage], [catalog], grace_days=10).outcome is Outcome.GRACE
    )
    wrong_window = replace(usage, period_start=date(2024, 12, 1), period_end=date(2024, 12, 31))
    assert engine.overage(customer, charge, [wrong_window], [catalog]).outcome is Outcome.BLOCKED


def test_duplicate_usage_is_collapsed_and_conflicts_fail(customer, charge, catalog, usage):
    engine = LeakageEngine(as_of=AS_OF)
    clean = engine.overage(customer, charge, [usage], [catalog])
    replay = engine.overage(customer, charge, [usage, usage], [catalog])
    assert replay == clean
    with pytest.raises(ValueError, match="conflicting duplicate"):
        engine.overage(
            customer,
            charge,
            [usage, replace(usage, metrics={"api_calls": Decimal("90000")})],
            [catalog],
        )


def test_valid_and_expired_discounts(customer, charge, catalog):
    engine = LeakageEngine(as_of=AS_OF)
    assert engine.discount(customer, charge, [catalog]).outcome is Outcome.CLEAR
    expired = replace(catalog, discount_end_date=date(2024, 12, 31))
    result = engine.discount(customer, charge, [expired])
    assert result.outcome is Outcome.FINDING
    assert result.expected_value == Decimal("0.00")
    assert result.actual_value == Decimal("15.00")


def test_feature_entitlement_mismatch_and_grace(customer, catalog):
    entitled = LeakageEngine(as_of=AS_OF).entitlement(customer, [catalog])
    assert entitled.outcome is Outcome.CLEAR
    mismatch = replace(customer, enabled_features=frozenset({"api", "admin"}))
    assert LeakageEngine(as_of=AS_OF).entitlement(mismatch, [catalog]).outcome is Outcome.FINDING
    recent = replace(mismatch, plan_effective_date=AS_OF.date() - timedelta(days=2))
    assert (
        LeakageEngine(as_of=AS_OF).entitlement(recent, [catalog], grace_days=3).outcome
        is Outcome.GRACE
    )


def test_decimal_precision_and_currency_mismatch(customer, charge, catalog):
    precise_term = replace(catalog, base_price=Decimal("100.005"))
    precise_charge = replace(charge, base_charge=Decimal("100.004"))
    result = LeakageEngine(as_of=AS_OF).pricing(customer, precise_charge, [precise_term])
    assert result.expected_value == Decimal("100.01")
    assert result.actual_value == Decimal("100.00")
    assert result.outcome is Outcome.CLEAR  # one-cent tolerance avoids noise
    mismatch = LeakageEngine(as_of=AS_OF).pricing(
        customer, replace(charge, currency="EUR"), [catalog]
    )
    assert mismatch.outcome is Outcome.BLOCKED
    assert "currency mismatch" in mismatch.evidence["reason"]


def test_stale_and_missing_data_block_instead_of_becoming_clear(customer, charge, catalog):
    engine = LeakageEngine(as_of=AS_OF)
    assert engine.pricing(customer, None, [catalog]).outcome is Outcome.BLOCKED
    assert engine.overage(customer, charge, [], [catalog]).outcome is Outcome.BLOCKED
    stale = replace(catalog, source_updated_at=FRESH - timedelta(days=5))
    assert engine.pricing(customer, charge, [stale]).evidence["reason"] == "stale source data"
    other_customer = replace(charge, customer_id="customer-2")
    assert (
        engine.pricing(customer, other_customer, [catalog]).evidence["reason"]
        == "charge belongs to another customer"
    )


def test_duplicate_findings_have_stable_deduplication_key(customer, charge, catalog):
    engine = LeakageEngine(as_of=AS_OF)
    finding = engine.pricing(customer, charge, [catalog])
    assert len(engine.deduplicate_findings([finding, finding])) == 1
    assert len(finding.finding_key) == 64


@pytest.mark.parametrize(
    "factory",
    [
        lambda: Charge(
            "",
            CUSTOMER_ID,
            date(2025, 1, 1),
            date(2025, 1, 31),
            Decimal("1"),
            Decimal("0"),
            Decimal("0"),
            "USD",
            FRESH,
        ),
        lambda: Charge(
            "i",
            CUSTOMER_ID,
            date(2025, 2, 1),
            date(2025, 1, 31),
            Decimal("1"),
            Decimal("0"),
            Decimal("0"),
            "USD",
            FRESH,
        ),
        lambda: Usage(
            "u",
            CUSTOMER_ID,
            date(2025, 1, 1),
            date(2025, 1, 31),
            {"api_calls": Decimal("NaN")},
            FRESH,
        ),
        lambda: Customer(CUSTOMER_ID, "US", "pro"),
    ],
)
def test_invalid_values_are_rejected(factory):
    with pytest.raises(ValueError):
        factory()
