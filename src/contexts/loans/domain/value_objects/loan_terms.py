"""Términos económicos del préstamo (objeto de valor inmutable).

``initial_payment_pct`` y ``balloon_pct`` son fracciones (0.20 = 20 %).
Si hay cuota balón (%final > 0), el plan es de la modalidad Compra
Inteligente; si no, es un francés puro sobre precio − cuota inicial.

Campos del modelo Interbank (hoja «Compra Inteligente IB»):

* ``financed_costs`` — costes/gastos iniciales que se FINANCIAN (notariales,
  registrales, tasación, comisiones marcadas «Préstamo» en la hoja). Se suman
  al monto del préstamo: ``Prestamo = PV − CI + financed_costs``.
* ``desgravamen_monthly_pct`` — % MENSUAL del seguro de desgravamen sobre el
  saldo (celda ``pSegDes``). La tasa del período es
  ``pSegDesPer = pSegDes × frec/30`` y va DENTRO de la cuota francesa:
  la cuota se calcula con ``PMT(TEP + pSegDesPer, …)``.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from src.shared.domain.money import Currency


@dataclass(frozen=True, slots=True)
class LoanTerms:
    currency: Currency
    vehicle_price: Decimal
    initial_payment_pct: Decimal
    balloon_pct: Decimal
    term_periods: int
    frequency_days: int
    financed_costs: Decimal = Decimal(0)
    desgravamen_monthly_pct: Decimal = Decimal(0)

    @property
    def is_compra_inteligente(self) -> bool:
        return self.balloon_pct > Decimal(0)

    @property
    def desgravamen_pct_per_period(self) -> Decimal:
        """pSegDesPer = pSegDes × frec/30 (meses de 30 días)."""
        return self.desgravamen_monthly_pct * Decimal(self.frequency_days) / Decimal(30)

    @property
    def loan_principal(self) -> Decimal:
        """Monto del préstamo: PV − cuota inicial + costes financiados."""
        return (
            self.vehicle_price * (Decimal(1) - self.initial_payment_pct)
            + self.financed_costs
        )
