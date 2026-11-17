# ADR 0001: bounded read-only inventory foundation

Status: accepted for local development only, 2026-10-29.

Python 3.12 is mandatory. Development currently has 3.12.4 outside PATH; the reproducible
Docker/CI target is 3.12.10. Both are 3.12; update the patch pin together after compatibility
and security review. Node is not used in this backend-only slice. No frontend is scaffolded.
Direct dependencies are pinned in requirements.in and pyproject.toml; requirements.lock pins
the resolved transitive environment. These are compatibility baseline pins, not claims of
latest versions or completed vulnerability review. Linux installation remains unverified.

Use FastAPI, Pydantic 2, SQLAlchemy Core 2 and Alembic. PostgreSQL is canonical; SQLite is
only a deterministic test/development fallback and does not provide RLS. Migration ownership
and runtime roles differ. FORCE RLS and transaction-local tenant context defend against pool
reuse; API checks additionally restrict repository reads to the registering principal.
Two server-configured development tokens map to two tenant administrator identities. This
is deliberately not OIDC or a general role/grant implementation. Production startup fails.

For this slice PostgreSQL itself is the durable queue: API insertion is the dispatch boundary,
and an explicit one-pass worker atomically claims queued jobs. This avoids a pretend Redis/
Celery outbox. Distributed Celery delivery, outbox, leases, cancellation, crash recovery and
automatic retries remain pending Phase 1 gates. A worker crash leaves running work visible;
create a new job with a new key after investigating it. Never automatically reclaim a running
job without fencing. Only one owner per repository is supported; sharing/revocation is pending.

The production source adapter is public GitHub HTTPS object ingestion, not git clone. This is
an explicit narrow implementation of safe repository fetching. Resolve ref to full commit/tree
once, persist them, enumerate tree by tree SHA, fetch blobs by SHA and verify Git blob hashes.
No checkout, submodules, LFS, hooks, Git configuration, credentials, archive extraction, package
installation, or imported test commands are used. Reject redirects and noncanonical remotes.
Resolve api.github.com, deny non-global addresses, connect directly to the selected validated
IP and validate TLS against api.github.com. Proxy environment settings are not consumed.
Private providers and authenticated imports are not yet supported. GitHub rate limits fail
explicitly; there are no implicit retries or hidden fallback sources.

Inventory completion is not full indexing success. stage=inventory_complete/status=succeeded
means this inventory-only job completed; no index generation or active snapshot is published.
Files are metadata only; raw source is discarded after UTF-8/binary inspection, avoiding an
unencrypted source store. Parsing, secret scanning, projections, models, and source viewing
remain pending. No source can reach a model in this implementation.

Compose starts only the PostgreSQL dependency this slice consumes, plus API and manual worker/
migration profiles. Redis, Qdrant, Neo4j, object storage and semantic/UI services remain pending
until their first real use. Image version tags are concrete but digest pinning is blocked on
registry/engine verification; do not call these release-ready images.

Official contracts consulted:
- https://docs.sqlalchemy.org/en/20/core/connections.html
- https://fastapi.tiangolo.com/tutorial/dependencies/
- https://docs.github.com/en/rest/git/trees
- https://www.postgresql.org/docs/current/ddl-rowsecurity.html

Semantic adapters, Tree-sitter spans, generation filters, model candidates/licenses and sandbox
selection are unresolved Phase 0 risk spikes. No private source may be sent externally.
