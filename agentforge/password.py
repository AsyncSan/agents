"""Password hashing helper using bcrypt directly.

``passlib[bcrypt]`` 1.7 is incompatible with recent ``bcrypt`` releases;
the raw ``bcrypt`` API is simple enough that we do not need passlib.
"""

from __future__ import annotations

import bcrypt

# bcrypt has a 72-byte input limit. We reject anything longer at the
# register/login boundary rather than silently truncating.
MAX_PASSWORD_BYTES = 72


class PasswordTooLong(ValueError):
    pass


def hash_password(plain: str) -> str:
    """Return a bcrypt hash as a UTF-8 string suitable for DB storage."""
    encoded = plain.encode("utf-8")
    if len(encoded) > MAX_PASSWORD_BYTES:
        raise PasswordTooLong(
            f"Password must be at most {MAX_PASSWORD_BYTES} bytes when UTF-8 encoded."
        )
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, stored_hash: str) -> bool:
    """Constant-time verify a plaintext password against a stored hash."""
    if not stored_hash:
        return False
    encoded = plain.encode("utf-8")
    if len(encoded) > MAX_PASSWORD_BYTES:
        return False
    try:
        return bcrypt.checkpw(encoded, stored_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False
