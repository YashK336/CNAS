"""Overlay so imported records join the existing CSV-backed loaders.

Imported persons, FIRs, vehicles, and entity-mapping rows are concatenated onto
the preloaded datasets. People, Cases, analytics, and graph planning therefore
see imported facts through the same `load_*` functions — not a parallel store.

Rows are kept in memory for the process lifetime and flushed to JSON files under
``app/data/overlay`` so they survive backend restart. Seed CSVs are not rewritten.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

OVERLAY_SOURCES = ("persons", "fir", "vehicles", "entity_mapping")

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_OVERLAY_DIR = BASE_DIR / "data" / "overlay"

_overlay: dict[str, list[dict[str, Any]]] = {
    source: [] for source in OVERLAY_SOURCES
}
_overlay_dir: Path = DEFAULT_OVERLAY_DIR
_persist = True


def overlay_directory() -> Path:
    return _overlay_dir


def configure_overlay(*, directory: Path | None = None, persist: bool | None = None) -> None:
    """Point overlay persistence at a directory, or disable disk writes (tests)."""
    global _overlay_dir, _persist
    if directory is not None:
        _overlay_dir = Path(directory)
    if persist is not None:
        _persist = persist


def reset_overlay() -> None:
    for source in OVERLAY_SOURCES:
        _overlay[source] = []


def overlay_rows(source: str) -> list[dict[str, Any]]:
    return list(_overlay.get(source, []))


def overlay_dataframe(source: str) -> pd.DataFrame | None:
    rows = _overlay.get(source) or []
    if not rows:
        return None
    return pd.DataFrame(rows)


def _source_path(source: str) -> Path:
    return _overlay_dir / f"{source}.json"


def load_overlay_from_disk() -> None:
    """Replace in-memory overlay with JSON files if they exist."""
    reset_overlay()
    for source in OVERLAY_SOURCES:
        path = _source_path(source)
        if not path.is_file():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, list):
            continue
        _overlay[source] = [dict(row) for row in payload if isinstance(row, dict)]


def persist_overlay() -> None:
    if not _persist:
        return
    _overlay_dir.mkdir(parents=True, exist_ok=True)
    for source in OVERLAY_SOURCES:
        path = _source_path(source)
        path.write_text(
            json.dumps(_overlay[source], ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )


def append_overlay_rows(source: str, rows: list[dict[str, Any]]) -> None:
    if source not in _overlay:
        raise ValueError(f"unsupported overlay source: {source}")
    _overlay[source].extend(dict(row) for row in rows)
    persist_overlay()


def remove_overlay_by_import(import_id: str) -> dict[str, int]:
    """Best-effort row removal by import_id column. Not a graph rollback."""
    removed: dict[str, int] = {}
    for source, rows in _overlay.items():
        kept = [row for row in rows if row.get("_import_id") != import_id]
        removed[source] = len(rows) - len(kept)
        _overlay[source] = kept
    persist_overlay()
    return removed
