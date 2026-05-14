from decimal import Decimal

import pytest

from src.contexts.loans.domain.services.compra_inteligente_service import (
    CompraInteligenteService,
)
from src.contexts.loans.domain.services.french_amortization_service import (
    SchedulePeriodInput,
)
from src.contexts.loans.domain.services.rate_converter import tep_from_tea
from src.shared.domain.exceptions import DomainError

TES_9 = tep_from_tea(Decimal("0.09"), 180)
TOL = Decimal("0.01")


def test_ci_constant_rate_no_balloon_matches_french() -> None:
    """Compra Inteligente con balloon = 0 y CI = 0 reduce al método francés puro."""
    periods = [SchedulePeriodInput(i, TES_9, "S") for i in range(1, 9)]
    sched = CompraInteligenteService.build_schedule(
        vehicle_price=Decimal("1440000"),
        initial_payment_pct=Decimal("0"),
        balloon_pct=Decimal("0"),
        periods=periods,
    )
    assert sched.initial_payment == Decimal("0")
    assert sched.balloon == Decimal("0")
    assert sched.amount_financed == Decimal("1440000")
    assert abs(sched.rows[0].payment - Decimal("-217454.11")) <= TOL


def test_ci_with_initial_and_balloon_constant_rate() -> None:
    price = Decimal("60000")
    ci_pct = Decimal("0.20")  # CI = 12,000
    cf_pct = Decimal("0.30")  # CF = 18,000
    periods = [
        SchedulePeriodInput(i, tep_from_tea(Decimal("0.12"), 30), "S")
        for i in range(1, 37)
    ]
    sched = CompraInteligenteService.build_schedule(
        vehicle_price=price,
        initial_payment_pct=ci_pct,
        balloon_pct=cf_pct,
        periods=periods,
    )
    assert sched.initial_payment == Decimal("12000.00")
    assert sched.balloon == Decimal("18000.00")
    assert sched.amount_financed == Decimal("48000.00")

    total_amort = sum((-r.amortization for r in sched.rows), Decimal(0))
    assert abs(total_amort - sched.amount_financed) <= TOL

    # Final period payment should include the balloon-magnitude amortization
    final = sched.rows[-1]
    assert abs(final.final_balance) <= TOL


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
    """Variable rate path: schedule must zero out and amortizations sum to MF."""
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
    total_amort = sum((-r.amortization for r in sched.rows), Decimal(0))
    assert abs(total_amort - sched.amount_financed) <= TOL
    assert abs(sched.rows[-1].final_balance) <= TOL
