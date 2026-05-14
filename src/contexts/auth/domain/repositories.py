from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.contexts.auth.domain.user import User


class UserRepository(Protocol):
    async def add(self, user: User) -> None: ...
    async def get(self, user_id: UUID) -> User: ...
    async def get_by_email(self, email: str) -> User | None: ...
