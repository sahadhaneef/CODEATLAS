# ADR 0003: incremental Phase 1 job lifecycle

2026-10-30; development implementation, Phase 1 gate remains in progress.

Keep the verified Phase 0 prototypes and migration 0001 intact. Add migrations 0002 and
0003 for job fencing/outbox/snapshot records and repository grants. Apply `alembic upgrade
head` before running the updated API; readiness now requires 0003. Upgrades are additive;
downgrades remove the new metadata and are restricted to disposable databases/backups.

Job creation and its unique outbox event commit together. The database polling worker claims
delivery transactionally, using an incrementing epoch and 60-second lease, refreshed at file
boundaries. Reconciliation fences expired workers, requeues at most three attempts, and keeps
the recorded commit/tree. Publication/inventory persistence holds the fenced row transaction;
cancelled or replaced workers cannot write completion/failure over the replacement.
Cancellation is durable immediately; blocking network calls stop cooperatively at the next
boundary. Snapshot rows are inserted only, unique per tenant/repository/full SHA; repeated jobs
check tree consistency. No index generation is published. Source bytes remain unretained.

This is database outbox delivery, not an implemented Celery/Redis dispatcher. Persistent
organizations/memberships, OIDC and the complete Phase 1 delivery architecture remain open
requirements, not silently replaced security requirements. No production startup is enabled.

Additional development identities may be server-configured via CODEATLAS_DEV_IDENTITIES JSON,
mapping long bearer tokens to [tenant, principal, organization_role]. Allowed roles are owner,
admin, developer and viewer. Registration requires owner/admin. Roles do not expose private
repositories: access additionally requires ownership or a repository read/index grant. Viewers
cannot enqueue even if given an index grant. Owners manage grants only for same-tenant configured
identities. Worker boundaries recheck repository index grants. These mappings are development
configuration, not production identity proof or a persisted membership administration system.

Known remaining gates include queue dispatch/reconciliation under real broker faults, durable
membership changes, source viewing/encrypted storage, database-enforced snapshot immutability,
and convergence of independently submitted keys for the same SHA/configuration. Live provider
verification is separate from controlled Source fixtures; no new live source was fetched.
