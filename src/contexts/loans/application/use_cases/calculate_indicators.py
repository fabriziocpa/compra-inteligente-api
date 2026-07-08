"""Caso de uso: indicadores financieros (VAN, TIR, TCEA) del préstamo.

El flujo de caja se arma desde el punto de vista del deudor con el cronograma
YA calculado (incluidos sus cargos por período), de modo que los indicadores
siempre coinciden con el plan que se le muestra al cliente:

* t = 0: el monto del préstamo (positivo): precio − cuota inicial + costes
  financiados (celda ``Prestamo`` de la hoja Interbank).
* t = 1..n(+1): cuota total del período (cuota del plan + cargos + desgravamen
  pagado aparte en gracia + cuotón en N+1), negativa.
"""

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

        disbursement = loan.terms.loan_principal

        # total_payment ya incluye los cargos del período (con signo negativo).
        cashflows: list[Decimal] = [disbursement]
        cashflows.extend(entry.total_payment for entry in loan.schedule)

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
