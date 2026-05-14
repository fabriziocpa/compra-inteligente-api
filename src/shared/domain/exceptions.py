class DomainError(Exception):
    """Base class for all domain-level errors."""


class NotFoundError(DomainError):
    """Raised when a requested aggregate is not found."""


class ValidationError(DomainError):
    """Raised when input fails domain validation rules."""


class ConvergenceError(DomainError):
    """Raised when an iterative numerical method fails to converge."""


class AuthenticationError(DomainError):
    """Raised when credentials are invalid or absent."""


class AuthorizationError(DomainError):
    """Raised when an action is not permitted for the current principal."""
