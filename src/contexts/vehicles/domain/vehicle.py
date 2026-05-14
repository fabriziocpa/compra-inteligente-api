from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from src.shared.domain.entity import AggregateRoot
from src.shared.domain.exceptions import DomainError
from src.shared.domain.money import Currency


@dataclass(eq=False)
class Vehicle(AggregateRoot):
    owner_id: UUID = field(default_factory=uuid4)
    brand: str = ""
    model: str = ""
    year: int = 0
    list_price: Decimal = Decimal(0)
    currency: Currency = Currency.PEN

    @classmethod
    def create(
        cls,
        *,
        owner_id: UUID,
        brand: str,
        model: str,
        year: int,
        list_price: Decimal,
        currency: Currency,
    ) -> Vehicle:
        if not brand.strip():
            raise DomainError("brand required")
        if not model.strip():
            raise DomainError("model required")
        if year < 1900:
            raise DomainError("year too small")
        if list_price <= Decimal(0):
            raise DomainError("list_price must be positive")
        now = datetime.now(UTC)
        return cls(
            id=uuid4(),
            created_at=now,
            updated_at=now,
            owner_id=owner_id,
            brand=brand.strip(),
            model=model.strip(),
            year=year,
            list_price=list_price,
            currency=currency,
        )

    def update_price(self, list_price: Decimal) -> None:
        if list_price <= Decimal(0):
            raise DomainError("list_price must be positive")
        self.list_price = list_price
        self.touch()
