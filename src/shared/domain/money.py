from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal
from enum import StrEnum

from src.shared.domain.exceptions import DomainError

_CENTS = Decimal("0.01")


class Currency(StrEnum):
    PEN = "PEN"
    USD = "USD"


@dataclass(frozen=True, slots=True)
class Money:
    amount: Decimal
    currency: Currency

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):  # type: ignore[unreachable]
            raise DomainError("Money.amount must be Decimal")

    def quantize(self) -> Money:
        return Money(self.amount.quantize(_CENTS, rounding=ROUND_HALF_EVEN), self.currency)

    def _check_currency(self, other: Money) -> None:
        if self.currency is not other.currency:
            raise DomainError(
                f"Currency mismatch: {self.currency.value} vs {other.currency.value}"
            )

    def __add__(self, other: Money) -> Money:
        self._check_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: Money) -> Money:
        self._check_currency(other)
        return Money(self.amount - other.amount, self.currency)

    def __mul__(self, factor: Decimal | int) -> Money:
        if isinstance(factor, int):
            factor = Decimal(factor)
        if not isinstance(factor, Decimal):
            raise DomainError("Money can only be multiplied by Decimal or int")
        return Money(self.amount * factor, self.currency)

    def __neg__(self) -> Money:
        return Money(-self.amount, self.currency)

    def is_zero(self) -> bool:
        return self.amount == Decimal(0)
