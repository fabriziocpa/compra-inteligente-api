from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from jose import JWTError, jwt

from src.config import settings
from src.shared.domain.exceptions import AuthenticationError


@dataclass(frozen=True, slots=True)
class TokenPair:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class JWTProvider:
    def __init__(
        self,
        secret: str | None = None,
        algorithm: str | None = None,
        access_minutes: int | None = None,
        refresh_days: int | None = None,
    ) -> None:
        self._secret = secret or settings.JWT_SECRET_KEY
        self._alg = algorithm or settings.JWT_ALGORITHM
        self._access_minutes = access_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
        self._refresh_days = refresh_days or settings.REFRESH_TOKEN_EXPIRE_DAYS

    def _encode(self, subject: str, expires_delta: timedelta, token_type: str) -> str:
        now = datetime.now(UTC)
        payload: dict[str, Any] = {
            "sub": subject,
            "iat": int(now.timestamp()),
            "exp": int((now + expires_delta).timestamp()),
            "type": token_type,
        }
        return jwt.encode(payload, self._secret, algorithm=self._alg)

    def issue(self, user_id: UUID) -> TokenPair:
        subj = str(user_id)
        access = self._encode(subj, timedelta(minutes=self._access_minutes), "access")
        refresh = self._encode(subj, timedelta(days=self._refresh_days), "refresh")
        return TokenPair(access_token=access, refresh_token=refresh)

    def decode(self, token: str, expected_type: str = "access") -> UUID:
        try:
            payload = jwt.decode(token, self._secret, algorithms=[self._alg])
        except JWTError as exc:
            raise AuthenticationError("Invalid or expired token") from exc
        if payload.get("type") != expected_type:
            raise AuthenticationError("Unexpected token type")
        sub = payload.get("sub")
        if not isinstance(sub, str):
            raise AuthenticationError("Token missing subject")
        try:
            return UUID(sub)
        except ValueError as exc:
            raise AuthenticationError("Invalid subject in token") from exc
