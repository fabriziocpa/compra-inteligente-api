from __future__ import annotations

from fastapi import FastAPI

# Se importan los modelos ORM para poblar BaseORM.metadata por completo.
from src.contexts.audit.infrastructure import orm_operation  # noqa: F401
from src.contexts.audit.interfaces.router import router as operations_router
from src.contexts.auth.infrastructure import orm_user  # noqa: F401
from src.contexts.auth.interfaces.router import router as auth_router
from src.contexts.clients.infrastructure import orm_client  # noqa: F401
from src.contexts.clients.interfaces.router import router as clients_router
from src.contexts.loans.infrastructure import orm_loan, orm_schedule_entry  # noqa: F401
from src.contexts.loans.interfaces.router import router as loans_router
from src.contexts.vehicles.infrastructure import orm_vehicle  # noqa: F401
from src.contexts.vehicles.interfaces.router import router as vehicles_router
from src.shared.interfaces.api_errors import register_exception_handlers

_tags_metadata = [
    {"name": "auth", "description": "Registro, login y token refresh."},
    {"name": "clients", "description": "Gestión de clientes del usuario autenticado."},
    {"name": "vehicles", "description": "Catálogo de vehículos disponibles."},
    {
        "name": "loans",
        "description": (
            "Simulación de crédito vehicular: creación, cronograma de pagos e indicadores "
            "financieros (TIR, TCEA, VAN)."
        ),
    },
    {"name": "operations", "description": "Bitácora de operaciones registradas en la BD."},
    {"name": "health", "description": "Estado del servicio."},
]

app = FastAPI(
    title="Compra Inteligente API",
    description="Backend para simular planes de pago de crédito vehicular bajo Compra Inteligente.",
    version="0.1.0",
    openapi_tags=_tags_metadata,
)

register_exception_handlers(app)

API_PREFIX = "/api/v1"

app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(clients_router, prefix=API_PREFIX)
app.include_router(vehicles_router, prefix=API_PREFIX)
app.include_router(loans_router, prefix=API_PREFIX)
app.include_router(operations_router, prefix=API_PREFIX)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
