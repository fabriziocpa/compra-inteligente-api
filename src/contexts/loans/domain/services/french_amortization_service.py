"""French (vencido ordinario) amortization service.

Supports variable rate (TEP changing between periods) and grace periods:
    * ``T`` total — payment 0, amortization 0, interest capitalises (SF = SI*(1+TEP)).
    * ``P`` partial — payment equals interest, amortization 0, SF unchanged.
    * ``S`` standard — fixed (recomputed) French payment.

Signs follow the spec: interest, payment and amortization are NEGATIVE (egresos del deudor).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

GraceType = Literal["T", "P", "S"]


@dataclass(frozen=True, slots=True)
class SchedulePeriodInput:
    period_number: int
    tep: Decimal
    grace_type: GraceType


@dataclass(frozen=True, slots=True)
class ScheduleRow:
    period: int
    grace_type: str
    initial_balance: Decimal
    interest: Decimal
    payment: Decimal
    amortization: Decimal
    final_balance: Decimal


def _french_payment(balance: Decimal, tep: Decimal, periods_remaining: int) -> Decimal:
    """Return the *negative* French payment R for ``periods_remaining`` periods."""
    one_plus_tep = Decimal(1) + tep
    factor = one_plus_tep**periods_remaining
    annuity = (factor - Decimal(1)) / (tep * factor)
    return -(balance / annuity)


class FrenchAmortizationService:
    """Pure-domain service. No I/O, no DB."""

    @staticmethod
    def build_schedule(
        principal: Decimal,
        periods: list[SchedulePeriodInput],
    ) -> list[ScheduleRow]:
        if principal <= Decimal(0):
            raise ValueError("principal must be positive")
        if not periods:
            raise ValueError("periods must not be empty")

        n = len(periods)
        rows: list[ScheduleRow] = []
        si = principal
        current_r: Decimal | None = None
        prev_tep: Decimal | None = None
        prev_grace: GraceType | None = None

        for idx, p in enumerate(periods, start=1):
            recompute = (
                current_r is None
                or (prev_tep is not None and p.tep != prev_tep)
                or prev_grace in ("T", "P")
            )

            if p.grace_type == "S" and recompute:
                remaining = n - idx + 1
                current_r = _french_payment(si, p.tep, remaining)

            interest = -(si * p.tep)

            if p.grace_type == "T":
                payment = Decimal(0)
                amortization = Decimal(0)
                sf = si * (Decimal(1) + p.tep)
            elif p.grace_type == "P":
                payment = interest
                amortization = Decimal(0)
                sf = si
            elif p.grace_type == "S":
                assert current_r is not None
                payment = current_r
                amortization = payment - interest
                sf = si + amortization
            else:
                raise ValueError(f"Unknown grace_type: {p.grace_type}")

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
            prev_tep = p.tep
            prev_grace = p.grace_type

        return rows
