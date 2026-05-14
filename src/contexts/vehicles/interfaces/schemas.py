from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class VehicleCreate(BaseModel):
    brand: str = Field(min_length=1, max_length=100)
    model: str = Field(min_length=1, max_length=100)
    year: int = Field(ge=1900, le=2100)
    list_price: Decimal = Field(gt=0)
    currency: str = Field(pattern="^(PEN|USD)$")


class VehicleUpdate(BaseModel):
    list_price: Decimal | None = Field(default=None, gt=0)


class VehicleResponse(BaseModel):
    id: UUID
    owner_id: UUID
    brand: str
    model: str
    year: int
    list_price: Decimal
    currency: str
    created_at: datetime

    model_config = {"json_encoders": {Decimal: str}}
