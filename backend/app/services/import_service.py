"""Data-import orchestration on top of existing CNAS pipelines.

Parse → map → validate → normalize → overlay CSV loaders → entity resolution
(report only, never auto-merge) → optional unstructured extraction → graph
import. Partial success is retained. Rollback is not implemented: Neo4j MERGE
plus overlay rows cannot be reversed safely without a snapshot.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

import pandas as pd

from app.services.adjudication_service import (
    AdjudicationValidationError,
    create_review_from_resolution,
)
from app.services.entity_resolution import (
    CanonicalRegistry,
    build_canonical_registry,
    resolve_candidate,
)
from app.services.extraction import (
    EntityCandidate,
    normalize_bank_account,
    normalize_phone,
    normalize_vehicle,
)
from app.services.graph.importer import import_cnas_graph
from app.services.graph.mapper import map_structured_import_records
from app.services.import_overlay import append_overlay_rows
from app.services.import_parsing import (
    ImportParseError,
    parse_structured_upload,
    parse_unstructured_upload,
)
from app.services.import_schema import (
    UNMAPPED_NOTICE,
    apply_user_mappings,
    mapping_lookup,
)
from app.services.import_store import (
    STATUS_COMPLETE,
    STATUS_COMPLETE_WARNINGS,
    STATUS_DRAFT,
    STATUS_FAILED,
    STATUS_IMPORTING,
    STATUS_PARTIAL,
    STATUS_READY,
    STATUS_VALIDATING,
    ImportAccessDenied,
    ImportNotFoundError,
    create_batch,
    get_batch,
    list_batches,
    save_batch,
)
from app.services.ingestion import load_fir, load_persons
from app.services.investigation_authorization import is_admin, user_jurisdictions
from app.services.user_repository import get_user_repository
from app.services.normalization import (
    NormalizedRecord,
    normalize_row,
    utc_now_iso,
)
from app.services.resolution_config import (
    RESOLUTION_STATUS_AMBIGUOUS,
    RESOLUTION_STATUS_RESOLVED,
)
from app.services.unstructured_graph_mapping import build_unstructured_fir_graph_plan
from app.services.unstructured_ingestion import ingest_unstructured_fir
from app.services.unstructured_ingestion import UnstructuredIngestionValidationError

WRITE_ROLES = frozenset({"ADMIN", "ANALYST"})
READ_ROLES = frozenset({"ADMIN", "ANALYST", "VIEWER"})

IDENTITY_FIELDS = ("fir_id", "person_id", "name", "phone", "vehicle_no")
MANUAL_MAPPED_COLUMNS = (
    "fir_id",
    "date",
    "crime",
    "jurisdiction",
    "person_id",
    "name",
    "phone",
    "vehicle_no",
    "bank_account",
    "social_id",
    "home_city",
    "location",
    "risk_group",
    "vehicle_type",
    "registered_city",
)
IMPORTABLE_CONFIRM_STATUSES = frozenset({"ready", "possible_duplicate"})
WARNING_CONFIRM_STATUSES = frozenset({"incomplete", "invalid"})

JURISDICTION_ALIASES = {
    "del": "DEL",
    "delhi": "DEL",
    "new delhi": "DEL",
    "nct": "DEL",
    "mum": "MUM",
    "mumbai": "MUM",
    "bombay": "MUM",
    "blr": "BLR",
    "bengaluru": "BLR",
    "bangalore": "BLR",
    "hyd": "HYD",
    "hyderabad": "HYD",
    "chn": "CHN",
    "chennai": "CHN",
    "kol": "KOL",
    "kolkata": "KOL",
    "calcutta": "KOL",
    "pun": "PUN",
    "pune": "PUN",
    "jai": "JAI",
    "jaipur": "JAI",
    "amd": "AMD",
    "ahmedabad": "AMD",
}

PHONE_DIGITS = re.compile(r"\D+")
DATE_FORMATS = ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%d.%m.%Y")


class ImportValidationError(ValueError):
    pass


GRAPH_STAGE_SUCCESS = frozenset({"imported", "dry_run"})
SKIP_ALL_NOTICE = (
    "No new records were added because all records were skipped."
)

_crime_index_cache: dict[str, str] | None = None
_unknown_crime_canonical: dict[str, str] = {}


def graph_import_stage_outcome(graph_status: str | None) -> str:
    """Map importer status onto a timeline outcome. Success is never implied."""
    if graph_status in GRAPH_STAGE_SUCCESS:
        return "complete"
    if graph_status == "unavailable":
        return "unavailable"
    return "failed"


def build_stage_results(graph_status: str | None) -> dict[str, str]:
    return {
        "uploading": "complete",
        "validating": "complete",
        "mapping": "complete",
        "normalizing": "complete",
        "extracting": "complete",
        "resolving": "complete",
        "graph_preparation": "complete",
        "graph_import": graph_import_stage_outcome(graph_status),
        "complete": "complete",
    }


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if text == "" or text.lower() in {"nan", "none", "null"}:
        return None
    return text


def normalize_jurisdiction_code(value: Any) -> str | None:
    text = _clean(value)
    if text is None:
        return None
    alias = JURISDICTION_ALIASES.get(text.lower())
    if alias:
        return alias
    compact = re.sub(r"[^a-z0-9]", "", text.lower())
    alias = JURISDICTION_ALIASES.get(compact)
    if alias:
        return alias
    return text.upper() if len(text) <= 5 else text


def _user_scope(user: dict[str, Any]) -> set[str]:
    return {normalize_jurisdiction_code(item) or item for item in user_jurisdictions(user)}


def _is_authorized_jurisdiction(user: dict[str, Any], jurisdiction: str | None) -> bool:
    if is_admin(user):
        return True
    if jurisdiction is None:
        return False
    scope = _user_scope(user)
    code = normalize_jurisdiction_code(jurisdiction)
    return code in scope or jurisdiction in user_jurisdictions(user)


def reset_crime_canonical_cache() -> None:
    global _crime_index_cache, _unknown_crime_canonical
    _crime_index_cache = None
    _unknown_crime_canonical = {}


def crime_match_key(value: str) -> str:
    """Collapse punctuation and whitespace so crime aliases share one key."""
    text = re.sub(r"[-_/.,]+", " ", str(value).strip().lower())
    text = re.sub(r"\s+", " ", text).strip()
    return re.sub(r"\s+", "", text)


def _crime_index() -> dict[str, str]:
    global _crime_index_cache
    if _crime_index_cache is not None:
        return _crime_index_cache
    index: dict[str, str] = {}
    firs = load_fir()
    if not firs.empty and "crime" in firs.columns:
        for raw in firs["crime"].dropna().astype(str):
            key = crime_match_key(raw)
            if key and key not in index:
                index[key] = str(raw).strip()
    _crime_index_cache = index
    return index


def canonical_crime(value: Any) -> str | None:
    """Map equivalent crime spellings onto one canonical value.

    Hyphens, underscores, and spacing are ignored. Unrelated names are not
    merged: ``cyber bullying`` will not become ``Cyber Crime``.
    """
    text = _clean(value)
    if text is None:
        return None
    key = crime_match_key(text)
    if not key:
        return text
    known = _crime_index().get(key)
    if known:
        return known
    cached = _unknown_crime_canonical.get(key)
    if cached:
        return cached
    spaced = re.sub(r"[-_/.,]+", " ", text)
    spaced = re.sub(r"\s+", " ", spaced).strip()
    display = spaced.title() if " " in spaced else text.title()
    _unknown_crime_canonical[key] = display
    return display


def unresolved_decision_message(count: int) -> str:
    noun = "record" if count == 1 else "records"
    return f"{count} {noun} still require a decision. Mark them as Skip or resolve the issue before continuing."


def confirm_row_disposition(
    item: dict[str, Any],
    *,
    continue_with_warnings: bool = False,
) -> str:
    """READY/IMPORT, SKIPPED, UNRESOLVED, or FAILED — never infer skip from not-ready."""
    status = item.get("status")
    if status == "skipped":
        return "skipped"
    if status == "failed":
        return "failed"
    if status in IMPORTABLE_CONFIRM_STATUSES:
        return "import"
    if (
        status in WARNING_CONFIRM_STATUSES
        and item.get("importable")
        and continue_with_warnings
    ):
        return "import"
    return "unresolved"


def _parse_date(value: str) -> tuple[str | None, bool]:
    text = value.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        timestamp = pd.to_datetime(text, errors="coerce", format="%Y-%m-%d")
        if pd.notna(timestamp):
            return str(timestamp.date()), True
        return None, False
    timestamp = pd.to_datetime(text, errors="coerce", dayfirst=True)
    if pd.notna(timestamp):
        return str(timestamp.date()), True
    for fmt in DATE_FORMATS:
        try:
            parsed = pd.to_datetime(text, format=fmt)
            return str(parsed.date()), True
        except (ValueError, TypeError):
            continue
    return None, False


def _phone_valid(value: str) -> bool:
    digits = PHONE_DIGITS.sub("", value)
    if len(digits) == 10:
        return True
    if len(digits) >= 12 and digits.startswith("91"):
        return True
    return False


def _existing_indexes() -> dict[str, Any]:
    persons = load_persons()
    firs = load_fir()
    person_ids = set()
    person_names: dict[str, str] = {}
    phones: dict[str, str] = {}
    fir_ids = set()
    if not persons.empty and "person_id" in persons.columns:
        for _, row in persons.iterrows():
            pid = _clean(row.get("person_id"))
            if pid:
                person_ids.add(pid)
            name = _clean(row.get("name"))
            if pid and name:
                person_names[name.casefold()] = pid
            phone = _clean(row.get("phone"))
            if pid and phone:
                phones[normalize_phone(phone)] = pid
    if not firs.empty and "fir_id" in firs.columns:
        for _, row in firs.iterrows():
            fir_id = _clean(row.get("fir_id"))
            if fir_id:
                fir_ids.add(fir_id)
    return {
        "person_ids": person_ids,
        "person_names": person_names,
        "phones": phones,
        "fir_ids": fir_ids,
    }


def _row_payload(
    row: dict[str, Any],
    column_to_field: dict[str, str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    mapped: dict[str, Any] = {}
    unmapped: dict[str, Any] = {}
    for column, value in row.items():
        field_id = column_to_field.get(column)
        cleaned = _clean(value)
        if field_id:
            if cleaned is not None:
                mapped[field_id] = cleaned
        elif cleaned is not None:
            unmapped[column] = cleaned
    return mapped, unmapped


def _identity_hash(mapped: dict[str, Any]) -> str:
    payload = {key: mapped.get(key) for key in IDENTITY_FIELDS + ("date", "crime", "location")}
    canonical = "|".join(f"{key}={payload[key] or ''}" for key in sorted(payload))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _build_candidate(mapped: dict[str, Any], record_id: str) -> EntityCandidate | None:
    name = mapped.get("name")
    if not name:
        return None
    return EntityCandidate(
        entity_type="person_name",
        value=str(name),
        normalized_value=str(name).strip(),
        confidence=0.9,
        source="data_import",
        record_id=record_id,
        start=0,
        end=len(str(name)),
        offset=0,
        source_text=str(name),
        extraction_method="structured",
        resolution_eligible=True,
    )


def evaluate_rows(
    *,
    user: dict[str, Any],
    rows: list[dict[str, Any]],
    mappings: list[dict[str, Any]],
    skip_indexes: set[int] | None = None,
    registry: CanonicalRegistry | None = None,
) -> dict[str, Any]:
    column_to_field = mapping_lookup(mappings)
    skip = skip_indexes or set()
    existing = _existing_indexes()
    active_registry = registry
    seen_hashes: dict[str, int] = {}
    generated_persons: dict[str, str] = {}
    assessments: list[dict[str, Any]] = []

    ready = incomplete = invalid = unauthorized = duplicates = possible = skipped = 0

    for index, row in enumerate(rows):
        mapped, unmapped = _row_payload(row, column_to_field)
        reasons: list[str] = []
        flags: list[str] = []
        status = "ready"

        jurisdiction = normalize_jurisdiction_code(mapped.get("jurisdiction"))
        if mapped.get("jurisdiction") and not jurisdiction:
            jurisdiction = _clean(mapped.get("jurisdiction"))

        has_identity = any(_clean(mapped.get(field)) for field in IDENTITY_FIELDS)
        has_narrative = bool(_clean(mapped.get("narrative_text")) or _clean(mapped.get("text")))
        if not has_identity and not has_narrative:
            status = "incomplete"
            reasons.append(
                "Not enough identity information. Map a case ID, person, phone, "
                "or vehicle so CNAS can represent this record."
            )

        phone_raw = mapped.get("phone")
        if phone_raw:
            if _phone_valid(str(phone_raw)):
                mapped["phone"] = normalize_phone(str(phone_raw))
            else:
                status = "invalid" if status == "ready" else status
                flags.append("invalid")
                reasons.append(
                    f"Phone value '{phone_raw}' is not a recognisable Indian mobile "
                    "format. The original value is kept as source data and will not "
                    "be used as a phone identifier."
                )
                unmapped.setdefault("phone_original", phone_raw)
                mapped.pop("phone", None)

        vehicle_raw = mapped.get("vehicle_no")
        if vehicle_raw:
            mapped["vehicle_no"] = normalize_vehicle(str(vehicle_raw))

        bank_raw = mapped.get("bank_account")
        if bank_raw:
            mapped["bank_account"] = normalize_bank_account(str(bank_raw))

        crime_raw = mapped.get("crime")
        if crime_raw:
            canonical = canonical_crime(str(crime_raw))
            if canonical:
                if canonical != str(crime_raw).strip():
                    unmapped.setdefault("crime_original", str(crime_raw).strip())
                mapped["crime"] = canonical

        date_raw = mapped.get("date")
        if date_raw:
            parsed, ok = _parse_date(str(date_raw))
            if ok and parsed:
                mapped["date"] = parsed
            else:
                flags.append("invalid")
                reasons.append(
                    f"Date '{date_raw}' could not be parsed. The original value is "
                    "retained as source data; CNAS will not invent a date."
                )
                unmapped.setdefault("date_original", date_raw)
                mapped.pop("date", None)
                if status == "ready":
                    status = "incomplete"

        if jurisdiction:
            mapped["jurisdiction"] = jurisdiction
            if not _is_authorized_jurisdiction(user, jurisdiction):
                status = "unauthorized"
                reasons = [
                    "This record belongs to a jurisdiction outside your current access."
                ]
        elif has_narrative and not jurisdiction:
            status = "incomplete"
            reasons.append(
                "Unstructured extraction requires a jurisdiction. CNAS will not invent one."
            )
        elif not is_admin(user) and (has_identity or has_narrative):
            status = "incomplete"
            reasons.append(
                "Jurisdiction is missing, so CNAS cannot confirm this record is "
                "within your access. Map a jurisdiction/district column or skip "
                "the record."
            )

        ident = _identity_hash(mapped)
        if ident in seen_hashes and status in {"ready", "incomplete"}:
            status = "duplicate"
            reasons.append(
                f"Exact duplicate of row {seen_hashes[ident] + 1} in this file."
            )
        else:
            seen_hashes[ident] = index

        fir_id = _clean(mapped.get("fir_id"))
        person_id = _clean(mapped.get("person_id"))
        if fir_id and fir_id in existing["fir_ids"] and status != "unauthorized":
            status = "duplicate"
            reasons.append(f"FIR/Case ID {fir_id} already exists in CNAS.")
        if person_id and person_id in existing["person_ids"] and status not in {
            "unauthorized",
            "duplicate",
        }:
            status = "duplicate"
            reasons.append(
                f"Person ID {person_id} already exists. CNAS will not merge or "
                "overwrite that person automatically."
            )

        possible_match = None
        existing_phone_owner = None
        if mapped.get("phone"):
            existing_phone_owner = existing["phones"].get(str(mapped["phone"]))
        existing_name_owner = None
        name_key = str(mapped.get("name") or "").strip().casefold()
        if name_key:
            existing_name_owner = existing["person_names"].get(name_key)

        if (
            status in {"ready", "incomplete"}
            and (existing_phone_owner or existing_name_owner)
            and not person_id
        ):
            status = "possible_duplicate"
            possible_match = {
                "entity_id": existing_phone_owner or existing_name_owner,
                "confidence": 1.0 if existing_phone_owner else 0.95,
                "method": "exact_phone" if existing_phone_owner else "exact_name",
            }
            reasons.append(
                "Possible match to an existing person. CNAS will not merge "
                "automatically; skip this row or continue as a new person."
            )
        elif (
            status in {"ready", "incomplete"}
            and mapped.get("name")
            and not person_id
        ):
            if active_registry is None:
                active_registry = build_canonical_registry()
            candidate = _build_candidate(mapped, f"import-row:{index}")
            if candidate is not None:
                try:
                    result = resolve_candidate(
                        candidate,
                        active_registry,
                        jurisdiction=jurisdiction,
                    )
                except Exception:
                    result = {}
                res_status = result.get("status")
                if res_status == RESOLUTION_STATUS_RESOLVED and result.get(
                    "matched_entity_id"
                ):
                    status = "possible_duplicate"
                    possible_match = {
                        "entity_id": result.get("matched_entity_id"),
                        "confidence": result.get("confidence"),
                        "method": result.get("method"),
                    }
                    reasons.append(
                        "Possible match to an existing person. CNAS will not merge "
                        "automatically; skip this row or continue as a new person."
                    )
                elif res_status == RESOLUTION_STATUS_AMBIGUOUS:
                    status = "possible_duplicate"
                    possible_match = {
                        "proposed_entity_ids": result.get("proposed_entity_ids") or [],
                        "confidence": result.get("confidence"),
                        "method": result.get("method"),
                        "ambiguous": True,
                    }
                    reasons.append(
                        "Ambiguous identity match. The record can still be imported "
                        "as a new person; a review will be queued instead of merging."
                    )

        if status == "ready" and unmapped:
            flags.append("unmapped")

        after_phone = any(_clean(mapped.get(field)) for field in IDENTITY_FIELDS) or has_narrative
        importable = False
        explicitly_skipped = index in skip
        was_unauthorized = status == "unauthorized"
        if explicitly_skipped:
            skipped += 1
            if not any("chose to skip" in reason for reason in reasons):
                reasons.append("Investigator chose to skip this record.")
            status = "skipped"
            importable = False
            disposition = "skipped"
        elif status == "ready":
            importable = True
            ready += 1
            disposition = "import"
        elif status == "possible_duplicate":
            importable = True
            possible += 1
            disposition = "import"
        elif status == "incomplete":
            incomplete += 1
            missing_scope = (not is_admin(user)) and not jurisdiction
            importable = after_phone and not missing_scope
            if has_narrative and not jurisdiction:
                importable = False
            disposition = "unresolved"
        elif status == "invalid":
            invalid += 1
            importable = after_phone
            disposition = "unresolved"
        elif status == "unauthorized":
            unauthorized += 1
            disposition = "unresolved"
        elif status == "duplicate":
            duplicates += 1
            disposition = "unresolved"
        elif status == "failed":
            disposition = "failed"
        else:
            disposition = "unresolved"

        redacted = was_unauthorized and not is_admin(user)
        preview_mapped = {} if redacted else mapped
        preview_unmapped = {} if redacted else unmapped

        person_key = None
        if not redacted:
            if person_id:
                person_key = person_id
            else:
                grouping = "|".join(
                    [
                        str(mapped.get("name") or "").casefold(),
                        str(mapped.get("phone") or ""),
                        str(mapped.get("vehicle_no") or ""),
                    ]
                )
                if grouping != "||":
                    person_key = generated_persons.setdefault(
                        grouping, f"IMP-{index:04d}"
                    )

        assessments.append(
            {
                "index": index,
                "status": status,
                "reasons": reasons,
                "flags": flags,
                "mapped": preview_mapped,
                "unmapped": preview_unmapped,
                "jurisdiction": None if redacted else jurisdiction,
                "possible_match": None if redacted else possible_match,
                "person_key": None if redacted else person_key,
                "redacted": redacted,
                "importable": importable,
                "disposition": disposition,
                "unmapped_notice": UNMAPPED_NOTICE if unmapped and not redacted else None,
            }
        )

    unauthorized_message = None
    if unauthorized:
        unauthorized_message = (
            f"{unauthorized} record{'s' if unauthorized != 1 else ''} cannot be "
            "imported because they belong to jurisdictions outside your current "
            "access. Remove or skip them before import. Their contents are not "
            "shown."
        )

    return {
        "detected": len(rows),
        "ready": ready,
        "incomplete": incomplete,
        "invalid": invalid,
        "duplicates": duplicates,
        "possible_duplicates": possible,
        "unauthorized": unauthorized,
        "skipped": skipped,
        "unmapped_columns": [
            item["column"] for item in mappings if not item.get("cnas_field")
        ],
        "unauthorized_message": unauthorized_message,
        "rows": assessments,
        "importable_indexes": [
            item["index"] for item in assessments if item.get("importable")
        ],
        "unresolved_indexes": [
            item["index"]
            for item in assessments
            if item.get("disposition") == "unresolved"
        ],
        "blocking_unauthorized": unauthorized > 0,
        "blocking_unresolved": any(
            item.get("disposition") == "unresolved" for item in assessments
        ),
        "can_continue_with_warnings": incomplete > 0 or possible > 0 or invalid > 0,
    }


def _public_batch(batch: dict[str, Any], *, include_rows: bool = False) -> dict[str, Any]:
    payload = {
        "id": batch["id"],
        "filename": batch.get("filename"),
        "format": batch.get("format"),
        "kind": batch.get("kind"),
        "source_kind": batch.get("source_kind"),
        "status": batch.get("status"),
        "row_count": batch.get("row_count"),
        "created_at": batch.get("created_at"),
        "updated_at": batch.get("updated_at"),
        "uploader_id": batch.get("uploader_id"),
        "uploader_username": batch.get("uploader_username"),
        "columns": batch.get("columns") or [],
        "samples": batch.get("samples") or {},
        "mappings": batch.get("mappings") or [],
        "validation": batch.get("validation_summary"),
        "stages": batch.get("stages") or [],
        "result": batch.get("result"),
        "error": batch.get("error"),
        "limitation": batch.get("limitation"),
    }
    if include_rows:
        payload["preview_rows"] = (batch.get("validation") or {}).get("rows") or []
    return payload


def _assert_owner_or_admin(user: dict[str, Any], batch: dict[str, Any]) -> None:
    if is_admin(user):
        return
    if batch.get("uploader_id") != user.get("id"):
        raise ImportAccessDenied(
            "You do not have access to this import batch."
        )


def inspect_upload(
    *,
    user: dict[str, Any],
    filename: str,
    payload: bytes,
    content_type: str | None,
    source_kind: str,
    jurisdiction: str | None = None,
) -> dict[str, Any]:
    kind = (source_kind or "structured").strip().lower()
    if kind not in {"structured", "unstructured"}:
        raise ImportParseError(
            "Choose Structured table (CSV / JSON / Excel) or Unstructured "
            "narrative. CNAS does not auto-detect arbitrary binary files."
        )

    if kind == "structured":
        parsed = parse_structured_upload(
            filename=filename, payload=payload, content_type=content_type
        )
    else:
        parsed = parse_unstructured_upload(
            filename=filename, payload=payload, content_type=content_type
        )
        if jurisdiction:
            for row in parsed["rows"]:
                row.setdefault("jurisdiction", jurisdiction)
        if parsed["rows"]:
            parsed["columns"] = list(parsed["rows"][0].keys())

    mappings = apply_user_mappings(parsed["columns"], None)
    if kind == "unstructured":
        mappings = apply_user_mappings(
            parsed["columns"],
            {
                "text": "narrative_text",
                "source_ref": "source_ref",
                "jurisdiction": "jurisdiction",
            },
        )

    batch = create_batch(
        {
            "filename": filename,
            "format": parsed["format"],
            "kind": parsed["kind"],
            "source_kind": kind,
            "status": STATUS_DRAFT,
            "row_count": parsed["row_count"],
            "columns": parsed["columns"],
            "samples": parsed["samples"],
            "rows": parsed["rows"],
            "mappings": mappings,
            "uploader_id": user.get("id"),
            "uploader_username": user.get("username"),
            "default_jurisdiction": jurisdiction,
            "limitation": (
                "Safe batch rollback is not available: imported graph edges use "
                "idempotent MERGE and overlay rows share the live People/Cases "
                "datasets."
            ),
        }
    )
    return {
        **_public_batch(batch),
        "accepted_formats": {
            "structured": "CSV, JSON (array of objects), Excel (.xlsx)",
            "unstructured": "plain text (.txt, .md) or JSON with a text field",
        },
        "security_notice": (
            "Only upload investigative information you are authorized to process."
        ),
    }


def _public_investigator(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": record.get("id"),
        "username": record.get("username"),
        "role": record.get("role"),
        "jurisdictions": list(record.get("jurisdictions") or []),
    }


def _known_jurisdiction_codes() -> list[str]:
    codes = set(JURISDICTION_ALIASES.values())
    firs = load_fir()
    if not firs.empty and "jurisdiction" in firs.columns:
        for raw in firs["jurisdiction"].dropna().astype(str):
            code = normalize_jurisdiction_code(raw)
            if code:
                codes.add(code)
    return sorted(codes)


def import_entry_options(user: dict[str, Any]) -> dict[str, Any]:
    firs = load_fir()
    crimes: list[str] = []
    if not firs.empty and "crime" in firs.columns:
        crimes = sorted(
            {
                str(value).strip()
                for value in firs["crime"].dropna().astype(str)
                if str(value).strip()
            }
        )

    assigned = [
        normalize_jurisdiction_code(item) or item for item in user_jurisdictions(user)
    ]
    admin = is_admin(user)
    if admin:
        jurisdictions = _known_jurisdiction_codes()
        investigators = [
            _public_investigator(record)
            for record in get_user_repository().list_all()
            if record.get("role") in WRITE_ROLES
        ]
    else:
        jurisdictions = assigned
        investigators = [_public_investigator(user)]

    default_jurisdiction = jurisdictions[0] if len(jurisdictions) == 1 else None
    return {
        "investigator_locked": not admin,
        "jurisdiction_locked": not admin and len(jurisdictions) <= 1,
        "default_investigator": user.get("username"),
        "default_jurisdiction": default_jurisdiction,
        "jurisdictions": jurisdictions,
        "investigators": investigators,
        "crimes": crimes,
    }


def _enforce_manual_scope(
    user: dict[str, Any],
    *,
    jurisdiction: str | None,
    investigator: str | None,
) -> tuple[str | None, str]:
    requested_investigator = _clean(investigator)
    if is_admin(user):
        if requested_investigator:
            target = get_user_repository().get_by_username(requested_investigator)
            if target is None or target.get("role") not in WRITE_ROLES:
                raise ImportAccessDenied(
                    "That investigator is not authorized for data import."
                )
            chosen_investigator = str(target["username"])
        else:
            chosen_investigator = str(user.get("username") or "")
    else:
        current_username = str(user.get("username") or "")
        if requested_investigator and requested_investigator != current_username:
            raise ImportAccessDenied(
                "You cannot submit investigative records as another investigator."
            )
        chosen_investigator = current_username

    requested_jurisdiction = normalize_jurisdiction_code(jurisdiction)
    assigned = [
        normalize_jurisdiction_code(item) or item for item in user_jurisdictions(user)
    ]
    if is_admin(user):
        return requested_jurisdiction, chosen_investigator

    if requested_jurisdiction:
        if not _is_authorized_jurisdiction(user, requested_jurisdiction):
            raise ImportAccessDenied(
                "You are not authorized to import records for that jurisdiction."
            )
        return requested_jurisdiction, chosen_investigator

    if len(assigned) == 1:
        return assigned[0], chosen_investigator
    return None, chosen_investigator


def _manual_payload_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    body = payload or {}
    raw = body.get("records")
    if isinstance(raw, list):
        records = [item for item in raw if isinstance(item, dict)]
        if not records:
            raise ImportValidationError(
                "Add at least one investigative record before validating."
            )
        return records
    return [body]


def _build_manual_row(user: dict[str, Any], body: dict[str, Any]) -> dict[str, Any]:
    jurisdiction, investigator = _enforce_manual_scope(
        user,
        jurisdiction=_clean(body.get("jurisdiction")),
        investigator=_clean(body.get("investigator")),
    )

    crime_raw = _clean(body.get("crime"))
    crime = canonical_crime(crime_raw) if crime_raw else None
    date_raw = _clean(body.get("date"))
    parsed_date = None
    if date_raw:
        parsed_date, ok = _parse_date(date_raw)
        if not ok:
            parsed_date = date_raw

    row: dict[str, Any] = {}
    values = {
        "fir_id": _clean(body.get("fir_id")),
        "date": parsed_date,
        "crime": crime,
        "jurisdiction": jurisdiction,
        "person_id": _clean(body.get("person_id")),
        "name": _clean(body.get("name")),
        "phone": _clean(body.get("phone")),
        "vehicle_no": _clean(body.get("vehicle_no")),
        "bank_account": _clean(body.get("bank_account")),
        "social_id": _clean(body.get("social_id")),
        "home_city": _clean(body.get("home_city")),
        "location": _clean(body.get("location")),
        "risk_group": _clean(body.get("risk_group")),
        "vehicle_type": _clean(body.get("vehicle_type")),
        "registered_city": _clean(body.get("registered_city")),
    }
    for column in MANUAL_MAPPED_COLUMNS:
        value = values.get(column)
        if value is not None:
            row[column] = value

    if investigator:
        row["Investigator"] = investigator
    notes = _clean(body.get("notes"))
    if notes:
        row["Investigator Notes"] = notes
    if crime_raw and crime and crime_raw != crime:
        row["crime_original"] = crime_raw
    if date_raw and parsed_date and date_raw != parsed_date:
        row["date_original"] = date_raw

    custom_fields = body.get("custom_fields") or []
    if isinstance(custom_fields, dict):
        custom_fields = [
            {"key": key, "value": value} for key, value in custom_fields.items()
        ]
    if isinstance(custom_fields, list):
        reserved = set(row.keys()) | set(MANUAL_MAPPED_COLUMNS)
        for item in custom_fields:
            if not isinstance(item, dict):
                continue
            key = _clean(item.get("key") or item.get("name"))
            value = _clean(item.get("value"))
            if key and value and key not in reserved:
                row[key] = value
                reserved.add(key)
    return row


def inspect_manual_record(
    *,
    user: dict[str, Any],
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Create an import batch from one or more case-centered investigator forms."""
    records = _manual_payload_records(payload)
    rows = [_build_manual_row(user, record) for record in records]
    columns: list[str] = []
    for row in rows:
        for column in row.keys():
            if column not in columns:
                columns.append(column)
    mappings = apply_user_mappings(columns, None)
    samples: dict[str, list[str]] = {column: [] for column in columns}
    for row in rows:
        for column in columns:
            value = row.get(column)
            if value is not None and len(samples[column]) < 3:
                samples[column].append(str(value))

    batch = create_batch(
        {
            "filename": "manual-entry" if len(rows) == 1 else f"manual-entry-{len(rows)}",
            "format": "manual",
            "kind": "structured",
            "source_kind": "manual",
            "status": STATUS_DRAFT,
            "row_count": len(rows),
            "columns": columns,
            "samples": samples,
            "rows": rows,
            "mappings": mappings,
            "uploader_id": user.get("id"),
            "uploader_username": user.get("username"),
            "limitation": (
                "Safe batch rollback is not available: imported graph edges use "
                "idempotent MERGE and overlay rows share the live People/Cases "
                "datasets."
            ),
        }
    )
    return {
        **_public_batch(batch),
        "security_notice": (
            "Only upload investigative information you are authorized to process."
        ),
    }


def update_mappings(
    *,
    user: dict[str, Any],
    import_id: str,
    user_mappings: dict[str, str | None],
) -> dict[str, Any]:
    batch = get_batch(import_id)
    _assert_owner_or_admin(user, batch)
    mappings = apply_user_mappings(batch.get("columns") or [], user_mappings)
    save_batch(import_id, {"mappings": mappings, "status": STATUS_DRAFT})
    return _public_batch(get_batch(import_id))


def validate_import(
    *,
    user: dict[str, Any],
    import_id: str,
    user_mappings: dict[str, str | None] | None = None,
    skip_indexes: list[int] | None = None,
) -> dict[str, Any]:
    batch = get_batch(import_id)
    _assert_owner_or_admin(user, batch)
    save_batch(import_id, {"status": STATUS_VALIDATING})
    mappings = batch.get("mappings") or apply_user_mappings(batch.get("columns") or [], None)
    if user_mappings is not None:
        mappings = apply_user_mappings(batch.get("columns") or [], user_mappings)

    evaluation = evaluate_rows(
        user=user,
        rows=batch.get("rows") or [],
        mappings=mappings,
        skip_indexes=set(skip_indexes or []),
    )
    summary = {
        "detected": evaluation["detected"],
        "ready": evaluation["ready"],
        "incomplete": evaluation["incomplete"],
        "invalid": evaluation["invalid"],
        "duplicates": evaluation["duplicates"],
        "possible_duplicates": evaluation["possible_duplicates"],
        "unauthorized": evaluation["unauthorized"],
        "skipped": evaluation["skipped"],
        "unmapped_columns": evaluation["unmapped_columns"],
        "unauthorized_message": evaluation["unauthorized_message"],
        "blocking_unauthorized": evaluation["blocking_unauthorized"],
        "blocking_unresolved": evaluation["blocking_unresolved"],
        "unresolved": len(evaluation["unresolved_indexes"]),
        "can_continue_with_warnings": evaluation["can_continue_with_warnings"],
    }
    status = STATUS_READY
    if evaluation["blocking_unauthorized"]:
        status = STATUS_READY
    save_batch(
        import_id,
        {
            "status": status,
            "mappings": mappings,
            "validation": evaluation,
            "validation_summary": summary,
            "skip_indexes": list(skip_indexes or []),
        },
    )
    public = _public_batch(get_batch(import_id), include_rows=True)
    public["validation"] = summary
    public["preview_rows"] = evaluation["rows"]
    return public


def _person_id_for(item: dict[str, Any], import_id: str) -> str:
    mapped = item.get("mapped") or {}
    if mapped.get("person_id"):
        return str(mapped["person_id"])
    key = item.get("person_key")
    if key and str(key).startswith("IMP-"):
        return f"IMP-{import_id[:8]}-{str(key).split('-')[-1]}"
    if key:
        return str(key)
    return f"IMP-{import_id[:8]}-{item['index']:04d}"


def _overlay_person(
    item: dict[str, Any],
    import_id: str,
    ingested_at: str | None = None,
) -> dict[str, Any]:
    mapped = item.get("mapped") or {}
    person_id = _person_id_for(item, import_id)
    home_city = mapped.get("home_city")
    return {
        "person_id": person_id,
        "name": mapped.get("name") or person_id,
        "phone": mapped.get("phone"),
        "vehicle_no": mapped.get("vehicle_no"),
        "bank_account": mapped.get("bank_account"),
        "social_id": mapped.get("social_id"),
        "home_city": home_city,
        "risk_group": mapped.get("risk_group"),
        "_import_id": import_id,
        "_ingested_at": ingested_at,
    }


def _overlay_fir(
    item: dict[str, Any],
    import_id: str,
    person_id: str,
    ingested_at: str | None = None,
) -> dict[str, Any] | None:
    mapped = item.get("mapped") or {}
    fir_id = mapped.get("fir_id")
    if not fir_id:
        return None
    return {
        "fir_id": fir_id,
        "person_id": person_id,
        "crime": mapped.get("crime"),
        "date": mapped.get("date"),
        "location": mapped.get("location"),
        "_import_id": import_id,
        "_ingested_at": ingested_at,
    }


def _overlay_vehicle(item: dict[str, Any], import_id: str, person_id: str) -> dict[str, Any] | None:
    mapped = item.get("mapped") or {}
    vehicle_no = mapped.get("vehicle_no")
    if not vehicle_no:
        return None
    return {
        "person_id": person_id,
        "vehicle_no": vehicle_no,
        "registered_city": mapped.get("registered_city"),
        "vehicle_type": mapped.get("vehicle_type"),
        "_import_id": import_id,
    }


def _mapping_rows(person: dict[str, Any], import_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {
            "entity_id": person["person_id"],
            "entity_type": "person",
            "source": "data_import",
            "source_id": person["person_id"],
            "_import_id": import_id,
        }
    ]
    if person.get("phone"):
        rows.append(
            {
                "entity_id": person["person_id"],
                "entity_type": "phone",
                "source": "data_import",
                "source_id": person["phone"],
                "_import_id": import_id,
            }
        )
    if person.get("vehicle_no"):
        rows.append(
            {
                "entity_id": person["person_id"],
                "entity_type": "vehicle",
                "source": "data_import",
                "source_id": person["vehicle_no"],
                "_import_id": import_id,
            }
        )
    if person.get("bank_account"):
        rows.append(
            {
                "entity_id": person["person_id"],
                "entity_type": "bank_account",
                "source": "data_import",
                "source_id": person["bank_account"],
                "_import_id": import_id,
            }
        )
    return rows


def _normalized_from_overlay(source: str, rows: list[dict[str, Any]], ingested_at: str) -> list[NormalizedRecord]:
    records: list[NormalizedRecord] = []
    for index, row in enumerate(rows):
        payload = {key: value for key, value in row.items() if key != "_import_id"}
        series = pd.Series(payload)
        record = normalize_row(source, series, index, ingested_at=ingested_at)
        metadata = {
            "import_id": row.get("_import_id"),
            "extraction_method": "structured",
        }
        record["data"] = {**record["data"], "metadata": metadata}
        records.append(record)
    return records


def _skipped_row_payload(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "index": item.get("index"),
        "status": item.get("status"),
        "reasons": item.get("reasons") or ["Record was skipped."],
        "redacted": item.get("redacted", False),
    }


def _finish_skipped_only_import(
    *,
    user: dict[str, Any],
    import_id: str,
    batch: dict[str, Any],
    skipped_items: list[dict[str, Any]],
) -> dict[str, Any]:
    """Complete a batch when every record was skipped. No overlay or graph write."""
    ingested_at = utc_now_iso()
    skipped_rows = [_skipped_row_payload(item) for item in skipped_items]
    notice = SKIP_ALL_NOTICE
    result = {
        "imported": 0,
        "skipped": len(skipped_items),
        "failed": 0,
        "warnings": 1,
        "queued_reviews": 0,
        "persons": 0,
        "firs": 0,
        "vehicles": 0,
        "notice": notice,
        "graph": {
            "status": None,
            "nodes": None,
            "relationships": None,
            "detail": None,
            "warning": None,
        },
        "stage_results": {
            "uploading": "complete",
            "validating": "complete",
            "mapping": "complete",
            "complete": "complete",
        },
        "failed_rows": [],
        "warning_reasons": [
            {
                "index": None,
                "status": "skipped",
                "reasons": [notice],
            }
        ],
        "skipped_rows": skipped_rows,
        "provenance": {
            "import_id": import_id,
            "source_file": batch.get("filename"),
            "uploader_id": user.get("id"),
            "uploader_username": user.get("username"),
            "timestamp": ingested_at,
            "extraction_method": (
                "unstructured" if batch.get("kind") == "unstructured" else "structured"
            ),
            "records": [],
        },
    }
    save_batch(
        import_id,
        {
            "status": STATUS_COMPLETE_WARNINGS,
            "stages": ["uploading", "validating", "mapping", "complete"],
            "result": result,
            "error": None,
        },
    )
    public = _public_batch(get_batch(import_id))
    public["result"] = result
    return public


def confirm_import(
    *,
    user: dict[str, Any],
    import_id: str,
    user_mappings: dict[str, str | None] | None = None,
    skip_indexes: list[int] | None = None,
    continue_with_warnings: bool = False,
    include_ner: bool = True,
    dry_run_graph: bool = False,
) -> dict[str, Any]:
    batch = get_batch(import_id)
    _assert_owner_or_admin(user, batch)

    validate_import(
        user=user,
        import_id=import_id,
        user_mappings=user_mappings,
        skip_indexes=skip_indexes,
    )
    batch = get_batch(import_id)
    evaluation = batch.get("validation") or {}
    rows = evaluation.get("rows") or []
    to_import: list[dict[str, Any]] = []
    skipped_items: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    for item in rows:
        disposition = confirm_row_disposition(
            item,
            continue_with_warnings=continue_with_warnings,
        )
        if disposition == "skipped":
            skipped_items.append(item)
        elif disposition == "import":
            to_import.append(item)
        else:
            unresolved.append(item)

    if unresolved:
        raise ImportValidationError(unresolved_decision_message(len(unresolved)))

    if not to_import:
        if skipped_items:
            return _finish_skipped_only_import(
                user=user,
                import_id=import_id,
                batch=batch,
                skipped_items=skipped_items,
            )
        raise ImportValidationError(
            "No records remain to import after validation. Skip unauthorized "
            "or invalid rows, then confirm again."
        )

    save_batch(import_id, {"status": STATUS_IMPORTING, "stages": ["uploading", "validating", "mapping"]})

    ingested_at = utc_now_iso()
    person_rows: list[dict[str, Any]] = []
    fir_rows: list[dict[str, Any]] = []
    vehicle_rows: list[dict[str, Any]] = []
    mapping_rows: list[dict[str, Any]] = []
    seen_persons: set[str] = set()
    provenance_rows: list[dict[str, Any]] = []
    queued_reviews: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    imported_items: list[dict[str, Any]] = []
    warning_items: list[dict[str, Any]] = []

    stages = ["uploading", "validating", "mapping", "normalizing"]
    save_batch(import_id, {"stages": stages})

    for item in to_import:
        try:
            mapped = item.get("mapped") or {}
            structured = any(_clean(mapped.get(field)) for field in IDENTITY_FIELDS)
            person_id = None
            if structured:
                person = _overlay_person(item, import_id, ingested_at)
                person_id = person["person_id"]
                if person_id not in seen_persons:
                    person_rows.append(person)
                    mapping_rows.extend(_mapping_rows(person, import_id))
                    seen_persons.add(person_id)
                fir = _overlay_fir(item, import_id, person_id, ingested_at)
                if fir:
                    fir_rows.append(fir)
                vehicle = _overlay_vehicle(item, import_id, person_id)
                if vehicle:
                    vehicle_rows.append(vehicle)
            provenance_rows.append(
                {
                    "index": item["index"],
                    "status": "imported",
                    "person_id": person_id,
                    "fir_id": mapped.get("fir_id"),
                    "original": item.get("mapped"),
                    "unmapped": item.get("unmapped") or {},
                    "mapping": {
                        column: field
                        for column, field in mapping_lookup(batch.get("mappings") or []).items()
                    },
                    "jurisdiction": item.get("jurisdiction"),
                    "possible_match": item.get("possible_match"),
                    "extraction_method": (
                        "unstructured"
                        if mapped.get("narrative_text") and not structured
                        else "structured"
                    ),
                }
            )
            if item.get("status") in {"incomplete", "possible_duplicate"}:
                warning_items.append(item)
            imported_items.append(item)

            match = item.get("possible_match") or {}
            if match.get("ambiguous"):
                candidate = _build_candidate(mapped, f"import:{import_id}:{item['index']}")
                proposed = match.get("proposed_entity_ids") or []
                if candidate is not None and proposed:
                    try:
                        review = create_review_from_resolution(
                            result={
                                "status": RESOLUTION_STATUS_AMBIGUOUS,
                                "candidate_value": mapped.get("name"),
                                "entity_type": candidate["entity_type"],
                                "proposed_entity_ids": proposed,
                                "confidence": match.get("confidence") or 0.0,
                                "method": match.get("method") or "fuzzy_name",
                            },
                            jurisdiction=item.get("jurisdiction"),
                            candidate=candidate,
                        )
                    except AdjudicationValidationError:
                        review = None
                    if review is not None:
                        queued_reviews.append(review)
        except Exception as exc:  # noqa: BLE001 - isolate per-record failure
            failed.append(
                {
                    "index": item.get("index"),
                    "status": "failed",
                    "reasons": [
                        "This record could not be converted into a CNAS entity. "
                        "It was skipped; other records were not discarded."
                    ],
                    "detail": str(exc.__class__.__name__),
                }
            )

    append_overlay_rows("persons", person_rows)
    append_overlay_rows("fir", fir_rows)
    append_overlay_rows("vehicles", vehicle_rows)
    append_overlay_rows("entity_mapping", mapping_rows)

    stages.append("extracting")
    stages.append("resolving")
    save_batch(import_id, {"stages": stages})

    unstructured_plans = []
    kind = batch.get("kind")
    if kind == "unstructured" or any(
        (item.get("mapped") or {}).get("narrative_text") for item in to_import
    ):
        for item in to_import:
            mapped = item.get("mapped") or {}
            text = mapped.get("narrative_text") or mapped.get("text")
            if not text:
                continue
            jurisdiction = item.get("jurisdiction")
            if not jurisdiction and is_admin(user):
                failed.append(
                    {
                        "index": item["index"],
                        "status": "failed",
                        "reasons": [
                            "Unstructured extraction requires a jurisdiction. "
                            "CNAS will not invent one."
                        ],
                    }
                )
                continue
            if not jurisdiction:
                continue
            source_ref = mapped.get("source_ref") or mapped.get("fir_id") or f"{import_id}:{item['index']}"
            try:
                record = ingest_unstructured_fir(
                    {
                        "source": "unstructured_fir",
                        "source_ref": str(source_ref),
                        "jurisdiction": str(jurisdiction),
                        "text": str(text),
                        "metadata": {
                            "import_id": import_id,
                            "uploader_id": user.get("id"),
                            "unmapped": item.get("unmapped") or {},
                        },
                    },
                    ingested_at=ingested_at,
                )
                plan_result = build_unstructured_fir_graph_plan(
                    record,
                    include_ner=include_ner,
                    queue_reviews=True,
                )
                unstructured_plans.append(plan_result)
                queued_reviews.extend(plan_result.queued_reviews)
            except (UnstructuredIngestionValidationError, Exception) as exc:  # noqa: BLE001
                failed.append(
                    {
                        "index": item.get("index"),
                        "status": "failed",
                        "reasons": [
                            "Narrative text could not be extracted. Structured "
                            "fields from this row were still imported where valid."
                        ],
                        "detail": str(exc.__class__.__name__),
                    }
                )

    stages.append("graph_preparation")
    save_batch(import_id, {"stages": stages})

    person_records = _normalized_from_overlay("persons", person_rows, ingested_at)
    fir_records = _normalized_from_overlay("fir", fir_rows, ingested_at)
    vehicle_records = _normalized_from_overlay("vehicles", vehicle_rows, ingested_at)
    plan = map_structured_import_records(
        persons=person_records,
        firs=fir_records,
        vehicles=vehicle_records,
    )
    for build in unstructured_plans:
        plan.nodes.extend(build.plan.nodes)
        plan.relationships.extend(build.plan.relationships)

    save_batch(import_id, {"stages": stages})

    graph_result = import_cnas_graph(plan=plan, dry_run=dry_run_graph)
    graph_status = str(graph_result.get("status") or "failed")
    graph_warning = None
    if graph_status == "unavailable":
        graph_warning = (
            "Records were added to People and Cases. Graph import did not "
            "complete because the graph store is unavailable. Retry graph "
            "import once it is available."
        )
    elif graph_status == "failed":
        graph_warning = (
            "Records were added to People and Cases. Graph import did not "
            "complete; retry graph import once the graph store is available."
        )

    imported_count = len(imported_items)
    skipped_count = len(skipped_items)
    failed_count = len(failed)
    warning_reasons = [
        {
            "index": item["index"],
            "status": item["status"],
            "reasons": item.get("reasons") or [],
        }
        for item in warning_items
    ]
    if graph_warning:
        warning_reasons.append(
            {
                "index": None,
                "status": graph_status,
                "reasons": [graph_warning],
            }
        )
    warning_count = len(warning_reasons)
    graph_outcome = graph_import_stage_outcome(graph_status)
    if graph_outcome == "complete":
        stages.append("graph_import")

    if imported_count == 0 and failed_count > 0:
        final_status = STATUS_FAILED
    elif failed_count > 0 and imported_count > 0:
        final_status = STATUS_PARTIAL
    elif warning_count > 0:
        final_status = STATUS_COMPLETE_WARNINGS
    else:
        final_status = STATUS_COMPLETE

    stages.append("complete")
    result = {
        "imported": imported_count,
        "skipped": skipped_count,
        "failed": failed_count,
        "warnings": warning_count,
        "queued_reviews": len(queued_reviews),
        "persons": len(person_rows),
        "firs": len(fir_rows),
        "vehicles": len(vehicle_rows),
        "graph": {
            "status": graph_status,
            "nodes": graph_result.get("nodes"),
            "relationships": graph_result.get("relationships"),
            "detail": graph_result.get("detail"),
            "warning": graph_warning,
        },
        "stage_results": build_stage_results(graph_status),
        "failed_rows": failed,
        "warning_reasons": warning_reasons,
        "skipped_rows": [
            {
                "index": item["index"],
                "status": item["status"],
                "reasons": item.get("reasons") or [],
                "redacted": item.get("redacted", False),
            }
            for item in skipped_items
        ],
        "provenance": {
            "import_id": import_id,
            "source_file": batch.get("filename"),
            "uploader_id": user.get("id"),
            "uploader_username": user.get("username"),
            "timestamp": ingested_at,
            "extraction_method": "unstructured" if kind == "unstructured" else "structured",
            "records": provenance_rows[:200],
        },
    }
    save_batch(
        import_id,
        {
            "status": final_status,
            "stages": stages,
            "result": result,
            "error": None if final_status != STATUS_FAILED else "No records could be imported.",
        },
    )
    public = _public_batch(get_batch(import_id))
    public["result"] = result
    return public


def serialize_history_item(batch: dict[str, Any]) -> dict[str, Any]:
    result = batch.get("result") or {}
    summary = batch.get("validation_summary") or {}
    return {
        "id": batch["id"],
        "filename": batch.get("filename"),
        "format": batch.get("format"),
        "kind": batch.get("kind"),
        "status": batch.get("status"),
        "created_at": batch.get("created_at"),
        "updated_at": batch.get("updated_at"),
        "uploader_username": batch.get("uploader_username"),
        "row_count": batch.get("row_count"),
        "imported": result.get("imported"),
        "skipped": result.get("skipped"),
        "failed": result.get("failed"),
        "warnings": result.get("warnings"),
        "validation": summary or None,
    }


def list_imports_for_user(user: dict[str, Any]) -> dict[str, Any]:
    batches = list_batches()
    if not is_admin(user):
        batches = [batch for batch in batches if batch.get("uploader_id") == user.get("id")]
    items = [serialize_history_item(batch) for batch in batches]
    return {"total": len(items), "data": items}


def get_import_for_user(user: dict[str, Any], import_id: str) -> dict[str, Any]:
    batch = get_batch(import_id)
    _assert_owner_or_admin(user, batch)
    public = _public_batch(batch, include_rows=True)
    if batch.get("status") in {STATUS_DRAFT, STATUS_READY, STATUS_VALIDATING}:
        public["preview_rows"] = (batch.get("validation") or {}).get("rows") or []
    return public


def assert_write_role(user: dict[str, Any]) -> None:
    if user.get("role") not in WRITE_ROLES:
        raise ImportAccessDenied(
            "Your role cannot upload investigative data. Ask an analyst or "
            "administrator if you need this import to proceed."
        )


def assert_read_role(user: dict[str, Any]) -> None:
    if user.get("role") not in READ_ROLES:
        raise ImportAccessDenied("Insufficient permissions")
