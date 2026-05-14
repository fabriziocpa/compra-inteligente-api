from __future__ import annotations

from typing import cast

from src.contexts.loans.application.commands.create_loan_command import CreateLoanCommand
from src.contexts.loans.domain.entities.loan import Loan
from src.contexts.loans.domain.repositories import LoanRepository
from src.contexts.loans.domain.value_objects.additional_charge import (
    AdditionalCharge,
    ChargeBasis,
    ChargeKind,
)
from src.contexts.loans.domain.value_objects.grace_period_policy import (
    GraceCode,
    GracePeriodPolicy,
)
from src.contexts.loans.domain.value_objects.interest_rate_spec import (
    InterestRateSpec,
    RateKind,
    RateSegment,
)
from src.contexts.loans.domain.value_objects.loan_terms import LoanTerms
from src.shared.domain.money import Currency


class CreateLoanUseCase:
    def __init__(self, repo: LoanRepository) -> None:
        self._repo = repo

    async def execute(self, cmd: CreateLoanCommand) -> Loan:
        terms = LoanTerms(
            currency=Currency(cmd.currency),
            vehicle_price=cmd.vehicle_price,
            initial_payment_pct=cmd.initial_payment_pct,
            balloon_pct=cmd.balloon_pct,
            term_periods=cmd.term_periods,
            frequency_days=cmd.frequency_days,
        )
        rate_spec = InterestRateSpec(
            days_in_period=cmd.frequency_days,
            segments=tuple(
                RateSegment(
                    from_period=s.from_period,
                    to_period=s.to_period,
                    rate_kind=cast(RateKind, s.rate_kind),
                    rate_value=s.rate_value,
                    capitalizations_per_year=s.capitalizations_per_year,
                )
                for s in cmd.rate_segments
            ),
        )
        grace = GracePeriodPolicy(
            periods=tuple(cast(GraceCode, g) for g in cmd.grace_periods)
        )
        charges = tuple(
            AdditionalCharge(
                name=c.name,
                kind=cast(ChargeKind, c.kind),
                basis=cast(ChargeBasis, c.basis),
                value=c.value,
                applies_from_period=c.applies_from_period,
                applies_to_period=c.applies_to_period,
            )
            for c in cmd.additional_charges
        )
        loan = Loan.create(
            client_id=cmd.client_id,
            vehicle_id=cmd.vehicle_id,
            terms=terms,
            rate_spec=rate_spec,
            grace_policy=grace,
            additional_charges=charges,
        )
        await self._repo.add(loan)
        return loan
