from __future__ import annotations

from decimal import Decimal
from typing import Any, cast

from src.contexts.loans.domain.entities.loan import Loan, LoanStatus
from src.contexts.loans.domain.entities.payment_schedule_entry import (
    ChargeAmount,
    PaymentScheduleEntry,
)
from src.contexts.loans.domain.value_objects.additional_charge import (
    AdditionalCharge,
    ChargeBasis,
    ChargeKind,
)
from src.contexts.loans.domain.value_objects.grace_period_policy import (
    GraceCode,
    GracePeriodPolicy,
)
from src.contexts.loans.domain.value_objects.initial_cost import InitialCost
from src.contexts.loans.domain.value_objects.interest_rate_spec import (
    InterestRateSpec,
    RateKind,
    RateSegment,
)
from src.contexts.loans.domain.value_objects.loan_terms import LoanTerms
from src.contexts.loans.infrastructure.orm_loan import LoanORM
from src.contexts.loans.infrastructure.orm_schedule_entry import ScheduleEntryORM
from src.shared.domain.money import Currency


def rate_spec_to_dict(spec: InterestRateSpec) -> dict[str, Any]:
    return {
        "days_in_period": spec.days_in_period,
        "days_in_year": spec.days_in_year,
        "segments": [
            {
                "from_period": s.from_period,
                "to_period": s.to_period,
                "rate_kind": s.rate_kind,
                "rate_value": str(s.rate_value),
                "capitalizations_per_year": s.capitalizations_per_year,
            }
            for s in spec.segments
        ],
    }


def rate_spec_from_dict(payload: dict[str, Any]) -> InterestRateSpec:
    segments = tuple(
        RateSegment(
            from_period=int(s["from_period"]),
            to_period=int(s["to_period"]),
            rate_kind=cast(RateKind, s["rate_kind"]),
            rate_value=Decimal(s["rate_value"]),
            capitalizations_per_year=s.get("capitalizations_per_year"),
        )
        for s in payload.get("segments", [])
    )
    return InterestRateSpec(
        days_in_period=int(payload["days_in_period"]),
        days_in_year=int(payload.get("days_in_year", 360)),
        segments=segments,
    )


def grace_policy_to_dict(policy: GracePeriodPolicy) -> dict[str, Any]:
    return {"periods": list(policy.periods)}


def grace_policy_from_dict(payload: dict[str, Any]) -> GracePeriodPolicy:
    return GracePeriodPolicy(
        periods=tuple(cast(GraceCode, p) for p in payload.get("periods", []))
    )


def charge_to_dict(c: AdditionalCharge) -> dict[str, Any]:
    return {
        "name": c.name,
        "kind": c.kind,
        "basis": c.basis,
        "value": str(c.value),
        "applies_from_period": c.applies_from_period,
        "applies_to_period": c.applies_to_period,
    }


def charge_from_dict(payload: dict[str, Any]) -> AdditionalCharge:
    return AdditionalCharge(
        name=payload["name"],
        kind=cast(ChargeKind, payload["kind"]),
        basis=cast(ChargeBasis, payload["basis"]),
        value=Decimal(payload["value"]),
        applies_from_period=int(payload.get("applies_from_period", 1)),
        applies_to_period=payload.get("applies_to_period"),
    )


def initial_cost_to_dict(c: InitialCost) -> dict[str, Any]:
    return {"name": c.name, "amount": str(c.amount), "financed": c.financed}


def initial_cost_from_dict(payload: dict[str, Any]) -> InitialCost:
    return InitialCost(
        name=payload["name"],
        amount=Decimal(payload["amount"]),
        financed=bool(payload.get("financed", True)),
    )


def loan_to_orm(loan: Loan, orm: LoanORM | None = None) -> LoanORM:
    if orm is None:
        orm = LoanORM()
    orm.id = loan.id
    orm.created_at = loan.created_at
    orm.updated_at = loan.updated_at
    orm.client_id = loan.client_id
    orm.vehicle_id = loan.vehicle_id
    orm.currency = loan.terms.currency.value
    orm.vehicle_price = loan.terms.vehicle_price
    orm.initial_payment_pct = loan.terms.initial_payment_pct
    orm.balloon_pct = loan.terms.balloon_pct if loan.terms.balloon_pct > 0 else None
    orm.term_periods = loan.terms.term_periods
    orm.frequency_days = loan.terms.frequency_days
    orm.financed_costs = loan.terms.financed_costs
    orm.desgravamen_monthly_pct = loan.terms.desgravamen_monthly_pct
    orm.rate_spec = rate_spec_to_dict(loan.rate_spec)
    orm.grace_policy = grace_policy_to_dict(loan.grace_policy)
    orm.additional_charges = [charge_to_dict(c) for c in loan.additional_charges]
    orm.initial_costs = [initial_cost_to_dict(c) for c in loan.initial_costs]
    orm.status = loan.status

    orm.schedule_entries = [
        ScheduleEntryORM(
            loan_id=loan.id,
            period=e.period,
            grace_type=e.grace_type,
            initial_balance=e.initial_balance,
            interest=e.interest,
            payment=e.payment,
            amortization=e.amortization,
            final_balance=e.final_balance,
            insurance=e.insurance,
            balloon_initial=e.balloon_initial,
            balloon_interest=e.balloon_interest,
            balloon_insurance=e.balloon_insurance,
            balloon_amortization=e.balloon_amortization,
            balloon_final=e.balloon_final,
            charges=[
                {"name": c.name, "kind": c.kind, "amount": str(c.amount)}
                for c in e.charges
            ],
        )
        for e in loan.schedule
    ]
    return orm


def loan_from_orm(orm: LoanORM) -> Loan:
    terms = LoanTerms(
        currency=Currency(orm.currency),
        vehicle_price=orm.vehicle_price,
        initial_payment_pct=orm.initial_payment_pct,
        balloon_pct=orm.balloon_pct or Decimal(0),
        term_periods=orm.term_periods,
        frequency_days=orm.frequency_days,
        financed_costs=orm.financed_costs or Decimal(0),
        desgravamen_monthly_pct=orm.desgravamen_monthly_pct or Decimal(0),
    )
    schedule = tuple(
        PaymentScheduleEntry(
            period=e.period,
            grace_type=e.grace_type,
            initial_balance=e.initial_balance,
            interest=e.interest,
            payment=e.payment,
            amortization=e.amortization,
            final_balance=e.final_balance,
            insurance=e.insurance or Decimal(0),
            balloon_initial=e.balloon_initial or Decimal(0),
            balloon_interest=e.balloon_interest or Decimal(0),
            balloon_insurance=e.balloon_insurance or Decimal(0),
            balloon_amortization=e.balloon_amortization or Decimal(0),
            balloon_final=e.balloon_final or Decimal(0),
            charges=tuple(
                ChargeAmount(
                    name=c["name"], kind=c["kind"], amount=Decimal(c["amount"])
                )
                for c in (e.charges or [])
            ),
        )
        for e in sorted(orm.schedule_entries, key=lambda e: e.period)
    )
    loan = Loan(
        id=orm.id,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
        client_id=orm.client_id,
        vehicle_id=orm.vehicle_id,
        terms=terms,
        rate_spec=rate_spec_from_dict(orm.rate_spec),
        grace_policy=grace_policy_from_dict(orm.grace_policy),
        additional_charges=tuple(charge_from_dict(c) for c in orm.additional_charges),
        initial_costs=tuple(
            initial_cost_from_dict(c) for c in (orm.initial_costs or [])
        ),
        status=cast(LoanStatus, orm.status),
        schedule=schedule,
    )
    return loan
