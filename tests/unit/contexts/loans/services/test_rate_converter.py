from decimal import Decimal

import pytest

from src.contexts.loans.domain.services.rate_converter import (
    tea_from_tna_nominal,
    tep_from_tea,
    tep_from_tna_nominal,
)


def _close(actual: Decimal, expected: Decimal, tol: Decimal = Decimal("0.0000000001")) -> bool:
    return abs(actual - expected) <= tol


@pytest.mark.parametrize(
    "tea,d,expected",
    [
        (Decimal("0.09"), 180, Decimal("0.0440307175")),  # TES from TEA 9%
        (Decimal("0.09"), 30, Decimal("0.0072073234")),   # TEM from TEA 9%
        (Decimal("0.08"), 180, Decimal("0.0392304845")),  # TES from TEA 8%
        (Decimal("0.095"), 120, Decimal("0.0307136846")),  # TEC from TEA 9.5%
        (Decimal("0.115"), 120, Decimal("0.0369511292")),  # TEC from TEA 11.5%
    ],
)
def test_tep_from_tea_matches_class_examples(tea: Decimal, d: int, expected: Decimal) -> None:
    actual = tep_from_tea(tea, d)
    assert _close(actual, expected, Decimal("0.0000001")), (
        f"tep_from_tea({tea}, {d}) = {actual}, expected {expected}"
    )


def test_tea_from_tna_nominal_known_value() -> None:
    # TNA 12% capitalizable mensualmente → TEA = (1 + 0.01)^12 - 1 ≈ 0.12682503
    tea = tea_from_tna_nominal(Decimal("0.12"), 12)
    assert abs(tea - Decimal("0.12682503")) <= Decimal("0.00000001")


def test_tep_from_tna_nominal_composes() -> None:
    # TNA 12% cap. mensual → TEM should be 1% (the underlying nominal step)
    tem = tep_from_tna_nominal(Decimal("0.12"), 12, 30)
    assert abs(tem - Decimal("0.01")) <= Decimal("0.0000001")


