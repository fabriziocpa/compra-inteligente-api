from decimal import Decimal

import pytest

from src.contexts.loans.domain.services.financial_indicators_service import (
    FinancialIndicatorsService,
)
from src.contexts.loans.domain.services.french_amortization_service import (
    FrenchAmortizationService,
    SchedulePeriodInput,
)
from src.contexts.loans.domain.services.rate_converter import tep_from_tea
from src.shared.domain.exceptions import DomainError


def test_van_zero_when_discount_rate_equals_tir() -> None:
    # 100 → 12 cuotas iguales con TEM 1%
    tem = Decimal("0.01")
    n = 12
    one_plus = Decimal(1) + tem
    annuity = (one_plus**n - Decimal(1)) / (tem * one_plus**n)
    payment = Decimal("100") / annuity
    cashflows = [Decimal("100")] + [-payment for _ in range(n)]
    van = FinancialIndicatorsService.van(cashflows, tem)
    assert abs(van) <= Decimal("0.0000001")


def test_tir_recovers_tem() -> None:
    tem = Decimal("0.01")
    n = 12
    one_plus = Decimal(1) + tem
    annuity = (one_plus**n - Decimal(1)) / (tem * one_plus**n)
    payment = Decimal("100") / annuity
    cashflows = [Decimal("100")] + [-payment for _ in range(n)]
    tir = FinancialIndicatorsService.tir(cashflows)
    assert abs(tir - tem) <= Decimal("0.00001")


def test_tcea_from_monthly_tir() -> None:
    # TIR mensual de 1% → TCEA = (1.01)^12 - 1 ≈ 0.12682503
    tcea = FinancialIndicatorsService.tcea(Decimal("0.01"), 30)
    assert abs(tcea - Decimal("0.12682503")) <= Decimal("0.00000001")


def test_van_tir_tcea_for_example_1_french() -> None:
    """Para el préstamo ejemplo 1 (TEA 9% constante, semestral)."""
    tes = tep_from_tea(Decimal("0.09"), 180)
    periods = [SchedulePeriodInput(i, tes, "S") for i in range(1, 9)]
    rows = FrenchAmortizationService.build_schedule(Decimal("1440000"), periods)
    cashflows = [Decimal("1440000")] + [row.payment for row in rows]
    tir = FinancialIndicatorsService.tir(cashflows)
    tcea = FinancialIndicatorsService.tcea(tir, 180)
    assert abs(tir - tes) <= Decimal("0.00001")
    assert abs(tcea - Decimal("0.09")) <= Decimal("0.00001")


def test_van_raises_on_empty() -> None:
    with pytest.raises(DomainError):
        FinancialIndicatorsService.van([], Decimal("0.01"))


def test_tir_raises_on_singleton() -> None:
    with pytest.raises(DomainError):
        FinancialIndicatorsService.tir([Decimal("100")])
