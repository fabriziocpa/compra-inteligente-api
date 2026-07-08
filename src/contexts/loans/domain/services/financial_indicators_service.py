"""VAN, TIR y TCEA calculados desde el punto de vista del DEUDOR.

Procedimiento
=============
El flujo de caja del deudor se arma así:

* ``cashflows[0]``: el monto del préstamo RECIBIDO (positivo). En la variante
  Interbank es ``Prestamo = PV − CI + costes iniciales financiados``.
* ``cashflows[t>0]``: el egreso total del período (negativo) = cuota del plan
  más cargos adicionales (seguros, comisiones, portes). Con cuota balón el
  flujo llega hasta el período N+1, donde se paga el cuotón (= CF) más los
  cargos de ese período.

Indicadores:

* **VAN** (valor actual neto) a una tasa de descuento del período ``i``::

      VAN = Σ  FC_t / (1+i)^t

  Si VAN > 0 a la tasa de oportunidad del deudor, la financiación le conviene.

* **TIR** del período: la tasa que hace VAN = 0. Se resuelve numéricamente con
  ``scipy.optimize.brentq`` tras acotar un cambio de signo; solo el interior
  del optimizador usa ``float``, el resultado vuelve a ``Decimal``. Sin cargos
  adicionales, la TIR del período coincide con la TEP del préstamo.

* **TCEA** (tasa de costo efectivo anual, norma de transparencia SBS): la TIR
  del período anualizada con el año bancario de 360 días::

      TCEA = (1 + TIR)^(360/d) − 1
"""

from __future__ import annotations

from decimal import Decimal

from scipy.optimize import brentq  # type: ignore[import-untyped]

from src.contexts.loans.domain.services.rate_converter import _pow_decimal
from src.shared.domain.exceptions import ConvergenceError, DomainError


class FinancialIndicatorsService:
    @staticmethod
    def van(cashflows: list[Decimal], discount_rate_per_period: Decimal) -> Decimal:
        """VAN = Σ FC_t / (1+i)^t con ``i`` = tasa de descuento del período."""
        if not cashflows:
            raise DomainError("cashflows must not be empty")
        i = discount_rate_per_period
        one_plus = Decimal(1) + i
        total = Decimal(0)
        factor = Decimal(1)
        for cf in cashflows:
            total += cf / factor
            factor *= one_plus
        return total

    @staticmethod
    def tir(cashflows: list[Decimal], guess: Decimal = Decimal("0.01")) -> Decimal:
        """TIR del período: raíz de VAN(i) = 0, resuelta con Brent."""
        if len(cashflows) < 2:
            raise DomainError("cashflows must contain at least two entries")
        flows = [float(cf) for cf in cashflows]

        def npv(rate: float) -> float:
            total = 0.0
            denom = 1.0
            one_plus = 1.0 + rate
            for cf in flows:
                total += cf / denom
                denom *= one_plus
            return total

        # Acotar la raíz: se parte de un intervalo amplio y, si el signo no
        # cambia, se prueban cotas intermedias.
        lo, hi = -0.9999, 10.0
        try:
            if npv(lo) * npv(hi) > 0:
                found = False
                for candidate in (-0.5, -0.1, 0.0, 0.05, 0.1, 0.5, 1.0, 5.0):
                    if npv(lo) * npv(candidate) < 0:
                        hi = candidate
                        found = True
                        break
                if not found:
                    raise ConvergenceError("TIR: unable to bracket a sign change")
            root = brentq(npv, lo, hi, maxiter=200, xtol=1e-12)
        except ConvergenceError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ConvergenceError(f"TIR solver failed: {exc}") from exc
        return Decimal(str(root))

    @staticmethod
    def tcea(
        tir_per_period: Decimal,
        days_in_period: int,
        days_in_year: int = 360,
    ) -> Decimal:
        """TCEA = (1 + TIR del período)^(360/d) − 1 (año bancario)."""
        if days_in_period <= 0:
            raise DomainError("days_in_period must be positive")
        exponent = Decimal(days_in_year) / Decimal(days_in_period)
        return _pow_decimal(Decimal(1) + tir_per_period, exponent) - Decimal(1)
