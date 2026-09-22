from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core import config  # noqa: F401 - load backend/.env at startup
from app.api import network
from app.api import entities
from app.api import analytics
from app.api import neo4j_analytics
from app.api import cases
from app.api import investigations
from app.api import auth
from app.api import adjudication
from app.api import audit_logs
from app.api import imports

app = FastAPI(
    title="CNAS API",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(entities.router)
app.include_router(network.router)
app.include_router(analytics.router)
app.include_router(neo4j_analytics.router, prefix="/analytics")
app.include_router(cases.router)
app.include_router(investigations.router)
app.include_router(auth.router)
app.include_router(adjudication.router)
app.include_router(audit_logs.router)
app.include_router(imports.router)


@app.on_event("startup")
def initialize_persistence() -> None:
    from app.core.config import use_memory_store
    from app.services.audit_repository import initialize_audit_store
    from app.services.dev_store import bootstrap_memory_stores
    from app.services.import_overlay import load_overlay_from_disk
    from app.services.import_store import initialize_import_store
    from app.services.investigation_repository import initialize_investigations_store
    from app.services.review_repository import initialize_review_store
    from app.services.user_repository import initialize_users_store

    if use_memory_store():
        bootstrap_memory_stores()
        load_overlay_from_disk()
        return

    initialize_users_store()
    initialize_investigations_store()
    initialize_audit_store()
    initialize_review_store()
    initialize_import_store()
    load_overlay_from_disk()


@app.get("/")
def root():
    return {
        "message": "CNAS API is running"
    }