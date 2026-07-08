from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from src.contexts.loans.application.commands.create_loan_command import (
    AdditionalChargeInput,
    CreateLoanCommand,
    RateSegmentInput,
)
from src.contexts.loans.application.use_cases.calculate_indicators import (
    CalculateIndicatorsUseCase,
)
from src.contexts.loans.application.use_cases.calculate_schedule import (
    CalculateScheduleUseCase,
)
from src.contexts.loans.application.use_cases.create_loan import CreateLoanUseCase
from src.contexts.loans.domain.entities.loan import Loan
from src.shared.domain.exceptions import NotFoundError


class InMemoryLoanRepo:
    def __init__(self) -> None:
        self._store: dict[UUID, Loan] = {}

    async def add(self, loan: Loan) -> None:
        self._store[loan.id] = loan

    async def get(self, loan_id: UUID) -> Loan:
        if loan_id not in self._store:
            raise NotFoundError(f"Loan {loan_id} not found")
        return self._store[loan_id]

    async def list_by_client(self, client_id: UUID) -> list[Loan]:
        return [loan for loan in self._store.values() if loan.client_id == client_id]

    async def list_all(self) -> list[Loan]:
        return list(self._store.values())

    async def update(self, loan: Loan) -> None:
        self._store[loan.id] = loan

    async def delete(self, loan_id: UUID) -> None:
        self._store.pop(loan_id, None)


def _base_cmd() -> CreateLoanCommand:
    return CreateLoanCommand(
        client_id=uuid4(),
        vehicle_id=uuid4(),
        currency="USD",
        vehicle_price=Decimal("1440000"),
        initial_payment_pct=Decimal("0"),
        balloon_pct=Decimal("0"),
        term_periods=8,
        frequency_days=180,
        rate_segments=[
            RateSegmentInput(
                from_period=1, to_period=8, rate_kind="TEA", rate_value=Decimal("0.09")
            )
        ],
        grace_periods=[],
        additional_charges=[],
    )


@pytest.mark.asyncio
async def test_create_then_schedule_then_indicators_for_example_1() -> None:
    repo = InMemoryLoanRepo()
    loan = await CreateLoanUseCase(repo).execute(_base_cmd())
    assert loan.status == "draft"

    loan = await CalculateScheduleUseCase(repo).execute(loan.id)
    assert loan.status == "scheduled"
    assert len(loan.schedule) == 8
    assert abs(loan.schedule[0].payment - Decimal("-217454.11")) <= Decimal("0.01")
    assert abs(loan.schedule[0].final_balance - Decimal("1285950.02")) <= Decimal("0.01")
    assert abs(loan.schedule[-1].final_balance) <= Decimal("0.10")

    result = await CalculateIndicatorsUseCase(repo).execute(loan.id)
    # TIR semestral ≈ TES 9% ≈ 0.04403, TCEA ≈ 0.09
    assert abs(result.tir_per_period - Decimal("0.04403065")) <= Decimal("0.00001")
    assert abs(result.tcea - Decimal("0.09")) <= Decimal("0.00001")


@pytest.mark.asyncio
async def test_compra_inteligente_with_balloon_and_initial_payment() -> None:
    repo = InMemoryLoanRepo()
    cmd = _base_cmd()
    object.__setattr__(cmd, "vehicle_price", Decimal("60000"))
    object.__setattr__(cmd, "initial_payment_pct", Decimal("0.20"))
    object.__setattr__(cmd, "balloon_pct", Decimal("0.30"))
    object.__setattr__(cmd, "term_periods", 36)
    object.__setattr__(cmd, "frequency_days", 30)
    object.__setattr__(
        cmd,
        "rate_segments",
        [
            RateSegmentInput(
                from_period=1, to_period=36, rate_kind="TEA", rate_value=Decimal("0.12")
            )
        ],
    )

    loan = await CreateLoanUseCase(repo).execute(cmd)
    loan = await CalculateScheduleUseCase(repo).execute(loan.id)

    # Modelo Interbank: N cuotas regulares + período N+1 donde se paga el cuotón.
    assert len(loan.schedule) == 37
    # El cronograma regular cierra en 0 en el período N…
    assert abs(loan.schedule[35].final_balance) <= Decimal("0.01")
    # …y el cuotón paga el balón íntegro (18,000) en N+1.
    balloon = Decimal("60000") * Decimal("0.30")
    assert abs(loan.schedule[36].balloon_amortization + balloon) <= Decimal("0.01")
    assert abs(loan.schedule[36].balloon_final) <= Decimal("0.01")

    result = await CalculateIndicatorsUseCase(repo).execute(loan.id)
    assert result.tir_per_period > Decimal(0)
    assert result.tcea > Decimal(0)


@pytest.mark.asyncio
async def test_golden_excel_interbank_end_to_end() -> None:
    """Reproduce la hoja «Compra Inteligente IB» completa: flujo → TIR/TCEA/VAN.

    Datos: PV 16,000 · Plan 36 · CI 20 % · CF 40 % · TNA 15 % cap. diaria ·
    desgravamen 0.049 % mensual · costes financiados 175 · gracia T×3, P×3 ·
    GPS 20 · Portes 3.50 · Gastos adm. 3.50 · seguro riesgo 0.3 % anual del PV.
    Resultados de la hoja: cuota −379.158434, TIR 1.586175 % mensual,
    TCEA 20.785636 %, VAN 4,436.183166 con COK 50 % anual.
    """
    repo = InMemoryLoanRepo()
    cmd = _base_cmd()
    object.__setattr__(cmd, "currency", "PEN")
    object.__setattr__(cmd, "vehicle_price", Decimal("16000"))
    object.__setattr__(cmd, "initial_payment_pct", Decimal("0.20"))
    object.__setattr__(cmd, "balloon_pct", Decimal("0.40"))
    object.__setattr__(cmd, "term_periods", 36)
    object.__setattr__(cmd, "frequency_days", 30)
    object.__setattr__(cmd, "financed_costs", Decimal("175"))
    object.__setattr__(cmd, "desgravamen_monthly_pct", Decimal("0.00049"))
    object.__setattr__(
        cmd,
        "rate_segments",
        [
            RateSegmentInput(
                from_period=1,
                to_period=36,
                rate_kind="TNA",
                rate_value=Decimal("0.15"),
                capitalizations_per_year=360,
            )
        ],
    )
    object.__setattr__(cmd, "grace_periods", ["T", "T", "T", "P", "P", "P"])
    object.__setattr__(
        cmd,
        "additional_charges",
        [
            AdditionalChargeInput(name="GPS", kind="otro", basis="fixed", value=Decimal("20")),
            AdditionalChargeInput(name="Portes", kind="portes", basis="fixed", value=Decimal("3.5")),
            AdditionalChargeInput(name="Gastos adm.", kind="comision", basis="fixed", value=Decimal("3.5")),
            AdditionalChargeInput(
                name="Seguro riesgo", kind="seguro", basis="vehicle_pct_annual", value=Decimal("0.003")
            ),
        ],
    )

    loan = await CreateLoanUseCase(repo).execute(cmd)
    loan = await CalculateScheduleUseCase(repo).execute(loan.id)

    tol = Decimal("0.01")
    assert len(loan.schedule) == 37
    # Flujos del deudor (columna R de la hoja).
    assert abs(loan.schedule[0].total_payment - Decimal("-35.417835")) <= tol
    assert abs(loan.schedule[3].total_payment - Decimal("-153.301736")) <= tol
    assert abs(loan.schedule[6].total_payment - Decimal("-410.158434")) <= tol
    assert abs(loan.schedule[36].total_payment - Decimal("-6431.00")) <= tol

    # COKi = (1 + 50 %)^(30/360) − 1 = 3.436608 % (celda J24).
    coki = (Decimal("1.5") ** (Decimal(30) / Decimal(360))) - Decimal(1)
    result = await CalculateIndicatorsUseCase(repo).execute(loan.id, coki)
    # t0 = Prestamo (J10): PV − CI + costes financiados.
    assert result.cashflows[0] == Decimal("12975.00")
    assert abs(result.tir_per_period - Decimal("0.01586175")) <= Decimal("0.0000001")
    assert abs(result.tcea - Decimal("0.20785636")) <= Decimal("0.000001")
    assert result.van_at_period_rate is not None
    assert abs(result.van_at_period_rate - Decimal("4436.183166")) <= Decimal("0.01")


@pytest.mark.asyncio
async def test_golden_excel_schedule_summary() -> None:
    """El bloque «Resultados» de la hoja, calculado en el servidor.

    Valores de la hoja: TEA 16.1797946 %, TEM 1.2575815 %, CI 3,200,
    CF 6,400, Prestamo 12,975, saldo en cuotas 9,015.99, seguro riesgo 4.00
    por período, Intereses 2,264.74, Amortización 15,760.44, SegDes 102.72,
    GPS 740, Portes 129.50, Gastos adm. 129.50, Seguro riesgo 148.00.
    """
    from src.contexts.loans.domain.services.schedule_summary_service import (
        ScheduleSummaryService,
    )

    repo = InMemoryLoanRepo()
    cmd = _base_cmd()
    object.__setattr__(cmd, "currency", "PEN")
    object.__setattr__(cmd, "vehicle_price", Decimal("16000"))
    object.__setattr__(cmd, "initial_payment_pct", Decimal("0.20"))
    object.__setattr__(cmd, "balloon_pct", Decimal("0.40"))
    object.__setattr__(cmd, "term_periods", 36)
    object.__setattr__(cmd, "frequency_days", 30)
    object.__setattr__(cmd, "financed_costs", Decimal("175"))
    object.__setattr__(cmd, "desgravamen_monthly_pct", Decimal("0.00049"))
    object.__setattr__(
        cmd,
        "rate_segments",
        [
            RateSegmentInput(
                from_period=1,
                to_period=36,
                rate_kind="TNA",
                rate_value=Decimal("0.15"),
                capitalizations_per_year=360,
            )
        ],
    )
    object.__setattr__(cmd, "grace_periods", ["T", "T", "T", "P", "P", "P"])
    object.__setattr__(
        cmd,
        "additional_charges",
        [
            AdditionalChargeInput(name="GPS", kind="otro", basis="fixed", value=Decimal("20")),
            AdditionalChargeInput(name="Portes", kind="portes", basis="fixed", value=Decimal("3.5")),
            AdditionalChargeInput(name="Gastos adm.", kind="comision", basis="fixed", value=Decimal("3.5")),
            AdditionalChargeInput(
                name="Seguro riesgo", kind="seguro", basis="vehicle_pct_annual", value=Decimal("0.003")
            ),
        ],
    )

    loan = await CreateLoanUseCase(repo).execute(cmd)
    loan = await CalculateScheduleUseCase(repo).execute(loan.id)
    s = ScheduleSummaryService.summarize(loan)

    tol = Decimal("0.01")
    # … del financiamiento
    assert abs(s.tea - Decimal("0.161797946")) <= Decimal("0.000000001")
    assert abs(s.tep - Decimal("0.012575815")) <= Decimal("0.000000001")
    assert s.payments_per_year == 12
    assert s.total_payments == 36
    assert s.initial_payment == Decimal("3200.00")
    assert s.balloon == Decimal("6400.00")
    assert s.loan_principal == Decimal("12975.00")
    assert abs(s.regular_principal - Decimal("9015.990703")) <= tol
    assert abs(s.balloon_present_value - Decimal("3959.009297")) <= tol
    assert abs(s.regular_payment - Decimal("379.158434")) <= tol
    assert abs(s.balloon_payment - Decimal("6400")) <= tol
    assert s.has_balloon is True
    # … de los costes/gastos periódicos
    assert s.desgravamen_pct_per_period == Decimal("0.00049")
    periodic = {c.name: c.amount for c in s.periodic_charges}
    assert periodic["GPS"] == Decimal("20.0")
    assert abs(periodic["Seguro riesgo"] - Decimal("4.00")) <= tol
    # … totales por concepto (celdas del bloque de resultados)
    assert abs(s.total_interest - Decimal("2264.74")) <= tol
    assert abs(s.total_amortization - Decimal("15760.44")) <= tol
    assert abs(s.total_insurance - Decimal("102.72")) <= tol
    totales = {c.name: c.amount for c in s.total_charges}
    assert abs(totales["GPS"] - Decimal("740.00")) <= tol
    assert abs(totales["Portes"] - Decimal("129.50")) <= tol
    assert abs(totales["Gastos adm."] - Decimal("129.50")) <= tol
    assert abs(totales["Seguro riesgo"] - Decimal("148.00")) <= tol
    # Pie de tabla: coherencia interna (el cuotón paga el balón exacto).
    assert s.column_totals.total_payment < Decimal(0)
    assert abs(s.column_totals.balloon_amortization + Decimal("6400")) <= tol


@pytest.mark.asyncio
async def test_charges_are_stored_per_period_and_enter_indicators() -> None:
    """Los cargos deben quedar en cada fila (cuota total) y subir la TCEA."""
    repo = InMemoryLoanRepo()

    cmd = _base_cmd()
    loan_sin_cargos = await CreateLoanUseCase(repo).execute(cmd)
    loan_sin_cargos = await CalculateScheduleUseCase(repo).execute(loan_sin_cargos.id)
    base = await CalculateIndicatorsUseCase(repo).execute(loan_sin_cargos.id)

    cmd2 = _base_cmd()
    object.__setattr__(
        cmd2,
        "additional_charges",
        [
            AdditionalChargeInput(
                name="Seguro desgravamen",
                kind="seguro",
                basis="balance_pct",
                value=Decimal("0.001"),
            )
        ],
    )
    loan = await CreateLoanUseCase(repo).execute(cmd2)
    loan = await CalculateScheduleUseCase(repo).execute(loan.id)

    first = loan.schedule[0]
    assert len(first.charges) == 1
    # 0.1 % del saldo inicial, con signo negativo (egreso del deudor).
    esperado = -(first.initial_balance * Decimal("0.001"))
    assert abs(first.charges[0].amount - esperado) <= Decimal("0.01")
    assert first.total_payment == first.payment + first.charges_total

    con_cargos = await CalculateIndicatorsUseCase(repo).execute(loan.id)
    # El costo efectivo (TCEA) debe subir al incluir el seguro.
    assert con_cargos.tcea > base.tcea


@pytest.mark.asyncio
async def test_initial_costs_breakdown_drives_financed_costs() -> None:
    """Con desglose de costos iniciales, financed_costs = Σ financiados.

    Mismo caso golden del Excel: notariales 100 + registrales 75 financiados
    (Prestamo 12,975) más una tasación de 120 al contado que NO entra al
    préstamo ni a los flujos.
    """
    from src.contexts.loans.application.commands.create_loan_command import (
        InitialCostInput,
    )
    from src.contexts.loans.domain.value_objects.initial_cost import (
        cash_total,
        financed_total,
    )

    repo = InMemoryLoanRepo()
    cmd = _base_cmd()
    object.__setattr__(cmd, "currency", "PEN")
    object.__setattr__(cmd, "vehicle_price", Decimal("16000"))
    object.__setattr__(cmd, "initial_payment_pct", Decimal("0.20"))
    object.__setattr__(cmd, "balloon_pct", Decimal("0.40"))
    object.__setattr__(cmd, "term_periods", 36)
    object.__setattr__(cmd, "frequency_days", 30)
    # financed_costs contradictorio a propósito: el desglose debe mandar.
    object.__setattr__(cmd, "financed_costs", Decimal("999"))
    object.__setattr__(
        cmd,
        "initial_costs",
        [
            InitialCostInput(name="Gastos notariales", amount=Decimal("100"), financed=True),
            InitialCostInput(name="Gastos registrales", amount=Decimal("75"), financed=True),
            InitialCostInput(name="Tasación", amount=Decimal("120"), financed=False),
        ],
    )
    object.__setattr__(
        cmd,
        "rate_segments",
        [
            RateSegmentInput(
                from_period=1,
                to_period=36,
                rate_kind="TNA",
                rate_value=Decimal("0.15"),
                capitalizations_per_year=360,
            )
        ],
    )

    loan = await CreateLoanUseCase(repo).execute(cmd)
    assert loan.terms.financed_costs == Decimal("175")
    assert loan.terms.loan_principal == Decimal("12975.00")
    assert financed_total(loan.initial_costs) == Decimal("175")
    assert cash_total(loan.initial_costs) == Decimal("120")

    # El contado no altera el flujo t0 (= Prestamo, fiel a la hoja).
    loan = await CalculateScheduleUseCase(repo).execute(loan.id)
    result = await CalculateIndicatorsUseCase(repo).execute(loan.id)
    assert abs(result.cashflows[0] - Decimal("12975")) <= Decimal("0.01")
