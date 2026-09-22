"""Parse supported investigative upload formats into a tabular envelope.

Supported:
- CSV
- JSON (array, ``{data|records: [...]}``, or a single object)
- Excel (.xlsx / .xls) via pandas + openpyxl
- Unstructured text (.txt / .md) and JSON documents with a ``text`` field

Unsupported formats are rejected with an explicit reason — no fake parsers.
"""

from __future__ import annotations

import json
from io import BytesIO
from typing import Any

import pandas as pd

SUPPORTED_STRUCTURED = ("csv", "json", "xlsx")
SUPPORTED_UNSTRUCTURED = ("txt", "md", "json")
MAX_UPLOAD_BYTES = 8 * 1024 * 1024
MAX_ROWS = 5_000
SAMPLE_VALUES = 3

STRUCTURED_ACCEPT = "CSV, JSON (array of objects), or Excel (.xlsx)"
UNSTRUCTURED_ACCEPT = "plain text (.txt, .md) or JSON with a text field"


class ImportParseError(ValueError):
    """Raised when an upload cannot be parsed as a supported source."""


def _extension(filename: str | None) -> str:
    name = (filename or "").strip().lower()
    if "." not in name:
        return ""
    return name.rsplit(".", 1)[-1]


def detect_format(filename: str | None, content_type: str | None = None) -> str | None:
    ext = _extension(filename)
    if ext in {"csv"}:
        return "csv"
    if ext in {"json"}:
        return "json"
    if ext in {"xlsx", "xls"}:
        return "xlsx"
    if ext in {"txt", "text"}:
        return "txt"
    if ext in {"md", "markdown"}:
        return "md"

    ctype = (content_type or "").split(";")[0].strip().lower()
    if ctype in {"text/csv", "application/csv"}:
        return "csv"
    if ctype in {"application/json", "text/json"}:
        return "json"
    if ctype in {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
    }:
        return "xlsx"
    if ctype in {"text/plain"}:
        return "txt"
    if ctype in {"text/markdown"}:
        return "md"
    return None


def _dataframe_from_records(records: list[dict[str, Any]]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame()
    frame = pd.DataFrame.from_records(records)
    return frame.where(pd.notnull(frame), None)


def _parse_json_bytes(payload: bytes) -> Any:
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ImportParseError(
            "JSON file is not valid UTF-8. Save the file as UTF-8 and retry."
        ) from exc
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ImportParseError(
            f"JSON could not be parsed ({exc.msg} at line {exc.lineno}). "
            "CNAS accepts an array of objects, a single object, or "
            "{data: [...]} / {records: [...]}."
        ) from exc


def _json_to_dataframe(document: Any) -> pd.DataFrame:
    if isinstance(document, list):
        if not document:
            return pd.DataFrame()
        if all(isinstance(item, dict) for item in document):
            return _dataframe_from_records(document)
        raise ImportParseError(
            "JSON arrays must contain objects (one record per object). "
            "Primitive arrays are not a supported investigative table."
        )
    if isinstance(document, dict):
        for key in ("records", "data", "rows", "items"):
            nested = document.get(key)
            if isinstance(nested, list) and all(
                isinstance(item, dict) for item in nested
            ):
                return _dataframe_from_records(nested)
        if any(isinstance(value, (list, dict)) is False for value in document.values()):
            return _dataframe_from_records([document])
        raise ImportParseError(
            "JSON object did not contain a records/data array of objects. "
            f"{STRUCTURED_ACCEPT} are accepted for structured import."
        )
    raise ImportParseError(
        "JSON root must be an object or an array of objects."
    )


def _parse_csv(payload: bytes) -> pd.DataFrame:
    buffer = BytesIO(payload)
    try:
        frame = pd.read_csv(buffer)
    except Exception as exc:  # noqa: BLE001 - surface a user-facing parse reason
        raise ImportParseError(
            "CSV could not be read. Confirm the file is comma-separated text "
            "with a header row."
        ) from exc
    return frame.where(pd.notnull(frame), None)


def _parse_excel(payload: bytes) -> pd.DataFrame:
    buffer = BytesIO(payload)
    try:
        frame = pd.read_excel(buffer, engine="openpyxl")
    except ImportError as exc:
        raise ImportParseError(
            "Excel support is not installed on this CNAS instance (openpyxl). "
            f"Use {STRUCTURED_ACCEPT.replace(' or Excel (.xlsx)', '')}."
        ) from exc
    except Exception as exc:  # noqa: BLE001
        raise ImportParseError(
            "Excel workbook could not be read. Upload .xlsx with a header row "
            "on the first sheet."
        ) from exc
    return frame.where(pd.notnull(frame), None)


def _rows_from_frame(frame: pd.DataFrame) -> list[dict[str, Any]]:
    if len(frame.index) > MAX_ROWS:
        raise ImportParseError(
            f"This file has {len(frame.index)} rows. CNAS accepts at most "
            f"{MAX_ROWS} records per import in this prototype."
        )
    rows: list[dict[str, Any]] = []
    for record in frame.to_dict(orient="records"):
        cleaned: dict[str, Any] = {}
        for key, value in record.items():
            column = str(key).strip()
            if column == "" or column.lower().startswith("unnamed"):
                continue
            if value is None:
                cleaned[column] = None
                continue
            if isinstance(value, float) and pd.isna(value):
                cleaned[column] = None
                continue
            if hasattr(value, "isoformat"):
                cleaned[column] = value.isoformat()
                continue
            text = str(value).strip()
            if text == "" or text.lower() in {"nan", "none", "null"}:
                cleaned[column] = None
            else:
                cleaned[column] = text
        rows.append(cleaned)
    return rows


def _sample_values(rows: list[dict[str, Any]], column: str) -> list[str]:
    values: list[str] = []
    for row in rows:
        value = row.get(column)
        if value is None:
            continue
        text = str(value).strip()
        if not text:
            continue
        values.append(text)
        if len(values) >= SAMPLE_VALUES:
            break
    return values


def parse_structured_upload(
    *,
    filename: str,
    payload: bytes,
    content_type: str | None = None,
) -> dict[str, Any]:
    if len(payload) > MAX_UPLOAD_BYTES:
        raise ImportParseError(
            f"File is larger than {MAX_UPLOAD_BYTES // (1024 * 1024)} MB. "
            "Split the dataset or upload a smaller extract."
        )
    fmt = detect_format(filename, content_type)
    if fmt == "csv":
        frame = _parse_csv(payload)
    elif fmt == "json":
        frame = _json_to_dataframe(_parse_json_bytes(payload))
    elif fmt == "xlsx":
        frame = _parse_excel(payload)
    else:
        detected = fmt or (_extension(filename) or "unknown")
        raise ImportParseError(
            f"'{detected}' is not a supported structured format. "
            f"Accepted: {STRUCTURED_ACCEPT}."
        )

    rows = _rows_from_frame(frame)
    columns = list(rows[0].keys()) if rows else [str(c) for c in frame.columns]
    return {
        "format": "xlsx" if fmt == "xlsx" else fmt,
        "kind": "structured",
        "columns": columns,
        "row_count": len(rows),
        "rows": rows,
        "samples": {column: _sample_values(rows, column) for column in columns},
    }


def parse_unstructured_upload(
    *,
    filename: str,
    payload: bytes,
    content_type: str | None = None,
) -> dict[str, Any]:
    if len(payload) > MAX_UPLOAD_BYTES:
        raise ImportParseError(
            f"File is larger than {MAX_UPLOAD_BYTES // (1024 * 1024)} MB."
        )
    fmt = detect_format(filename, content_type)
    if fmt == "json":
        document = _parse_json_bytes(payload)
        return _unstructured_from_json(document, filename)
    if fmt in {"txt", "md"}:
        try:
            text = payload.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ImportParseError("Text file is not valid UTF-8.") from exc
        if not text.strip():
            raise ImportParseError("Unstructured file is empty.")
        row = {
            "text": text,
            "source_ref": _stem(filename),
        }
        return {
            "format": fmt,
            "kind": "unstructured",
            "columns": list(row.keys()),
            "row_count": 1,
            "rows": [row],
            "samples": {"text": [text.strip()[:180]]},
        }

    detected = fmt or (_extension(filename) or "unknown")
    raise ImportParseError(
        f"'{detected}' is not a supported unstructured format. "
        f"Accepted: {UNSTRUCTURED_ACCEPT}. "
        "PDF, images, and audio are not parsed in this prototype."
    )


def _unstructured_from_json(document: Any, filename: str) -> dict[str, Any]:
    records: list[dict[str, Any]]
    if isinstance(document, dict) and isinstance(document.get("text"), str):
        records = [document]
    elif isinstance(document, list) and all(isinstance(item, dict) for item in document):
        records = document
    elif isinstance(document, dict):
        for key in ("records", "data", "items"):
            nested = document.get(key)
            if isinstance(nested, list):
                records = [item for item in nested if isinstance(item, dict)]
                break
        else:
            raise ImportParseError(
                "Unstructured JSON must include a text field, or a records "
                "array of objects that each include text."
            )
    else:
        raise ImportParseError(
            "Unstructured JSON must be an object with text, or an array of "
            "such objects."
        )

    rows: list[dict[str, Any]] = []
    for index, item in enumerate(records):
        text = item.get("text")
        if not isinstance(text, str) or not text.strip():
            continue
        row = {
            "text": text,
            "source_ref": item.get("source_ref") or item.get("source") or f"{_stem(filename)}:{index + 1}",
            "jurisdiction": item.get("jurisdiction"),
            "source": item.get("source") or "unstructured_fir",
        }
        metadata = item.get("metadata")
        if isinstance(metadata, dict):
            row["metadata"] = metadata
        rows.append(row)

    if not rows:
        raise ImportParseError(
            "Unstructured JSON did not contain any non-empty text fields."
        )
    if len(rows) > MAX_ROWS:
        raise ImportParseError(
            f"This file has {len(rows)} documents. CNAS accepts at most "
            f"{MAX_ROWS} per import in this prototype."
        )
    return {
        "format": "json",
        "kind": "unstructured",
        "columns": list(rows[0].keys()),
        "row_count": len(rows),
        "rows": rows,
        "samples": {"text": [str(rows[0]["text"]).strip()[:180]]},
    }


def _stem(filename: str) -> str:
    name = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    if "." in name:
        return name.rsplit(".", 1)[0]
    return name or "upload"
