"""VAN, TIR and TCEA computed from the debtor's perspective.

Cashflow sign convention:
    * ``cashflows[0]`` is the *net disbursement received* by the debtor (positive).
    * ``cashflows[t>0]`` is the *negative* total outflow of period t (payment plus
      additional charges).

``TIR`` is solved with ``scipy.optimize.brentq`` after bracketing.  ``float`` is
only used inside the optimiser; the result is cast back to ``Decimal``.
"""

from __future__ import annotations

from decimal import Decimal

from scipy.optimize import brentq  # type: ignore[import-untyped]

from src.contexts.loans.domain.services.rate_converter import _pow_decimal
from src.shared.domain.exceptions import ConvergenceError, DomainError


class FinancialIndicatorsService:
    @staticmethod
    def van(cashflows: list[Decimal], discount_rate_per_period: Decimal) -> Decimal:
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

        # Bracket the root.  Start from the guess and expand outward.
        lo, hi = -0.9999, 10.0
        try:
            if npv(lo) * npv(hi) > 0:
                # Sign doesn't change in the default bracket — try a tighter search.
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
        if days_in_period <= 0:
            raise DomainError("days_in_period must be positive")
        exponent = Decimal(days_in_year) / Decimal(days_in_period)
        return _pow_decimal(Decimal(1) + tir_per_period, exponent) - Decimal(1)
