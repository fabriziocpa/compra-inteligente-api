from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from src.shared.domain.money import Currency


@dataclass(frozen=True, slots=True)
class LoanTerms:
    currency: Currency
    vehicle_price: Decimal
    initial_payment_pct: Decimal
    balloon_pct: Decimal
    term_periods: int
    frequency_days: int

    @property
    def is_compra_inteligente(self) -> bool:
        return self.balloon_pct > Decimal(0)
