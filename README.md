# CodeAtlas foundation

Latest Phase 1 setup is documented in the final section below. Earlier Phase 0 commands and
results are retained for history; migration head is now 0007, encrypted source needs a key,
and the default worker is broker-backed. See IMPLEMENTATION_STATUS.md for current blockers.

Before running project commands, initialize the process-scoped settings in the **Storage
policy and configured locations** section below. Each new terminal/tool shell needs its own
initialization; settings in a child shell cannot configure its parent or unrelated sessions.

Read-only Phase 0 / first Phase 1 inventory slice. Agents, patch generation and execution of
imported code/tests are disabled and have no routes. Full indexing/search/UI is pending.
See [implementation status](docs/IMPLEMENTATION_STATUS.md) and [ADR](docs/adr/0001-foundation.md).

## Prerequisites (actually inspected)

Git 2.54.0, Node 24.15.0/npm 11.12.1, Docker CLI 29.8.1 and Compose 5.5.1 are installed.
Python on PATH is 3.11.9; **use Python 3.12**. Installed 3.12.4 is at the explicit path below.
The py launcher fails to locate Python. No tool installation is needed on this computer;
start Docker Desktop with the Linux engine before Docker commands. Node/Git are not needed
to run this backend slice. Docker/CI use Python 3.12.10 (same required minor version).

## Start with Docker (PowerShell, project root)

1. Start Docker Desktop and wait until `docker info` succeeds.
2. Create development tokens and the ignored configuration file:

```powershell
Copy-Item .env.example .env
# Edit .env: replace both token placeholders with distinct random secrets >=24 characters.
# For example generate each with:
[Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
```

3. Start the database, apply migrations, start the API:

```powershell
docker compose -f infra/compose/compose.yaml up -d postgres
docker compose -f infra/compose/compose.yaml run --rm migrate
docker compose -f infra/compose/compose.yaml up -d --build api
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
Invoke-RestMethod http://127.0.0.1:8000/api/v1/ready
```

Open http://127.0.0.1:8000/docs for the generated OpenAPI contract. Readiness checks the migrated
database only; it does not imply provider availability or a running background worker.

## Register, queue, ingest and verify

Registration requires a configured tenant administrator token and creates a private owner grant.
Only public GitHub repositories are supported; registration records intent, and actual remote
access is checked by the tracked fetch job. Replace the URL/ref with a small repository you
are authorized to import. Avoid large repositories: unauthenticated GitHub rate limits apply.

```powershell
$tokenA = (Get-Content .env | Where-Object { $_ -like 'CODEATLAS_DEV_TOKEN_A=*' }).Split('=',2)[1]
$headers = @{ Authorization = "Bearer $tokenA" }
$repo = Invoke-RestMethod http://127.0.0.1:8000/api/v1/repositories -Method Post -Headers $headers -ContentType application/json -Body '{"remote_url":"https://github.com/YOUR-OWNER/YOUR-SMALL-REPO","requested_ref":"main","visibility_policy":"private"}'
$jobHeaders = @{ Authorization = "Bearer $tokenA"; 'Idempotency-Key' = [guid]::NewGuid().ToString() }
$job = Invoke-RestMethod "http://127.0.0.1:8000/api/v1/repositories/$($repo.id)/index" -Method Post -Headers $jobHeaders -ContentType application/json -Body '{"ref":"main"}'
docker compose -f infra/compose/compose.yaml run --rm worker --tenant 00000000-0000-0000-0000-000000000001
Invoke-RestMethod "http://127.0.0.1:8000$($job.status_url)" -Headers $headers
Invoke-RestMethod "http://127.0.0.1:8000$($job.status_url)/files?limit=100" -Headers $headers
```

Expect a full `commit_sha`, `tree_sha`, `stage=inventory_complete` and `status=succeeded` for
an inventory-only job. Inspect `error_code` on failure. This never publishes a searchable
generation. List endpoints accept `limit` (1–100) and exclusive `after` (last ID or file path).
The worker processes at most ten queued jobs per invocation; invoke again for more. Repeating
an Idempotency-Key with the same request returns its existing job; conflicting reuse is 409.
Tenant B's token must return 404 for tenant A's job and repository mutations and an empty list
of tenant A repositories. Invalid remotes such as file:///tmp/repo must return 422.

## Develop and run CodeAtlas's own checks with Python 3.12

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m venv .venv312
.\.venv312\Scripts\python -m pip install -r requirements.lock
.\.venv312\Scripts\python -m pip install --no-deps --no-build-isolation -e .
.\.venv312\Scripts\python -m ruff check .
.\.venv312\Scripts\python -m ruff format --check .
.\.venv312\Scripts\python -m pytest -q
```

Real PostgreSQL RLS test (dedicated development DB only, migration owner URL):

```powershell
$env:CODEATLAS_TEST_POSTGRES='postgresql+psycopg://codeatlas:local-development-only@localhost:5432/codeatlas'
.\.venv312\Scripts\python -m pytest -q tests/test_postgres.py
```

To run the API on the host, load .env into this shell and use the app database role:

```powershell
Get-Content .env | Where-Object { $_ -match '^[A-Z_]+=' } | ForEach-Object { $parts=$_.Split('=',2); [Environment]::SetEnvironmentVariable($parts[0],$parts[1],'Process') }
$env:CODEATLAS_DATABASE_URL='postgresql+psycopg://codeatlas_app:local-app-only@localhost:5432/codeatlas'
.\.venv312\Scripts\python -m uvicorn codeatlas.main:create_app --factory --host 127.0.0.1 --port 8000
```

Offline local alternative: set CODEATLAS_DATABASE_URL to `sqlite:///local.db`, run
`python -m alembic upgrade head`, then start the same API/worker with the configured tokens.
SQLite cannot verify PostgreSQL RLS; it is not a production substitute.

## Operations and limitations

`docker compose -f infra/compose/compose.yaml down` stops services and retains database data.
Never remove the volume to repair a failed migration. Upgrade is `alembic upgrade head`;
`alembic downgrade base` destroys all slice tables and is for disposable test databases only.
Back up before migrating real data. Initial role SQL runs only on a fresh PostgreSQL volume.

No automatic retries/recovery of running jobs: inspect a crashed worker/job, then enqueue a
new request with a new key. No cancellation or source content viewer yet. Inventory metadata
persists; source bytes do not. No secret scanning or external model use exists. Phase 0 risk
spikes now have controlled fixture evidence; full Phase 1 acceptance remains pending.
Docker image digests, Linux installation, PostgreSQL migration/RLS, and dependency readiness
were verified on 2026-10-30. Dependency vulnerability review and live provider ingestion are
still unverified; the presence of CI configuration is not a passing remote CI run.

## Reproduce the Phase 0 gate

These are development experiments, separate from production indexing. Keep Node tooling out
of imported repositories; only the first-party controlled fixtures are analyzed. Install the
Python 3.12 base dependencies as above, then:

```powershell
.\.venv312\Scripts\python -m pip install -r requirements-spikes.lock
npm.cmd ci --prefix spikes/semantic --ignore-scripts --no-audit --no-fund
docker compose -p codeatlas-phase0-verify -f infra/compose/verify.yaml up -d --wait --wait-timeout 90
.\.venv312\Scripts\python scripts/wait_for_spikes.py
$env:CODEATLAS_TEST_POSTGRES='postgresql+psycopg://codeatlas:local-development-only@127.0.0.1:55432/codeatlas?connect_timeout=5'
$env:CODEATLAS_TEST_QDRANT='http://127.0.0.1:56333'
$env:CODEATLAS_TEST_NEO4J='bolt://127.0.0.1:57687'
.\.venv312\Scripts\python -m pytest -q
.\.venv312\Scripts\python -m ruff check .
.\.venv312\Scripts\python -m ruff format --check .
.\.venv312\Scripts\python scripts/export_contracts.py --check
```

Expect the current test count recorded in IMPLEMENTATION_STATUS.md with all prerequisites installed. When service URLs or Node/
parser dependencies are missing, spike tests skip explicitly; that is not full gate validation.
The generated API and manifest schemas are under docs/api/, docs/models/, and evals/manifests/.
See ADR 0002 for measured semantic capabilities, model candidates/privacy policy, and image pins.

The verification API started for the 2026-10-30 gate is at http://127.0.0.1:58000/docs using
Compose project `codeatlas-phase0-boot` (port 8000 was occupied and was left alone). Its .env
contains generated local tokens, never printed in logs. For the same boot project, use:

```powershell
$env:CODEATLAS_API_PORT='58000'
docker compose -p codeatlas-phase0-boot -f infra/compose/compose.yaml up -d --build api
Invoke-RestMethod http://127.0.0.1:58000/api/v1/ready
```

Use port 58000 in the registration commands when verifying this running instance. Override
CODEATLAS_API_PORT to another available loopback port when needed. Stop only these stacks:

```powershell
docker compose -p codeatlas-phase0-verify -f infra/compose/verify.yaml down
docker compose -p codeatlas-phase0-boot -f infra/compose/compose.yaml down
```

Both commands retain named volumes. No imported source or tests are executed by the probes;
Tree-sitter is syntax only and Pyright diagnostics are not reference-resolution support.

## Phase 1 development additions (gate incomplete)

Apply `python -m alembic upgrade head` using Python 3.12 and the migration-owner URL before
starting updated code; schema head is now 0003. Preserve the Phase 0 database and volumes.
The existing Docker API must be rebuilt/recreated to serve these additions; an already running
Phase 0 image does not pick up host edits automatically.

`POST /api/v1/index-jobs/{id}/cancel` durably cancels queued/running work. Worker invocations
now reconcile expired 60-second leases through the database outbox, fencing stale workers and
retaining pinned SHAs. Attempts are capped at three; failed permanent jobs are not implicitly
retried. `GET /api/v1/repositories/{id}/snapshots` lists inventory-completed commit records.
No searchable generation is published. The PostgreSQL outbox is not yet a Redis/Celery queue.

Optional CODEATLAS_DEV_IDENTITIES maps additional secret tokens to `[tenant, principal, role]`
in JSON; do not expose or commit it. Owner/admin identities can register repositories and use
`PUT /repositories/{id}/grants` with `{principal_id, capability: "read"|"index"}` for configured
same-tenant members. Delete `/repositories/{id}/grants/{principal_id}` to revoke. All paths
have the `/api/v1` prefix. Viewer role forbids indexing. OIDC and persisted membership
administration are not implemented, and production startup remains refused. See ADR 0003.

## Current Phase 1 setup (2026-10-30)

Use Python 3.12. Install updated requirements.lock and migrate with the database-owner URL:

```powershell
.\.venv312\Scripts\python -m pip install -r requirements.lock
# Load .env into the shell as shown above; use the migration-owner database URL.
.\.venv312\Scripts\python -m alembic upgrade head
```

Set CODEATLAS_SOURCE_KEY once in the ignored .env, generated with:

```powershell
.\.venv312\Scripts\python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Back up this key separately from the database. Never regenerate it casually: existing source
will become unreadable. Source-key errors produce unavailable/failed states. Source envelopes
are encrypted in PostgreSQL; file metadata lists never contain the ciphertext or raw source.
`GET /api/v1/files/{id}/content?snapshot_id={id}&start_line=1&end_line=100` authorizes each read,
verifies its immutable scope/hash, and caps output at 500 lines/64 KiB. Excluded, binary, old
unretained and oversized files have no source bytes. No index generation exists in Phase 1.

After Docker storage is healthy, start/rebuild the local broker stack with the existing project
name if preserving its database (do not switch projects accidentally):

```powershell
docker compose -p codeatlas-phase0-boot -f infra/compose/compose.yaml up -d postgres redis
docker compose -p codeatlas-phase0-boot -f infra/compose/compose.yaml run --rm migrate
$env:CODEATLAS_API_PORT='58000'
docker compose -p codeatlas-phase0-boot -f infra/compose/compose.yaml up -d --build api worker
docker compose -p codeatlas-phase0-boot -f infra/compose/compose.yaml run --rm dispatcher --tenant 00000000-0000-0000-0000-000000000001
```

Run a dispatcher for each operator-approved tenant. It reconciles leases and republishes queued
outbox work every two seconds; transient broker failures retain pending events. The dispatch
command is long-running; `--once` runs one pass. Worker messages contain identifiers only.
The legacy `python -m codeatlas.worker --tenant ...` is a manual diagnostic path; it bypasses
broker delivery and is not evidence of the broker-backed workflow. Cancellation is cooperative
at bounded fetch/file/persistence boundaries; it never overwrites terminal successful work.

OIDC mode (API bearer access tokens, no browser login): set CODEATLAS_AUTH_MODE=oidc,
CODEATLAS_ENV=production, CODEATLAS_OIDC_ISSUER (HTTPS), CODEATLAS_OIDC_AUDIENCE and
CODEATLAS_OIDC_KEYS (JSON mapping trusted kid to RSA public-key PEM). Remove development token
variables/mappings entirely. Pin/rotate these keys as an operator; token headers cannot supply
URLs or algorithms. Only RS256, matching issuer/audience, exp/iat/sub and lifetimes <=1 hour
are accepted. No actual issuer credentials or tokens are bundled or verified live.

Provision memberships explicitly using the migration-owner environment and a JSON file with
organization_id, principal_id, issuer, subject and role:

```powershell
.\.venv312\Scripts\python scripts/provision_membership.py path-to-approved-membership.json
```

Issuer/subject/tenant must match a verified bearer token; a token cannot create memberships.
Persisted role/status controls access, and revoked dev memberships are not re-created on login.
Current membership bindings support one organization per external subject; multi-organization
accounts and a membership-management UI/API remain limitations. Operator SQL changes require
appropriate controlled/audited credentials. Repository grants remain a separate requirement.

Full checks use the earlier PostgreSQL/Qdrant/Neo4j variables plus
CODEATLAS_TEST_BROKER=redis://127.0.0.1:56379/0. Install requirements-spikes.lock and Node probe
dependencies before the full suite. If C: temp storage is full, create .verification and use a
fresh `--basetemp=.verification/your-new-test-run` on D: (pytest clears its chosen base directory).
The real broker test kills only its own controlled worker process and cleans only its unique
queue. Do not run destructive fault drills against a shared production database/broker.

Approved live check: `python scripts/verify_live.py --approved-octocat-hello-world` (or add
`--via-broker` when a Celery worker and Redis broker are running) using the isolated
database/runtime-role URL and backed-up source key. It imports only the explicitly approved
public octocat/Hello-World repository at a full resolved SHA and prints metadata, never source.
Each run creates an isolated repository record; no upstream write/test/script occurs.
The retained result is docs/evidence/live-20261030.json.

Current machine blocker: C: ran out of space and Docker containerd reported read-only metadata
during image export. No Docker reset, prune or volume deletion was performed. Free space using
your normal reviewed maintenance, then restart/check Docker Desktop and repeat the build/start
and Linux checks. Existing Phase 0 evidence is retained; Phase 1 remains in progress.

## Storage policy and configured locations

Docker is still blocked. Read-only diagnosis found a disk-full shutdown and an ext4 journal
abort/read-only remount; permanent containerd metadata corruption is not established. The
[approval procedure](docs/runbooks/DOCKER_RECOVERY_APPROVAL.md) proposes an offline verified
backup and Desktop-managed relocation to D:, with repair kept behind a separate approval.
No recovery action has been executed. D: is on a different physical disk from C:/E:.

Keep the checkout at `D:\projects\CODEATLAS`. All new project files, environments, downloads,
caches, temp files, build outputs, logs, models and datasets belong on D:, with E: as the
capacity fallback. Preserve existing files, source keys, databases and artifacts. Deleting
files, pruning Docker, moving existing application/system data or changing global/user-wide
settings requires explicit approval; this policy does not authorize those operations.

Initialize every PowerShell session before project work:

```powershell
Set-Location D:\projects\CODEATLAS
Get-PSDrive C,D,E | Select-Object Name,Free,Used
. .\scripts\Use-CodeAtlasStorage.ps1 -ExpectedGiB 5
```

Estimate *additional peak* usage, including downloads, unpacking, temporary copies and outputs.
The helper checks that estimate plus 10 GiB headroom (`-MinimumFreeGiB` is configurable),
choosing D: then E:. It stops if neither qualifies; there is no C: fallback. This is a preflight
floor, not a quota guarantee. Recheck before and during large operations. It creates dedicated
folders and sets only process variables; no installation, activation, deletion or data move.

Configured paths (verified 2026-10-30):

- Checkout: `D:\projects\CODEATLAS`; existing Python 3.12 environment: `.venv312` beneath it.
  The old `.venv` remains unused and preserved. CODEATLAS_VENV_PATH reuses `.venv312` on D:.
- New default storage: `D:\projects\CODEATLAS\.storage`. Capacity fallback:
  `E:\CodeAtlas\CODEATLAS-storage`, subject to filesystem permission. If a sandbox blocks E:
  creation, request that exact access; do not use C:. E: was not needed during verification.
- TEMP/TMP: `<storage-root>\temp\<unique-session-id>`. A fresh session never reuses or deletes
  earlier temporary work. Standard child-process tempfile/pytest/pip writes inherit this path.
- Caches: `<storage-root>\cache\pip`, `npm`, `uv`, `ruff`, `mypy`, `python-bytecode`, `xdg`, via
  PIP_CACHE_DIR, NPM_CONFIG_CACHE, UV_CACHE_DIR, RUFF_CACHE_DIR, MYPY_CACHE_DIR,
  PYTHONPYCACHEPREFIX and XDG_CACHE_HOME. Existing caches are not moved or copied.
- Models: `<storage-root>\models\huggingface` (HF_HOME), its `hub` directory (HF_HUB_CACHE),
  and `models\torch` (TORCH_HOME). Datasets: `datasets\huggingface` (HF_DATASETS_CACHE).
  Setup downloads no model/dataset. Node dependencies remain within the D: project.
- Output folders: `<storage-root>\downloads`, `build`, `logs`, `artifacts`, via
  CODEATLAS_DOWNLOAD_DIR, CODEATLAS_BUILD_DIR, CODEATLAS_LOG_DIR, CODEATLAS_ARTIFACT_DIR.
  These custom variables are destinations, not universal tool settings: supply each tool's
  supported output/log arguments. Example: `python -m pip download -r requirements.lock
  --dest $env:CODEATLAS_DOWNLOAD_DIR`. A future build tool must receive its `--outdir` explicitly.
- With E: selected, CODEATLAS_VENV_PATH names `<storage-root>\venvs\py312` for any explicitly
  needed new environment. The helper never recreates/moves an existing environment automatically.
- Existing `.verification` and pytest caches already reside under the D: checkout. `.storage`
  is excluded from Git, Docker build contexts and Ruff; caches/artifacts must not ship as code.

Verify redirection in that same initialized process, without downloading/building:

```powershell
& "$env:CODEATLAS_VENV_PATH\Scripts\python.exe" -c "import sys,tempfile; print(sys.version); print(tempfile.gettempdir()); print(sys.pycache_prefix)"
& "$env:CODEATLAS_VENV_PATH\Scripts\python.exe" -m pip cache dir
npm.cmd config get cache
```

If a disk fills, stop the affected operation, inspect its exit status/partial outputs, recheck
capacity and redirect only supported new/resumable storage. Preserve verified downloads,
encryption keys, pinned revisions and validated checkpoints. Resume only where supported;
otherwise use a distinct output/run directory and record the incomplete attempt. Never blindly
duplicate large datasets, overwrite good results or silently accept corrupt partial artifacts.
No destructive cleanup or migration is automatic. Request approval when permissions or an
existing-data move are needed; report exact unsupported C: usage instead of retrying blindly.

### Docker and unavoidable C: usage

Read-only host inspection located Docker Desktop storage on C:, despite the D: checkout:

- `C:\Users\Sahad\AppData\Local\Docker\wsl\disk\docker_data.vhdx`:
  9,496,952,832 bytes (about 8.8 GiB).
- `C:\Users\Sahad\AppData\Local\Docker\wsl\main\ext4.vhdx`:
  100,663,296 bytes.
- Settings: `C:\Users\Sahad\AppData\Roaming\Docker\settings-store.json`. No explicit alternate
  disk/data-folder setting was found in the inspected file.

Active context is `desktop-linux`, but `docker info` fails with **Docker Desktop is unable
to start**. Daemon DockerRootDir and individual volume locations remain unverified. A Linux
`/var/lib/docker` path would not establish the Windows drive holding it. Images, named volumes,
build cache and daemon logs are managed by Docker's virtual disk; client TEMP/cache settings
and D: build context paths do not redirect them. Block storage-heavy Docker pulls/builds/service
startup until host storage location and capacity satisfy this policy. Relocating the existing
VHD via supported Docker Desktop settings requires separate explicit approval and was not
performed. Do not manually move VHD files, reset Docker or prune data as an automatic repair.

At inspection C: had about 2.75 GiB free, D: 213.5 GiB and E: 158 GiB; these are observations,
not future guarantees. C: previously had only megabytes free. Existing Python 3.12/Node/Docker
installations and desktop application settings/state/logs may still use C:. PATH's Python is
3.11: use the D: 3.12 environment explicitly. The helper redirects supported project-child
temp/cache/bytecode writes; it cannot relocate Windows-managed data, application/harness logs,
or launcher activity before initialization. No system-wide setting or existing C: data changed.
Report unavoidable application-managed C: writes and block dependent operations where needed;
do not claim all machine activity has moved off C:.

Approved cleanup result (2026-10-30): the exact approved candidates were archived to
`D:\CodeAtlas\storage-review\20261030-153051-de6984b415a1494ca54249e68d99dcd0`.
All 23,316 retained copies passed a final SHA-256 audit. The two Chrome cache roots were
skipped because Chrome background processes remained; nothing outside the approved scope
was added. Verified removed originals totaled 6.65 GiB logically; the operation's measured
net C: free-space gain was 5.79 GiB. Post-audit C: free space was 18.92 GiB. Retain the archive
and its manifest/summary/verification/space reports; do not auto-delete them. Docker and WSL
were untouched, and recovery still awaits separate saved-WSL-work confirmation, a fresh
capacity check, and verified cold VHD backups. Phase 1 remains in progress.
