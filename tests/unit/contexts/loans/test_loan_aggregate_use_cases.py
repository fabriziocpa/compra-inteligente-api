from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from src.contexts.loans.application.commands.create_loan_command import (
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
from src.shared.domain.exceptions import NotFoundError


class InMemoryLoanRepo:
    def __init__(self) -> None:
        self._store: dict[UUID, Loan] = {}

    async def add(self, loan: Loan) -> None:
        self._store[loan.id] = loan

    async def get(self, loan_id: UUID) -> Loan:
        if loan_id not in self._store:
            raise NotFoundError(f"Loan {loan_id} not found")
        return self._store[loan_id]

    async def list_by_client(self, client_id: UUID) -> list[Loan]:
        return [loan for loan in self._store.values() if loan.client_id == client_id]

    async def list_all(self) -> list[Loan]:
        return list(self._store.values())

    async def update(self, loan: Loan) -> None:
        self._store[loan.id] = loan

    async def delete(self, loan_id: UUID) -> None:
        self._store.pop(loan_id, None)


def _base_cmd() -> CreateLoanCommand:
    return CreateLoanCommand(
        client_id=uuid4(),
        vehicle_id=uuid4(),
        currency="USD",
        vehicle_price=Decimal("1440000"),
        initial_payment_pct=Decimal("0"),
        balloon_pct=Decimal("0"),
        term_periods=8,
        frequency_days=180,
        rate_segments=[
            RateSegmentInput(
                from_period=1, to_period=8, rate_kind="TEA", rate_value=Decimal("0.09")
            )
        ],
        grace_periods=[],
        additional_charges=[],
    )


@pytest.mark.asyncio
async def test_create_then_schedule_then_indicators_for_example_1() -> None:
    repo = InMemoryLoanRepo()
    loan = await CreateLoanUseCase(repo).execute(_base_cmd())
    assert loan.status == "draft"

    loan = await CalculateScheduleUseCase(repo).execute(loan.id)
    assert loan.status == "scheduled"
    assert len(loan.schedule) == 8
    assert abs(loan.schedule[0].payment - Decimal("-217454.11")) <= Decimal("0.01")
    assert abs(loan.schedule[0].final_balance - Decimal("1285950.02")) <= Decimal("0.01")
    assert abs(loan.schedule[-1].final_balance) <= Decimal("0.10")

    result = await CalculateIndicatorsUseCase(repo).execute(loan.id)
    # TIR semestral ≈ TES 9% ≈ 0.04403, TCEA ≈ 0.09
    assert abs(result.tir_per_period - Decimal("0.04403065")) <= Decimal("0.00001")
    assert abs(result.tcea - Decimal("0.09")) <= Decimal("0.00001")


@pytest.mark.asyncio
async def test_compra_inteligente_with_balloon_and_initial_payment() -> None:
    repo = InMemoryLoanRepo()
    cmd = _base_cmd()
    object.__setattr__(cmd, "vehicle_price", Decimal("60000"))
    object.__setattr__(cmd, "initial_payment_pct", Decimal("0.20"))
    object.__setattr__(cmd, "balloon_pct", Decimal("0.30"))
    object.__setattr__(cmd, "term_periods", 36)
    object.__setattr__(cmd, "frequency_days", 30)
    object.__setattr__(
        cmd,
        "rate_segments",
        [
            RateSegmentInput(
                from_period=1, to_period=36, rate_kind="TEA", rate_value=Decimal("0.12")
            )
        ],
    )

    loan = await CreateLoanUseCase(repo).execute(cmd)
    loan = await CalculateScheduleUseCase(repo).execute(loan.id)

    assert len(loan.schedule) == 36
    # The total amortization should equal the financed amount (price * (1 - CI pct)).
    financed = Decimal("60000") * (Decimal(1) - Decimal("0.20"))
    total_amort = sum((-e.amortization for e in loan.schedule), Decimal(0))
    assert abs(total_amort - financed) <= Decimal("0.01")
    assert abs(loan.schedule[-1].final_balance) <= Decimal("0.01")

    result = await CalculateIndicatorsUseCase(repo).execute(loan.id)
    assert result.tir_per_period > Decimal(0)
    assert result.tcea > Decimal(0)
