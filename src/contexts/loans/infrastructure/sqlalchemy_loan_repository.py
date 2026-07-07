from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.contexts.loans.domain.entities.loan import Loan
from src.contexts.loans.infrastructure.loan_mapper import loan_from_orm, loan_to_orm
from src.contexts.loans.infrastructure.orm_loan import LoanORM
from src.shared.domain.exceptions import NotFoundError


class SqlAlchemyLoanRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, loan: Loan) -> None:
        orm = loan_to_orm(loan)
        self._session.add(orm)
        await self._session.flush()

    async def get(self, loan_id: UUID) -> Loan:
        orm = await self._session.get(LoanORM, loan_id)
        if orm is None:
            raise NotFoundError(f"Loan {loan_id} not found")
        return loan_from_orm(orm)

    async def list_by_client(self, client_id: UUID) -> list[Loan]:
        result = await self._session.execute(
            select(LoanORM).where(LoanORM.client_id == client_id)
        )
        return [loan_from_orm(o) for o in result.scalars().all()]

    async def list_all(self) -> list[Loan]:
        result = await self._session.execute(select(LoanORM))
        return [loan_from_orm(o) for o in result.scalars().all()]

    async def update(self, loan: Loan) -> None:
        orm = await self._session.get(LoanORM, loan.id)
        if orm is None:
            raise NotFoundError(f"Loan {loan.id} not found")
        # Hay que hacer flush de los DELETE huérfanos antes de que loan_to_orm
        # vuelva a poblar el cronograma; en un solo flush SQLAlchemy emite
        # primero los INSERT nuevos y viola uq_schedule_loan_period.
        orm.schedule_entries.clear()
        await self._session.flush()
        loan_to_orm(loan, orm)
        await self._session.flush()

    async def delete(self, loan_id: UUID) -> None:
        orm = await self._session.get(LoanORM, loan_id)
        if orm is None:
            raise NotFoundError(f"Loan {loan_id} not found")
        await self._session.delete(orm)
        await self._session.flush()
