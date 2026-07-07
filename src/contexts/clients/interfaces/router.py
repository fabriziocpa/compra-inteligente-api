from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.contexts.audit.infrastructure.orm_operation import registrar_operacion
from src.contexts.auth.interfaces.dependencies import CurrentUser
from src.contexts.clients.domain.client import Client
from src.contexts.clients.infrastructure.sqlalchemy_client_repository import (
    SqlAlchemyClientRepository,
)
from src.contexts.clients.interfaces.schemas import (
    ClientCreate,
    ClientResponse,
    ClientUpdate,
)
from src.shared.domain.exceptions import AuthorizationError
from src.shared.infrastructure.database import get_session

router = APIRouter(prefix="/clients", tags=["clients"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def _to_response(c: Client) -> ClientResponse:
    return ClientResponse(
        id=c.id,
        owner_id=c.owner_id,
        full_name=c.full_name,
        document_id=c.document_id,
        email=c.email,
        phone=c.phone,
        created_at=c.created_at,
    )


def _ensure_owner(client: Client, user_id: UUID) -> None:
    if client.owner_id != user_id:
        raise AuthorizationError("Not authorised to access this client")


@router.get("", response_model=list[ClientResponse])
async def list_clients(user: CurrentUser, session: SessionDep) -> list[ClientResponse]:
    repo = SqlAlchemyClientRepository(session)
    return [_to_response(c) for c in await repo.list_for_owner(user.id)]


@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    body: ClientCreate, user: CurrentUser, session: SessionDep
) -> ClientResponse:
    repo = SqlAlchemyClientRepository(session)
    client = Client.create(
        owner_id=user.id,
        full_name=body.full_name,
        document_id=body.document_id,
        email=body.email,
        phone=body.phone,
    )
    await repo.add(client)
    registrar_operacion(
        session,
        user_id=user.id,
        action="client.created",
        entity_type="client",
        entity_id=client.id,
        detail={"full_name": client.full_name},
    )
    await session.commit()
    return _to_response(client)


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: UUID, user: CurrentUser, session: SessionDep
) -> ClientResponse:
    repo = SqlAlchemyClientRepository(session)
    client = await repo.get(client_id)
    _ensure_owner(client, user.id)
    return _to_response(client)


@router.patch("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: UUID, body: ClientUpdate, user: CurrentUser, session: SessionDep
) -> ClientResponse:
    repo = SqlAlchemyClientRepository(session)
    client = await repo.get(client_id)
    _ensure_owner(client, user.id)
    client.update_data(
        full_name=body.full_name,
        document_id=body.document_id,
        email=body.email,
        phone=body.phone,
    )
    await repo.update(client)
    registrar_operacion(
        session,
        user_id=user.id,
        action="client.updated",
        entity_type="client",
        entity_id=client.id,
        detail={"fields": sorted(body.model_dump(exclude_unset=True).keys())},
    )
    await session.commit()
    return _to_response(client)


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
    client_id: UUID, user: CurrentUser, session: SessionDep
) -> None:
    repo = SqlAlchemyClientRepository(session)
    client = await repo.get(client_id)
    _ensure_owner(client, user.id)
    await repo.delete(client_id)
    registrar_operacion(
        session,
        user_id=user.id,
        action="client.deleted",
        entity_type="client",
        entity_id=client_id,
    )
    await session.commit()
