"""Costo/gasto inicial del crédito (se paga UNA sola vez al inicio).

Son los conceptos de la hoja Interbank (gastos notariales, registrales,
tasación, comisiones de estudio/activación…). Cada uno se marca como:

* ``financed=True`` — «Préstamo» en la hoja: el monto se FINANCIA y se suma
  al monto del préstamo (``Prestamo = PV − CI + Σ financiados``).
* ``financed=False`` — «Al contado»: el deudor lo paga por separado en el
  desembolso. Es informativo: NO entra al préstamo ni a los flujos de
  TIR/TCEA/VAN (fiel a la hoja de referencia).

``LoanTerms.financed_costs`` sigue siendo el insumo del motor; cuando el
préstamo trae el desglose, ese campo se deriva como la suma de los
financiados (ver router/use cases).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class InitialCost:
    name: str
    amount: Decimal
    financed: bool = True


def financed_total(costs: tuple[InitialCost, ...] | list[InitialCost]) -> Decimal:
    """Suma de los costos marcados «financiado» (insumo de ``financed_costs``)."""
    return sum((c.amount for c in costs if c.financed), Decimal(0))


def cash_total(costs: tuple[InitialCost, ...] | list[InitialCost]) -> Decimal:
    """Suma de los costos pagados al contado (informativo)."""
    return sum((c.amount for c in costs if not c.financed), Decimal(0))
