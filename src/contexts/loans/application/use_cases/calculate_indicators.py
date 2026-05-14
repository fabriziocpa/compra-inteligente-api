from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from src.contexts.loans.domain.repositories import LoanRepository
from src.contexts.loans.domain.services.financial_indicators_service import (
    FinancialIndicatorsService,
)
from src.shared.domain.exceptions import DomainError


@dataclass(frozen=True, slots=True)
class IndicatorsResult:
    van_at_period_rate: Decimal | None
    tir_per_period: Decimal
    tcea: Decimal
    cashflows: list[Decimal]


class CalculateIndicatorsUseCase:
    def __init__(self, repo: LoanRepository) -> None:
        self._repo = repo

    async def execute(self, loan_id: UUID, discount_rate_per_period: Decimal | None = None) -> IndicatorsResult:
        loan = await self._repo.get(loan_id)
        if not loan.schedule:
            raise DomainError("Loan has no schedule. Run /schedule first.")

        # t=0: net disbursement received by the debtor.
        # Under Compra Inteligente / Francés the debtor receives MF = price - CI.
        # (Initial charges could subtract from this; current charge model is per-period.)
        disbursement = loan.terms.vehicle_price * (
            Decimal(1) - loan.terms.initial_payment_pct
        )

        cashflows: list[Decimal] = [disbursement]
        for entry in loan.schedule:
            outflow = entry.payment  # negative
            for charge in loan.additional_charges:
                outflow -= charge.amount_for(
                    period=entry.period,
                    initial_balance=entry.initial_balance,
                    payment=entry.payment,
                )
            cashflows.append(outflow)

        tir = FinancialIndicatorsService.tir(cashflows)
        tcea = FinancialIndicatorsService.tcea(tir, loan.terms.frequency_days)
        van: Decimal | None = None
        if discount_rate_per_period is not None:
            van = FinancialIndicatorsService.van(cashflows, discount_rate_per_period)

        return IndicatorsResult(
            van_at_period_rate=van,
            tir_per_period=tir,
            tcea=tcea,
            cashflows=cashflows,
        )
