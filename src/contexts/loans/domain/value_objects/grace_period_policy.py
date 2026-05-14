from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from src.contexts.loans.domain.services.french_amortization_service import GraceType

GraceCode = Literal["T", "P", "S"]


@dataclass(frozen=True, slots=True)
class GracePeriodPolicy:
    """Per-period grace assignment."""

    periods: tuple[GraceCode, ...] = field(default_factory=tuple)

    def grace_for(self, period: int, total_periods: int) -> GraceType:
        if not self.periods:
            return "S"
        if period < 1 or period > total_periods:
            raise ValueError(f"period {period} out of range 1..{total_periods}")
        if period > len(self.periods):
            return "S"
        return self.periods[period - 1]
