from pathlib import Path
import pandas as pd

from app.services.import_overlay import overlay_dataframe
from app.services.normalization import (
    NormalizedRecord,
    find_duplicate_hashes,
    normalize_dataframe,
)

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data" / "raw"

SOURCE_FILES: dict[str, str] = {
    "persons": "persons.csv",
    "vehicles": "vehicles.csv",
    "cdr": "cdr.csv",
    "finance": "finance.csv",
    "fir": "fir.csv",
    "social": "social.csv",
    "surveillance": "surveillance.csv",
    "entity_mapping": "entity_mapping.csv",
}


def load_csv(filename: str):
    file_path = DATA_DIR / filename

    df = pd.read_csv(file_path)

    df = df.where(pd.notnull(df), None)

    return df


def _json_safe_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Replace pandas/NumPy missing values so FastAPI can JSON-encode rows."""
    return df.where(pd.notnull(df), None)


def _with_overlay(source: str, df: pd.DataFrame) -> pd.DataFrame:
    extra = overlay_dataframe(source)
    if extra is None or extra.empty:
        return _json_safe_frame(df)
    merged = pd.concat([df, extra], ignore_index=True, sort=False)
    return _json_safe_frame(merged)


def dataframe_records(df: pd.DataFrame, *, drop_internal: bool = True) -> list[dict]:
    """Serialize a loader frame without NaN or internal overlay columns."""
    safe = _json_safe_frame(df)
    records: list[dict] = []
    for row in safe.to_dict(orient="records"):
        item = {}
        for key, value in row.items():
            if drop_internal and str(key).startswith("_"):
                continue
            if isinstance(value, float) and pd.isna(value):
                item[str(key)] = None
            else:
                item[str(key)] = value
        records.append(item)
    return records


def load_source_records(source: str) -> list[NormalizedRecord]:
    """Load one dataset as normalized records with hashing metadata."""
    filename = SOURCE_FILES[source]
    df = load_csv(filename)
    df = _with_overlay(source, df)
    return normalize_dataframe(source, df)


def load_records_with_duplicates(
    source: str,
) -> tuple[list[NormalizedRecord], dict[str, list[str]]]:
    """Normalized records plus duplicate hash groups for the source."""
    records = load_source_records(source)
    duplicates = find_duplicate_hashes(records)
    return records, duplicates


def load_persons():
    return _with_overlay("persons", load_csv("persons.csv"))


def load_vehicles():
    return _with_overlay("vehicles", load_csv("vehicles.csv"))


def load_cdr():
    return load_csv("cdr.csv")


def load_finance():
    return load_csv("finance.csv")


def load_fir():
    return _with_overlay("fir", load_csv("fir.csv"))


def load_social():
    return load_csv("social.csv")


def load_surveillance():
    return load_csv("surveillance.csv")


def load_entity_mapping():
    return _with_overlay("entity_mapping", load_csv("entity_mapping.csv"))
