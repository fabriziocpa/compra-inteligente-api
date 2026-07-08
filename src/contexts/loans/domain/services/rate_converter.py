"""Conversión entre convenciones de tasas de interés (metodología del curso).

Todo el cálculo usa exclusivamente ``Decimal`` (``getcontext().prec = 28`` se
fija en ``src.shared.domain.__init__``) para no perder precisión en las
potencias encadenadas.

Convenciones de la separata:

* TEA — Tasa Efectiva Anual.
* TEP — Tasa Efectiva del Período de ``d`` días (TES si d=180, TEC si d=120,
  TEM si d=30, etc.).
* TNA — Tasa Nominal Anual capitalizable ``m`` veces al año.
* Año bancario de 360 días y meses de 30 días.

Procedimiento
=============
1. De TEA a TEP (equivalencia de tasas efectivas, proporción de días)::

       TEP = (1 + TEA)^(d/360) - 1

   Ej. de la separata: TEA 9% → TES (d=180) = 4.4030651 %.

2. De TNA a TEA (la nominal se divide entre sus capitalizaciones y se
   compone ``m`` veces)::

       TEA = (1 + TNA/m)^m - 1

3. De TNA a TEP: se compone TNA → TEA → TEP con las dos fórmulas anteriores.
"""

from __future__ import annotations

from decimal import Decimal


def _pow_decimal(base: Decimal, exponent: Decimal) -> Decimal:
    """Potencia con exponente ``Decimal`` (vía ln/exp cuando no es entero)."""
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
    """Composición TNA → TEA → TEP."""
    tea = tea_from_tna_nominal(tna, capitalizations_per_year)
    return tep_from_tea(tea, days_in_period, days_in_year)
