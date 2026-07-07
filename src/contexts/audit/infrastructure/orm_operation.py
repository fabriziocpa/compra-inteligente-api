"""Bitácora de operaciones: registro en BD de cada operación del sistema.

Cumple el requisito del enunciado de «registrar todas las operaciones
realizadas en una base de datos»: cada mutación (registro, login, altas,
ediciones, eliminaciones, cálculo de cronogramas e indicadores) inserta una
fila con el usuario que la ejecutó, la acción, la entidad afectada y un
detalle en JSON.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.infrastructure.base_orm import BaseORM


class OperationLogORM(BaseORM):
    __tablename__ = "operations_log"

    user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(60), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    entity_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    detail: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


def registrar_operacion(
    session: AsyncSession,
    *,
    user_id: UUID | None,
    action: str,
    entity_type: str,
    entity_id: UUID | None = None,
    detail: dict[str, Any] | None = None,
) -> None:
    """Agrega la fila a la sesión; se persiste con el commit de la operación."""
    session.add(
        OperationLogORM(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            detail=detail or {},
        )
    )
