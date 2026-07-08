"""Eventos de dominio del contexto de préstamos."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.shared.domain.events import DomainEvent


@dataclass(frozen=True)
class LoanCreated(DomainEvent):
    loan_id: UUID = None  # type: ignore[assignment]


@dataclass(frozen=True)
class LoanUpdated(DomainEvent):
    loan_id: UUID = None  # type: ignore[assignment]


@dataclass(frozen=True)
class ScheduleGenerated(DomainEvent):
    loan_id: UUID = None  # type: ignore[assignment]
    rows: int = 0
