from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.contexts.auth.application.get_current_user import GetCurrentUserUseCase
from src.contexts.auth.domain.user import User
from src.contexts.auth.infrastructure.sqlalchemy_user_repository import SqlAlchemyUserRepository
from src.shared.infrastructure.database import get_session
from src.shared.infrastructure.jwt_provider import JWTProvider

_bearer = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    token = credentials.credentials
    repo = SqlAlchemyUserRepository(session)
    uc = GetCurrentUserUseCase(repo, JWTProvider())
    return await uc.execute(token)


CurrentUser = Annotated[User, Depends(get_current_user)]
