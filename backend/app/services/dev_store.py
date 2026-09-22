"""In-memory persistence bootstrap for local development without PostgreSQL."""

from __future__ import annotations

from app.services.audit_repository import InMemoryAuditRepository, set_repository as set_audit_repository
from app.services.investigation_repository import (
    InMemoryInvestigationRepository,
    set_repository as set_investigation_repository,
)
from app.services.review_repository import InMemoryReviewRepository, set_repository as set_review_repository
from app.services.user_repository import (
    InMemoryUserRepository,
    seed_default_users,
    set_repository as set_user_repository,
)


def bootstrap_memory_stores() -> None:
    from app.services.import_store import reset_import_store

    set_user_repository(InMemoryUserRepository())
    set_investigation_repository(InMemoryInvestigationRepository())
    set_audit_repository(InMemoryAuditRepository())
    set_review_repository(InMemoryReviewRepository())
    reset_import_store()
    seed_default_users()
