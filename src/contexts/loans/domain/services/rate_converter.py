"""Conversions between interest-rate conventions.

All computations use ``Decimal`` exclusively. ``getcontext().prec`` is set to 28
in ``src.shared.domain.__init__`` to give us enough precision for chained
exponentiations.

Conventions follow the class material:

* TEA (Tasa Efectiva Anual)
* TEP (Tasa Efectiva por Periodo) — period of ``d`` days
* TNA (Tasa Nominal Anual) capitalized ``m`` times per year
* Year base defaults to 360 days (banking convention used in class).
"""

from __future__ import annotations

from decimal import Decimal


def _pow_decimal(base: Decimal, exponent: Decimal) -> Decimal:
    """Power that supports a Decimal exponent by routing through ln/exp."""
    if exponent == Decimal(0):
        return Decimal(1)
    if exponent == exponent.to_integral_value():
        return base ** int(exponent)
    return (base.ln() * exponent).exp()


def tep_from_tea(
    tea: Decimal,
    days_in_period: int,
    days_in_year: int = 360,
) -> Decimal:
    """TEP = (1 + TEA)^(d / 360) - 1."""
    if days_in_period <= 0:
        raise ValueError("days_in_period must be positive")
    if days_in_year <= 0:
        raise ValueError("days_in_year must be positive")
    exponent = Decimal(days_in_period) / Decimal(days_in_year)
    return _pow_decimal(Decimal(1) + tea, exponent) - Decimal(1)


def tea_from_tna_nominal(tna: Decimal, capitalizations_per_year: int) -> Decimal:
    """TEA = (1 + TNA / m)^m - 1."""
    if capitalizations_per_year <= 0:
        raise ValueError("capitalizations_per_year must be positive")
    m = Decimal(capitalizations_per_year)
    return (Decimal(1) + tna / m) ** capitalizations_per_year - Decimal(1)


def tep_from_tna_nominal(
    tna: Decimal,
    capitalizations_per_year: int,
    days_in_period: int,
    days_in_year: int = 360,
) -> Decimal:
    """Compose TNA → TEA → TEP."""
    tea = tea_from_tna_nominal(tna, capitalizations_per_year)
    return tep_from_tea(tea, days_in_period, days_in_year)
