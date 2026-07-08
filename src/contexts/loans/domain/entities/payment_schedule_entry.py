"""Fila del cronograma de pagos (plan de pagos del método francés).

Convención de signos de la metodología del curso: interés, cuota y
amortización son NEGATIVOS porque son egresos del deudor. Los cargos
adicionales (seguros, comisiones, portes) también se guardan con signo
negativo para que la cuota total sea simplemente cuota + cargos.

Columnas del modelo Interbank:

* ``insurance`` — seguro de desgravamen del período sobre el saldo regular.
  En períodos normales (S) ya está DENTRO de ``payment`` («Cuota inc Seg
  Des»); en gracia T/P la cuota no lo contiene y se paga en efectivo.
* ``balloon_*`` — sub-cronograma del cuotón: saldo, interés, desgravamen y
  amortización de la cuota final, que se paga íntegra en el período N+1.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ChargeAmount:
    """Cargo adicional ya evaluado para un período concreto.

    ``amount`` es el importe NEGATIVO (egreso) que ese cargo genera en el
    período, calculado según su base (monto fijo, % del saldo, % de la cuota
    o % anual del precio del vehículo).
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
    insurance: Decimal = Decimal(0)
    balloon_initial: Decimal = Decimal(0)
    balloon_interest: Decimal = Decimal(0)
    balloon_insurance: Decimal = Decimal(0)
    balloon_amortization: Decimal = Decimal(0)
    balloon_final: Decimal = Decimal(0)

    @property
    def charges_total(self) -> Decimal:
        """Suma (negativa) de todos los cargos del período."""
        return sum((c.amount for c in self.charges), Decimal(0))

    @property
    def total_payment(self) -> Decimal:
        """Desembolso real del deudor en el período (columna ``Flujo``).

        Flujo = cuota + cargos + desgravamen pagado aparte (solo en gracia
        T/P, porque en S ya viene dentro de la cuota) + pago del cuotón
        (solo en el período N+1). Norma de transparencia: la cuota mostrada
        al cliente debe incluir seguros y portes.
        """
        total = self.payment + self.charges_total
        if self.grace_type in ("T", "P"):
            total += self.insurance
        total += self.balloon_amortization
        return total
