from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.contexts.auth.domain.user import User
from src.contexts.auth.infrastructure.orm_user import UserORM
from src.shared.domain.exceptions import NotFoundError


def _to_orm(user: User, orm: UserORM | None = None) -> UserORM:
    if orm is None:
        orm = UserORM()
    orm.id = user.id
    orm.created_at = user.created_at
    orm.updated_at = user.updated_at
    orm.email = user.email
    orm.hashed_password = user.hashed_password
    orm.full_name = user.full_name
    orm.is_active = user.is_active
    return orm


def _from_orm(orm: UserORM) -> User:
    return User(
        id=orm.id,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
        email=orm.email,
        hashed_password=orm.hashed_password,
        full_name=orm.full_name,
        is_active=orm.is_active,
    )


class SqlAlchemyUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user: User) -> None:
        self._session.add(_to_orm(user))
        await self._session.flush()

    async def get(self, user_id: UUID) -> User:
        orm = await self._session.get(UserORM, user_id)
        if orm is None:
            raise NotFoundError(f"User {user_id} not found")
        return _from_orm(orm)

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(
            select(UserORM).where(UserORM.email == email.lower())
        )
        orm = result.scalar_one_or_none()
        return _from_orm(orm) if orm else None
