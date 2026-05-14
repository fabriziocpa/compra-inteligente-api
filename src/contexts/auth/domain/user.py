from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from src.shared.domain.entity import AggregateRoot
from src.shared.domain.exceptions import DomainError


@dataclass(eq=False)
class User(AggregateRoot):
    email: str = ""
    hashed_password: str = ""
    full_name: str = ""
    is_active: bool = True

    @classmethod
    def create(cls, *, email: str, hashed_password: str, full_name: str) -> User:
        if "@" not in email or len(email) < 5:
            raise DomainError("invalid email")
        if not hashed_password:
            raise DomainError("hashed_password required")
        if not full_name.strip():
            raise DomainError("full_name required")
        now = datetime.now(UTC)
        return cls(
            id=uuid4(),
            created_at=now,
            updated_at=now,
            email=email.lower(),
            hashed_password=hashed_password,
            full_name=full_name.strip(),
            is_active=True,
        )
