"""Compra Inteligente schedule service.

Models the Peruvian "Compra Inteligente" modality:

* The buyer pays an *initial payment* (CI) at t=0.
* A regular French payment R is paid at the end of each of N periods.
* A balloon (cuota final / CF) is paid at the end of period N.

The principal MF = vehicle_price - CI.  Equating present values at the periodic
rate i (TEP) gives, for a constant rate and no grace::

        MF = R * a(N, i) + CF / (1+i)^N
   →    R = (MF - CF / (1+i)^N) / a(N, i)

For variable rate or grace periods we delegate to ``FrenchAmortizationService``
treating the balloon as an extra amortization paid in the final period.
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
    initial_payment: Decimal
    balloon: Decimal
    amount_financed: Decimal
    rows: list[ScheduleRow]
    additional_charges_per_period: list[Decimal]


def _annuity_factor(tep: Decimal, n: int) -> Decimal:
    one_plus = Decimal(1) + tep
    factor = one_plus**n
    return (factor - Decimal(1)) / (tep * factor)


def _present_value(amount: Decimal, tep: Decimal, n: int) -> Decimal:
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
                    # Final period: regular payment + balloon
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
    """Variable-rate / grace path.

    We find the regular payment R that, when applied to a French schedule on the
    full MF with the supplied period structure, leaves exactly ``cf`` outstanding
    at the end of the final period.  The final-period row is then rewritten so
    its amortization absorbs the remaining balance (the balloon).
    """
    n = len(periods)
    last_grace: GraceType = periods[-1].grace_type
    if last_grace != "S":
        raise DomainError("Final period must not be in grace for Compra Inteligente")

    # We build a synthetic French schedule where the *effective principal*
    # has been reduced by the present value of CF, so the resulting payment R
    # is the regular instalment of the Compra Inteligente plan.
    # Discount CF through every period back to t=0 using each period's TEP.
    discount = Decimal(1)
    for p in periods:
        discount *= Decimal(1) + p.tep
    effective_principal = mf - cf / discount
    if effective_principal <= Decimal(0):
        raise DomainError("Balloon too large relative to amount financed")

    synthetic = FrenchAmortizationService.build_schedule(effective_principal, periods)

    # Re-derive the *real* schedule against MF using the payments from the
    # synthetic schedule for periods 1..n-1.  Period n absorbs the balloon.
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
