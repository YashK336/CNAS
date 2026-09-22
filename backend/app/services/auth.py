"""Authentication helpers for CNAS users."""

from __future__ import annotations

from typing import Any

import bcrypt

from app.services.user_repository import get_user_repository


class AuthenticationError(Exception):
    pass


def hash_password(password: str) -> str:
    if not isinstance(password, str) or not password:
        raise ValueError("password is required")
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    if not password or not password_hash:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def serialize_public_user(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(user["id"]),
        "username": user["username"],
        "role": user["role"],
        "jurisdictions": list(user.get("jurisdictions") or []),
        "created_at": user["created_at"],
    }


def authenticate_user(username: str, password: str) -> dict[str, Any] | None:
    normalized = (username or "").strip()
    if not normalized:
        return None

    user = get_user_repository().get_by_username(normalized)
    if user is None:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return user
