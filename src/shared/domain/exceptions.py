"""Jerarquía de errores del dominio (se traducen a HTTP en api_errors)."""


class DomainError(Exception):
    """Clase base de todos los errores de nivel de dominio."""


class NotFoundError(DomainError):
    """El agregado solicitado no existe."""


class ValidationError(DomainError):
    """La entrada viola las reglas de validación del dominio."""


class ConvergenceError(DomainError):
    """Un método numérico iterativo (p. ej. la TIR) no convergió."""


class AuthenticationError(DomainError):
    """Credenciales inválidas o ausentes."""


class AuthorizationError(DomainError):
    """La acción no está permitida para el usuario actual."""
