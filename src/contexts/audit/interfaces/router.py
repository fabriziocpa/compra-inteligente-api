"""Consulta de la bitácora de operaciones del usuario autenticado."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.contexts.audit.infrastructure.orm_operation import OperationLogORM
from src.contexts.auth.interfaces.dependencies import CurrentUser
from src.shared.infrastructure.database import get_session

router = APIRouter(prefix="/operations", tags=["operations"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


class OperationResponse(BaseModel):
    id: UUID
    action: str
    entity_type: str
    entity_id: UUID | None
    detail: dict[str, Any]
    created_at: datetime


@router.get("", response_model=list[OperationResponse])
async def list_operations(
    user: CurrentUser,
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[OperationResponse]:
    result = await session.execute(
        select(OperationLogORM)
        .where(OperationLogORM.user_id == user.id)
        .order_by(OperationLogORM.created_at.desc())
        .limit(limit)
    )
    return [
        OperationResponse(
            id=op.id,
            action=op.action,
            entity_type=op.entity_type,
            entity_id=op.entity_id,
            detail=op.detail,
            created_at=op.created_at,
        )
        for op in result.scalars().all()
    ]
