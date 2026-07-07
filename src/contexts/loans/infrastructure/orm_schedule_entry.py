from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.contexts.loans.infrastructure.orm_loan import LoanORM
from src.shared.infrastructure.base_orm import BaseORM


class ScheduleEntryORM(BaseORM):
    __tablename__ = "payment_schedule_entries"
    __table_args__ = (UniqueConstraint("loan_id", "period", name="uq_schedule_loan_period"),)

    loan_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("loans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    period: Mapped[int] = mapped_column(nullable=False)
    grace_type: Mapped[str] = mapped_column(String(1), nullable=False)
    initial_balance: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    interest: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    payment: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    amortization: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    final_balance: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    # Cargos del período: [{name, kind, amount}] con montos negativos (egresos).
    charges: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    loan: Mapped[LoanORM] = relationship(back_populates="schedule_entries")
