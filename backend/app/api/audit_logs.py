from typing import Any

from fastapi import APIRouter, Depends, Query

from app.core.security import authorize_roles, get_current_user
from app.services.audit_log_service import list_audit_logs_for_user

router = APIRouter(
    prefix="/audit",
    tags=["Audit"],
)

READ_ROLES = ("ADMIN", "ANALYST", "VIEWER")


@router.get("/logs")
@router.get("/logs/")
def get_audit_logs(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    authorize_roles(
        current_user,
        *READ_ROLES,
        resource_type="audit_log",
    )
    return list_audit_logs_for_user(current_user, limit=limit, offset=offset)
