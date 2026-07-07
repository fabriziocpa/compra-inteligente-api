"""Esquemas (contratos HTTP) del contexto de clientes."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class ClientCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    document_id: str = Field(min_length=1, max_length=50)
    email: EmailStr
    phone: str = Field(default="", max_length=50)


class ClientUpdate(BaseModel):
    """Edición parcial: cualquier dato registrado puede corregirse."""

    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    document_id: str | None = Field(default=None, min_length=1, max_length=50)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)


class ClientResponse(BaseModel):
    id: UUID
    owner_id: UUID
    full_name: str
    document_id: str
    email: str
    phone: str
    created_at: datetime
