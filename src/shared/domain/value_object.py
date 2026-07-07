from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ValueObject:
    """Base de los objetos de valor. Las subclases también deben usar ``@dataclass(frozen=True, slots=True)``."""
