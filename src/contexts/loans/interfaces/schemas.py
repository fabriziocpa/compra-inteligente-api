"""Esquemas (contratos HTTP) del contexto de préstamos.

Los montos y tasas viajan como ``Decimal`` serializado a string para no
perder precisión. Las fracciones (cuota inicial, balón, tasas, cargos en %)
van en 0..1: ``"0.20"`` = 20 %.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

# S = sin gracia (normal), P = parcial (solo interés), T = total (capitaliza)
GraceCodeSchema = Literal["S", "P", "T"]


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
    grace_periods: list[GraceCodeSchema] = Field(default_factory=list)
    additional_charges: list[AdditionalChargeSchema] = Field(default_factory=list)


class LoanPatchRequest(BaseModel):
    """Edición parcial: todos los campos son opcionales.

    Editar cualquier parámetro invalida el cronograma; hay que volver a
    llamar a POST /loans/{id}/schedule.
    """

    currency: str | None = Field(default=None, pattern="^(PEN|USD)$")
    vehicle_price: Decimal | None = Field(default=None, gt=0)
    initial_payment_pct: Decimal | None = Field(default=None, ge=0, lt=1)
    balloon_pct: Decimal | None = Field(default=None, ge=0, lt=1)
    term_periods: int | None = Field(default=None, gt=0)
    frequency_days: int | None = Field(default=None, gt=0)
    rate_segments: list[RateSegmentSchema] | None = None
    grace_periods: list[GraceCodeSchema] | None = None
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
    rate_segments: list[RateSegmentSchema]
    grace_periods: list[GraceCodeSchema]
    additional_charges: list[AdditionalChargeSchema]
    status: str
    created_at: datetime

    model_config = {"json_encoders": {Decimal: str}}


class ChargeAmountResponse(BaseModel):
    """Cargo evaluado en un período (monto negativo: egreso del deudor)."""

    name: str
    kind: str
    amount: Decimal

    model_config = {"json_encoders": {Decimal: str}}


class ScheduleEntryResponse(BaseModel):
    period: int
    grace_type: str
    initial_balance: Decimal
    interest: Decimal
    payment: Decimal
    amortization: Decimal
    final_balance: Decimal
    charges: list[ChargeAmountResponse] = Field(default_factory=list)
    charges_total: Decimal = Decimal(0)
    total_payment: Decimal = Decimal(0)

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
