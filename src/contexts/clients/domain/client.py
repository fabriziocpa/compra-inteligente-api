from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.shared.domain.entity import AggregateRoot
from src.shared.domain.exceptions import DomainError


@dataclass(eq=False)
class Client(AggregateRoot):
    owner_id: UUID = uuid4()  # placeholder; siempre se asigna en create()
    full_name: str = ""
    document_id: str = ""  # DNI / RUC
    email: str = ""
    phone: str = ""

    @classmethod
    def create(
        cls,
        *,
        owner_id: UUID,
        full_name: str,
        document_id: str,
        email: str,
        phone: str = "",
    ) -> Client:
        if not full_name.strip():
            raise DomainError("full_name required")
        if not document_id.strip():
            raise DomainError("document_id required")
        if "@" not in email:
            raise DomainError("invalid email")
        now = datetime.now(UTC)
        return cls(
            id=uuid4(),
            created_at=now,
            updated_at=now,
            owner_id=owner_id,
            full_name=full_name.strip(),
            document_id=document_id.strip(),
            email=email.lower(),
            phone=phone,
        )

    def update_data(
        self,
        *,
        full_name: str | None = None,
        document_id: str | None = None,
        email: str | None = None,
        phone: str | None = None,
    ) -> None:
        """Edición parcial de los datos registrados (requisito 3 del enunciado)."""
        if full_name is not None:
            if not full_name.strip():
                raise DomainError("full_name required")
            self.full_name = full_name.strip()
        if document_id is not None:
            if not document_id.strip():
                raise DomainError("document_id required")
            self.document_id = document_id.strip()
        if email is not None:
            if "@" not in email:
                raise DomainError("invalid email")
            self.email = email.lower()
        if phone is not None:
            self.phone = phone
        self.touch()
