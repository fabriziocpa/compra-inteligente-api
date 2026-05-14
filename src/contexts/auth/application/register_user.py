from __future__ import annotations

from dataclasses import dataclass

from src.contexts.auth.domain.repositories import UserRepository
from src.contexts.auth.domain.user import User
from src.shared.domain.exceptions import DomainError
from src.shared.infrastructure.password_hasher import PasswordHasher


@dataclass(frozen=True, slots=True)
class RegisterUserInput:
    email: str
    password: str
    full_name: str


class RegisterUserUseCase:
    def __init__(self, repo: UserRepository, hasher: PasswordHasher) -> None:
        self._repo = repo
        self._hasher = hasher

    async def execute(self, data: RegisterUserInput) -> User:
        if len(data.password) < 8:
            raise DomainError("password must be at least 8 characters long")
        existing = await self._repo.get_by_email(data.email)
        if existing is not None:
            raise DomainError("Email already registered")
        user = User.create(
            email=data.email,
            hashed_password=self._hasher.hash(data.password),
            full_name=data.full_name,
        )
        await self._repo.add(user)
        return user
