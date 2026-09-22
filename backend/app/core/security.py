"""JWT configuration and FastAPI authentication dependencies."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Callable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import jwt_settings
from app.services.audit_service import AuditWriteError, audit_auth_unauthenticated
from app.services.auth import AuthenticationError, authenticate_user, serialize_public_user
from app.services.user_repository import get_user_repository

ROLES = ("ADMIN", "ANALYST", "VIEWER")

bearer_scheme = HTTPBearer(auto_error=False)


def create_access_token(user: dict[str, Any]) -> str:
    settings = jwt_settings()
    expires = datetime.now(timezone.utc) + timedelta(minutes=int(settings["expire_minutes"]))
    payload = {
        "sub": str(user["id"]),
        "username": user["username"],
        "role": user["role"],
        "exp": expires,
    }
    return jwt.encode(payload, settings["secret"], algorithm=settings["algorithm"])


def decode_access_token(token: str) -> dict[str, Any]:
    settings = jwt_settings()
    try:
        return jwt.decode(
            token,
            settings["secret"],
            algorithms=[settings["algorithm"]],
        )
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Invalid or expired token") from exc


def _raise_unauthenticated(reason: str) -> None:
    try:
        audit_auth_unauthenticated(reason=reason)
    except AuditWriteError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Audit logging unavailable",
        ) from exc
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        _raise_unauthenticated("missing_or_invalid_scheme")

    try:
        payload = decode_access_token(credentials.credentials)
    except AuthenticationError:
        _raise_unauthenticated("invalid_or_expired_token")

    user = get_user_repository().get_by_id(str(payload.get("sub")))
    if user is None:
        _raise_unauthenticated("user_not_found")
    return user


def require_roles(*allowed_roles: str) -> Callable[..., dict[str, Any]]:
    def dependency(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
        authorize_roles(current_user, *allowed_roles)
        return current_user

    return dependency


def authorize_roles(
    user: dict[str, Any],
    *allowed_roles: str,
    resource_type: str = "authorization",
    resource_id: str | None = None,
) -> None:
    if user.get("role") in set(allowed_roles):
        return

    from app.services.audit_service import audit_authorization_role_denied

    try:
        audit_authorization_role_denied(
            user,
            allowed_roles=allowed_roles,
            resource_type=resource_type,
            resource_id=resource_id,
        )
    except AuditWriteError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Audit logging unavailable",
        ) from exc

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient permissions",
    )


def login(username: str, password: str) -> dict[str, Any]:
    user = authenticate_user(username, password)
    if user is None:
        raise AuthenticationError("Invalid username or password")
    token = create_access_token(user)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": serialize_public_user(user),
    }


def get_current_user_profile(current_user: dict[str, Any]) -> dict[str, Any]:
    return serialize_public_user(current_user)
