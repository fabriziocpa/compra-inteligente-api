"""Caso de uso: generar el cronograma de pagos de un préstamo.

Procedimiento:
1. Resuelve cada período (TEP del tramo vigente + tipo de gracia).
2. Construye el plan con el motor Interbank de Compra Inteligente cuando hay
   cuota balón, desgravamen o costes financiados (todos parte de ese modelo);
   con el francés puro en caso contrario.
3. Evalúa los cargos adicionales de cada período (seguro/comisión/portes)
   sobre el saldo, la cuota o el precio del vehículo, y los guarda junto a la
   fila para que el cronograma muestre la cuota total (norma de transparencia).
   Con balón, los cargos también se cobran en el período N+1 (columna
   ``IF(NC<=N+1, …)`` de la hoja).
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from src.contexts.loans.domain.entities.loan import Loan
from src.contexts.loans.domain.entities.payment_schedule_entry import (
    ChargeAmount,
    PaymentScheduleEntry,
)
from src.contexts.loans.domain.repositories import LoanRepository
from src.contexts.loans.domain.services.compra_inteligente_service import (
    CompraInteligenteService,
)
from src.contexts.loans.domain.services.french_amortization_service import (
    FrenchAmortizationService,
    SchedulePeriodInput,
)


class CalculateScheduleUseCase:
    def __init__(self, repo: LoanRepository) -> None:
        self._repo = repo

    async def execute(self, loan_id: UUID) -> Loan:
        loan = await self._repo.get(loan_id)
        period_inputs = [
            SchedulePeriodInput(
                period_number=i,
                tep=loan.rate_spec.tep_for_period(i),
                grace_type=loan.grace_policy.grace_for(i, loan.terms.term_periods),
            )
            for i in range(1, loan.terms.term_periods + 1)
        ]

        uses_interbank_model = (
            loan.terms.is_compra_inteligente
            or loan.terms.desgravamen_monthly_pct > Decimal(0)
            or loan.terms.financed_costs > Decimal(0)
        )
        if uses_interbank_model:
            sched = CompraInteligenteService.build_schedule(
                vehicle_price=loan.terms.vehicle_price,
                initial_payment_pct=loan.terms.initial_payment_pct,
                balloon_pct=loan.terms.balloon_pct,
                periods=period_inputs,
                financed_costs=loan.terms.financed_costs,
                desgravamen_pct_per_period=loan.terms.desgravamen_pct_per_period,
            )
            rows = sched.rows
        else:
            principal = loan.terms.vehicle_price * (Decimal(1) - loan.terms.initial_payment_pct)
            rows = FrenchAmortizationService.build_schedule(principal, period_inputs)

        entries = []
        for r in rows:
            # Cargos del período con signo negativo (egresos del deudor).
            charges = tuple(
                ChargeAmount(
                    name=c.name,
                    kind=c.kind,
                    amount=-c.amount_for(
                        period=r.period,
                        initial_balance=r.initial_balance,
                        payment=r.payment,
                        vehicle_price=loan.terms.vehicle_price,
                        frequency_days=loan.terms.frequency_days,
                    ),
                )
                for c in loan.additional_charges
                if c.applies_in(r.period)
            )
            entries.append(
                PaymentScheduleEntry(
                    period=r.period,
                    grace_type=r.grace_type,
                    initial_balance=r.initial_balance,
                    interest=r.interest,
                    payment=r.payment,
                    amortization=r.amortization,
                    final_balance=r.final_balance,
                    charges=charges,
                    insurance=r.insurance,
                    balloon_initial=r.balloon_initial,
                    balloon_interest=r.balloon_interest,
                    balloon_insurance=r.balloon_insurance,
                    balloon_amortization=r.balloon_amortization,
                    balloon_final=r.balloon_final,
                )
            )
        loan.set_schedule(entries)
        await self._repo.update(loan)
        return loan
