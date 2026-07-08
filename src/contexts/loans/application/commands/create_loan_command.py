from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RateSegmentInput:
    from_period: int
    to_period: int
    rate_kind: str  # "TEA" o "TNA"
    rate_value: Decimal
    capitalizations_per_year: int | None = None


@dataclass(frozen=True, slots=True)
class AdditionalChargeInput:
    name: str
    kind: str  # "seguro", "comision", "portes", "otro"
    basis: str  # "fixed", "balance_pct", "payment_pct", "vehicle_pct_annual"
    value: Decimal
    applies_from_period: int = 1
    applies_to_period: int | None = None


@dataclass(frozen=True, slots=True)
class InitialCostInput:
    name: str
    amount: Decimal
    financed: bool = True


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
    initial_costs: list[InitialCostInput] = field(default_factory=list)
    # Insumo del motor. Si initial_costs no está vacío, el caso de uso lo
    # deriva como la suma de los ítems financiados (este valor se ignora).
    financed_costs: Decimal = Decimal(0)
    desgravamen_monthly_pct: Decimal = Decimal(0)
