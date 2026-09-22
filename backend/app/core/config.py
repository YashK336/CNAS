import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_DIR / ".env"

NEO4J_URI = ""
NEO4J_USERNAME = ""
NEO4J_PASSWORD = ""
NEO4J_DATABASE = "neo4j"

DATABASE_URL = ""
POSTGRES_HOST = "localhost"
POSTGRES_PORT = "5432"
POSTGRES_DB = "cnas"
POSTGRES_USER = "cnas"
POSTGRES_PASSWORD = ""


JWT_SECRET = ""
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 480

CNAS_USE_MEMORY_STORE = ""

GDS_SESSION_NAME = "cnas-analytics"
GDS_SESSION_MEMORY = "2GB"
GDS_SESSION_TTL_MINUTES = 30


def _apply_env_settings() -> None:
    """Refresh module settings from the current process environment."""
    global NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, NEO4J_DATABASE
    global DATABASE_URL, POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB
    global POSTGRES_USER, POSTGRES_PASSWORD
    global JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_MINUTES
    global CNAS_USE_MEMORY_STORE
    global GDS_SESSION_NAME, GDS_SESSION_MEMORY, GDS_SESSION_TTL_MINUTES

    NEO4J_URI = os.getenv("NEO4J_URI", "")
    NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")
    NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

    DATABASE_URL = os.getenv("DATABASE_URL", "")
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB = os.getenv("POSTGRES_DB", "cnas")
    POSTGRES_USER = os.getenv("POSTGRES_USER", "cnas")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")

    JWT_SECRET = os.getenv("JWT_SECRET", "")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))
    CNAS_USE_MEMORY_STORE = os.getenv("CNAS_USE_MEMORY_STORE", "")

    GDS_SESSION_NAME = os.getenv("GDS_SESSION_NAME", "cnas-analytics")
    GDS_SESSION_MEMORY = os.getenv("GDS_SESSION_MEMORY", "2GB")
    GDS_SESSION_TTL_MINUTES = int(os.getenv("GDS_SESSION_TTL_MINUTES", "30"))


def load_env() -> None:
    """Load backend/.env and refresh settings without overriding existing env vars."""
    load_dotenv(ENV_FILE, override=False)
    _apply_env_settings()


load_env()


def neo4j_configured() -> bool:
    load_env()
    return bool(NEO4J_URI and NEO4J_USERNAME and NEO4J_PASSWORD)


def database_url() -> str:
    """Resolve the PostgreSQL connection URL from environment variables."""
    load_env()
    if DATABASE_URL:
        return DATABASE_URL
    if POSTGRES_USER and POSTGRES_PASSWORD and POSTGRES_DB:
        return (
            f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
            f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
        )
    return ""


def postgres_configured() -> bool:
    load_env()
    return bool(database_url())


def jwt_configured() -> bool:
    load_env()
    return bool(JWT_SECRET)


def jwt_settings() -> dict[str, str | int]:
    load_env()
    if not JWT_SECRET:
        raise RuntimeError("JWT_SECRET is not configured")
    return {
        "secret": JWT_SECRET,
        "algorithm": JWT_ALGORITHM,
        "expire_minutes": JWT_EXPIRE_MINUTES,
    }


def use_memory_store() -> bool:
    load_env()
    return CNAS_USE_MEMORY_STORE.strip().lower() in {"1", "true", "yes", "on"}


def gds_session_settings() -> dict[str, str | int]:
    load_env()
    return {
        "name": GDS_SESSION_NAME,
        "memory": GDS_SESSION_MEMORY,
        "ttl_minutes": GDS_SESSION_TTL_MINUTES,
    }
