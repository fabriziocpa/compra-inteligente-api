from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

ChargeKind = Literal["seguro", "comision", "portes", "otro"]
ChargeBasis = Literal["fixed", "balance_pct", "payment_pct"]


@dataclass(frozen=True, slots=True)
class AdditionalCharge:
    name: str
    kind: ChargeKind
    basis: ChargeBasis
    value: Decimal  # absolute amount for ``fixed``; rate (0..1) for the others
    applies_from_period: int = 1
    applies_to_period: int | None = None  # None = until end

    def applies_in(self, period: int) -> bool:
        if period < self.applies_from_period:
            return False
        if self.applies_to_period is not None and period > self.applies_to_period:
            return False
        return True

    def amount_for(self, period: int, initial_balance: Decimal, payment: Decimal) -> Decimal:
        if not self.applies_in(period):
            return Decimal(0)
        if self.basis == "fixed":
            return self.value
        if self.basis == "balance_pct":
            return initial_balance * self.value
        if self.basis == "payment_pct":
            return abs(payment) * self.value
        raise ValueError(f"Unknown basis: {self.basis}")
