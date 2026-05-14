from __future__ import annotations

from src.contexts.auth.domain.repositories import UserRepository
from src.contexts.auth.domain.user import User
from src.shared.domain.exceptions import AuthenticationError
from src.shared.infrastructure.jwt_provider import JWTProvider


class GetCurrentUserUseCase:
    def __init__(self, repo: UserRepository, jwt_provider: JWTProvider) -> None:
        self._repo = repo
        self._jwt = jwt_provider

    async def execute(self, access_token: str) -> User:
        user_id = self._jwt.decode(access_token, expected_type="access")
        user = await self._repo.get(user_id)
        if not user.is_active:
            raise AuthenticationError("User is inactive")
        return user
