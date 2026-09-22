"""AN-2 cross-jurisdictional identifier recurrence findings."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from app.services.entity_resolution import (
    CanonicalRegistry,
    build_canonical_registry,
    resolve_candidate,
)
from app.services.extraction import (
    EntityCandidate,
    candidate_normalized_value,
    normalize_bank_account,
    normalize_ifsc,
    normalize_phone,
    normalize_vehicle,
)
from app.services.resolution_config import RESOLUTION_STATUS_RESOLVED
from app.services.unstructured_extraction import extract_unified_from_unstructured_record
from app.services.normalization import NormalizedRecord


AN2_METHOD = "identifier_recurrence_v1"
DEFAULT_MIN_CASES = 3
DEFAULT_MIN_JURISDICTIONS = 2
IDENTIFIER_NORMALIZERS = {
    "phone": normalize_phone,
    "vehicle": normalize_vehicle,
    "bank_account": normalize_bank_account,
    "ifsc": normalize_ifsc,
}
DATE_KEYS = ("event_date", "occurred_at", "date", "valid_from")
DATE_IN_TEXT = re.compile(
    r"\b(?:dated|on|occurred)\s+(\d{1,2}[-/]\d{1,2}[-/]\d{4}|\d{4}-\d{2}-\d{2})",
    re.IGNORECASE,
)


def _normalize_date(value: Any) -> str | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return raw


def _temporal_bounds(record: NormalizedRecord) -> tuple[str | None, str | None]:
    data = record["data"]
    metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
    valid_from = next(
        (_normalize_date(metadata.get(key)) for key in DATE_KEYS if metadata.get(key)),
        None,
    )
    if valid_from is None:
        valid_from = next(
            (_normalize_date(data.get(key)) for key in DATE_KEYS if data.get(key)),
            None,
        )
    if valid_from is None:
        match = DATE_IN_TEXT.search(str(data.get("text") or ""))
        if match:
            valid_from = _normalize_date(match.group(1))

    valid_to = next(
        (_normalize_date(metadata.get(key)) for key in ("event_end", "valid_to") if metadata.get(key)),
        None,
    )
    return valid_from, valid_to


def _observation_confidence(candidate: EntityCandidate, resolution: dict[str, Any]) -> float:
    values = [candidate.get("confidence"), resolution.get("confidence")]
    present = [float(value) for value in values if value is not None]
    return round(min(present), 4) if present else 0.0


def _evidence(
    record: NormalizedRecord,
    candidate: EntityCandidate,
    resolution: dict[str, Any],
    *,
    source_ref: str,
    jurisdiction: str,
    valid_from: str | None,
    valid_to: str | None,
) -> dict[str, Any]:
    return {
        "source": record["source"],
        "source_ref": source_ref,
        "record_id": record["record_id"],
        "content_hash": record["content_hash"],
        "ingested_at": record["ingested_at"],
        "jurisdiction": jurisdiction,
        "case_ref": source_ref,
        "identifier_type": candidate["entity_type"],
        "identifier_value": candidate_normalized_value(candidate),
        "source_text": candidate.get("source_text") or candidate.get("value"),
        "extraction_method": candidate.get("extraction_method"),
        "resolution_status": resolution.get("status"),
        "matched_entity_id": resolution.get("matched_entity_id"),
        "confidence": _observation_confidence(candidate, resolution),
        "valid_from": valid_from,
        "valid_to": valid_to,
    }


def _claim(identifier_type: str, identifier_value: str, cases: int, jurisdictions: int) -> str:
    return (
        f"The {identifier_type} identifier {identifier_value} recurs across "
        f"{cases} distinct cases in {jurisdictions} jurisdictions."
    )


def detect_identifier_recurrence(
    records: list[NormalizedRecord],
    *,
    registry: CanonicalRegistry | None = None,
    min_cases: int = DEFAULT_MIN_CASES,
    min_jurisdictions: int = DEFAULT_MIN_JURISDICTIONS,
    include_ner: bool = True,
) -> list[dict[str, Any]]:
    """Return provenance-complete AN-2 findings from unstructured FIR records."""
    if min_cases < 1 or min_jurisdictions < 1:
        raise ValueError("AN-2 thresholds must be positive")

    active_registry = registry or build_canonical_registry()
    grouped: dict[tuple[str, str], dict[str, Any]] = {}

    for record in records:
        data = record.get("data", {})
        source_ref = str(data.get("source_ref") or record["record_id"]).strip()
        jurisdiction = str(data.get("jurisdiction") or "").strip()
        if not source_ref or not jurisdiction:
            continue
        valid_from, valid_to = _temporal_bounds(record)
        candidates = extract_unified_from_unstructured_record(record, include_ner=include_ner)
        seen_observations: set[tuple[str, str, str]] = set()

        for candidate in candidates:
            entity_type = candidate.get("entity_type")
            normalizer = IDENTIFIER_NORMALIZERS.get(entity_type or "")
            if normalizer is None:
                continue
            identifier_value = normalizer(candidate_normalized_value(candidate))
            if not identifier_value:
                continue
            observation_key = (entity_type or "", identifier_value, record["content_hash"])
            if observation_key in seen_observations:
                continue
            seen_observations.add(observation_key)

            resolution = resolve_candidate(candidate, active_registry, jurisdiction=jurisdiction)
            group = grouped.setdefault(
                (entity_type or "", identifier_value),
                {"observations": {}, "matched_entity_ids": set()},
            )
            evidence = _evidence(
                record,
                candidate,
                resolution,
                source_ref=source_ref,
                jurisdiction=jurisdiction,
                valid_from=valid_from,
                valid_to=valid_to,
            )
            evidence_key = (source_ref, jurisdiction, record["content_hash"])
            group["observations"][evidence_key] = evidence
            matched_entity_id = resolution.get("matched_entity_id")
            if resolution.get("status") == RESOLUTION_STATUS_RESOLVED and matched_entity_id:
                group["matched_entity_ids"].add(str(matched_entity_id))

    findings: list[dict[str, Any]] = []
    for (identifier_type, identifier_value), group in grouped.items():
        evidence = sorted(
            group["observations"].values(),
            key=lambda item: (item["case_ref"], item["jurisdiction"], item["content_hash"]),
        )
        case_refs = sorted({item["case_ref"] for item in evidence})
        jurisdictions = sorted({item["jurisdiction"] for item in evidence})
        if len(case_refs) < min_cases or len(jurisdictions) < min_jurisdictions:
            continue

        confidence = min(item["confidence"] for item in evidence)
        limits = [
            "Identifier recurrence is not proof of common ownership or identity.",
            "Finding scope is limited to the supplied unstructured FIR records.",
        ]
        if any(item["valid_from"] is None for item in evidence):
            limits.append("One or more observations has no recoverable event date.")
        observation_dates = [
            value
            for item in evidence
            for value in (item["valid_from"], item["valid_to"])
            if value
        ]
        finding_key = f"{identifier_type}:{identifier_value}"
        findings.append(
            {
                "finding_id": f"AN-2:{finding_key}",
                "finding_type": "AN-2",
                "claim": _claim(identifier_type, identifier_value, len(case_refs), len(jurisdictions)),
                "identifier": {
                    "type": identifier_type,
                    "value": identifier_value,
                },
                "cases": case_refs,
                "jurisdictions": jurisdictions,
                "evidence": evidence,
                "method": {
                    "name": AN2_METHOD,
                    "min_distinct_cases": min_cases,
                    "min_jurisdictions": min_jurisdictions,
                    "deduplication_key": "source_ref + jurisdiction + content_hash",
                },
                "confidence": confidence,
                "limits": limits,
                "matched_entity_ids": sorted(group["matched_entity_ids"]),
                "valid_from": min(observation_dates, default=None),
                "valid_to": max(observation_dates, default=None),
            }
        )

    return sorted(findings, key=lambda finding: finding["finding_id"])
