"""Endpoints de préstamos: creación, edición, cronograma e indicadores."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.contexts.audit.infrastructure.orm_operation import registrar_operacion
from src.contexts.auth.interfaces.dependencies import CurrentUser
from src.contexts.clients.infrastructure.sqlalchemy_client_repository import (
    SqlAlchemyClientRepository,
)
from src.contexts.loans.application.commands.create_loan_command import (
    AdditionalChargeInput,
    CreateLoanCommand,
    RateSegmentInput,
)
from src.contexts.loans.application.use_cases.calculate_indicators import (
    CalculateIndicatorsUseCase,
)
from src.contexts.loans.application.use_cases.calculate_schedule import (
    CalculateScheduleUseCase,
)
from src.contexts.loans.application.use_cases.create_loan import CreateLoanUseCase
from src.contexts.loans.domain.entities.loan import Loan
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
from src.contexts.loans.infrastructure.sqlalchemy_loan_repository import (
    SqlAlchemyLoanRepository,
)
from src.contexts.loans.interfaces.schemas import (
    AdditionalChargeSchema,
    ChargeAmountResponse,
    GraceCodeSchema,
    IndicatorsResponse,
    LoanCreateRequest,
    LoanPatchRequest,
    LoanResponse,
    RateSegmentSchema,
    ScheduleEntryResponse,
    ScheduleResponse,
)
from src.shared.domain.exceptions import AuthorizationError, NotFoundError
from src.shared.domain.money import Currency
from src.shared.infrastructure.database import get_session

router = APIRouter(prefix="/loans", tags=["loans"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def _to_response(loan: Loan) -> LoanResponse:
    return LoanResponse(
        id=loan.id,
        client_id=loan.client_id,
        vehicle_id=loan.vehicle_id,
        currency=loan.terms.currency.value,
        vehicle_price=loan.terms.vehicle_price,
        initial_payment_pct=loan.terms.initial_payment_pct,
        balloon_pct=loan.terms.balloon_pct,
        term_periods=loan.terms.term_periods,
        frequency_days=loan.terms.frequency_days,
        rate_segments=[
            RateSegmentSchema(
                from_period=s.from_period,
                to_period=s.to_period,
                rate_kind=s.rate_kind,
                rate_value=s.rate_value,
                capitalizations_per_year=s.capitalizations_per_year,
            )
            for s in loan.rate_spec.segments
        ],
        grace_periods=[cast(GraceCodeSchema, g) for g in loan.grace_policy.periods],
        additional_charges=[
            AdditionalChargeSchema(
                name=c.name,
                kind=c.kind,
                basis=c.basis,
                value=c.value,
                applies_from_period=c.applies_from_period,
                applies_to_period=c.applies_to_period,
            )
            for c in loan.additional_charges
        ],
        status=loan.status,
        created_at=loan.created_at,
    )


def _schedule_response(loan: Loan) -> ScheduleResponse:
    return ScheduleResponse(
        loan_id=loan.id,
        rows=[
            ScheduleEntryResponse(
                period=e.period,
                grace_type=e.grace_type,
                initial_balance=e.initial_balance,
                interest=e.interest,
                payment=e.payment,
                amortization=e.amortization,
                final_balance=e.final_balance,
                charges=[
                    ChargeAmountResponse(name=c.name, kind=c.kind, amount=c.amount)
                    for c in e.charges
                ],
                charges_total=e.charges_total,
                total_payment=e.total_payment,
            )
            for e in loan.schedule
        ],
    )


async def _ensure_owner(loan: Loan, user_id: UUID, session: AsyncSession) -> None:
    client_repo = SqlAlchemyClientRepository(session)
    try:
        client = await client_repo.get(loan.client_id)
    except NotFoundError as exc:
        raise AuthorizationError("Loan client not found") from exc
    if client.owner_id != user_id:
        raise AuthorizationError("Not authorised to access this loan")


@router.get("", response_model=list[LoanResponse])
async def list_loans(user: CurrentUser, session: SessionDep) -> list[LoanResponse]:
    client_repo = SqlAlchemyClientRepository(session)
    own_client_ids = {c.id for c in await client_repo.list_for_owner(user.id)}
    loan_repo = SqlAlchemyLoanRepository(session)
    return [
        _to_response(loan)
        for loan in await loan_repo.list_all()
        if loan.client_id in own_client_ids
    ]


@router.post("", response_model=LoanResponse, status_code=status.HTTP_201_CREATED)
async def create_loan(
    body: LoanCreateRequest, user: CurrentUser, session: SessionDep
) -> LoanResponse:
    client_repo = SqlAlchemyClientRepository(session)
    client = await client_repo.get(body.client_id)
    if client.owner_id != user.id:
        raise AuthorizationError("Cannot create a loan for a client you don't own")

    cmd = CreateLoanCommand(
        client_id=body.client_id,
        vehicle_id=body.vehicle_id,
        currency=body.currency,
        vehicle_price=body.vehicle_price,
        initial_payment_pct=body.initial_payment_pct,
        balloon_pct=body.balloon_pct,
        term_periods=body.term_periods,
        frequency_days=body.frequency_days,
        rate_segments=[
            RateSegmentInput(
                from_period=s.from_period,
                to_period=s.to_period,
                rate_kind=s.rate_kind,
                rate_value=s.rate_value,
                capitalizations_per_year=s.capitalizations_per_year,
            )
            for s in body.rate_segments
        ],
        grace_periods=body.grace_periods,
        additional_charges=[
            AdditionalChargeInput(
                name=c.name,
                kind=c.kind,
                basis=c.basis,
                value=c.value,
                applies_from_period=c.applies_from_period,
                applies_to_period=c.applies_to_period,
            )
            for c in body.additional_charges
        ],
    )
    repo = SqlAlchemyLoanRepository(session)
    uc = CreateLoanUseCase(repo)
    loan = await uc.execute(cmd)
    registrar_operacion(
        session,
        user_id=user.id,
        action="loan.created",
        entity_type="loan",
        entity_id=loan.id,
        detail={"client_id": str(loan.client_id), "vehicle_price": str(loan.terms.vehicle_price)},
    )
    await session.commit()
    return _to_response(loan)


@router.get("/{loan_id}", response_model=LoanResponse)
async def get_loan(
    loan_id: UUID, user: CurrentUser, session: SessionDep
) -> LoanResponse:
    repo = SqlAlchemyLoanRepository(session)
    loan = await repo.get(loan_id)
    await _ensure_owner(loan, user.id, session)
    return _to_response(loan)


@router.patch("/{loan_id}", response_model=LoanResponse)
async def update_loan(
    loan_id: UUID, body: LoanPatchRequest, user: CurrentUser, session: SessionDep
) -> LoanResponse:
    repo = SqlAlchemyLoanRepository(session)
    loan = await repo.get(loan_id)
    await _ensure_owner(loan, user.id, session)

    changed = body.model_dump(exclude_unset=True).keys()

    new_terms = LoanTerms(
        currency=Currency(body.currency) if body.currency is not None else loan.terms.currency,
        vehicle_price=body.vehicle_price if body.vehicle_price is not None else loan.terms.vehicle_price,
        initial_payment_pct=(
            body.initial_payment_pct
            if body.initial_payment_pct is not None
            else loan.terms.initial_payment_pct
        ),
        balloon_pct=body.balloon_pct if body.balloon_pct is not None else loan.terms.balloon_pct,
        term_periods=body.term_periods if body.term_periods is not None else loan.terms.term_periods,
        frequency_days=(
            body.frequency_days if body.frequency_days is not None else loan.terms.frequency_days
        ),
    )
    new_spec: InterestRateSpec | None = None
    if body.rate_segments is not None:
        new_spec = InterestRateSpec(
            days_in_period=new_terms.frequency_days,
            segments=tuple(
                RateSegment(
                    from_period=s.from_period,
                    to_period=s.to_period,
                    rate_kind=cast(RateKind, s.rate_kind),
                    rate_value=s.rate_value,
                    capitalizations_per_year=s.capitalizations_per_year,
                )
                for s in body.rate_segments
            ),
        )
    new_grace: GracePeriodPolicy | None = None
    if body.grace_periods is not None:
        new_grace = GracePeriodPolicy(
            periods=tuple(cast(GraceCode, g) for g in body.grace_periods)
        )
    new_charges: tuple[AdditionalCharge, ...] | None = None
    if body.additional_charges is not None:
        new_charges = tuple(
            AdditionalCharge(
                name=c.name,
                kind=cast(ChargeKind, c.kind),
                basis=cast(ChargeBasis, c.basis),
                value=c.value,
                applies_from_period=c.applies_from_period,
                applies_to_period=c.applies_to_period,
            )
            for c in body.additional_charges
        )

    loan.update_parameters(
        terms=new_terms,
        rate_spec=new_spec,
        grace_policy=new_grace,
        additional_charges=new_charges,
    )
    await repo.update(loan)
    registrar_operacion(
        session,
        user_id=user.id,
        action="loan.updated",
        entity_type="loan",
        entity_id=loan.id,
        detail={"fields": sorted(changed)},
    )
    await session.commit()
    return _to_response(loan)


@router.delete("/{loan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_loan(
    loan_id: UUID, user: CurrentUser, session: SessionDep
) -> None:
    repo = SqlAlchemyLoanRepository(session)
    loan = await repo.get(loan_id)
    await _ensure_owner(loan, user.id, session)
    await repo.delete(loan_id)
    registrar_operacion(
        session,
        user_id=user.id,
        action="loan.deleted",
        entity_type="loan",
        entity_id=loan_id,
    )
    await session.commit()


@router.post("/{loan_id}/schedule", response_model=ScheduleResponse)
async def generate_schedule(
    loan_id: UUID, user: CurrentUser, session: SessionDep
) -> ScheduleResponse:
    repo = SqlAlchemyLoanRepository(session)
    loan = await repo.get(loan_id)
    await _ensure_owner(loan, user.id, session)
    uc = CalculateScheduleUseCase(repo)
    loan = await uc.execute(loan_id)
    registrar_operacion(
        session,
        user_id=user.id,
        action="loan.schedule_generated",
        entity_type="loan",
        entity_id=loan.id,
        detail={"rows": len(loan.schedule)},
    )
    await session.commit()
    return _schedule_response(loan)


@router.get("/{loan_id}/schedule", response_model=ScheduleResponse)
async def get_schedule(
    loan_id: UUID, user: CurrentUser, session: SessionDep
) -> ScheduleResponse:
    repo = SqlAlchemyLoanRepository(session)
    loan = await repo.get(loan_id)
    await _ensure_owner(loan, user.id, session)
    return _schedule_response(loan)


@router.get("/{loan_id}/indicators", response_model=IndicatorsResponse)
async def get_indicators(
    loan_id: UUID,
    user: CurrentUser,
    session: SessionDep,
    discount_rate_per_period: Annotated[Decimal | None, Query()] = None,
) -> IndicatorsResponse:
    repo = SqlAlchemyLoanRepository(session)
    loan = await repo.get(loan_id)
    await _ensure_owner(loan, user.id, session)
    uc = CalculateIndicatorsUseCase(repo)
    result = await uc.execute(loan_id, discount_rate_per_period)
    registrar_operacion(
        session,
        user_id=user.id,
        action="loan.indicators_calculated",
        entity_type="loan",
        entity_id=loan.id,
        detail={"tcea": str(result.tcea)},
    )
    await session.commit()
    return IndicatorsResponse(
        loan_id=loan.id,
        tir_per_period=result.tir_per_period,
        tcea=result.tcea,
        van_at_period_rate=result.van_at_period_rate,
        cashflows=result.cashflows,
    )
