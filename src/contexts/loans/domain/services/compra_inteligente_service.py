"""Cronograma de la modalidad «Compra Inteligente» (crédito con cuota balón).

Procedimiento
=============
La modalidad peruana «Compra Inteligente» combina tres pagos:

* Una *cuota inicial* CI = precio × %inicial, pagada en t=0.
* ``N`` cuotas francesas regulares ``R`` al vencimiento de cada período.
* Una *cuota final* (balón) CF = precio × %final, pagada junto con la cuota
  del último período.

El monto financiado es MF = precio − CI. Igualando valores presentes a la
tasa del período ``i`` (TEP), con tasa constante y sin gracia::

    MF = R * a(N, i) + CF / (1+i)^N
  → R  = ( MF − CF / (1+i)^N ) / a(N, i)

donde ``a(N, i) = [(1+i)^N − 1] / [i(1+i)^N]`` es el factor de la anualidad.
Es decir: la cuota regular se calcula sobre el principal *reducido* por el
valor presente del balón, y el balón se amortiza íntegro al final.

Con tasa variable o períodos de gracia no hay fórmula cerrada; la abstracción
reutiliza ``FrenchAmortizationService``:

1. Se descuenta CF a t=0 componiendo la TEP de *cada* período.
2. Se construye un cronograma francés *sintético* sobre el principal efectivo
   ``MF − VP(CF)``; sus cuotas son las cuotas regulares del plan.
3. Se recorre el saldo real (que parte de MF) aplicando esas cuotas; el último
   período amortiza todo el saldo restante (cuota regular + balón).

Los signos siguen la metodología: interés/cuota/amortización negativos.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from src.contexts.loans.domain.services.french_amortization_service import (
    FrenchAmortizationService,
    GraceType,
    SchedulePeriodInput,
    ScheduleRow,
)
from src.shared.domain.exceptions import DomainError


@dataclass(frozen=True, slots=True)
class CompraInteligenteSchedule:
    """Resultado del plan: CI, balón, monto financiado y filas del cronograma."""

    initial_payment: Decimal
    balloon: Decimal
    amount_financed: Decimal
    rows: list[ScheduleRow]
    additional_charges_per_period: list[Decimal]


def _annuity_factor(tep: Decimal, n: int) -> Decimal:
    """Factor de la anualidad a(n, i) = [(1+i)^n − 1] / [i(1+i)^n]."""
    one_plus = Decimal(1) + tep
    factor = one_plus**n
    return (factor - Decimal(1)) / (tep * factor)


def _present_value(amount: Decimal, tep: Decimal, n: int) -> Decimal:
    """Valor presente de un monto pagado dentro de ``n`` períodos a tasa TEP."""
    return amount / ((Decimal(1) + tep) ** n)


def _all_rates_equal(periods: list[SchedulePeriodInput]) -> bool:
    return all(p.tep == periods[0].tep for p in periods)


def _all_no_grace(periods: list[SchedulePeriodInput]) -> bool:
    return all(p.grace_type == "S" for p in periods)


class CompraInteligenteService:
    @staticmethod
    def build_schedule(
        vehicle_price: Decimal,
        initial_payment_pct: Decimal,
        balloon_pct: Decimal,
        periods: list[SchedulePeriodInput],
        additional_charges_per_period: list[Decimal] | None = None,
    ) -> CompraInteligenteSchedule:
        if vehicle_price <= Decimal(0):
            raise DomainError("vehicle_price must be positive")
        if not (Decimal(0) <= initial_payment_pct < Decimal(1)):
            raise DomainError("initial_payment_pct must be in [0, 1)")
        if not (Decimal(0) <= balloon_pct < Decimal(1)):
            raise DomainError("balloon_pct must be in [0, 1)")
        if initial_payment_pct + balloon_pct >= Decimal(1):
            raise DomainError("initial_payment_pct + balloon_pct must be < 1")
        if not periods:
            raise DomainError("periods must not be empty")

        n = len(periods)
        if additional_charges_per_period is None:
            additional_charges_per_period = [Decimal(0)] * n
        elif len(additional_charges_per_period) != n:
            raise DomainError("additional_charges_per_period length must match periods")

        ci = vehicle_price * initial_payment_pct
        cf = vehicle_price * balloon_pct
        mf = vehicle_price - ci

        if _all_rates_equal(periods) and _all_no_grace(periods):
            # Caso con fórmula cerrada: R = (MF − VP(CF)) / a(N, i).
            tep = periods[0].tep
            r = -((mf - _present_value(cf, tep, n)) / _annuity_factor(tep, n))
            rows: list[ScheduleRow] = []
            si = mf
            for idx, p in enumerate(periods, start=1):
                interest = -(si * tep)
                if idx < n:
                    payment = r
                    amortization = payment - interest
                    sf = si + amortization
                else:
                    # Último período: la amortización absorbe todo el saldo
                    # (cuota regular + balón) y el saldo cierra en 0.
                    amortization = -si
                    payment = interest + amortization
                    sf = Decimal(0)
                rows.append(
                    ScheduleRow(
                        period=p.period_number,
                        grace_type=p.grace_type,
                        initial_balance=si,
                        interest=interest,
                        payment=payment,
                        amortization=amortization,
                        final_balance=sf,
                    )
                )
                si = sf
        else:
            rows = _build_variable_rate_or_grace(mf, cf, periods)

        # Verificación de cierre: la amortización total debe igualar el MF.
        amort_total = sum((-row.amortization for row in rows), Decimal(0))
        if abs(amort_total - mf) > Decimal("0.01"):
            raise DomainError(
                f"Amortization total {amort_total} does not match MF {mf}"
            )

        return CompraInteligenteSchedule(
            initial_payment=ci,
            balloon=cf,
            amount_financed=mf,
            rows=rows,
            additional_charges_per_period=list(additional_charges_per_period),
        )


def _build_variable_rate_or_grace(
    mf: Decimal,
    cf: Decimal,
    periods: list[SchedulePeriodInput],
) -> list[ScheduleRow]:
    """Camino de tasa variable o con gracia (sin fórmula cerrada).

    Se busca la cuota regular R que deja exactamente ``cf`` de saldo al final
    del último período: se descuenta CF a t=0 componiendo la TEP de cada
    período, se arma un cronograma francés sintético sobre ``MF − VP(CF)`` y
    luego se reconstruye el cronograma real sobre MF usando esas cuotas; el
    último período amortiza el saldo restante (el balón).
    """
    n = len(periods)
    last_grace: GraceType = periods[-1].grace_type
    if last_grace != "S":
        raise DomainError("Final period must not be in grace for Compra Inteligente")

    # VP del balón: se compone la TEP de cada período (soporta tasa variable).
    discount = Decimal(1)
    for p in periods:
        discount *= Decimal(1) + p.tep
    effective_principal = mf - cf / discount
    if effective_principal <= Decimal(0):
        raise DomainError("Balloon too large relative to amount financed")

    synthetic = FrenchAmortizationService.build_schedule(effective_principal, periods)

    # Cronograma real contra MF con las cuotas del sintético (períodos 1..n-1);
    # el período n absorbe el balón.
    rows: list[ScheduleRow] = []
    si = mf
    for idx, (p, srow) in enumerate(zip(periods, synthetic, strict=True), start=1):
        interest = -(si * p.tep)
        if p.grace_type == "T":
            payment = Decimal(0)
            amortization = Decimal(0)
            sf = si * (Decimal(1) + p.tep)
        elif p.grace_type == "P":
            payment = interest
            amortization = Decimal(0)
            sf = si
        else:
            if idx < n:
                payment = srow.payment
                amortization = payment - interest
                sf = si + amortization
            else:
                amortization = -si
                payment = interest + amortization
                sf = Decimal(0)
        rows.append(
            ScheduleRow(
                period=p.period_number,
                grace_type=p.grace_type,
                initial_balance=si,
                interest=interest,
                payment=payment,
                amortization=amortization,
                final_balance=sf,
            )
        )
        si = sf
    return rows
