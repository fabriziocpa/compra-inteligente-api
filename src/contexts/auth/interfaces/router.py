from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.contexts.auth.application.login_user import (
    LoginInput,
    LoginUserUseCase,
    RefreshTokenUseCase,
)
from src.contexts.auth.application.register_user import (
    RegisterUserInput,
    RegisterUserUseCase,
)
from src.contexts.auth.infrastructure.sqlalchemy_user_repository import SqlAlchemyUserRepository
from src.contexts.auth.interfaces.dependencies import CurrentUser
from src.contexts.auth.interfaces.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from src.shared.infrastructure.database import get_session
from src.shared.infrastructure.jwt_provider import JWTProvider
from src.shared.infrastructure.password_hasher import PasswordHasher

router = APIRouter(prefix="/auth", tags=["auth"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, session: SessionDep) -> UserResponse:
    repo = SqlAlchemyUserRepository(session)
    uc = RegisterUserUseCase(repo, PasswordHasher())
    user = await uc.execute(
        RegisterUserInput(email=body.email, password=body.password, full_name=body.full_name)
    )
    await session.commit()
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, session: SessionDep) -> TokenResponse:
    repo = SqlAlchemyUserRepository(session)
    uc = LoginUserUseCase(repo, PasswordHasher(), JWTProvider())
    tokens = await uc.execute(LoginInput(email=body.email, password=body.password))
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, session: SessionDep) -> TokenResponse:
    repo = SqlAlchemyUserRepository(session)
    uc = RefreshTokenUseCase(repo, JWTProvider())
    tokens = await uc.execute(body.refresh_token)
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
    )


@router.get("/me", response_model=UserResponse)
async def me(user: CurrentUser) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        created_at=user.created_at,
    )
