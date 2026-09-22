from typing import Any, Literal

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from fastapi.responses import Response

from app.core.security import authorize_roles, get_current_user
from app.services.audit_service import (
    AuditWriteError,
    audit_investigation_create,
    audit_investigation_report,
    audit_investigation_update,
)
from app.services.investigation_authorization import (
    authorize_investigation_read,
    authorize_investigation_update,
    resolve_create_jurisdiction,
)
from app.services.investigations import (
    InvestigationNotFoundError,
    InvestigationValidationError,
    create_investigation,
    get_investigation,
    list_investigations_for_user,
    update_investigation,
)
from app.services.report_pdf import render_investigation_report_pdf
from app.services.report_service import build_investigation_report

router = APIRouter(
    prefix="/investigations",
    tags=["Investigations"],
)

READ_ROLES = ("ADMIN", "ANALYST", "VIEWER")
WRITE_ROLES = ("ADMIN", "ANALYST")


def _raise_audit_unavailable(exc: AuditWriteError) -> None:
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Audit logging unavailable",
    ) from exc


@router.get("")
@router.get("/")
def get_investigations(
    current_user: dict[str, Any] = Depends(get_current_user),
):
    authorize_roles(
        current_user,
        *READ_ROLES,
        resource_type="investigation",
    )
    return list_investigations_for_user(current_user)


@router.get("/{investigation_id}")
def get_investigation_by_id(
    investigation_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    authorize_roles(
        current_user,
        *READ_ROLES,
        resource_type="investigation",
        resource_id=investigation_id,
    )
    try:
        investigation = get_investigation(investigation_id)
        authorize_investigation_read(current_user, investigation)
        return investigation
    except InvestigationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AuditWriteError as exc:
        _raise_audit_unavailable(exc)


@router.get("/{investigation_id}/report")
def get_investigation_report(
    investigation_id: str,
    format: Literal["json", "pdf"] = Query(default="json"),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    authorize_roles(
        current_user,
        *READ_ROLES,
        resource_type="investigation",
        resource_id=investigation_id,
    )
    try:
        investigation = get_investigation(investigation_id)
        authorize_investigation_read(current_user, investigation)
        payload = build_investigation_report(investigation, current_user)
        audit_investigation_report(
            current_user,
            investigation_id=investigation_id,
            jurisdiction=investigation.get("jurisdiction"),
            result="success",
            metadata={"format": format, "source": "investigation"},
        )
        if format == "pdf":
            filename = f"cnas-investigation-{investigation_id}.pdf"
            return Response(
                content=render_investigation_report_pdf(payload),
                media_type="application/pdf",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )
        return payload
    except InvestigationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AuditWriteError as exc:
        _raise_audit_unavailable(exc)


@router.post("")
@router.post("/")
def post_investigation(
    payload: dict[str, Any] = Body(...),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    authorize_roles(
        current_user,
        *WRITE_ROLES,
        resource_type="investigation",
    )
    try:
        jurisdiction = resolve_create_jurisdiction(current_user, payload)
        created = create_investigation(
            payload,
            created_by=current_user["id"],
            jurisdiction=jurisdiction,
        )
        audit_investigation_create(
            current_user,
            investigation_id=created["id"],
            jurisdiction=created.get("jurisdiction"),
            result="success",
            metadata={"name": created.get("name")},
        )
        return created
    except InvestigationValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AuditWriteError as exc:
        _raise_audit_unavailable(exc)


@router.put("/{investigation_id}")
def put_investigation(
    investigation_id: str,
    payload: dict[str, Any] = Body(...),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    authorize_roles(
        current_user,
        *WRITE_ROLES,
        resource_type="investigation",
        resource_id=investigation_id,
    )
    try:
        existing = get_investigation(investigation_id)
        authorize_investigation_update(current_user, existing)
        updated = update_investigation(investigation_id, payload)
        audit_investigation_update(
            current_user,
            investigation_id=investigation_id,
            jurisdiction=updated.get("jurisdiction"),
            result="success",
        )
        return updated
    except InvestigationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvestigationValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AuditWriteError as exc:
        _raise_audit_unavailable(exc)
