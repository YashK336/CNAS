"""HTTP API for the CNAS data-import / upload workflow."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile, status

from app.core.security import authorize_roles, get_current_user
from app.services.audit_service import (
    AuditWriteError,
    audit_import_confirm,
    audit_import_inspect,
    audit_import_read,
)
from app.services.import_parsing import ImportParseError
from app.services.import_schema import field_catalog
from app.services.import_service import (
    ImportAccessDenied,
    ImportValidationError,
    assert_read_role,
    assert_write_role,
    confirm_import,
    get_import_for_user,
    import_entry_options,
    inspect_manual_record,
    inspect_upload,
    list_imports_for_user,
    update_mappings,
    validate_import,
)
from app.services.import_store import ImportNotFoundError

router = APIRouter(
    prefix="/imports",
    tags=["Data Import"],
)

READ_ROLES = ("ADMIN", "ANALYST", "VIEWER")
WRITE_ROLES = ("ADMIN", "ANALYST")


def _raise_audit_unavailable(exc: AuditWriteError) -> None:
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Audit logging unavailable",
    ) from exc


def _http_from_import_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ImportNotFoundError):
        return HTTPException(status_code=404, detail="Import batch not found")
    if isinstance(exc, ImportAccessDenied):
        return HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, ImportParseError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, ImportValidationError):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(
        status_code=400,
        detail=(
            "The upload could not be processed. Check the file format and "
            "column mapping, then try again."
        ),
    )


@router.get("/fields")
def get_import_fields(
    current_user: dict[str, Any] = Depends(get_current_user),
):
    authorize_roles(
        current_user,
        *READ_ROLES,
        resource_type="data_import",
    )
    return {"data": field_catalog()}


@router.get("/options")
def get_import_options(
    current_user: dict[str, Any] = Depends(get_current_user),
):
    authorize_roles(
        current_user,
        *WRITE_ROLES,
        resource_type="data_import",
    )
    try:
        assert_write_role(current_user)
        return import_entry_options(current_user)
    except ImportAccessDenied as exc:
        raise _http_from_import_error(exc) from exc


@router.get("")
@router.get("/")
def get_imports(
    current_user: dict[str, Any] = Depends(get_current_user),
):
    authorize_roles(
        current_user,
        *READ_ROLES,
        resource_type="data_import",
    )
    try:
        assert_read_role(current_user)
        return list_imports_for_user(current_user)
    except ImportAccessDenied as exc:
        raise _http_from_import_error(exc) from exc


@router.get("/{import_id}")
def get_import(
    import_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    authorize_roles(
        current_user,
        *READ_ROLES,
        resource_type="data_import",
        resource_id=import_id,
    )
    try:
        return get_import_for_user(current_user, import_id)
    except ImportAccessDenied as exc:
        try:
            audit_import_read(current_user, import_id=import_id, result="denied")
        except AuditWriteError as audit_exc:
            _raise_audit_unavailable(audit_exc)
        raise _http_from_import_error(exc) from exc
    except ImportNotFoundError as exc:
        raise _http_from_import_error(exc) from exc


@router.post("/inspect")
async def post_inspect(
    file: UploadFile = File(...),
    source_kind: str = Form(default="structured"),
    jurisdiction: str | None = Form(default=None),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    authorize_roles(
        current_user,
        *WRITE_ROLES,
        resource_type="data_import",
    )
    try:
        assert_write_role(current_user)
        payload = await file.read()
        result = inspect_upload(
            user=current_user,
            filename=file.filename or "upload",
            payload=payload,
            content_type=file.content_type,
            source_kind=source_kind,
            jurisdiction=jurisdiction,
        )
        audit_import_inspect(
            current_user,
            import_id=result.get("id"),
            result="success",
            metadata={
                "filename": result.get("filename"),
                "format": result.get("format"),
                "row_count": result.get("row_count"),
            },
        )
        return result
    except (ImportParseError, ImportAccessDenied) as exc:
        try:
            audit_import_inspect(
                current_user,
                import_id=None,
                result="failure",
                metadata={"reason": exc.__class__.__name__},
            )
        except AuditWriteError as audit_exc:
            _raise_audit_unavailable(audit_exc)
        raise _http_from_import_error(exc) from exc
    except AuditWriteError as exc:
        _raise_audit_unavailable(exc)


@router.post("/inspect-manual")
def post_inspect_manual(
    payload: dict[str, Any] = Body(...),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    authorize_roles(
        current_user,
        *WRITE_ROLES,
        resource_type="data_import",
    )
    try:
        assert_write_role(current_user)
        result = inspect_manual_record(user=current_user, payload=payload)
        audit_import_inspect(
            current_user,
            import_id=result.get("id"),
            result="success",
            metadata={
                "filename": result.get("filename"),
                "format": result.get("format"),
                "row_count": result.get("row_count"),
                "source_kind": "manual",
            },
        )
        return result
    except (ImportParseError, ImportAccessDenied, ImportValidationError) as exc:
        try:
            audit_import_inspect(
                current_user,
                import_id=None,
                result="failure",
                metadata={"reason": exc.__class__.__name__, "source_kind": "manual"},
            )
        except AuditWriteError as audit_exc:
            _raise_audit_unavailable(audit_exc)
        raise _http_from_import_error(exc) from exc
    except AuditWriteError as exc:
        _raise_audit_unavailable(exc)


@router.post("/{import_id}/mapping")
def post_mapping(
    import_id: str,
    payload: dict[str, Any] = Body(...),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    authorize_roles(
        current_user,
        *WRITE_ROLES,
        resource_type="data_import",
        resource_id=import_id,
    )
    try:
        assert_write_role(current_user)
        mappings = payload.get("mappings") or {}
        if not isinstance(mappings, dict):
            raise ImportValidationError("mappings must be an object of column → field")
        return update_mappings(
            user=current_user,
            import_id=import_id,
            user_mappings=mappings,
        )
    except (ImportNotFoundError, ImportAccessDenied, ImportValidationError) as exc:
        raise _http_from_import_error(exc) from exc


@router.post("/{import_id}/validate")
def post_validate(
    import_id: str,
    payload: dict[str, Any] | None = Body(default=None),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    authorize_roles(
        current_user,
        *WRITE_ROLES,
        resource_type="data_import",
        resource_id=import_id,
    )
    body = payload or {}
    try:
        assert_write_role(current_user)
        return validate_import(
            user=current_user,
            import_id=import_id,
            user_mappings=body.get("mappings"),
            skip_indexes=body.get("skip_indexes") or [],
        )
    except (ImportNotFoundError, ImportAccessDenied, ImportValidationError) as exc:
        raise _http_from_import_error(exc) from exc


@router.post("/{import_id}/confirm")
def post_confirm(
    import_id: str,
    payload: dict[str, Any] | None = Body(default=None),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    authorize_roles(
        current_user,
        *WRITE_ROLES,
        resource_type="data_import",
        resource_id=import_id,
    )
    body = payload or {}
    try:
        assert_write_role(current_user)
        result = confirm_import(
            user=current_user,
            import_id=import_id,
            user_mappings=body.get("mappings"),
            skip_indexes=body.get("skip_indexes") or [],
            continue_with_warnings=bool(body.get("continue_with_warnings")),
        )
        audit_import_confirm(
            current_user,
            import_id=import_id,
            result="success",
            metadata={
                "status": result.get("status"),
                "imported": (result.get("result") or {}).get("imported"),
                "failed": (result.get("result") or {}).get("failed"),
            },
        )
        return result
    except (ImportNotFoundError, ImportAccessDenied, ImportValidationError) as exc:
        try:
            audit_import_confirm(
                current_user,
                import_id=import_id,
                result="failure",
                metadata={"reason": exc.__class__.__name__},
            )
        except AuditWriteError as audit_exc:
            _raise_audit_unavailable(audit_exc)
        raise _http_from_import_error(exc) from exc
    except AuditWriteError as exc:
        _raise_audit_unavailable(exc)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail=(
                "Import processing stopped because the file could not be converted "
                "into CNAS records. Check mapping and try again."
            ),
        )
