from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from .engine import LeakageEngine
from .models import Charge, Customer, Evaluation, PriceTerm, Usage

AS_OF = datetime(2025, 2, 10, 12, tzinfo=UTC)
FRESH = AS_OF - timedelta(hours=1)


def evaluate_variant(variant: str) -> Evaluation:
    customer = Customer("synthetic-customer", "USD", "pro", frozenset({"api"}), date(2025, 1, 1))
    charge = Charge(
        "invoice-jan",
        customer.customer_id,
        date(2025, 1, 1),
        date(2025, 1, 31),
        Decimal("100"),
        Decimal("0"),
        Decimal("10"),
        "USD",
        FRESH,
    )
    term = PriceTerm(
        "catalog-v1",
        "pro",
        Decimal("120"),
        "USD",
        date(2025, 1, 1),
        discount_percent=Decimal("8.333333"),
        discount_end_date=date(2025, 12, 31),
        included_usage={"api_calls": Decimal("10000")},
        overage_rates={"api_calls_per_1000": Decimal("5")},
        entitled_features=frozenset({"api"}),
        source_updated_at=FRESH,
    )
    usage = Usage(
        "usage-jan",
        customer.customer_id,
        charge.period_start,
        charge.period_end,
        {"api_calls": Decimal("12000")},
        FRESH,
    )
    engine = LeakageEngine(as_of=AS_OF)
    if variant == "pricing_outdated":
        return engine.pricing(customer, charge, [term])
    if variant == "pricing_current":
        return engine.pricing(customer, replace(charge, base_charge=Decimal("120")), [term])
    if variant == "pricing_negotiated":
        negotiated = replace(
            term,
            term_id="negotiated-v1",
            customer_id=customer.customer_id,
            base_price=Decimal("100"),
        )
        return engine.pricing(customer, charge, [term, negotiated])
    if variant == "overage_missing":
        return engine.overage(customer, charge, [usage], [term])
    if variant == "overage_correct":
        return engine.overage(
            customer, replace(charge, overage_charge=Decimal("10")), [usage], [term]
        )
    if variant == "discount_valid":
        return engine.discount(customer, charge, [term])
    if variant == "discount_expired":
        return engine.discount(
            customer, charge, [replace(term, discount_end_date=date(2024, 12, 31))]
        )
    if variant == "feature_valid":
        return engine.entitlement(customer, [term])
    if variant == "feature_mismatch":
        return engine.entitlement(
            replace(customer, enabled_features=frozenset({"api", "admin"})), [term]
        )
    if variant == "stale_input":
        return engine.pricing(
            customer, charge, [replace(term, source_updated_at=FRESH - timedelta(days=7))]
        )
    if variant == "missing_input":
        return engine.pricing(customer, None, [term])
    raise ValueError(f"unknown synthetic variant: {variant}")
