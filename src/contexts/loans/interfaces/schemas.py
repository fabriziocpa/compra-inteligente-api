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
    basis: str = Field(pattern="^(fixed|balance_pct|payment_pct|vehicle_pct_annual)$")
    value: Decimal = Field(ge=0)
    applies_from_period: int = Field(default=1, ge=1)
    applies_to_period: int | None = Field(default=None, ge=1)


class InitialCostSchema(BaseModel):
    """Costo/gasto inicial (una sola vez). ``financed=True`` se suma al
    préstamo; ``financed=False`` («al contado») es informativo."""

    name: str = Field(min_length=1, max_length=120)
    amount: Decimal = Field(ge=0)
    financed: bool = True


class LoanCreateRequest(BaseModel):
    client_id: UUID
    vehicle_id: UUID
    currency: str = Field(pattern="^(PEN|USD)$")
    vehicle_price: Decimal = Field(gt=0)
    initial_payment_pct: Decimal = Field(ge=0, lt=1)
    balloon_pct: Decimal = Field(ge=0, lt=1)
    term_periods: int = Field(gt=0)
    frequency_days: int = Field(gt=0)
    # Costes iniciales que se FINANCIAN (se suman al monto del préstamo).
    # Si llega ``initial_costs``, este campo se IGNORA y se deriva como la
    # suma de los ítems financiados.
    financed_costs: Decimal = Field(default=Decimal(0), ge=0)
    # Desglose de costos iniciales (notariales, registrales, tasación…).
    initial_costs: list[InitialCostSchema] = Field(default_factory=list)
    # % MENSUAL del seguro de desgravamen sobre el saldo (va dentro de la cuota).
    desgravamen_monthly_pct: Decimal = Field(default=Decimal(0), ge=0, lt=1)
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
    financed_costs: Decimal | None = Field(default=None, ge=0)
    # Si llega, reemplaza el desglose completo y financed_costs se deriva
    # de los ítems financiados (ignorando el financed_costs del body).
    initial_costs: list[InitialCostSchema] | None = None
    desgravamen_monthly_pct: Decimal | None = Field(default=None, ge=0, lt=1)
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
    financed_costs: Decimal
    initial_costs: list[InitialCostSchema]
    desgravamen_monthly_pct: Decimal
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
    # Desgravamen del período (negativo). En períodos S ya está dentro de
    # ``payment``; en gracia T/P se paga aparte (ver total_payment).
    insurance: Decimal = Decimal(0)
    # Sub-cronograma del cuotón (0 si el plan no tiene cuota balón).
    balloon_initial: Decimal = Decimal(0)
    balloon_interest: Decimal = Decimal(0)
    balloon_insurance: Decimal = Decimal(0)
    balloon_amortization: Decimal = Decimal(0)
    balloon_final: Decimal = Decimal(0)
    charges: list[ChargeAmountResponse] = Field(default_factory=list)
    charges_total: Decimal = Decimal(0)
    total_payment: Decimal = Decimal(0)

    model_config = {"json_encoders": {Decimal: str}}


class ChargeSummaryItemResponse(BaseModel):
    """Cargo con su importe (positivo): por período o total según contexto."""

    name: str
    kind: str
    amount: Decimal

    model_config = {"json_encoders": {Decimal: str}}


class ColumnTotalsResponse(BaseModel):
    """Suma CON SIGNO de cada columna monetaria (fila «Totales» de la tabla)."""

    interest: Decimal
    payment: Decimal
    amortization: Decimal
    insurance: Decimal
    balloon_amortization: Decimal
    charges: Decimal
    total_payment: Decimal

    model_config = {"json_encoders": {Decimal: str}}


class ScheduleSummaryResponse(BaseModel):
    """Bloque «Resultados» de la hoja, calculado íntegramente en el servidor
    (el frontend solo renderiza). Ver ``ScheduleSummaryService``."""

    # … del financiamiento
    tea: Decimal
    tep: Decimal
    payments_per_year: int
    total_payments: int
    initial_payment: Decimal
    balloon: Decimal
    # Costos iniciales: financiados (dentro del préstamo) y al contado
    # (informativo: se pagan aparte en el desembolso).
    financed_costs: Decimal
    cash_costs: Decimal
    loan_principal: Decimal
    regular_principal: Decimal
    balloon_present_value: Decimal
    regular_payment: Decimal
    balloon_payment: Decimal
    has_balloon: bool
    # … de los costes/gastos periódicos
    desgravamen_pct_per_period: Decimal
    periodic_charges: list[ChargeSummaryItemResponse]
    # … totales por concepto (positivos)
    total_interest: Decimal
    total_amortization: Decimal
    total_insurance: Decimal
    total_charges: list[ChargeSummaryItemResponse]
    # pie de tabla (con signo)
    column_totals: ColumnTotalsResponse

    model_config = {"json_encoders": {Decimal: str}}


class ScheduleResponse(BaseModel):
    loan_id: UUID
    rows: list[ScheduleEntryResponse]
    summary: ScheduleSummaryResponse | None = None


class IndicatorsResponse(BaseModel):
    loan_id: UUID
    tir_per_period: Decimal
    tcea: Decimal
    van_at_period_rate: Decimal | None
    # COKi efectivamente usado para el VAN (eco de la conversión anual→período).
    discount_rate_per_period: Decimal | None = None
    cashflows: list[Decimal]

    model_config = {"json_encoders": {Decimal: str}}
