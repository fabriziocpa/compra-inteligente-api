from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.contexts.clients.domain.client import Client
from src.contexts.clients.infrastructure.orm_client import ClientORM
from src.shared.domain.exceptions import NotFoundError


def _to_orm(c: Client, orm: ClientORM | None = None) -> ClientORM:
    if orm is None:
        orm = ClientORM()
    orm.id = c.id
    orm.created_at = c.created_at
    orm.updated_at = c.updated_at
    orm.owner_id = c.owner_id
    orm.full_name = c.full_name
    orm.document_id = c.document_id
    orm.email = c.email
    orm.phone = c.phone
    return orm


def _from_orm(orm: ClientORM) -> Client:
    return Client(
        id=orm.id,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
        owner_id=orm.owner_id,
        full_name=orm.full_name,
        document_id=orm.document_id,
        email=orm.email,
        phone=orm.phone,
    )


class SqlAlchemyClientRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, client: Client) -> None:
        self._session.add(_to_orm(client))
        await self._session.flush()

    async def get(self, client_id: UUID) -> Client:
        orm = await self._session.get(ClientORM, client_id)
        if orm is None:
            raise NotFoundError(f"Client {client_id} not found")
        return _from_orm(orm)

    async def list_for_owner(self, owner_id: UUID) -> list[Client]:
        result = await self._session.execute(
            select(ClientORM).where(ClientORM.owner_id == owner_id)
        )
        return [_from_orm(o) for o in result.scalars().all()]

    async def update(self, client: Client) -> None:
        orm = await self._session.get(ClientORM, client.id)
        if orm is None:
            raise NotFoundError(f"Client {client.id} not found")
        _to_orm(client, orm)
        await self._session.flush()

    async def delete(self, client_id: UUID) -> None:
        orm = await self._session.get(ClientORM, client_id)
        if orm is None:
            raise NotFoundError(f"Client {client_id} not found")
        await self._session.delete(orm)
        await self._session.flush()
