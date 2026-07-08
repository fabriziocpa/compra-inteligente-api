"""Política de gracia: qué tipo de período le toca a cada cuota.

Códigos (los mismos en la BD, el API y el UI):

* ``S`` — sin gracia (período normal, cuota francesa completa).
* ``P`` — gracia parcial (se paga solo el interés).
* ``T`` — gracia total (no se paga nada; el interés se capitaliza).

La lista ``periods`` es posicional: ``periods[k-1]`` es el código del período
``k``. Si la lista está vacía o es más corta que el plazo, los períodos sin
código se tratan como normales (``S``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from src.contexts.loans.domain.services.french_amortization_service import GraceType

GraceCode = Literal["T", "P", "S"]


@dataclass(frozen=True, slots=True)
class GracePeriodPolicy:
    periods: tuple[GraceCode, ...] = field(default_factory=tuple)

    def grace_for(self, period: int, total_periods: int) -> GraceType:
        """Código de gracia del período ``period`` (1-indexado)."""
        if not self.periods:
            return "S"
        if period < 1 or period > total_periods:
            raise ValueError(f"period {period} out of range 1..{total_periods}")
        if period > len(self.periods):
            return "S"
        return self.periods[period - 1]
