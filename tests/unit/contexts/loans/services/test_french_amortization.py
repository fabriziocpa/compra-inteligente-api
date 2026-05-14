from decimal import Decimal

import pytest

from src.contexts.loans.domain.services.french_amortization_service import (
    FrenchAmortizationService,
    SchedulePeriodInput,
)
from src.contexts.loans.domain.services.rate_converter import tep_from_tea

PRINCIPAL = Decimal("1440000")
TES_9 = tep_from_tea(Decimal("0.09"), 180)
TES_8 = tep_from_tea(Decimal("0.08"), 180)
TOL = Decimal("0.01")


def _approx(a: Decimal, b: Decimal, tol: Decimal = TOL) -> bool:
    return abs(a - b) <= tol


def test_example_1_french_constant_rate() -> None:
    """Préstamo USD 1,440,000, 4 años semestral, TEA 9% constante."""
    periods = [SchedulePeriodInput(i, TES_9, "S") for i in range(1, 9)]
    rows = FrenchAmortizationService.build_schedule(PRINCIPAL, periods)
    assert _approx(rows[0].payment, Decimal("-217454.11"))
    assert _approx(rows[0].final_balance, Decimal("1285950.02"))
    assert _approx(rows[-1].final_balance, Decimal("0"), Decimal("0.10"))


def test_example_2_french_rate_change_at_period_5() -> None:
    """TEA 9% en periodos 1-4, 8% en periodos 5-8."""
    periods = [
        SchedulePeriodInput(i, TES_9 if i <= 4 else TES_8, "S") for i in range(1, 9)
    ]
    rows = FrenchAmortizationService.build_schedule(PRINCIPAL, periods)
    assert _approx(rows[0].payment, Decimal("-217454.11"))
    assert _approx(rows[4].payment, Decimal("-215013.72"))
    assert _approx(rows[4].final_balance, Decimal("597555.18"))


def test_example_3_grace_total_period_1_then_rate_change() -> None:
    """Gracia Total en periodo 1, luego rate change 9%→8% en periodo 5."""
    periods = [
        SchedulePeriodInput(1, TES_9, "T"),
        *[SchedulePeriodInput(i, TES_9, "S") for i in range(2, 5)],
        *[SchedulePeriodInput(i, TES_8, "S") for i in range(5, 9)],
    ]
    rows = FrenchAmortizationService.build_schedule(PRINCIPAL, periods)
    assert _approx(rows[0].final_balance, Decimal("1503404.14"))
    assert _approx(rows[1].payment, Decimal("-254225.60"))


def test_example_4_grace_total_then_partial_then_rate_change() -> None:
    """T en 1, P en 2 y 3, S en 4-8 con rate change 9%→8% en periodo 5."""
    periods = [
        SchedulePeriodInput(1, TES_9, "T"),
        SchedulePeriodInput(2, TES_9, "P"),
        SchedulePeriodInput(3, TES_9, "P"),
        SchedulePeriodInput(4, TES_9, "S"),
        *[SchedulePeriodInput(i, TES_8, "S") for i in range(5, 9)],
    ]
    rows = FrenchAmortizationService.build_schedule(PRINCIPAL, periods)
    assert _approx(rows[2].final_balance, Decimal("1503404.14"))
    assert _approx(rows[3].payment, Decimal("-341538.35"))
    assert _approx(rows[4].payment, Decimal("-337705.42"))


def test_validation_principal_positive() -> None:
    with pytest.raises(ValueError):
        FrenchAmortizationService.build_schedule(
            Decimal("0"), [SchedulePeriodInput(1, TES_9, "S")]
        )


def test_balance_zeroes_out_constant_rate() -> None:
    periods = [SchedulePeriodInput(i, TES_9, "S") for i in range(1, 9)]
    rows = FrenchAmortizationService.build_schedule(PRINCIPAL, periods)
    assert abs(rows[-1].final_balance) <= Decimal("0.10")
