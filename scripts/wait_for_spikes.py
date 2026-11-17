"""Bounded readiness check for the dedicated Phase 0 verification services."""

import time

import httpx
from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError, ServiceUnavailable, SessionExpired


def main():
    deadline = time.monotonic() + 55
    while time.monotonic() < deadline:
        try:
            httpx.get("http://127.0.0.1:56333/readyz", timeout=2).raise_for_status()
            with GraphDatabase.driver(
                "bolt://127.0.0.1:57687",
                auth=("neo4j", "local-spike-password"),
                connection_timeout=2,
                max_transaction_retry_time=0,
            ) as driver:
                driver.verify_connectivity()
            print("Qdrant and Neo4j ready")
            return
        except (httpx.HTTPError, Neo4jError, ServiceUnavailable, SessionExpired, OSError):
            time.sleep(1)
    raise SystemExit("Phase 0 services did not become ready within 55 seconds")


if __name__ == "__main__":
    main()
