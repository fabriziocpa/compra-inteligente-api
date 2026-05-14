from __future__ import annotations

from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


class PasswordHasher:
    def hash(self, password: str) -> str:
        return _pwd_context.hash(password)

    def verify(self, password: str, hashed: str) -> bool:
        try:
            return _pwd_context.verify(password, hashed)
        except ValueError:
            return False
