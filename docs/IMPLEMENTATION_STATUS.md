# Implementation status — updated 2026-10-30

This is a local development foundation, not a production release. Phase 0's gate is now
verified with the evidence below. Earlier entries are retained as historical results;
the 2026-10-30 acceptance record supersedes their unavailable-Docker/spike blockers.

## Phases

- Phase 0: **verified** for section 16's contracts/risk-spike gate. See the criterion-by-criterion
  acceptance record below; this does not imply production indexing or deployment readiness.
- Phase 1: full-phase gate **in_progress, not verified**. The previously implemented authorized registration →
  pinned inventory → tracked job slice is preserved with its evidence; it is not a completed
  Phase 1. OIDC, general memberships/roles/grants, source viewer, outbox/Celery, cancellation,
  leases/fencing, crash resume, audit and complete immutable snapshot schema remain **pending**.
  No new Phase 1 feature work was started during Phase 0 completion.
- Phase 2: **pending**.
- Phase 3: **pending**.
- Phase 4: **pending**.
- Phase 5: **pending**; agents, patch generation and imported test execution disabled.
- Phase 6: **pending**.

## Implemented behavior and evidence

Historical foundation record from 2026-10-29 (see the latest acceptance record below).

- Sections 2/3/18: backend package, Alembic, pinned direct/transitive Python dependencies,
  Python 3.12 in project metadata, AGENTS.md, specification, Docker and CI. Actual runtime
  used for checks: 3.12.4; Docker/CI patch target: 3.12.10. No web or semantic service yet.
- Sections 4/10: two development tokens map server-side to distinct tenant/admin principals;
  per-owner repository access; tenant conditions and composite foreign keys; PostgreSQL
  FORCE RLS with transaction-local context. Production mode startup is rejected. API-level
  isolation is **verified** by tests. Real PostgreSQL RLS enforcement is **blocked/unverified**.
- Sections 5/11: private repository registration, durable queued jobs, scoped Idempotency-Key,
  conflicting reuse rejection, atomic worker claim, full SHA pin retained before inventory,
  sanitized failure state, bounded cursor reads and health/readiness. Controlled-source API
  workflow is **verified**; readiness distinguishes missing migrations from liveness.
- Sections 4/5: canonical public GitHub HTTPS adapter; fixed API destination; DNS/IP-pinned TLS;
  no redirects, credentials, Git hooks/config, local paths, submodule/LFS expansion or checkout.
  Tree truncation/limits fail explicitly, blob bytes verified against Git SHA, unsafe paths
  rejected, sensitive paths/symlinks/oversized/unsupported files skipped with reasons. UTF-8
  and binary inspection implemented. No source retention, parsing, embeddings or publication.
  URL/path/redirect/private-DNS failures and classifications are **verified** with fixtures;
  live GitHub download, transport timeout and remote tree provenance are **unverified**.
- Sections 15/18: local PostgreSQL/API/explicit manual worker and migration service definitions;
  non-root API/worker, read-only filesystem, loopback ingress, separate database runtime role.
  Compose syntax is **verified**; images/build/startup are **blocked/unverified**.

## Actual checks

Historical 2026-10-29 checks, retained without presenting them as current runs.

Run from D:\projects\CODEATLAS using .venv312\Scripts\python (Python 3.12.4):

- `-m pytest -q`: **25 passed, 1 skipped**, 0.51 seconds. One dependency deprecation warning
  from Starlette's AnyIO BlockingPortal alias. PostgreSQL RLS test skipped because
  CODEATLAS_TEST_POSTGRES is unset and Docker engine unavailable. Initial sandbox attempt:
  21 passed, 4 setup errors from denied temporary-directory access, 1 skipped; rerun outside
  the sandbox succeeded. These are CodeAtlas implementation tests, never imported repo tests.
- `-m ruff check .`: **passed**.
- `-m ruff format --check .`: **passed** (13 Python files in the final check).
- `-m pip check`: **passed**, no broken requirements.
- `-m pip install --no-deps --no-build-isolation -e .`: **passed**; editable package built
  and installed using Python 3.12 after retrying denied sandbox temporary-directory access.
- Migration upgrade → downgrade → upgrade: **verified on disposable SQLite** through tests;
  missing schema readiness returns 503. PostgreSQL migration execution remains **blocked**.
- `docker compose -f infra/compose/compose.yaml config --no-env-resolution --quiet`: **passed**.
- `docker info --format '{{.ServerVersion}}'`: **failed**, missing dockerDesktopLinuxEngine pipe.
  No Docker image build, real service startup, PostgreSQL integration, UI/type checks or remote
  CI run is claimed. There is no UI or TypeScript code to check in this slice.
- `git status --short`: workspace is not a Git repository. Existing specification preserved
  except the requested explicit Python 3.12 requirement; no repository was initialized.

## Computer prerequisites

Git 2.54.0; Python 3.11.9 on PATH; Python 3.12.4 found directly under the user's Python312
installation; Node 24.15.0; npm 11.12.1; Docker CLI 29.8.1; Compose 5.5.1.
`py --version` fails to discover Python. Use the explicit 3.12 path in README.
No prerequisite installation is needed for this slice. Docker Desktop Linux engine must start.
Pinned dependencies installed successfully after sandbox network/temporary-directory failures
were retried with permission. The earlier .venv contains 3.11 tooling only and is unused;
.venv312 is the supported environment. Both are ignored.

## Next gates and limitations

Follow README's exact boot/check sequence and its Phase 0 reproduction commands. Linux
installation/build, empty PostgreSQL migration, RLS/pool reuse, real projections and image
digests were verified on 2026-10-30. Live GitHub ingestion and dependency vulnerability/security
review are still unverified; complete these before applicable deployment/release claims.

Phase 0 risk experiments are complete with bounded capabilities recorded in ADR 0002.
Before full Phase 1 acceptance add scoped general grants, immutable snapshots, cancellation and crash-safe
fenced retries with outbox integration. Running jobs intentionally remain visible after worker
death; no unsafe automatic retry is implemented. Job success means inventory complete only,
never a published index. Source bytes are discarded; secret scanning and encrypted source
storage must precede model/retrieval use. No model or execution calls are possible today.

## Workspace guidance update — 2026-10-30

- Expanded root `AGENTS.md` from specification sections 2–5, 9–11, 13–16, and 18–19,
  preserving all six existing instructions verbatim. Added Python 3.12 consistency,
  phased scope, architecture/contracts, testing, security, and progress-tracking rules.
- Documentation-only change: verified original-instruction preservation and required guidance
  by reading/checking the updated file. Application tests were not rerun; earlier test evidence
  above remains historical. No implementation or phase state changed.

## Phase 0 acceptance record — 2026-10-30

The earliest incomplete gate was Phase 0 (specification section 16). Its gate is now
**verified**. Work was confined to experiments, contracts, reproducibility and validation of
the existing foundation. Later-phase implementation remains pending; prior Phase 1 code and
all six original workspace instructions were preserved.

### Deliverables and acceptance evidence

- **Verified — contracts, schema, layout, ADRs and threat model (§§2–4/10–11/16/18):**
  existing layout/threat model/ADR 0001 retained; ADR 0002 records experiment decisions.
  Generated docs/api/openapi.json describes only implemented routes; schema-0001.sql is
  the PostgreSQL migration draft. Dataset and model manifest schemas are generated from
  validated Pydantic contracts, with a repeatable export/drift command. Full future schema
  remains a design in section 10, not unused production tables.
- **Verified — pinned compatible stack (§§2/16):** requirements.lock installed and package
  built under Windows Python 3.12.4 and Linux Python 3.12.10. Parser/Neo4j experiment tools
  are pinned separately in requirements-spikes.lock; Pyright 1.1.405 and TypeScript 5.8.3
  are pinned in spikes/semantic/package-lock.json with integrity hashes and lifecycle scripts
  disabled. Python/PostgreSQL/Qdrant/Neo4j image digests are embedded in Docker/Compose.
  This compatibility verification does not certify current vulnerability status.
- **Verified — documented dependency startup (§16):** new isolated Compose projects
  codeatlas-phase0-verify and codeatlas-phase0-boot started from fresh databases. PostgreSQL
  17.4, Qdrant 1.14.1 and Neo4j 5.26.5 ran successfully. The API image built from the locked
  Linux dependency set and runs as UID/GID 10001 with read-only filesystem and no capabilities.
  Both health and readiness returned 200 on http://127.0.0.1:58000; Docker reports healthy.
  Existing port 8000 was occupied and untouched; CODEATLAS_API_PORT now permits a loopback
  override. The dedicated boot database's owner/runtime roles were created by init.sql.
- **Verified — migrations on empty PostgreSQL (§16):** documented migrate service exited 0
  on a fresh boot-project volume; SELECT version_num returned 0001. The real integration
  test additionally applies the migration to the separate verification database and confirms
  RLS read isolation, cross-tenant write rejection, and transaction-local pool context reset.
  Destructive downgrade/upgrade remains limited to disposable SQLite fixtures; no user data
  or existing containers were reset or removed.
- **Verified — parser/semantic fixture evidence (§16):** Tree-sitter Python/TypeScript/TSX
  probes retain UTF-8 byte spans and CRLF lines after Unicode and report malformed syntax.
  Pyright detects the deliberate assignment mismatch in a controlled temporary fixture;
  its CLI offers diagnostics, not a supported definition/reference API. Python resolution
  stays syntax-only/unavailable until a later bounded LSP adapter. TypeScript's in-memory
  compiler host resolves a direct call/signature and demonstrates UTF-16→UTF-8 conversion.
  These are narrow capability experiments, not integrated Phase 2 parsers/resolvers.
- **Verified — real generation/scope projections (§16):** Qdrant's identical vectors across
  four independent scope dimensions return only the authorized point when filtering before
  ranking. Neo4j's bounded traversal rejects nodes and edges with each mismatched tenant,
  repository, snapshot or generation. Test collections/nodes use unique namespaces and are
  removed in finally blocks. These tests do not claim a production authorization adapter.
- **Verified — repository configuration is data; execution disabled (§§4/9/16):** TypeScript
  uses an in-memory host with no emit/config/dependency discovery. Pyright uses a server-written
  config, bundled typeshed and exact Python 3.12 interpreter against first-party fixture data;
  fixture code is never run. Neither tool is connected to production ingestion. Health reports
  agents=false, patches=false, execution=false; no corresponding routes or backend exist.
- **Verified — model candidates and privacy/license decision (§16):** docs/models/candidates.json
  pins BAAI/bge-small-en-v1.5 at 5c38ec7c405ec4b44b94cc5a9bb96e735b38267a and
  BAAI/bge-reranker-base at 2cfc18c9415c912f9d8155881c133215df768a70 using public metadata.
  Model cards declare MIT; ADR 0002 records budgets, tokenizer/revision rules, privacy/retention
  constraints, and the mismatch between 512-token budgets and the proposed chunk target.
  Candidates are local-only, unapproved for private source, unbenchmarked and not downloaded.
  No private source, embedding/model call, weights, or benchmark score is involved.

### Actual commands and outcomes

From D:\projects\CODEATLAS; Windows checks used .venv312\Scripts\python (3.12.4),
Node 24.15.0/npm 11.12.1. Docker Linux Engine 29.8.1 is now reachable outside the sandbox
(the sandbox initially returned permission denied; the authorized retry succeeded).

- `docker compose -p codeatlas-phase0-verify -f infra/compose/verify.yaml up -d`: **passed**,
  pulled/started the three isolated backing services. Inspected registry digests were pinned.
- `python -m pip install -r requirements-spikes.in` (explicit 3.12 executable): **passed**;
  `npm.cmd install --ignore-scripts --no-audit --no-fund` in spikes/semantic: **passed**.
  Subsequent setup uses the resulting Python/npm lockfiles documented in README.
- Full configured `python -m pytest -q --tb=short`: **36 passed, zero skipped**, 4.57 seconds.
  Environment: CODEATLAS_TEST_POSTGRES=postgresql+psycopg://codeatlas:local-development-only@127.0.0.1:55432/codeatlas?connect_timeout=5,
  CODEATLAS_TEST_QDRANT=http://127.0.0.1:56333 and CODEATLAS_TEST_NEO4J=bolt://127.0.0.1:57687.
  One pre-existing Starlette/AnyIO BlockingPortal deprecation warning remains.
- Initial full attempt was **interrupted without a passing result** after Pyright diagnostics
  failed and an unbounded localhost database connection stalled. Explicit Python/typeshed
  discovery and IPv4 test URLs with connection timeouts corrected the checks; the complete
  passing run above includes those cases. No assertion was weakened to hide the failure.
- `docker compose -p codeatlas-phase0-boot -f infra/compose/compose.yaml build api`:
  **passed**; `run --rm migrate`: **passed**; `up -d api` with CODEATLAS_API_PORT=58000:
  **passed**. Initial default-port boot failed because 8000 was occupied; no existing process
  was stopped. `exec -T api python --version`: 3.12.10; `exec -T api id`: UID/GID 10001.
- `docker run --rm --network codeatlas-phase0-verify_default --mount type=bind,source=D:\projects\CODEATLAS,target=/workspace,readonly --tmpfs /tmp:rw,nosuid,nodev --workdir /workspace -e CODEATLAS_TEST_POSTGRES=postgresql+psycopg://codeatlas:local-development-only@postgres:5432/codeatlas codeatlas-phase0-boot-api:latest python -m pytest -q -p no:cacheprovider tests/test_foundation.py tests/test_contracts.py tests/test_postgres.py`:
  **28 passed**, 1.02 seconds, same dependency deprecation warning. This verifies the foundation
  and RLS subset on Linux Python 3.12.10; semantic/projection probes ran on Windows, not this image.
- Running Linux API smoke: tenant A registration **201**, tenant B listing excluded it;
  readiness **200**. No remote fetch was requested. The private owner record is in the
  isolated boot database only; no real repository content was ingested.
- `python -m ruff check .`: **passed**; `python -m ruff format --check .`: **passed**,
  21 Python files; `python -m pip check`: **passed**.
- `python scripts/export_contracts.py --check`: **passed**; `node --check spikes/semantic/probe.cjs`:
  **passed**; `python scripts/wait_for_spikes.py`: **passed**.
- Both `docker compose -f infra/compose/compose.yaml config --quiet` and the verify.yaml
  variant: **passed**. The CI workflow now runs the probe dependencies/services, contract drift,
  and full suite, but remote GitHub CI has **not run**. This workspace is still not a Git repo.

### Remaining risks and next gate

No Phase 0 acceptance blocker remains for this controlled local foundation. No release or
full Phase 1 acceptance is claimed. Dependency vulnerability review, broad semantic coverage,
live authorized provider fetch, crash recovery/outbox/fencing/cancellation, complete identity/
grant/snapshot schema, private provider credentials, encrypted source storage and secret scans
remain explicit subsequent gates. Production model selection requires measured retrieval
baselines; hardened execution backend selection remains deferred with execution disabled.

The verification API and database remain running at loopback 58000/5432 under
codeatlas-phase0-boot. Qdrant/Neo4j/PostgreSQL experiments remain running at 56333/57687/55432
under codeatlas-phase0-verify. README includes exact reproducible checks and project-scoped
shutdown commands; named volumes are retained. The new ignored .env contains generated local
development tokens; no secret values were printed or added to tracked documentation.

## Phase 1 implementation evidence — 2026-10-30

Phase 1 is **in_progress, not verified**. Phase 0 evidence is preserved; Phases 2–6 remain
pending. The user explicitly authorized Phase 1 after the earlier foundation-only scope.

Implemented additions (specification §§4–5/10–11/16):

- Additive migrations 0002/0003 add snapshot records, repository grants, job lease epochs,
  lease expiry and tenant-scoped outbox records, with composite tenant foreign keys and RLS.
  Migration 0001 and its exported schema draft remain unchanged. Readiness requires 0003.
- API job and unique outbox creation are atomic; worker delivery claims the database event.
  Expired workers are fenced before requeueing, up to three attempts. Recovery reuses the
  recorded full commit/tree; cancellation increments the fence and prevents stale completion
  or failure writes. Blocking fetches cancel cooperatively at the next boundary.
- Completed inventory creates a unique tenant/repository/SHA snapshot record and checks
  existing tree consistency. Snapshots are application-insert-only; database enforcement
  against arbitrary runtime-role updates remains unfinished. No searchable generation exists.
- Server-configured additional development identities support owner/admin/developer/viewer
  organization roles. Private access needs ownership or explicit read/index grants; role alone
  grants no repository access. Same-tenant grant administration/revocation endpoints exist.
  Viewers cannot enqueue; workers recheck repository index access at persistence boundaries.
  These are development mappings, not OIDC or persisted organization memberships.
- Existing strict public-GitHub HTTPS adapter and inventory exclusion/status behavior retained.
  API adds durable cancellation and bounded snapshot listing; no source retention/viewer yet.

Actual verification on Python 3.12.4:

- Full configured `python -m pytest -q --tb=short`: **41 passed**, zero skipped, 4.20 seconds,
  with the existing Starlette/AnyIO deprecation warning. Real PostgreSQL used port 55432 with
  connect_timeout=5; Qdrant 56333 and Neo4j 57687. The real PostgreSQL test applied migrations
  through 0003; Phase 0 parser/semantic/projection regressions passed in this run.
- New controlled tests cover death after pin persistence, branch movement on recovery,
  duplicate delivery, snapshot reuse, stale worker replacement, in-flight cancellation,
  two-tenant cancellation denial, development role restrictions, explicit grants and revocation.
  A malicious source fixture raises if executed; ingestion completes with subprocess.run/Popen
  prohibited by the test. Only CodeAtlas test code executes, never imported repository code.
- Ruff lint/format checks passed (27 Python files). OpenAPI export regenerated and its drift
  check passed. `python -m pip check` passed. No dependency/runtime downgrade was made.
- An earlier default suite run reported 36 passed/3 skipped without integration URLs; the
  configured 41-pass run above supersedes those skips. New Linux image build/boot, remote CI,
  and **live-provider ingestion were not run** for these additions. The prior running Docker
  API still serves its Phase 0 image until rebuilt; do not confuse it with host-source tests.

Acceptance audit and remaining limitations:

- Controlled two-tenant isolation, prohibited URL/path rejection, same-key duplicate handling,
  pin preservation, unsupported/excluded inventory reasons, development production refusal,
  cooperative cancellation, and simulated crash fencing: tested. This is controlled-fixture
  verification, not a live provider end-to-end certification or a real process-kill fault drill.
- **Unfinished:** OIDC verification/configuration and persisted users/organizations/memberships;
  complete grant-policy lifecycle; source viewer plus encrypted source retention; Celery/Redis
  dispatcher and broker-fault outbox tests; convergence across distinct idempotency keys for
  identical SHA/configuration; retry classification/backoff and true process-death testing;
  database-enforced immutable snapshot ancestry/file associations and production quotas/audit.
  Live authorized provider access has not been verified. Consequently Phase 1 MUST NOT be
  marked verified. These are outstanding implementation requirements, not waived gates.

Next action: continue these Phase 1 requirements, then rerun the complete acceptance suite
including real services and a separately recorded authorized live-provider check. README and
ADR 0003 document current development setup and migration/rebuild commands. Product agents,
patch generation and imported-code execution remain disabled; production identity startup
continues to fail closed. No later-phase implementation was started.

## Phase 1 continuation — 2026-10-30 (latest)

Phase 1 remains **in_progress, not verified**. This entry supersedes the earlier missing-
implementation list where explicitly addressed below. Verified Phase 0 evidence is preserved;
Phases 2–6 remain pending, with product agents, patching and imported-code execution disabled.

### Changes in requested order

1. **Persisted identity/grants and OIDC:** migration 0004 adds tenant-scoped persistent
   memberships with issuer/subject/principal binding, role, and active/revoked status. API role
   checks and worker repository-access checks now use persisted membership. Development
   bootstrap never overwrites persisted roles/revocation. Existing repository grants persist
   separately. OIDC bearer mode uses pinned RSA keys with RS256 only, required issuer/audience/
   exp/iat/sub, maximum one-hour lifetime, and independently provisioned tenant membership;
   token tenant IDs only select a binding. No automatic signup or token-supplied verifier URL.
   Development mode refuses production; OIDC mode forbids configured development tokens.
   Controlled signed-token/revocation/cross-tenant/expired/incorrect issuer-audience tests pass.
   Operator provisioning CLI added. **Real issuer deployment is unverified:** no issuer,
   audience, production key set or tokens were provided. No fabricated credentials were used.
2. **Encrypted immutable source/viewer:** migration 0005 adds encrypted source envelopes,
   hashes and snapshot IDs; triggers reject UPDATE/DELETE of source and snapshot records.
   Migration 0007 enforces tenant/repository/job/snapshot ancestry in PostgreSQL (equivalent
   SQLite fixture trigger). Allowed UTF-8 source is authenticated/encrypted using Fernet with
   a key outside PostgreSQL; envelope binds tenant/repository/commit/path. Key is in ignored
   .env, never logs or committed files. Inventory excludes ciphertext; bounded source endpoint
   rechecks membership/grants and limits reads to 500 lines/64 KiB. Excluded/oversized/binary
   files retain reasons, no bytes. PostgreSQL snapshot mutation rejection was tested. Old
   inventory-only records explicitly report source_not_retained. Extensionless README/LICENSE
   documentation now inventories as text. ADR 0004 documents the bounded PostgreSQL source
   store choice, key/retention limits and future encrypted-object-store migration.
3. **Broker-backed outbox:** migration 0006 adds dispatch scheduling; Celery/Redis transports
   JSON identifiers only. Publishing precedes marking dispatched, so failures retain pending
   events and publication/commit interruptions may safely redeliver. Reconciler republishes
   still-queued events after 30 seconds, fences expired leases, and caps attempts at three.
   Transient transport errors use bounded exponential delay; policy/integrity errors fail
   terminally. Late acknowledgement, reject-on-worker-loss, prefetch one, socket timeouts and
   90-second Redis visibility are configured. Docker definitions include pinned Redis, worker
   and per-tenant dispatcher. Existing direct worker remains a diagnostic path only.
4. **Fault tests:** real Redis/Celery tests cover duplicate publication, broker publication
   failure, worker restart, three-attempt limit and an actual controlled worker kill after its
   pin is persisted. Lease expiry is advanced explicitly in the DB rather than waiting 60
   seconds: this is a controlled clock, not an actual 60-second outage. Recovery preserves the
   pin and rejects stale writes. Additional tests revoke a developer's grant during a blob
   read; final persistence is denied and new reads return 404. Existing cancellation races,
   stale-worker, no-subprocess/malicious-source, URL/path and tenant fixtures remain passing.
5. **Approved live provider:** the user explicitly approved only octocat/Hello-World. The
   strict production GitHubSource adapter resolved and fetched full commit
   7fd1a60b01f91b314f59955a4e4d4e80d8edf11d, tree b4eecafa9be2f2006ce1b709d6857b07069b4608.
   One README was inventoried and encrypted; authorized source read returned HTTP 200. Job
   050177ec-a6a8-4ad7-97ff-dba67a07c1f8 succeeded without error. Evidence is retained in
   docs/evidence/live-20261030.json (2026-10-30 09:11:46 UTC). This used the real adapter and
   runtime database role in the isolated verification DB, directly through the production
   ingestion service. It did **not** exercise the live provider through a deployed Celery
   worker. No imported code, hook, dependency script, test or upstream write was executed.

### Actual check results

Python used: Windows 3.12.4, with pinned runtime requirement 3.12 and Docker/CI target 3.12.10.
New pinned runtime dependencies: PyJWT 2.10.1, cryptography 44.0.3, Celery 5.5.2, Redis client
5.2.1; transitive versions recorded in requirements.lock. No claim of a vulnerability audit.

- Identity/role/recovery coherent-slice suite: **7 passed**, 1.39 seconds.
- Source/OIDC coherent-slice suite: **3 passed**, 0.66 seconds.
- Broker fault suite with real Redis: **3 passed**, 5.68 seconds, including controlled process
  death after persisted pin, restart and lease-fenced completion.
- Full configured `python -m pytest -q --tb=short`: **49 passed, zero skipped**, 13.18 seconds.
  PostgreSQL URL used 127.0.0.1:55432 with connect_timeout=5; Qdrant 56333, Neo4j 57687 and
  CODEATLAS_TEST_BROKER=redis://127.0.0.1:56379/0. This run applied schema through 0007 and
  includes all prior Phase 0 parser/semantic/projection regressions. One existing dependency
  warning remains: Starlette's deprecated AnyIO BlockingPortal alias.
- Approved live command: `python scripts/verify_live.py --approved-octocat-hello-world`,
  explicit Python 3.12 executable, isolated runtime-role DB URL and externally supplied source
  key: **passed**. Only metadata evidence was printed. This remains separate from fixture tests.
- Updated Linux build command:
  `docker compose -p codeatlas-phase1 -f infra/compose/compose.yaml build api worker dispatcher migrate`:
  **failed during image export**. Locked dependency installation and wheel build reached
  completion, but Docker containerd reported input/output errors and read-only metadata
  filesystem. No completed Linux image, updated stack boot, or Linux suite is claimed.
- Subsequent independent rerun on C: temp storage: **6 passed, 1 skipped, 3 setup errors**,
  SQLite reported database/disk full. Inspection showed C: free space about 7.4 MiB; D: had
  about 213 GiB free. First attempt to relocate pytest temp missed its parent directory and
  produced 9 setup errors/1 skip; creating the project-local parent corrected that invocation.
- Latest independent run:
  `python -m pytest -q --basetemp=.verification/pytest-phase1-final-b --tb=short`:
  **44 passed, 5 skipped**, 4.61 seconds. Real service URLs were intentionally unset after the
  Docker storage failure, so real Redis, PostgreSQL (two tests), Qdrant and Neo4j tests skipped.
  This validates the final source line-bound checks and dispatcher changes independently;
  skipped checks are not a replacement for the earlier real-service evidence.
- Final Ruff lint and formatting checks: **passed**, 41 Python files. Generated OpenAPI drift
  check: **passed**. `python -m pip check`: **passed**. Both Compose configuration checks:
  **passed**. CI now configures the real Redis suite, but remote CI was not run.

### Remaining acceptance blockers and operational limits

- **Unverified external identity deployment:** no actual issuer/token credentials. Signed
  fixture verification is not a real OIDC deployment certification. Membership binding currently
  supports one organization per external subject, uses operator provisioning, and lacks complete
  persisted organization/user administration and audit lifecycle.
- **Blocked infrastructure check:** Docker image export/start and Linux regressions must be
  rerun after C: capacity/containerd storage is repaired. No reset, prune, deletion of user
  files, volumes or shared containers was performed. Old running images are not current code.
- **Unverified broader broker scenarios:** live provider through deployed broker worker,
  Redis server restart/durable-volume restoration, cancellation during every network boundary,
  concurrent multi-dispatcher stress and full broker/network partitions. Current worker restart
  evidence is real process death with controlled lease expiry, not every host-failure mode.
- **Remaining design/operations:** cross-key same-SHA job coalescing, complete audit/quotas,
  encrypted-store key rotation/backup/retention/deletion procedures, large-repository memory/load
  validation and private-provider credentials. Snapshot/source UPDATE/DELETE are intentionally
  blocked; a privileged reviewed retention workflow is needed before production deletion use.
  No production-ready, complete-phase or security-certification claim is made.

Next steps: repair/recheck Docker storage, repeat the locked Linux build and complete broker
deployment checks, configure an approved real OIDC issuer and record its verification, then
close remaining Phase 1 acceptance gaps. README's latest section and ADR 0004 provide exact
configuration, provisioning, migration (0007), worker/dispatcher and reproduction commands.

## Persistent storage policy — 2026-10-30

- Added AGENTS.md storage instructions without removing existing rules: keep checkout on D:,
  prefer D: for new supported storage with E: capacity fallback, preflight peak demand, recover
  safely, inspect Docker host storage, and require approval for cleanup/data moves/global
  settings. Phase states and prior acceptance evidence are unchanged.
- Added scripts/Use-CodeAtlasStorage.ps1 for process-scoped temp, tool caches, model/dataset
  directories and explicit output destinations. Default root: D:\projects\CODEATLAS\.storage;
  fallback: E:\CodeAtlas\CODEATLAS-storage, subject to filesystem permission. No E: folder,
  installation, download, data move, deletion or global setting change was performed.
- Executed helper with ExpectedGiB=1: **passed**, selected D:. Python **3.12.4** reported D:
  temp/bytecode paths; pip cache-dir and npm cache configuration both reported D: paths. Ruff
  lint/format checks **passed** (41 Python files). .storage is ignored/excluded from Git,
  Docker contexts and Ruff. Application tests were not rerun for this storage policy change.
- Read-only Docker inspection found docker_data.vhdx (9,496,952,832 bytes) and main ext4.vhdx
  (100,663,296 bytes) under C:\Users\Sahad\AppData\Local\Docker\wsl. Active context is
  desktop-linux; daemon query **failed: Docker Desktop is unable to start**. DockerRootDir
  remains unverified. No reset, prune, repeated repair attempt or VHD relocation was performed.
- Available-space observation: approximately 2.75 GiB on C:, 213.5 GiB on D:, 158 GiB on E:.
  README documents configured locations, supported process inheritance, unavoidable C: usage,
  and the exact Docker blocker. E: capacity fallback was not exercised; future shells must
  initialize the helper explicitly. No Docker build/pull or indexing was attempted in this turn.

## Read-only Docker diagnosis and recovery proposal — 2026-10-30

Phase 1 stays **in_progress**; later phases remain pending. All Docker/WSL diagnostic actions
were read-only. No shutdown/restart, mount, VHD copy/move, reset, prune, repair or settings change
was performed. The proposed recovery is recorded in docs/runbooks/DOCKER_RECOVERY_APPROVAL.md
for user approval; README links it.

- Current VHD locations/sizes remain C:\Users\Sahad\AppData\Local\Docker\wsl\disk\docker_data.vhdx
  (9,496,952,832 bytes) and main\ext4.vhdx (100,663,296 bytes). Desktop version 4.93.0.240920;
  CLI 29.8.1; desktop-linux context. No alternate disk path in inspected Desktop settings.
- Capacity observation: C: **3.87 GiB**, D: **213.54 GiB**, E: **158.00 GiB** free. C:/E: are
  partitions on disk 0; D: on disk 1. Volumes report NTFS/Healthy, which does not establish
  guest filesystem or hardware integrity. Bounded recent System-event query found no matching
  storage warnings/errors; that is not an exhaustive hardware diagnosis.
- Logs confirm host ENOSPC/disk-full error reports. At 14:44:37 IST the guest logged write
  I/O errors, aborted ext4 journal, failed superblock write and read-only remount. Containerd
  metadata write failures followed. At 14:46:47–54 IST Desktop reported insufficient space
  writing its VM log and stopped the engine. Earlier shutdown could not detach the data VHD.
- Diagnosis: confirmed disk exhaustion with ext4 journal/read-only fallout; possible data
  damage. Persistent Bolt metadata corruption is **unproven**. Ubuntu/docker-desktop WSL 2
  distributions are stopped; Docker UI/backend processes remain. WslService/vmcompute run.
  Docker server query still returns unable to start; no controlled restart was attempted, so
  stale failed-engine state versus persistent post-restart failure is not resolved. Get-VHD
  is unavailable, and guest free space/offline integrity were not checked by mounting anything.
- Proposed approval scope: quit Docker/save WSL work, WSL shutdown, verified cold backup on D:,
  one controlled startup after capacity preflight, and supported Desktop Disk image location
  change to D:\CodeAtlas\DockerDesktop. Reserve 50 GiB on D: for copies/growth and target
  10 GiB on C: before startup (operational precautions, not vendor minima). Current C: is
  below that proposed headroom; any C: cleanup needs its own exact approval. Filesystem repair
  and restoration remain a separate conditional approval. No manual VHD movement is proposed.
- Independent checks used Python 3.12.4 with initialized D: temp/bytecode/tool cache locations.
  Ruff lint and OpenAPI drift checks **passed**. Targeted OIDC/source/recovery suite:
  **7 passed**, 1.12 seconds, one existing Starlette/AnyIO deprecation warning. A sandboxed
  full-suite attempt stalled without useful output and was interrupted; no success is claimed
  for that attempt. External execution of the independent checks succeeded. Docker-backed
  acceptance checks remain unavailable; the proposal is not evidence of recovered services.
- Final Docker-independent full suite outside the sandbox, with D: temp/cache storage:
  **44 passed, 5 skipped**, 3.52 seconds. Skips are real Redis, PostgreSQL (two tests), Qdrant
  and Neo4j checks with unavailable/unset service configuration. Ruff formatting **passed**
  (41 files); dependency consistency **passed**. No skipped Docker check is counted as verified.

## Approved recovery preflight — 2026-10-30

The user approved backup-first shutdown, one controlled startup and Desktop-managed relocation
to D:\CodeAtlas\DockerDesktop, conditional on saving WSL work first, verifying cold-backup
hashes, and satisfying the runbook space prerequisites. Cleanup, pruning, resets, filesystem
repair and manual movement/deletion of original VHDs remain prohibited.

Rechecked capacity before disturbing any processes: C: **4,147,056,640 bytes (3.86 GiB)**,
D: **229,260,988,416 bytes (213.52 GiB)**, E: **169,649,008,640 bytes (158.00 GiB)**.
D: exceeds the proposed 50-GiB budget, but C: is approximately **6.14 GiB short** of the approved
10-GiB restart margin. Per the user's explicit stop condition, recovery stopped at preflight.
No Docker/WSL shutdown or restart, backup copy/hash verification, relocation, cleanup or system
change was performed. No active WSL work was interrupted. Cold-backup and data-preservation
checks remain unperformed, not passed. Phase 1 remains in progress; later phases remain pending.

Existing conditional approval is recorded for a future compliant continuation. Recheck capacity
after C: headroom is restored through separately authorized action; obtain the user's saved-work
confirmation before shutting down WSL, then perform and verify the cold backup before any
controlled startup or relocation. No automatic C: cleanup is authorized.

## Approved exact-scope archive and C: recovery — 2026-10-30

The user approved only the listed storage-review candidates, verified D: copies followed by
removal of their verified C: originals, and confirmed that work was saved and affected apps
were closed. They explicitly withheld Docker shutdown/restart until separate saved-WSL-work
confirmation. Phase 1 remains in progress; later phases remain pending.

- Host preflight still found Chrome background processes. The initial archive invocation
  stopped before creating an archive or removing any file. No process was closed. The
  approved independent paths were then processed with Chrome's two cache roots skipped.
- Retained private archive:
  D:\CodeAtlas\storage-review\20261030-153051-de6984b415a1494ca54249e68d99dcd0.
  Its manifest.jsonl, summary.json, verification.json and space-final.json record the operation.
  No source file contents were printed; logs contain paths, sizes, timestamps, hashes and status.
- **23,316 files**, **7,135,971,827 logical bytes (6.65 GiB)**, were copied and SHA-256 verified
  before their C: originals were removed. The exact source file handle was held without
  write/delete sharing through verification; deletion applied to that verified handle rather
  than a potentially replaced path. No recursive directory removal was used. Scope was hard-
  coded to the 18 approved candidate paths; system data, environments, links, VHDs, Docker/WSL
  evidence and unapproved parent directories were excluded. Empty source folders remain.
- Final independent archive audit rehashed **all 23,316 copies** against the recorded hashes:
  **zero hash/size errors**, **zero removed original paths still present**. The D: archive
  remains intact. There were no additional locked/changed/unverifiable-file skips.
- The only skips were C:\Users\Sahad\AppData\Local\Google\Chrome\User Data\Default\Cache
  and its sibling Code Cache, because Chrome remained running. These were neither copied nor
  cleaned. Cleanup was not expanded to compensate for the skips; the original 7-GiB candidate
  target was not fully removed, but the required C: restart margin was exceeded.
- Net C: free-space gain measured within the archive operation: **6,217,379,840 bytes
  (5.79 GiB)**, from 13,827,874,816 to 20,045,254,656 bytes. This is distinct from logical file
  size; filesystem allocation and concurrent activity can change the net volume measurement.
  Later post-audit observation: **20,318,064,640 bytes (18.92 GiB)** free on C:, and about
  **206.77 GiB** free on D:. The timestamped space-final.json retains the last observation.
- Scripts/Archive-ApprovedStorage.ps1 is retained as the approval-scoped audit implementation;
  future execution/removal requires applicable explicit authorization, not an automatic retry.
  This was a storage operation, not an application code/phase acceptance change; no app suite
  was rerun. Verification consisted of per-file copy hashes, final rehash audit and capacity.
- **No Docker/WSL shutdown, restart, VHD backup/move, prune, reset, filesystem repair, or
  system-wide settings change occurred.** The earlier storage failure and recovery gates remain.
  Saved-WSL-work confirmation is still required; recheck capacity before any future recovery,
  then verify stopped-VHD backup hashes before the single controlled attempt/managed relocation.

## Phase 1 hardening and preflight check — 2026-11-10

Phase 1 remains **in_progress, not verified**; Phase 0 remains **verified**; Phases 2–6 remain
**pending**. Product agents, patch generation, imported-code execution, Docker pruning/reset,
filesystem repair, and manual VHD moves remain disabled.

### Code and test additions (specification §§4–5/10–11/16)

- **Gate 1 (OIDC & persisted membership hardening):** hardened OIDC JWT header checks in
  [auth.py](file:///D:/projects/CODEATLAS/services/api/codeatlas/auth.py) to explicitly reject
  header-supplied key parameters (`jku`, `jwk`, `x5u`, `x5c`), non-RS256 `alg` headers, and empty
  `sub` claims. Expanded [test_oidc.py](file:///D:/projects/CODEATLAS/tests/test_oidc.py) to
  verify rejection of lifetimes >1 hour, future `iat`, unprovisioned subjects (no auto-signup),
  header-injected `jku`, unknown `kid`, and mixed OIDC/dev-token configuration.
- **Gate 2 (Encrypted source storage & viewer bounds):** updated
  [storage.py](file:///D:/projects/CODEATLAS/services/api/codeatlas/storage.py) to raise typed
  `SourceError("source_key_invalid")` when `CODEATLAS_SOURCE_KEY` has invalid key material.
  Expanded [test_source_viewer.py](file:///D:/projects/CODEATLAS/tests/test_source_viewer.py) to
  cover `409 source_not_retained` on excluded files, `422 source_byte_limit` (>64 KiB),
  mismatched `snapshot_id` (`404`), missing `CODEATLAS_SOURCE_KEY` (`503`), and DB trigger
  rejection of `DELETE` on both `files` and `repository_snapshots`.
- **Gates 3 & 4 (Cancellation races, outbox redelivery & retry recovery):** expanded
  [test_job_recovery.py](file:///D:/projects/CODEATLAS/tests/test_job_recovery.py) with queued
  pre-claim cancellation and mid-blob-read cancellation fencing tests, and expanded
  [test_broker.py](file:///D:/projects/CODEATLAS/tests/test_broker.py) with transient
  `provider_transport_error` retry recovery and 30-second outbox republishing checks.
- **Gate 5 (Live-provider broker path readiness):** added `--via-broker` support to
  [verify_live.py](file:///D:/projects/CODEATLAS/scripts/verify_live.py) so the approved
  `https://github.com/octocat/Hello-World` commit-pinned verification can exercise both direct
  ingestion and the transactional outbox → Celery/Redis worker pipeline once Docker services
  are recovered.

### Actual checks on Python 3.12.4 (2026-11-10)

Initialized D: process storage via `scripts/Use-CodeAtlasStorage.ps1 -ExpectedGiB 1` and ran with
`D:\projects\CODEATLAS\.venv312\Scripts\python.exe` (Python 3.12.4):

- `-m ruff format --check .`: **passed** (41 files already formatted).
- `-m ruff check .`: **passed** (all checks passed).
- `scripts/export_contracts.py --check`: **passed** (`Contracts match`).
- `-m pip check`: **passed** (`No broken requirements found`).
- `docker compose -f infra/compose/compose.yaml config --no-env-resolution --quiet` and
  `verify.yaml` equivalent: **passed**.
- `-m pytest -q --tb=short`: **46 passed, 5 skipped, 1 warning in 4.03s**.
  - The 1 warning is the pre-existing Starlette `anyio.abc.BlockingPortal` deprecation warning.
  - The 5 skips are real-infrastructure integration tests (`test_postgres.py` [2],
    `test_broker.py::test_real_broker_duplicate_delivery_and_worker_restart` [1], and
    `test_phase0_projections.py` [2]) skipped because `CODEATLAS_TEST_POSTGRES`,
    `CODEATLAS_TEST_BROKER`, `CODEATLAS_TEST_QDRANT`, and `CODEATLAS_TEST_NEO4J` were unset
    while Docker Desktop remains stopped.

### Docker preflight status and remaining Phase 1 blockers

- **Preflight drive observation (2026-11-10):**
  - `C:`: **8,067,936,256 bytes (7.51 GiB)** free — **2.49 GiB below** the required **10 GiB**
    free startup margin.
  - `D:`: **226,205,118,464 bytes (210.67 GiB)** free — satisfies the 50 GiB D: reserve.
  - `E:`: **169,649,008,640 bytes (158.00 GiB)** free.
- **Stop condition enforced:** no Docker/WSL shutdown, backup copy, relocation, C: cleanup,
  prune, reset, or filesystem repair was performed because:
  1. Explicit user confirmation that WSL work is saved has not yet been provided, and
  2. `C:` free space is currently below the required 10 GiB threshold.
- **Remaining Phase 1 verification gates before marking Phase 1 `verified`:**
  1. Receive user confirmation that WSL work is saved and restore `C:` free space to ≥10 GiB
     through separately approved action.
  2. Execute the approved backup-first Docker recovery (normal Docker/WSL shutdown → cold VHD
     backup on `D:` with SHA-256 verification → single controlled Docker Desktop startup and
     Desktop-managed relocation to `D:\CodeAtlas\DockerDesktop` → active path and data check).
  3. Rebuild the locked Linux images (`api`, `worker`, `dispatcher`, `migrate`), apply migrations
     through `0007`, run the full real-service pytest suite (`CODEATLAS_TEST_POSTGRES`,
     `CODEATLAS_TEST_BROKER`, `CODEATLAS_TEST_QDRANT`, `CODEATLAS_TEST_NEO4J`) with zero skips,
     and run `scripts/verify_live.py --approved-octocat-hello-world --via-broker` against the
     isolated verification stack.

## Phase 1 baseline audit and requirement-to-evidence checklist — 2026-11-15

Phase 1 remains **in_progress, not verified**; Phase 0 remains **verified**; Phases 2–6 remain
**pending**. Product agents, patch generation, imported repository code/test execution, Docker
pruning/reset, filesystem repair, and manual VHD moves remain disabled.

### Inspected Computer Baseline (2026-11-15)

- Git: 2.54.0.windows.1; Node: v24.15.0; npm: 11.12.1.
- Python runtime: Python 3.12.4 (`D:\projects\CODEATLAS\.venv312\Scripts\python.exe`). PATH Python is 3.11.9 (unused).
- Locked dependencies: `requirements.lock` consistent with Python 3.12; Docker/CI target is 3.12.10 (same minor).
- Docker CLI: 29.8.1; Docker Compose: v5.5.1; Context: `desktop-linux`.
- WSL distros: `Ubuntu` (WSL 2, Stopped), `docker-desktop` (WSL 2, Stopped).
- Docker Daemon: Not running (`open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified`).
- Host storage:
  - `C:`: **5,753,925,632 bytes (5.36 GiB)** free — **4,983,492,608 bytes (4.64 GiB) below** the required 10 GiB threshold.
  - `D:`: **226,202,222,592 bytes (210.67 GiB)** free — satisfies and exceeds the 50 GiB reserve.
  - `E:`: **143,311,478,784 bytes (133.47 GiB)** free.
- Docker recovery status: Stopped at preflight per policy. Explicit confirmation that WSL work is saved is missing,
  and `C:` capacity is 4.64 GiB below the 10 GiB restart margin. No Docker/WSL shutdown, VHD copy, relocation, prune,
  reset, or cleanup was performed.

### Requirement-to-Evidence Acceptance Checklist

| Section & Requirement | Specification Reference | Implemented Component | Verification & Evidence | Status |
|---|---|---|---|---|
| **A1. Persisted Memberships & Roles** | §§4, 10, 16 | `memberships` table (migration 0004), roles: `owner`, `admin`, `developer`, `viewer` | `tests/test_grants.py::test_roles_grants_and_revocation`, `tests/test_oidc.py` | Implemented & verified (host unit) |
| **A2. Repository Grants** | §§4, 10, 16 | `repository_grants` table (migration 0003), capabilities: `read`, `index` | `tests/test_grants.py`, `tests/test_revocation_faults.py` | Implemented & verified (host unit) |
| **A3. OIDC Authentication** | §§4, 10, 16 | `auth.py`, `config.py` (strict RS256, pinned `kid`, iss/aud/exp/iat/sub, max 1h, header injection rejection) | `tests/test_oidc.py::test_verified_oidc_binding_revocation_and_claim_failures` | Implemented & verified (host unit) |
| **A4. Production Refusal of Dev Mode** | §§4, 10, 16 | `config.py::Settings.validate()` strictly rejects `auth_mode != 'development'` or `environment != 'development'` | `tests/test_foundation.py::test_production_refused` | Implemented & verified (host unit) |
| **A5. Identity-Derived Tenant Scope** | §§4, 10 | `auth.py::authenticate()` binds tenant & principal from verified DB membership | `tests/test_foundation.py::test_vertical_slice_and_two_tenants`, `tests/test_oidc.py` | Implemented & verified (host unit) |
| **A6. Repository Access Recheck** | §§4, 11 | `access.py::repository_access()` rechecked at API endpoints and in worker `fence()` | `tests/test_revocation_faults.py::test_revocation_during_ingestion_prevents_source_persistence` | Implemented & verified (host unit) |
| **A7. PostgreSQL RLS & Pool Reuse** | §§4, 10, 16 | Migrations 0001–0004 enable and FORCE RLS on all tenant tables with `current_setting('app.tenant', true)` | `tests/test_postgres.py::test_rls_and_pool_reuse` (historical 2026-10-30; skipped on current host check due to stopped engine) | Blocked on Docker recovery |
| **B1. Allowlisted HTTPS Providers** | §§4, 11 | `source.py::canonical_remote()` accepts only canonical `https://github.com/owner/repository` | `tests/test_foundation.py::test_url_rejection` (13 negative cases) | Implemented & verified (host unit) |
| **B2. Transport, Address & Rebinding Bounds** | §§4, 11 | `source.py::PinnedHTTPS` validates global IP, pins address, verifies TLS hostname, rejects private/loopback/link-local/metadata | `tests/test_foundation.py::test_dns_private_and_rebinding_boundary`, `test_redirect_is_not_followed` | Implemented & verified (host unit) |
| **B3. Full Commit SHA Pinning** | §§5, 10, 16 | Resolved full SHA recorded before inventory; moving refs never alter in-flight work | `tests/test_foundation.py::test_vertical_slice_and_two_tenants` | Implemented & verified (host unit) |
| **B4. Pin Preservation on Recovery** | §§5, 16 | `ingestion.py::run_job` reuses `job['commit_sha']` if present; never resolves branch again | `tests/test_job_recovery.py::test_outbox_pin_survives_crash_and_branch_move` | Implemented & verified (host unit) |
| **B5. Unsafe Paths & Symlinks Rejected** | §§4, 5 | `source.py::classify()` rejects traversal, Windows paths, NUL bytes, symlinks, submodules | `tests/test_foundation.py::test_path_rejection` (5 negative cases) | Implemented & verified (host unit) |
| **B6. Ingestion Resource Limits** | §§4, 5 | 100k files, 1 GiB total size, 16 MiB per payload, 1 MiB text file cap, 30 min deadline | `source.py::classify()`, `GitHubSource.get()`, `ingestion.py` | Implemented & verified (host unit) |
| **B7. Repository Code Never Executed** | §§4, 5, 9, 16 | Ingestion is data-only; subprocess/Popen forbidden | `tests/test_job_recovery.py::test_ingestion_never_executes_source_and_reuses_snapshot` | Implemented & verified (host unit) |
| **C1. Immutable Snapshots & Ancestry** | §§5, 10, 16 | `repository_snapshots` table (0002); ancestry constraints in 0007; update/delete triggers in 0005 | `tests/test_postgres.py::test_postgres_snapshot_mutation_rejected`, `tests/test_source_viewer.py` | Implemented (triggers verified on SQLite; PG blocked on Docker) |
| **C2. Classification Taxonomy** | §§4, 5 | `inventoried`, `excluded`, `oversized`, `unsupported`, `binary` with specific reasons | `tests/test_foundation.py::test_vertical_slice_and_two_tenants` | Implemented & verified (host unit) |
| **C3. Encrypted Source Envelopes** | §§4, 10 | Fernet AEAD envelope binds tenant/repo/commit/path with SHA-256 integrity check; key in `CODEATLAS_SOURCE_KEY` | `tests/test_source_viewer.py::test_encrypted_immutable_scoped_source` | Implemented & verified (host unit) |
| **C4. Bounded Source Viewer** | §§10, 11 | `GET /api/v1/files/{file_id}/content` enforces 500 lines, 64 KiB cap, verified snapshot/repo scope | `tests/test_source_viewer.py::test_encrypted_immutable_scoped_source` | Implemented & verified (host unit) |
| **C5. Immediate Revocation Enforcement** | §§4, 11 | Revoking membership or grant blocks subsequent source access immediately (`401` or `404`) | `tests/test_source_viewer.py`, `tests/test_revocation_faults.py` | Implemented & verified (host unit) |
| **D1. Durable States & Outbox** | §§5, 10, 16 | `index_jobs` state machine (`queued`, `running`, `succeeded`, `failed`, `cancelled`); `outbox_events` (0002, 0006) | `tests/test_job_recovery.py::test_outbox_pin_survives_crash_and_branch_move` | Implemented & verified (host unit) |
| **D2. Scoped Idempotency & Conflict** | §§5, 10, 11 | Unique `(org_id, requested_by, idempotency_key)` on `index_jobs`; conflicting digest returns 409 | `tests/test_foundation.py::test_vertical_slice_and_two_tenants` | Implemented & verified (host unit) |
| **D3. Broker Delivery & Worker Loss** | §§2, 5, 15 | Celery 5.5.2 + Redis 5.2.1 in `queue.py` (`task_acks_late=True`, `task_reject_on_worker_lost=True`) | `tests/test_broker.py::test_publish_failure_keeps_outbox_pending`, `test_real_broker_duplicate_delivery_and_worker_restart` | Broker unit verified; real Redis blocked on Docker |
| **D4. Lease Fencing & Stale Worker Replacement** | §§5, 10, 16 | `lease_epoch`, `lease_until` (60s), transactional fence in DB updates | `tests/test_job_recovery.py::test_expired_worker_cannot_overwrite_replacement` | Implemented & verified (host unit) |
| **D5. Exclusive Worker Claims** | §§5, 16 | Atomic worker claim on `queued` status; concurrent claims return False | `tests/test_job_recovery.py::test_concurrent_worker_claim_is_exclusive` | Implemented & verified (host unit) |
| **D6. Bounded Retries & Exhaustion** | §§5, 16 | Max 3 attempts for transient transport errors; failure with `attempt_limit` | `tests/test_broker.py::test_transient_retry_limit`, `tests/test_job_recovery.py::test_recovery_fences_exhausted_attempts` | Implemented & verified (host unit) |
| **D7. Cancellation Races & Omission** | §§5, 11, 16 | Durable cancel before claim, mid-blob read, and inflight; cancelled jobs omitted from dispatch | `tests/test_job_recovery.py::test_cancellation_fences_inflight_worker`, `test_cancellation_races_before_claim_and_during_blob`, `test_cancelled_job_not_dispatched` | Implemented & verified (host unit) |
| **D8. Live Provider Ingestion** | §§5, 16 | `octocat/Hello-World` full SHA `7fd1a60b01f91b314f59955a4e4d4e80d8edf11d` | Prior direct evidence in `docs/evidence/live-20261030.json`; `--via-broker` pipeline readiness added to `scripts/verify_live.py` | Broker live check blocked on Docker recovery |

### Current Test Execution Summary (Python 3.12.4)

Command: `python -m pytest -v --tb=short` with process storage on D:
- **49 passed, 5 skipped, 1 warning in 5.40s**.
- Warning: Starlette `anyio.abc.BlockingPortal` deprecation warning.
- Skipped tests (require running Docker services):
  1. `tests/test_postgres.py::test_rls_and_pool_reuse` (needs `CODEATLAS_TEST_POSTGRES`)
  2. `tests/test_postgres.py::test_postgres_snapshot_mutation_rejected` (needs `CODEATLAS_TEST_POSTGRES`)
  3. `tests/test_broker.py::test_real_broker_duplicate_delivery_and_worker_restart` (needs `CODEATLAS_TEST_BROKER`)
  4. `tests/test_phase0_projections.py::test_qdrant_all_scope_filters_before_ranking` (needs `CODEATLAS_TEST_QDRANT`)
  5. `tests/test_phase0_projections.py::test_neo4j_scopes_every_node_and_edge` (needs `CODEATLAS_TEST_NEO4J`)

## GitHub publication preparation — 2026-11-17

- User requested publishing this workspace to `https://github.com/sahadhaneef/CODEATLAS`.
  The destination was public and empty at inspection; the workspace had no Git history.
  Initialized a local `main` branch and configured that repository as `origin`.
- Reviewed 78 candidate project files (364,619 bytes before this status addition).
  `.env`, both virtual environments, `.storage`, `.verification`, databases, Python caches,
  and `node_modules` are excluded by `.gitignore`. No local secret values or common
  token/private-key patterns were found in candidate files; this is a limited publication
  check, not a comprehensive security audit. Existing local data and keys are preserved.
- Python 3.12.4: Ruff formatting (41 files), Ruff lint, contract drift, and `pip check`
  passed. The initial sandboxed pytest invocation stalled without results and was interrupted;
  the approved outside-sandbox run completed: **49 passed, 5 skipped, 1 warning in 4.47s**.
  The warning is Starlette's deprecated AnyIO BlockingPortal alias. Real PostgreSQL, broker,
  Qdrant, and Neo4j integration checks remain skipped with their test URLs unset.
- Phase 0 remains **verified**, Phase 1 **in_progress**, and Phases 2–6 **pending**.
  Publishing does not complete the remaining infrastructure or live-broker gates.
  No Docker/WSL recovery, cleanup, or imported repository execution was performed.
