from datetime import datetime, timezone
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from app.core.security import authorize_roles, get_current_user
from app.services.audit_service import AuditWriteError, audit_case_report
from app.services.ingestion import load_fir, load_persons
from app.services.report_pdf import render_investigation_report_pdf
from app.services.report_service import build_case_report


router = APIRouter(
    prefix="/cases",
    tags=["Cases"]
)


def _clean(value):
    if value is None:
        return None

    text = str(value).strip()

    if text == "" or text.lower() in {"nan", "none", "null"}:
        return None

    return text


def _equals_ignore_case(series, query):
    needle = query.strip().casefold()

    return series.map(
        lambda value: _clean(value) is not None
        and str(value).strip().casefold() == needle
    )


def _persons_by_id():
    index = {}

    for row in load_persons().to_dict(orient="records"):
        person_id = _clean(row.get("person_id"))
        if person_id:
            index[person_id] = row

    return index


def _involved_person(person_id, persons_by_id):
    if not person_id:
        return None

    person = persons_by_id.get(person_id)

    if person is None:
        return None

    return {
        "entity_id": _clean(person.get("person_id")),
        "name": _clean(person.get("name")),
        "phone": _clean(person.get("phone")),
        "home_city": _clean(person.get("home_city")),
        "risk_group": _clean(person.get("risk_group")),
    }


def _as_sort_datetime(value: Any) -> datetime | None:
    """Parse a date/timestamp for ordering. Display strings are not used."""
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        text = _clean(value)
        if text is None:
            return None
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            import pandas as pd

            stamp = pd.to_datetime(text, errors="coerce")
            if pd.isna(stamp):
                return None
            parsed = stamp.to_pydatetime()
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def sort_case_records(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Newest incident date first; import/creation timestamp breaks ties."""

    def key(row: dict[str, Any]) -> tuple:
        incident = _as_sort_datetime(row.get("date"))
        ingested = _as_sort_datetime(
            row.get("_ingested_at") or row.get("ingested_at")
        )
        fir_id = str(row.get("fir_id") or "")
        return (
            incident is not None,
            incident or datetime.min.replace(tzinfo=timezone.utc),
            ingested is not None,
            ingested or datetime.min.replace(tzinfo=timezone.utc),
            fir_id,
        )

    return sorted(rows, key=key, reverse=True)


def _serialize_case(row, persons_by_id, include_person=False):
    person_id = _clean(row.get("person_id"))

    record = {
        "fir_id": _clean(row.get("fir_id")),
        "person_id": person_id,
        "crime": _clean(row.get("crime")),
        "date": _clean(row.get("date")),
        "location": _clean(row.get("location")),
        "ingested_at": _clean(row.get("_ingested_at") or row.get("ingested_at")),
    }

    if include_person:
        record["involved_person"] = _involved_person(person_id, persons_by_id)

    return record


def list_cases(
    *,
    crime: str | None = None,
    location: str | None = None,
    person_id: str | None = None,
) -> dict[str, Any]:
    df = load_fir()

    if crime and crime.strip():
        df = df[_equals_ignore_case(df["crime"], crime)]

    if location and location.strip():
        df = df[_equals_ignore_case(df["location"], location)]

    if person_id and person_id.strip():
        df = df[_equals_ignore_case(df["person_id"], person_id)]

    persons_by_id = _persons_by_id()
    ordered = sort_case_records(df.to_dict(orient="records"))
    data = [
        _serialize_case(row, persons_by_id, include_person=True)
        for row in ordered
    ]

    return {
        "total": len(data),
        "data": data,
    }


@router.get("")
@router.get("/")
def get_cases(
    crime: Optional[str] = Query(default=None),
    location: Optional[str] = Query(default=None),
    person_id: Optional[str] = Query(default=None),
):
    return list_cases(crime=crime, location=location, person_id=person_id)


@router.get("/{fir_id}")
def get_case(fir_id: str):
    df = load_fir()

    match = df[df["fir_id"].astype(str) == str(fir_id)]

    if match.empty:
        raise HTTPException(
            status_code=404,
            detail="Case not found"
        )

    row = match.iloc[0].to_dict()
    persons_by_id = _persons_by_id()

    return _serialize_case(row, persons_by_id, include_person=True)


@router.get("/{fir_id}/report")
def get_case_report(
    fir_id: str,
    format: Literal["json", "pdf"] = Query(default="json"),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    authorize_roles(
        current_user,
        "ADMIN",
        "ANALYST",
        "VIEWER",
        resource_type="investigation_report",
        resource_id=fir_id,
    )
    try:
        payload = build_case_report(fir_id, current_user)
        if payload is None:
            raise HTTPException(status_code=404, detail="Case not found")
        audit_case_report(
            current_user,
            fir_id=fir_id,
            result="success",
            metadata={"format": format, "source": "case"},
        )
        if format == "pdf":
            filename = f"cnas-case-{fir_id}.pdf"
            return Response(
                content=render_investigation_report_pdf(payload),
                media_type="application/pdf",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )
        return payload
    except AuditWriteError as exc:
        raise HTTPException(
            status_code=503,
            detail="Audit logging unavailable",
        ) from exc
