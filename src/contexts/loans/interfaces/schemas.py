from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class RateSegmentSchema(BaseModel):
    from_period: int = Field(ge=1)
    to_period: int = Field(ge=1)
    rate_kind: str = Field(pattern="^(TEA|TNA)$")
    rate_value: Decimal
    capitalizations_per_year: int | None = None


class AdditionalChargeSchema(BaseModel):
    name: str
    kind: str = Field(pattern="^(seguro|comision|portes|otro)$")
    basis: str = Field(pattern="^(fixed|balance_pct|payment_pct)$")
    value: Decimal
    applies_from_period: int = 1
    applies_to_period: int | None = None


class LoanCreateRequest(BaseModel):
    client_id: UUID
    vehicle_id: UUID
    currency: str = Field(pattern="^(PEN|USD)$")
    vehicle_price: Decimal = Field(gt=0)
    initial_payment_pct: Decimal = Field(ge=0, lt=1)
    balloon_pct: Decimal = Field(ge=0, lt=1)
    term_periods: int = Field(gt=0)
    frequency_days: int = Field(gt=0)
    rate_segments: list[RateSegmentSchema]
    grace_periods: list[str] = Field(default_factory=list)
    additional_charges: list[AdditionalChargeSchema] = Field(default_factory=list)


class LoanPatchRequest(BaseModel):
    initial_payment_pct: Decimal | None = Field(default=None, ge=0, lt=1)
    balloon_pct: Decimal | None = Field(default=None, ge=0, lt=1)
    rate_segments: list[RateSegmentSchema] | None = None
    grace_periods: list[str] | None = None
    additional_charges: list[AdditionalChargeSchema] | None = None


class LoanResponse(BaseModel):
    id: UUID
    client_id: UUID
    vehicle_id: UUID
    currency: str
    vehicle_price: Decimal
    initial_payment_pct: Decimal
    balloon_pct: Decimal
    term_periods: int
    frequency_days: int
    status: str
    created_at: datetime

    model_config = {"json_encoders": {Decimal: str}}


class ScheduleEntryResponse(BaseModel):
    period: int
    grace_type: str
    initial_balance: Decimal
    interest: Decimal
    payment: Decimal
    amortization: Decimal
    final_balance: Decimal

    model_config = {"json_encoders": {Decimal: str}}


class ScheduleResponse(BaseModel):
    loan_id: UUID
    rows: list[ScheduleEntryResponse]


class IndicatorsResponse(BaseModel):
    loan_id: UUID
    tir_per_period: Decimal
    tcea: Decimal
    van_at_period_rate: Decimal | None
    cashflows: list[Decimal]

    model_config = {"json_encoders": {Decimal: str}}
