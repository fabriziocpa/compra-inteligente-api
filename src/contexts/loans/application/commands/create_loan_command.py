from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RateSegmentInput:
    from_period: int
    to_period: int
    rate_kind: str  # "TEA" or "TNA"
    rate_value: Decimal
    capitalizations_per_year: int | None = None


@dataclass(frozen=True, slots=True)
class AdditionalChargeInput:
    name: str
    kind: str  # "seguro", "comision", "portes", "otro"
    basis: str  # "fixed", "balance_pct", "payment_pct"
    value: Decimal
    applies_from_period: int = 1
    applies_to_period: int | None = None


@dataclass(frozen=True, slots=True)
class CreateLoanCommand:
    client_id: UUID
    vehicle_id: UUID
    currency: str
    vehicle_price: Decimal
    initial_payment_pct: Decimal
    balloon_pct: Decimal
    term_periods: int
    frequency_days: int
    rate_segments: list[RateSegmentInput]
    grace_periods: list[str] = field(default_factory=list)
    additional_charges: list[AdditionalChargeInput] = field(default_factory=list)
