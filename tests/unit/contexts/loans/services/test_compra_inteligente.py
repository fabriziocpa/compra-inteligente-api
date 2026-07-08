"""Tests del motor Compra Inteligente estilo Interbank.

El juego de datos «golden» reproduce celda por celda la hoja del curso
«06 - 06 - Planes de Pago - Ordinario - Compra Inteligente IB.xlsx»:
PV 16,000 · Plan 36 · CI 20 % · CF 40 % · TNA 15 % cap. diaria · 30/360 ·
desgravamen 0.049 % mensual · costes financiados 175 · gracia T,T,T,P,P,P.
"""

from decimal import Decimal

import pytest

from src.contexts.loans.domain.services.compra_inteligente_service import (
    CompraInteligenteService,
)
from src.contexts.loans.domain.services.french_amortization_service import (
    SchedulePeriodInput,
)
from src.contexts.loans.domain.services.rate_converter import (
    tep_from_tea,
    tep_from_tna_nominal,
)
from src.shared.domain.exceptions import DomainError

TES_9 = tep_from_tea(Decimal("0.09"), 180)
TOL = Decimal("0.01")

# TEM de la hoja: TNA 15 % capitalización diaria → TEA → TEM (30/360).
TEM_IB = tep_from_tna_nominal(Decimal("0.15"), 360, 30)
SEG_IB = Decimal("0.00049")  # pSegDes mensual; frec=30 → pSegDesPer = pSegDes


def _excel_schedule():
    grace = ["T"] * 3 + ["P"] * 3 + ["S"] * 30
    periods = [
        SchedulePeriodInput(period_number=i + 1, tep=TEM_IB, grace_type=g)
        for i, g in enumerate(grace)
    ]
    return CompraInteligenteService.build_schedule(
        vehicle_price=Decimal("16000"),
        initial_payment_pct=Decimal("0.20"),
        balloon_pct=Decimal("0.40"),
        periods=periods,
        financed_costs=Decimal("175"),
        desgravamen_pct_per_period=SEG_IB,
    )


def test_golden_excel_amounts_and_balances() -> None:
    sched = _excel_schedule()
    # Celdas J10 (Prestamo), J11 (Saldo) y C32 (SICF inicial).
    assert sched.amount_financed == Decimal("12975.00")
    assert abs(sched.balloon_present_value - Decimal("3959.009297")) <= TOL
    assert abs(sched.regular_principal - Decimal("9015.990703")) <= TOL
    assert len(sched.rows) == 37  # N + 1


def test_golden_excel_grace_rows() -> None:
    sched = _excel_schedule()
    # Fila 1 (gracia T): cuota 0, interés capitaliza, desgravamen en efectivo.
    r1 = sched.rows[0]
    assert r1.payment == Decimal(0)
    assert abs(r1.interest - Decimal("-113.383434")) <= TOL
    assert abs(r1.insurance - Decimal("-4.417835")) <= TOL
    assert abs(r1.final_balance - Decimal("9129.374137")) <= TOL
    # Cuotón de la fila 1 (columnas SICF/ICF/SegDesCF/SFCF).
    assert abs(r1.balloon_initial - Decimal("3959.009297")) <= TOL
    assert abs(r1.balloon_interest - Decimal("-49.787770")) <= TOL
    assert abs(r1.balloon_insurance - Decimal("-1.939915")) <= TOL
    assert abs(r1.balloon_final - Decimal("4010.736981")) <= TOL
    # Fila 4 (gracia P): cuota = interés; el saldo no baja.
    r4 = sched.rows[3]
    assert abs(r4.payment - Decimal("-117.715122")) <= TOL
    assert r4.amortization == Decimal(0)
    assert abs(r4.final_balance - Decimal("9360.436605")) <= TOL


def test_golden_excel_regular_payment_and_close() -> None:
    sched = _excel_schedule()
    # Fila 7 (primera S): cuota J38 con desgravamen dentro de la anualidad.
    r7 = sched.rows[6]
    assert abs(r7.payment - Decimal("-379.158434")) <= TOL
    assert abs(r7.amortization - Decimal("-256.856698")) <= TOL
    assert abs(r7.insurance - Decimal("-4.586614")) <= TOL
    # La cuota es constante de la fila 7 a la 36 y el saldo cierra en 0.
    for r in sched.rows[6:36]:
        assert abs(r.payment - r7.payment) <= TOL
    assert abs(sched.rows[35].final_balance) <= TOL


def test_golden_excel_balloon_period_n_plus_1() -> None:
    sched = _excel_schedule()
    r37 = sched.rows[36]
    assert r37.period == 37
    assert r37.payment == Decimal(0)
    assert abs(r37.balloon_initial - Decimal("6317.457270")) <= TOL
    assert abs(r37.balloon_interest - Decimal("-79.447176")) <= TOL
    assert abs(r37.balloon_insurance - Decimal("-3.095554")) <= TOL
    # ACF: el cuotón se paga íntegro (= CF = 6,400) y su saldo cierra en 0.
    assert abs(r37.balloon_amortization - Decimal("-6400")) <= TOL
    assert abs(r37.balloon_final) <= TOL


def test_ci_reduces_to_pure_french_without_balloon() -> None:
    """Sin balón, sin desgravamen y sin costes: francés puro (ejemplo TES 9 %)."""
    periods = [SchedulePeriodInput(i, TES_9, "S") for i in range(1, 9)]
    sched = CompraInteligenteService.build_schedule(
        vehicle_price=Decimal("1440000"),
        initial_payment_pct=Decimal("0"),
        balloon_pct=Decimal("0"),
        periods=periods,
    )
    assert sched.amount_financed == Decimal("1440000")
    assert sched.balloon_present_value == Decimal(0)
    assert len(sched.rows) == 8
    assert abs(sched.rows[0].payment - Decimal("-217454.11")) <= TOL
    assert abs(sched.rows[-1].final_balance) <= TOL


def test_ci_with_initial_and_balloon_constant_rate() -> None:
    price = Decimal("60000")
    periods = [
        SchedulePeriodInput(i, tep_from_tea(Decimal("0.12"), 30), "S")
        for i in range(1, 37)
    ]
    sched = CompraInteligenteService.build_schedule(
        vehicle_price=price,
        initial_payment_pct=Decimal("0.20"),
        balloon_pct=Decimal("0.30"),
        periods=periods,
    )
    assert sched.initial_payment == Decimal("12000.00")
    assert sched.balloon == Decimal("18000.00")
    assert sched.amount_financed == Decimal("48000.00")
    assert len(sched.rows) == 37
    # El cronograma regular amortiza exactamente su principal (saldo cierra).
    total_amort = sum((-r.amortization for r in sched.rows), Decimal(0))
    assert abs(total_amort - sched.regular_principal) <= TOL
    assert abs(sched.rows[35].final_balance) <= TOL
    # El cuotón paga el balón íntegro en N+1.
    assert abs(sched.rows[36].balloon_amortization + sched.balloon) <= TOL
    assert abs(sched.rows[36].balloon_final) <= TOL


def test_ci_supports_total_grace() -> None:
    """La gracia total capitaliza el interés y el plan sigue cerrando en 0."""
    tem = tep_from_tea(Decimal("0.12"), 30)
    grace = ["T", "T"] + ["S"] * 22
    periods = [
        SchedulePeriodInput(i + 1, tem, g) for i, g in enumerate(grace)
    ]
    sched = CompraInteligenteService.build_schedule(
        vehicle_price=Decimal("50000"),
        initial_payment_pct=Decimal("0.20"),
        balloon_pct=Decimal("0.25"),
        periods=periods,
    )
    r1 = sched.rows[0]
    assert r1.payment == Decimal(0)
    assert r1.final_balance > r1.initial_balance  # capitaliza
    assert abs(sched.rows[23].final_balance) <= TOL
    assert abs(sched.rows[24].balloon_final) <= TOL


def test_ci_rejects_grace_in_final_period() -> None:
    periods = [
        SchedulePeriodInput(1, TES_9, "S"),
        SchedulePeriodInput(2, TES_9, "T"),
    ]
    with pytest.raises(DomainError):
        CompraInteligenteService.build_schedule(
            Decimal("10000"), Decimal("0.1"), Decimal("0.2"), periods
        )


def test_ci_validates_pct_bounds() -> None:
    periods = [SchedulePeriodInput(1, TES_9, "S")]
    with pytest.raises(DomainError):
        CompraInteligenteService.build_schedule(
            Decimal("10000"), Decimal("-0.1"), Decimal("0.2"), periods
        )
    with pytest.raises(DomainError):
        CompraInteligenteService.build_schedule(
            Decimal("10000"), Decimal("0.5"), Decimal("0.5"), periods
        )


def test_ci_variable_rate_balances_to_zero() -> None:
    """Tasa variable: la cuota se recalcula y el plan cierra en 0."""
    tem9 = tep_from_tea(Decimal("0.09"), 30)
    tem8 = tep_from_tea(Decimal("0.08"), 30)
    periods = [
        SchedulePeriodInput(i, tem9 if i <= 12 else tem8, "S") for i in range(1, 25)
    ]
    sched = CompraInteligenteService.build_schedule(
        vehicle_price=Decimal("50000"),
        initial_payment_pct=Decimal("0.20"),
        balloon_pct=Decimal("0.25"),
        periods=periods,
    )
    assert abs(sched.rows[23].final_balance) <= TOL
    assert abs(sched.rows[24].balloon_final) <= TOL
