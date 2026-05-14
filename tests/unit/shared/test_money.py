from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from src.shared.domain.exceptions import DomainError
from src.shared.domain.money import Currency, Money


def test_money_is_immutable() -> None:
    m = Money(Decimal("100"), Currency.PEN)
    with pytest.raises(FrozenInstanceError):
        m.amount = Decimal("0")  # type: ignore[misc]


def test_money_addition_same_currency() -> None:
    a = Money(Decimal("100.50"), Currency.USD)
    b = Money(Decimal("200.25"), Currency.USD)
    assert (a + b).amount == Decimal("300.75")
    assert (a + b).currency is Currency.USD


def test_money_addition_mismatched_currency_raises() -> None:
    with pytest.raises(DomainError):
        Money(Decimal("100"), Currency.PEN) + Money(Decimal("100"), Currency.USD)


def test_money_subtraction_mismatched_currency_raises() -> None:
    with pytest.raises(DomainError):
        Money(Decimal("100"), Currency.PEN) - Money(Decimal("50"), Currency.USD)


def test_money_multiplication_by_decimal() -> None:
    m = Money(Decimal("100"), Currency.PEN) * Decimal("0.5")
    assert m.amount == Decimal("50.0")


def test_money_quantize_rounds_half_even() -> None:
    m = Money(Decimal("1.235"), Currency.PEN).quantize()
    assert m.amount == Decimal("1.24")
    m2 = Money(Decimal("1.225"), Currency.PEN).quantize()
    assert m2.amount == Decimal("1.22")
