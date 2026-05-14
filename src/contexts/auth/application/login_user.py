from __future__ import annotations

from dataclasses import dataclass

from src.contexts.auth.domain.repositories import UserRepository
from src.shared.domain.exceptions import AuthenticationError
from src.shared.infrastructure.jwt_provider import JWTProvider, TokenPair
from src.shared.infrastructure.password_hasher import PasswordHasher


@dataclass(frozen=True, slots=True)
class LoginInput:
    email: str
    password: str


class LoginUserUseCase:
    def __init__(
        self,
        repo: UserRepository,
        hasher: PasswordHasher,
        jwt_provider: JWTProvider,
    ) -> None:
        self._repo = repo
        self._hasher = hasher
        self._jwt = jwt_provider

    async def execute(self, data: LoginInput) -> TokenPair:
        user = await self._repo.get_by_email(data.email)
        if user is None or not user.is_active:
            raise AuthenticationError("Invalid credentials")
        if not self._hasher.verify(data.password, user.hashed_password):
            raise AuthenticationError("Invalid credentials")
        return self._jwt.issue(user.id)


class RefreshTokenUseCase:
    def __init__(self, repo: UserRepository, jwt_provider: JWTProvider) -> None:
        self._repo = repo
        self._jwt = jwt_provider

    async def execute(self, refresh_token: str) -> TokenPair:
        user_id = self._jwt.decode(refresh_token, expected_type="refresh")
        user = await self._repo.get(user_id)
        if not user.is_active:
            raise AuthenticationError("User is inactive")
        return self._jwt.issue(user.id)
