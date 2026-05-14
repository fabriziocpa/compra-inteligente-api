from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.contexts.auth.interfaces.dependencies import CurrentUser
from src.contexts.vehicles.domain.vehicle import Vehicle
from src.contexts.vehicles.infrastructure.sqlalchemy_vehicle_repository import (
    SqlAlchemyVehicleRepository,
)
from src.contexts.vehicles.interfaces.schemas import (
    VehicleCreate,
    VehicleResponse,
    VehicleUpdate,
)
from src.shared.domain.exceptions import AuthorizationError
from src.shared.domain.money import Currency
from src.shared.infrastructure.database import get_session

router = APIRouter(prefix="/vehicles", tags=["vehicles"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def _to_response(v: Vehicle) -> VehicleResponse:
    return VehicleResponse(
        id=v.id,
        owner_id=v.owner_id,
        brand=v.brand,
        model=v.model,
        year=v.year,
        list_price=v.list_price,
        currency=v.currency.value,
        created_at=v.created_at,
    )


def _ensure_owner(v: Vehicle, user_id: UUID) -> None:
    if v.owner_id != user_id:
        raise AuthorizationError("Not authorised to access this vehicle")


@router.get("", response_model=list[VehicleResponse])
async def list_vehicles(user: CurrentUser, session: SessionDep) -> list[VehicleResponse]:
    repo = SqlAlchemyVehicleRepository(session)
    return [_to_response(v) for v in await repo.list_for_owner(user.id)]


@router.post("", response_model=VehicleResponse, status_code=status.HTTP_201_CREATED)
async def create_vehicle(
    body: VehicleCreate, user: CurrentUser, session: SessionDep
) -> VehicleResponse:
    repo = SqlAlchemyVehicleRepository(session)
    vehicle = Vehicle.create(
        owner_id=user.id,
        brand=body.brand,
        model=body.model,
        year=body.year,
        list_price=body.list_price,
        currency=Currency(body.currency),
    )
    await repo.add(vehicle)
    await session.commit()
    return _to_response(vehicle)


@router.get("/{vehicle_id}", response_model=VehicleResponse)
async def get_vehicle(
    vehicle_id: UUID, user: CurrentUser, session: SessionDep
) -> VehicleResponse:
    repo = SqlAlchemyVehicleRepository(session)
    v = await repo.get(vehicle_id)
    _ensure_owner(v, user.id)
    return _to_response(v)


@router.patch("/{vehicle_id}", response_model=VehicleResponse)
async def update_vehicle(
    vehicle_id: UUID, body: VehicleUpdate, user: CurrentUser, session: SessionDep
) -> VehicleResponse:
    repo = SqlAlchemyVehicleRepository(session)
    v = await repo.get(vehicle_id)
    _ensure_owner(v, user.id)
    if body.list_price is not None:
        v.update_price(body.list_price)
    await repo.update(v)
    await session.commit()
    return _to_response(v)


@router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vehicle(
    vehicle_id: UUID, user: CurrentUser, session: SessionDep
) -> None:
    repo = SqlAlchemyVehicleRepository(session)
    v = await repo.get(vehicle_id)
    _ensure_owner(v, user.id)
    await repo.delete(vehicle_id)
    await session.commit()
