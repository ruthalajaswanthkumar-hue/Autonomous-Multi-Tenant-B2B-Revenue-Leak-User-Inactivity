from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from types import MappingProxyType

Money = Decimal


class Outcome(StrEnum):
    FINDING = "finding"
    CLEAR = "clear"
    BLOCKED = "blocked"
    GRACE = "grace"


class Severity(StrEnum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


def decimal(value: Decimal | str | int) -> Decimal:
    result = Decimal(value)
    if not result.is_finite():
        raise ValueError("financial values must be finite")
    return result


def currency(value: str) -> str:
    normalized = value.upper()
    if len(normalized) != 3 or not normalized.isalpha():
        raise ValueError("currency must be a three-letter ISO code")
    return normalized


def utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("source timestamps must be timezone-aware")
    return value.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class Customer:
    customer_id: str
    currency: str
    plan_name: str
    enabled_features: frozenset[str] = frozenset()
    plan_effective_date: date | None = None

    def __post_init__(self) -> None:
        if not self.customer_id or not self.plan_name:
            raise ValueError("customer_id and plan_name are required")
        object.__setattr__(self, "currency", currency(self.currency))


@dataclass(frozen=True, slots=True)
class PriceTerm:
    term_id: str
    plan_name: str
    base_price: Money
    currency: str
    effective_date: date
    end_date: date | None = None
    customer_id: str | None = None
    discount_percent: Money = Decimal("0")
    discount_end_date: date | None = None
    included_usage: Mapping[str, Money] = field(default_factory=dict)
    overage_rates: Mapping[str, Money] = field(default_factory=dict)
    entitled_features: frozenset[str] = frozenset()
    source_updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.term_id or not self.plan_name:
            raise ValueError("term_id and plan_name are required")
        if self.end_date is not None and self.end_date < self.effective_date:
            raise ValueError("end_date cannot precede effective_date")
        price = decimal(self.base_price)
        discount = decimal(self.discount_percent)
        if price < 0 or discount < 0 or discount > 100:
            raise ValueError("price and discount must be valid non-negative values")
        object.__setattr__(self, "base_price", price)
        object.__setattr__(self, "discount_percent", discount)
        object.__setattr__(self, "currency", currency(self.currency))
        object.__setattr__(self, "source_updated_at", utc(self.source_updated_at))
        object.__setattr__(
            self,
            "included_usage",
            MappingProxyType({key: decimal(value) for key, value in self.included_usage.items()}),
        )
        object.__setattr__(
            self,
            "overage_rates",
            MappingProxyType({key: decimal(value) for key, value in self.overage_rates.items()}),
        )


@dataclass(frozen=True, slots=True)
class Charge:
    event_id: str
    customer_id: str
    period_start: date
    period_end: date
    base_charge: Money
    overage_charge: Money
    discount: Money
    currency: str
    source_updated_at: datetime

    def __post_init__(self) -> None:
        if not self.event_id or not self.customer_id:
            raise ValueError("charge event_id and customer_id are required")
        if self.period_end < self.period_start:
            raise ValueError("charge period is invalid")
        for name in ("base_charge", "overage_charge", "discount"):
            value = decimal(getattr(self, name))
            if value < 0:
                raise ValueError(f"{name} cannot be negative")
            object.__setattr__(self, name, value)
        object.__setattr__(self, "currency", currency(self.currency))
        object.__setattr__(self, "source_updated_at", utc(self.source_updated_at))


@dataclass(frozen=True, slots=True)
class Usage:
    event_id: str
    customer_id: str
    period_start: date
    period_end: date
    metrics: Mapping[str, Money]
    source_updated_at: datetime

    def __post_init__(self) -> None:
        if not self.event_id or not self.customer_id:
            raise ValueError("usage event_id and customer_id are required")
        if self.period_end < self.period_start:
            raise ValueError("usage period is invalid")
        normalized = {key: decimal(value) for key, value in self.metrics.items()}
        if any(value < 0 for value in normalized.values()):
            raise ValueError("usage cannot be negative")
        object.__setattr__(self, "metrics", MappingProxyType(normalized))
        object.__setattr__(self, "source_updated_at", utc(self.source_updated_at))


@dataclass(frozen=True, slots=True)
class Evaluation:
    rule_id: str
    customer_id: str
    outcome: Outcome
    expected_value: Money | None
    actual_value: Money | None
    difference: Money | None
    impact_estimate: Money | None
    currency: str | None
    severity: Severity
    evidence: Mapping[str, object]
    rule_version: str
    finding_key: str

    def as_dict(self) -> dict[str, object]:
        return {
            "rule_id": self.rule_id,
            "customer_id": self.customer_id,
            "outcome": self.outcome.value,
            "expected_value": _string(self.expected_value),
            "actual_value": _string(self.actual_value),
            "difference": _string(self.difference),
            "impact_estimate": _string(self.impact_estimate),
            "currency": self.currency,
            "severity": self.severity.value,
            "evidence": dict(self.evidence),
            "rule_version": self.rule_version,
            "finding_key": self.finding_key,
        }


def _string(value: Money | None) -> str | None:
    return None if value is None else format(value, "f")
