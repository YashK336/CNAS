"""PostgreSQL connection helpers for CNAS persistence."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from app.core.config import database_url, postgres_configured

_connection_factory = None


def set_connection_factory(factory):
    """Testing hook to inject a mocked psycopg connection factory."""
    global _connection_factory
    _connection_factory = factory


def reset_connection_factory() -> None:
    global _connection_factory
    _connection_factory = None


@contextmanager
def get_connection():
    """Yield a psycopg connection using the configured database URL."""
    if not postgres_configured():
        raise RuntimeError(
            "PostgreSQL is not configured. Set DATABASE_URL or POSTGRES_* environment variables."
        )

    if _connection_factory is not None:
        conn = _connection_factory()
    else:
        import psycopg
        from psycopg.rows import dict_row

        conn = psycopg.connect(database_url(), row_factory=dict_row)

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@contextmanager
def get_cursor() -> Iterator:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            yield cursor
