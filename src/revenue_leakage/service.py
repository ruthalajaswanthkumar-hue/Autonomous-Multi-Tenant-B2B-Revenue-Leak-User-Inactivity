from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Annotated

from fastapi import FastAPI, Header, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict, Field

from .engine import LeakageEngine
from .models import Charge, Customer, PriceTerm, Usage

app = FastAPI(title="Revenue Leakage Rule Service", version="0.1.0")


class EvaluationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule: str
    as_of: datetime
    max_source_age_hours: int = Field(default=48, ge=0)
    grace_days: int = Field(default=0, ge=0)
    customer: dict[str, object]
    charge: dict[str, object] | None = None
    terms: list[dict[str, object]] = Field(default_factory=list)
    usage: list[dict[str, object]] = Field(default_factory=list)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "ruleset": "revenue-leakage-v1"}


@app.post("/v1/evaluate")
def evaluate(
    request: EvaluationRequest,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, object]:
    expected_token = os.environ.get("LEAKAGE_ENGINE_TOKEN")
    if expected_token and authorization != f"Bearer {expected_token}":
        raise HTTPException(status_code=401, detail="invalid service token")
    try:
        customer = _customer(request.customer)
        charge = _charge(request.charge) if request.charge else None
        terms = [_term(item) for item in request.terms]
        engine = LeakageEngine(
            as_of=request.as_of,
            max_source_age=timedelta(hours=request.max_source_age_hours),
        )
        if request.rule == "outdated_pricing":
            result = engine.pricing(customer, charge, terms)
        elif request.rule == "missing_overage":
            result = engine.overage(
                customer,
                charge,
                [_usage(item) for item in request.usage],
                terms,
                grace_days=request.grace_days,
            )
        elif request.rule == "invalid_discount":
            result = engine.discount(customer, charge, terms)
        elif request.rule == "feature_entitlement":
            result = engine.entitlement(customer, terms, grace_days=request.grace_days)
        else:
            raise ValueError(f"unsupported rule: {request.rule}")
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return jsonable_encoder(result.as_dict())


def _customer(item: dict[str, object]) -> Customer:
    return Customer(
        customer_id=str(item["customer_id"]),
        currency=str(item["currency"]),
        plan_name=str(item["plan_name"]),
        enabled_features=frozenset(str(value) for value in item.get("enabled_features", [])),
        plan_effective_date=_date(item.get("plan_effective_date")),
    )


def _charge(item: dict[str, object]) -> Charge:
    return Charge(
        event_id=str(item["event_id"]),
        customer_id=str(item["customer_id"]),
        period_start=_required_date(item["period_start"]),
        period_end=_required_date(item["period_end"]),
        base_charge=Decimal(str(item["base_charge"])),
        overage_charge=Decimal(str(item.get("overage_charge", "0"))),
        discount=Decimal(str(item.get("discount", "0"))),
        currency=str(item["currency"]),
        source_updated_at=_datetime(item["source_updated_at"]),
    )


def _term(item: dict[str, object]) -> PriceTerm:
    return PriceTerm(
        term_id=str(item["term_id"]),
        plan_name=str(item["plan_name"]),
        base_price=Decimal(str(item["base_price"])),
        currency=str(item["currency"]),
        effective_date=_required_date(item["effective_date"]),
        end_date=_date(item.get("end_date")),
        customer_id=str(item["customer_id"]) if item.get("customer_id") else None,
        discount_percent=Decimal(str(item.get("discount_percent", "0"))),
        discount_end_date=_date(item.get("discount_end_date")),
        included_usage={
            str(key): Decimal(str(value))
            for key, value in dict(item.get("included_usage", {})).items()
        },
        overage_rates={
            str(key): Decimal(str(value))
            for key, value in dict(item.get("overage_rates", {})).items()
        },
        entitled_features=frozenset(str(value) for value in item.get("entitled_features", [])),
        source_updated_at=_datetime(item["source_updated_at"]),
    )


def _usage(item: dict[str, object]) -> Usage:
    return Usage(
        event_id=str(item["event_id"]),
        customer_id=str(item["customer_id"]),
        period_start=_required_date(item["period_start"]),
        period_end=_required_date(item["period_end"]),
        metrics={str(key): Decimal(str(value)) for key, value in dict(item["metrics"]).items()},
        source_updated_at=_datetime(item["source_updated_at"]),
    )


def _date(value: object) -> date | None:
    return None if value in (None, "") else _required_date(value)


def _required_date(value: object) -> date:
    return value if isinstance(value, date) else date.fromisoformat(str(value))


def _datetime(value: object) -> datetime:
    return (
        value
        if isinstance(value, datetime)
        else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    )
