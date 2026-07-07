"""Cargo adicional del crédito (seguro desgravamen, comisiones, portes…).

Procedimiento de evaluación por período: cada cargo define una *base* y un
*valor*; el importe del período se obtiene así:

* ``fixed``:       importe = valor (monto fijo en la moneda del préstamo).
* ``balance_pct``: importe = saldo inicial del período × valor (tasa 0..1).
* ``payment_pct``: importe = |cuota del período| × valor (tasa 0..1).

El rango ``applies_from_period .. applies_to_period`` acota en qué períodos
se cobra (``None`` = hasta el final). Estos importes se suman a la cuota para
formar la *cuota total* que exige la norma de transparencia, y entran al
flujo de caja con el que se calculan TIR/TCEA/VAN.
"""

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
    value: Decimal  # monto absoluto si es ``fixed``; tasa (0..1) en los demás
    applies_from_period: int = 1
    applies_to_period: int | None = None  # None = hasta el final

    def applies_in(self, period: int) -> bool:
        """¿El cargo se cobra en este período?"""
        if period < self.applies_from_period:
            return False
        if self.applies_to_period is not None and period > self.applies_to_period:
            return False
        return True

    def amount_for(self, period: int, initial_balance: Decimal, payment: Decimal) -> Decimal:
        """Importe (positivo) del cargo en el período, según su base."""
        if not self.applies_in(period):
            return Decimal(0)
        if self.basis == "fixed":
            return self.value
        if self.basis == "balance_pct":
            return initial_balance * self.value
        if self.basis == "payment_pct":
            return abs(payment) * self.value
        raise ValueError(f"Unknown basis: {self.basis}")
