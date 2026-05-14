from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.shared.domain.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConvergenceError,
    DomainError,
    NotFoundError,
    ValidationError,
)


def _json(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": code, "message": message})


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFoundError)
    async def _not_found(_req: Request, exc: NotFoundError) -> JSONResponse:
        return _json(404, "not_found", str(exc))

    @app.exception_handler(ValidationError)
    async def _validation(_req: Request, exc: ValidationError) -> JSONResponse:
        return _json(422, "validation_error", str(exc))

    @app.exception_handler(AuthenticationError)
    async def _auth(_req: Request, exc: AuthenticationError) -> JSONResponse:
        return _json(401, "authentication_error", str(exc))

    @app.exception_handler(AuthorizationError)
    async def _forbidden(_req: Request, exc: AuthorizationError) -> JSONResponse:
        return _json(403, "authorization_error", str(exc))

    @app.exception_handler(ConvergenceError)
    async def _converge(_req: Request, exc: ConvergenceError) -> JSONResponse:
        return _json(422, "convergence_error", str(exc))

    @app.exception_handler(DomainError)
    async def _domain(_req: Request, exc: DomainError) -> JSONResponse:
        return _json(400, "domain_error", str(exc))
