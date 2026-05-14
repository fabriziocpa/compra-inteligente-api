from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ValueObject:
    """Base for value objects. Subclasses should also use ``@dataclass(frozen=True, slots=True)``."""
