from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.shared.infrastructure.base_orm import BaseORM

if TYPE_CHECKING:
    from src.contexts.loans.infrastructure.orm_schedule_entry import ScheduleEntryORM


class LoanORM(BaseORM):
    __tablename__ = "loans"

    client_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    vehicle_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    vehicle_price: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    initial_payment_pct: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    balloon_pct: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    term_periods: Mapped[int] = mapped_column(nullable=False)
    frequency_days: Mapped[int] = mapped_column(nullable=False)
    rate_spec: Mapped[dict] = mapped_column(JSONB, nullable=False)
    grace_policy: Mapped[dict] = mapped_column(JSONB, nullable=False)
    additional_charges: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")

    schedule_entries: Mapped[list[ScheduleEntryORM]] = relationship(
        back_populates="loan",
        cascade="all, delete-orphan",
        order_by="ScheduleEntryORM.period",
        lazy="selectin",
    )
