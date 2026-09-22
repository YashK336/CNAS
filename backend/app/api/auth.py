"""Authentication endpoints for CNAS."""

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, status

from app.core.security import get_current_user, get_current_user_profile, login
from app.services.audit_service import (
    AuditWriteError,
    audit_auth_login_failure,
    audit_auth_login_success,
)
from app.services.auth import AuthenticationError

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


def _raise_audit_unavailable(exc: AuditWriteError) -> None:
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Audit logging unavailable",
    ) from exc


@router.post("/login")
def post_login(payload: dict[str, Any] = Body(...)):
    username = payload.get("username")
    password = payload.get("password")
    if not isinstance(username, str) or not isinstance(password, str):
        try:
            audit_auth_login_failure(username=username if isinstance(username, str) else None)
        except AuditWriteError as exc:
            _raise_audit_unavailable(exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="username and password are required",
        )

    try:
        result = login(username, password)
        audit_auth_login_success(result["user"])
        return result
    except AuthenticationError as exc:
        try:
            audit_auth_login_failure(username=username)
        except AuditWriteError as audit_exc:
            _raise_audit_unavailable(audit_exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except AuditWriteError as exc:
        _raise_audit_unavailable(exc)


@router.get("/me")
def get_me(current_user: dict[str, Any] = Depends(get_current_user)):
    return get_current_user_profile(current_user)
