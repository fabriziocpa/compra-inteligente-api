from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.contexts.vehicles.domain.vehicle import Vehicle
from src.contexts.vehicles.infrastructure.orm_vehicle import VehicleORM
from src.shared.domain.exceptions import NotFoundError
from src.shared.domain.money import Currency


def _to_orm(v: Vehicle, orm: VehicleORM | None = None) -> VehicleORM:
    if orm is None:
        orm = VehicleORM()
    orm.id = v.id
    orm.created_at = v.created_at
    orm.updated_at = v.updated_at
    orm.owner_id = v.owner_id
    orm.brand = v.brand
    orm.model = v.model
    orm.year = v.year
    orm.list_price = v.list_price
    orm.currency = v.currency.value
    return orm


def _from_orm(orm: VehicleORM) -> Vehicle:
    return Vehicle(
        id=orm.id,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
        owner_id=orm.owner_id,
        brand=orm.brand,
        model=orm.model,
        year=orm.year,
        list_price=orm.list_price,
        currency=Currency(orm.currency),
    )


class SqlAlchemyVehicleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, vehicle: Vehicle) -> None:
        self._session.add(_to_orm(vehicle))
        await self._session.flush()

    async def get(self, vehicle_id: UUID) -> Vehicle:
        orm = await self._session.get(VehicleORM, vehicle_id)
        if orm is None:
            raise NotFoundError(f"Vehicle {vehicle_id} not found")
        return _from_orm(orm)

    async def list_for_owner(self, owner_id: UUID) -> list[Vehicle]:
        result = await self._session.execute(
            select(VehicleORM).where(VehicleORM.owner_id == owner_id)
        )
        return [_from_orm(o) for o in result.scalars().all()]

    async def update(self, vehicle: Vehicle) -> None:
        orm = await self._session.get(VehicleORM, vehicle.id)
        if orm is None:
            raise NotFoundError(f"Vehicle {vehicle.id} not found")
        _to_orm(vehicle, orm)
        await self._session.flush()

    async def delete(self, vehicle_id: UUID) -> None:
        orm = await self._session.get(VehicleORM, vehicle_id)
        if orm is None:
            raise NotFoundError(f"Vehicle {vehicle_id} not found")
        await self._session.delete(orm)
        await self._session.flush()
