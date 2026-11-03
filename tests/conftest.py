from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from revenue_leakage.models import Charge, Customer, PriceTerm, Usage

AS_OF = datetime(2025, 2, 10, 12, tzinfo=UTC)
FRESH = AS_OF - timedelta(hours=1)
CUSTOMER_ID = "customer-1"


@pytest.fixture
def customer() -> Customer:
    return Customer(CUSTOMER_ID, "USD", "pro", frozenset({"api", "analytics"}), date(2025, 1, 1))


@pytest.fixture
def charge() -> Charge:
    return Charge(
        "invoice-1",
        CUSTOMER_ID,
        date(2025, 1, 1),
        date(2025, 1, 31),
        Decimal("100"),
        Decimal("10"),
        Decimal("15"),
        "USD",
        FRESH,
    )


@pytest.fixture
def catalog() -> PriceTerm:
    return PriceTerm(
        "catalog-pro-v2",
        "pro",
        Decimal("120"),
        "USD",
        date(2025, 1, 1),
        discount_percent=Decimal("12.5"),
        discount_end_date=date(2025, 12, 31),
        included_usage={"api_calls": Decimal("10000"), "storage_gb": Decimal("50")},
        overage_rates={"api_calls_per_1000": Decimal("2.50"), "storage_gb": Decimal("1.25")},
        entitled_features=frozenset({"api", "analytics"}),
        source_updated_at=FRESH,
    )


@pytest.fixture
def usage() -> Usage:
    return Usage(
        "usage-1",
        CUSTOMER_ID,
        date(2025, 1, 1),
        date(2025, 1, 31),
        {"api_calls": Decimal("12500"), "storage_gb": Decimal("52")},
        FRESH,
    )
