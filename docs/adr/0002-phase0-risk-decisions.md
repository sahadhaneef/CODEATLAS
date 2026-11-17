# ADR 0002: Phase 0 experiment boundaries and capability decisions

Accepted for the Phase 0 gate, 2026-10-30. This supplements ADR 0001; it does not authorize
later implementation phases. Probes under spikes/ and their tests are not API features.

## Semantic adapters and repository configuration

Tree-sitter 0.25.2 with Python grammar 0.25.0 and TypeScript/TSX grammar 0.23.2 parses
in-memory bytes. Controlled Unicode/CRLF fixtures assert original byte spans, one-based
line coordinates, and parse-error visibility. Syntax extraction does not resolve references.
Decorators, overloads, nested declarations and complete language coverage remain Phase 2
implementation tests; this narrow experiment establishes the coordinate contract only.

Pyright 1.1.405 is integrated through its documented CLI, not private JavaScript library
internals. A temporary first-party fixture and server-written config specify Python 3.12,
typeshed location, and the exact Python 3.12 interpreter. The probe detects a deliberate
assignment error without running fixture.py. Initial discovery picked PATH's Python 3.11
and failed to find builtins; explicit paths fixed the probe. JSON diagnostics do not expose
definitions/references as a supported library API. Decision: Python semantic references are
unavailable for this foundation; use syntax-only status until a bounded LSP integration is
implemented and tested in Phase 2. Do not claim diagnostics provide reference resolution.

TypeScript 5.8.3's compiler API resolves a direct function call and return type using an
in-memory compiler host. It reads no disk project config, imports no project dependencies,
emits no files and demonstrates conversion from UTF-16 positions to UTF-8 bytes after an
emoji. Dynamic dispatch, missing dependencies, multi-file aliases and real-project support
remain unverified. Phase 2 must preserve unresolved/unknown edges rather than guessing.

No probe executes imported repository configuration. Current production ingestion never
invokes either tool. A later adapter must use a server-owned bounded host/workspace and
explicit configuration; package installation and project script execution remain prohibited.

## Projection experiments and schema

Use disposable Qdrant 1.14.1 and Neo4j 5.26.5 Community with real service tests. Qdrant
tests mandatory scope predicates before vector ranking with identical vectors across scopes;
Neo4j tests bounded traversal with scope predicates on every node and relationship. These
experiments demonstrate backing-store behavior, not a completed production search adapter.
Production services must construct filters from an independently authorized immutable scope.

Canonical initial schema is Alembic revision 0001; its PostgreSQL draft is exported under
docs/api/. Full future schema remains the section 10 design, not pre-created empty tables.
OpenAPI and manifest JSON schemas are exported and checked using scripts/export_contracts.py.
No nonexistent search, workflow, patch or execution routes are added to the API skeleton.

## Models, privacy and licensing

Candidate manifests in docs/models/candidates.json pin public metadata revisions (retrieved
2026-10-30). BAAI/bge-small-en-v1.5 is the 384-dimensional embedding candidate;
BAAI/bge-reranker-base is the cross-encoder candidate. Both model cards declare MIT.
They are candidates for a measured baseline, not a selected production release or benchmark
winner. Tokenizers must come from the same revisions. Inspect LICENSE and artifact hashes
again when downloading; no weights or third-party source are bundled here.

512-token candidate budgets require splitting/rejection rather than silently truncating
evidence; the proposed 800-token chunk target in the specification cannot be assumed to fit.
Phase 3 must measure suitable model/chunk budgets before selecting a release embedding.
No embedding/generation/reranking provider is configured. Both candidates are local-only
and explicitly unapproved for private source. No private code was sent to any model.
Retained local artifacts must be encrypted/access-controlled before real source use. Any
remote model needs tenant-approved provider/retention policy, secret/exclusion scanning,
egress controls and explicit data handling review. License alone is not privacy approval.

## Runtime and execution

Python 3.12.4 is the inspected Windows interpreter; Docker/CI use 3.12.10. Runtime images
are pinned by verified registry digests in Compose/Dockerfile; these are compatibility pins,
not a current vulnerability certification. Isolated verification stacks use distinct project
names and loopback ports. Dependency locks and the API image build are tested on Linux.
Only local code and first-party fixtures are executed by the development tests.

There is no ExecutionBackend implementation and no agent/patch/test-execution route. Decision:
fail closed; evaluating a microVM or other hostile-code sandbox remains a Phase 5 prerequisite,
not a reason to enable ordinary Docker execution. Source/config text cannot authorize it.

Official references:
- https://tree-sitter.github.io/py-tree-sitter/
- https://github.com/microsoft/pyright/blob/main/docs/command-line.md
- https://github.com/microsoft/TypeScript/wiki/Using-the-Compiler-API
- https://qdrant.tech/documentation/search/filtering/
- https://neo4j.com/docs/cypher-manual/current/clauses/match/
- https://huggingface.co/BAAI/bge-small-en-v1.5
- https://huggingface.co/BAAI/bge-reranker-base
