from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal
from hashlib import sha256

from .models import Charge, Customer, Evaluation, Outcome, PriceTerm, Severity, Usage

CENT = Decimal("0.01")
RULE_VERSIONS = {
    "outdated_pricing": "pricing.v1",
    "missing_overage": "overage.v1",
    "invalid_discount": "discount.v1",
    "feature_entitlement": "entitlement.v1",
}


class LeakageEngine:
    def __init__(self, *, as_of: datetime, max_source_age: timedelta = timedelta(days=2)):
        if as_of.tzinfo is None or as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        if max_source_age < timedelta(0):
            raise ValueError("max_source_age cannot be negative")
        self.as_of = as_of.astimezone(UTC)
        self.max_source_age = max_source_age

    def pricing(
        self,
        customer: Customer,
        charge: Charge | None,
        terms: Iterable[PriceTerm],
    ) -> Evaluation:
        rule = "outdated_pricing"
        if charge is None:
            return self._blocked(rule, customer, "missing actual charge")
        term = self._select_term(customer, charge.period_end, list(terms))
        if term is None:
            return self._blocked(rule, customer, "no effective pricing term")
        blocked = self._validate_inputs(rule, customer, charge, [term])
        if blocked:
            return blocked
        if mismatch := self._currency_mismatch(customer, charge, term):
            return self._blocked(rule, customer, mismatch)
        expected = money(term.base_price)
        actual = money(charge.base_charge)
        difference = money(expected - actual)
        return self._financial(
            rule,
            customer,
            expected,
            actual,
            difference,
            {
                "term_id": term.term_id,
                "precedence": "negotiated" if term.customer_id else "catalog",
            },
        )

    def overage(
        self,
        customer: Customer,
        charge: Charge | None,
        usage_events: Iterable[Usage],
        terms: Iterable[PriceTerm],
        *,
        grace_days: int = 0,
    ) -> Evaluation:
        rule = "missing_overage"
        usage = self._deduplicate_usage(customer, usage_events)
        if charge is None:
            return self._blocked(rule, customer, "missing actual charge")
        term = self._select_term(customer, charge.period_end, list(terms))
        if term is None:
            return self._blocked(rule, customer, "no effective pricing term")
        aligned = [
            u
            for u in usage
            if u.period_start == charge.period_start and u.period_end == charge.period_end
        ]
        if not aligned:
            return self._blocked(rule, customer, "no usage for charge billing window")
        blocked = self._validate_inputs(rule, customer, charge, [term, *aligned])
        if blocked:
            return blocked
        if self.as_of.date() <= charge.period_end + timedelta(days=grace_days):
            return self._grace(rule, customer, charge.period_end, grace_days)
        if mismatch := self._currency_mismatch(customer, charge, term):
            return self._blocked(rule, customer, mismatch)
        totals: dict[str, Decimal] = {}
        for event in aligned:
            for metric, value in event.metrics.items():
                totals[metric] = totals.get(metric, Decimal("0")) + value
        expected = Decimal("0")
        details: list[dict[str, str]] = []
        for metric, included in term.included_usage.items():
            actual_usage = totals.get(metric, Decimal("0"))
            excess = max(actual_usage - included, Decimal("0"))
            rate_key = f"{metric}_per_1000"
            if rate_key in term.overage_rates:
                units = (excess / Decimal("1000")).to_integral_value(rounding=ROUND_CEILING)
                amount = units * term.overage_rates[rate_key]
            else:
                amount = excess * term.overage_rates.get(metric, Decimal("0"))
            expected += amount
            details.append(
                {
                    "metric": metric,
                    "usage": str(actual_usage),
                    "excess": str(excess),
                    "charge": str(money(amount)),
                }
            )
        expected = money(expected)
        actual = money(charge.overage_charge)
        return self._financial(
            rule,
            customer,
            expected,
            actual,
            money(expected - actual),
            {
                "term_id": term.term_id,
                "usage_event_ids": sorted(u.event_id for u in aligned),
                "details": details,
            },
        )

    def discount(
        self,
        customer: Customer,
        charge: Charge | None,
        terms: Iterable[PriceTerm],
    ) -> Evaluation:
        rule = "invalid_discount"
        if charge is None:
            return self._blocked(rule, customer, "missing actual charge")
        term = self._select_term(customer, charge.period_end, list(terms))
        if term is None:
            return self._blocked(rule, customer, "no effective pricing term")
        blocked = self._validate_inputs(rule, customer, charge, [term])
        if blocked:
            return blocked
        if mismatch := self._currency_mismatch(customer, charge, term):
            return self._blocked(rule, customer, mismatch)
        valid = term.discount_end_date is None or charge.period_end <= term.discount_end_date
        expected = (
            money(term.base_price * term.discount_percent / Decimal("100"))
            if valid
            else Decimal("0.00")
        )
        actual = money(charge.discount)
        difference = money(actual - expected)
        return self._financial(
            rule,
            customer,
            expected,
            actual,
            difference,
            {
                "term_id": term.term_id,
                "discount_valid": valid,
                "discount_end_date": term.discount_end_date.isoformat()
                if term.discount_end_date
                else None,
            },
        )

    def entitlement(
        self,
        customer: Customer,
        terms: Iterable[PriceTerm],
        *,
        grace_days: int = 0,
    ) -> Evaluation:
        rule = "feature_entitlement"
        term_list = list(terms)
        term = self._select_term(customer, self.as_of.date(), term_list)
        if term is None:
            return self._blocked(rule, customer, "no effective pricing term")
        blocked = self._validate_inputs(rule, customer, None, [term], charge_required=False)
        if blocked:
            return blocked
        unexpected = sorted(customer.enabled_features - term.entitled_features)
        if not unexpected:
            return self._nonfinancial(
                rule, customer, Outcome.CLEAR, {"term_id": term.term_id, "unexpected_features": []}
            )
        if (
            customer.plan_effective_date
            and self.as_of.date() <= customer.plan_effective_date + timedelta(days=grace_days)
        ):
            return self._nonfinancial(
                rule,
                customer,
                Outcome.GRACE,
                {
                    "term_id": term.term_id,
                    "unexpected_features": unexpected,
                    "grace_days": grace_days,
                },
            )
        return self._nonfinancial(
            rule,
            customer,
            Outcome.FINDING,
            {"term_id": term.term_id, "unexpected_features": unexpected},
        )

    def deduplicate_findings(self, evaluations: Iterable[Evaluation]) -> list[Evaluation]:
        unique: dict[str, Evaluation] = {}
        for evaluation in evaluations:
            unique.setdefault(evaluation.finding_key, evaluation)
        return list(unique.values())

    def _validate_inputs(
        self,
        rule: str,
        customer: Customer,
        charge: Charge | None,
        sources: list[object],
        *,
        charge_required: bool = True,
    ) -> Evaluation | None:
        if charge_required and charge is None:
            return self._blocked(rule, customer, "missing actual charge")
        if charge is not None and charge.customer_id != customer.customer_id:
            return self._blocked(rule, customer, "charge belongs to another customer")
        if not sources:
            return self._blocked(rule, customer, "missing source data")
        timestamps = [getattr(source, "source_updated_at", None) for source in sources]
        if charge is not None:
            timestamps.append(charge.source_updated_at)
        if any(timestamp is None for timestamp in timestamps):
            return self._blocked(rule, customer, "missing source timestamp")
        if any(timestamp > self.as_of for timestamp in timestamps):
            return self._blocked(rule, customer, "source timestamp is after evaluation as_of")
        if any(self.as_of - timestamp > self.max_source_age for timestamp in timestamps):
            return self._blocked(rule, customer, "stale source data")
        return None

    @staticmethod
    def _select_term(
        customer: Customer, on_date: date, terms: Iterable[PriceTerm]
    ) -> PriceTerm | None:
        eligible = [
            term
            for term in terms
            if term.plan_name == customer.plan_name
            and term.effective_date <= on_date
            and (term.end_date is None or on_date <= term.end_date)
            and term.customer_id in (None, customer.customer_id)
        ]
        eligible.sort(
            key=lambda term: (
                term.customer_id == customer.customer_id,
                term.effective_date,
                term.term_id,
            ),
            reverse=True,
        )
        return eligible[0] if eligible else None

    @staticmethod
    def _deduplicate_usage(customer: Customer, events: Iterable[Usage]) -> list[Usage]:
        unique: dict[str, Usage] = {}
        for event in events:
            if event.customer_id != customer.customer_id:
                continue
            existing = unique.get(event.event_id)
            if existing is not None and existing != event:
                raise ValueError(f"conflicting duplicate usage event: {event.event_id}")
            unique[event.event_id] = event
        return list(unique.values())

    @staticmethod
    def _currency_mismatch(customer: Customer, charge: Charge, term: PriceTerm) -> str | None:
        values = {customer.currency, charge.currency, term.currency}
        return None if len(values) == 1 else f"currency mismatch: {sorted(values)}"

    def _financial(
        self,
        rule: str,
        customer: Customer,
        expected: Decimal,
        actual: Decimal,
        difference: Decimal,
        evidence: dict[str, object],
    ) -> Evaluation:
        finding = difference > Decimal("0.01")
        severity = severity_for(difference) if finding else Severity.NONE
        return self._evaluation(
            rule,
            customer,
            Outcome.FINDING if finding else Outcome.CLEAR,
            expected,
            actual,
            difference,
            max(difference, Decimal("0.00")),
            customer.currency,
            severity,
            evidence,
        )

    def _nonfinancial(
        self, rule: str, customer: Customer, outcome: Outcome, evidence: dict[str, object]
    ) -> Evaluation:
        return self._evaluation(
            rule,
            customer,
            outcome,
            None,
            None,
            None,
            None,
            customer.currency,
            Severity.MEDIUM if outcome is Outcome.FINDING else Severity.NONE,
            evidence,
        )

    def _blocked(self, rule: str, customer: Customer, reason: str) -> Evaluation:
        return self._evaluation(
            rule,
            customer,
            Outcome.BLOCKED,
            None,
            None,
            None,
            None,
            customer.currency,
            Severity.NONE,
            {"reason": reason},
        )

    def _grace(
        self, rule: str, customer: Customer, period_end: date, grace_days: int
    ) -> Evaluation:
        return self._evaluation(
            rule,
            customer,
            Outcome.GRACE,
            None,
            None,
            None,
            None,
            customer.currency,
            Severity.NONE,
            {"period_end": period_end.isoformat(), "grace_days": grace_days},
        )

    def _evaluation(
        self,
        rule: str,
        customer: Customer,
        outcome: Outcome,
        expected: Decimal | None,
        actual: Decimal | None,
        difference: Decimal | None,
        impact: Decimal | None,
        currency: str | None,
        severity: Severity,
        evidence: dict[str, object],
    ) -> Evaluation:
        version = RULE_VERSIONS[rule]
        fingerprint = "|".join(
            (rule, version, customer.customer_id, repr(sorted(evidence.items())))
        )
        return Evaluation(
            rule,
            customer.customer_id,
            outcome,
            expected,
            actual,
            difference,
            impact,
            currency,
            severity,
            evidence,
            version,
            sha256(fingerprint.encode()).hexdigest(),
        )


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def severity_for(difference: Decimal) -> Severity:
    if difference > Decimal("500"):
        return Severity.HIGH
    if difference > Decimal("100"):
        return Severity.MEDIUM
    return Severity.LOW
