"""Fila del cronograma de pagos (plan de pagos del método francés).

Convención de signos de la metodología del curso: interés, cuota y
amortización son NEGATIVOS porque son egresos del deudor. Los cargos
adicionales (seguros, comisiones, portes) también se guardan con signo
negativo para que la cuota total sea simplemente cuota + cargos.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ChargeAmount:
    """Cargo adicional ya evaluado para un período concreto.

    ``amount`` es el importe NEGATIVO (egreso) que ese cargo genera en el
    período, calculado según su base (monto fijo, % del saldo o % de la cuota).
    """

    name: str
    kind: str  # seguro | comision | portes | otro
    amount: Decimal


@dataclass(frozen=True, slots=True)
class PaymentScheduleEntry:
    period: int
    grace_type: str  # S = sin gracia, P = parcial, T = total
    initial_balance: Decimal
    interest: Decimal
    payment: Decimal
    amortization: Decimal
    final_balance: Decimal
    charges: tuple[ChargeAmount, ...] = ()

    @property
    def charges_total(self) -> Decimal:
        """Suma (negativa) de todos los cargos del período."""
        return sum((c.amount for c in self.charges), Decimal(0))

    @property
    def total_payment(self) -> Decimal:
        """Cuota total del período: cuota del plan + cargos adicionales.

        Es el desembolso real del deudor en el período (norma de transparencia:
        la cuota mostrada al cliente debe incluir seguros y portes).
        """
        return self.payment + self.charges_total
