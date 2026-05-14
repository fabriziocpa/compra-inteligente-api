from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal

from src.contexts.loans.domain.services.rate_converter import (
    tep_from_tea,
    tep_from_tna_nominal,
)

RateKind = Literal["TEA", "TNA"]


@dataclass(frozen=True, slots=True)
class RateSegment:
    """A contiguous block of periods sharing the same rate."""

    from_period: int
    to_period: int
    rate_kind: RateKind
    rate_value: Decimal
    capitalizations_per_year: int | None = None  # required for TNA


@dataclass(frozen=True, slots=True)
class InterestRateSpec:
    days_in_period: int
    segments: tuple[RateSegment, ...] = field(default_factory=tuple)
    days_in_year: int = 360

    def tep_for_period(self, period: int) -> Decimal:
        for seg in self.segments:
            if seg.from_period <= period <= seg.to_period:
                if seg.rate_kind == "TEA":
                    return tep_from_tea(seg.rate_value, self.days_in_period, self.days_in_year)
                if seg.rate_kind == "TNA":
                    if seg.capitalizations_per_year is None:
                        raise ValueError("TNA segment requires capitalizations_per_year")
                    return tep_from_tna_nominal(
                        seg.rate_value,
                        seg.capitalizations_per_year,
                        self.days_in_period,
                        self.days_in_year,
                    )
        raise ValueError(f"No rate segment covers period {period}")
