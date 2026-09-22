"""

Reusable Neo4j driver for AuraDB connectivity.



The driver is created lazily and reused for the process lifetime. Graph import

and analytics are intentionally out of scope for this module.

"""



from __future__ import annotations



from typing import Any



from neo4j import Driver, GraphDatabase



from app.core import config



_driver: Driver | None = None





def get_neo4j_driver() -> Driver | None:

    """Return the shared Neo4j driver, or None when settings are incomplete."""

    global _driver



    config.load_env()

    if not config.neo4j_configured():

        return None



    if _driver is None:

        _driver = GraphDatabase.driver(

            config.NEO4J_URI,

            auth=(config.NEO4J_USERNAME, config.NEO4J_PASSWORD),

        )



    return _driver





def verify_neo4j_connectivity() -> dict[str, Any]:

    """

    Verify Aura connectivity using the official driver health check.



    Returns a simple status payload suitable for API responses.

    """

    driver = get_neo4j_driver()



    if driver is None:

        return {

            "status": "unavailable",

            "detail": "Neo4j environment variables are not configured",

        }



    try:

        driver.verify_connectivity()

        return {

            "status": "connected",

            "database": config.NEO4J_DATABASE,

        }

    except Exception as exc:  # noqa: BLE001 - surface driver failures to health API

        return {

            "status": "unavailable",

            "detail": str(exc),

        }





def close_neo4j_driver() -> None:

    """Close and reset the shared driver."""

    global _driver



    if _driver is not None:

        _driver.close()

        _driver = None


