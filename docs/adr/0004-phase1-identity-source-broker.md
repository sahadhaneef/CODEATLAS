# ADR 0004: persisted identity, encrypted source and at-least-once delivery

2026-10-30. Phase 1 remains in progress; prior Phase 0 evidence is unchanged.

Memberships persist server-provisioned external issuer/subject bindings, principals, tenants,
roles and active/revoked status. Repository grants remain persisted and independent of role.
Every read/worker boundary rechecks membership and repository access. Development identities
bootstrap only missing records; they never overwrite persisted revocation or role changes.
OIDC mode accepts RS256 bearer tokens using operator-pinned public keys selected by kid.
Issuer, audience, exp, iat and sub are required; lifetimes over one hour are rejected. Signed
organization_id is only a lookup selector: the independently provisioned membership must match
issuer/subject/tenant. Unverified claims never grant membership. No remote jku/discovery URL
or unsigned/HS256 token can select a verifier. Operators rotate pinned keys through configuration.
No browser login, refresh-token storage or automatic user enrollment is implemented. A real
issuer deployment check needs approved issuer/audience/keys and tokens, currently unavailable.
OIDC mode forbids all development tokens/mappings; development mode refuses production.

Source bytes use Fernet authenticated encryption with a key supplied separately through
CODEATLAS_SOURCE_KEY. The encrypted envelope binds tenant/repository/commit/path and includes
the original bytes; a SHA-256 verifies plaintext integrity on read. Only allowed UTF-8 text is
retained; excluded/binary/oversized entries keep metadata/reasons. No plaintext source enters
broker messages, logs, API inventory listings or generated contracts. Source viewer rechecks
authorization and requires a snapshot ID, with 500-line and 64-KiB response caps. There is no
index generation in Phase 1. Missing keys/content fail explicitly, not with fake empty success.

For this bounded foundation, encrypted source envelopes live in PostgreSQL alongside canonical
file records rather than an unimplemented object service. This keeps source commit and fenced
inventory persistence atomic and avoids plaintext on host disks. Database size/load are an
explicit limitation: migrate behind a SourceStore adapter to scoped encrypted object storage
before large-scale hosting. PostgreSQL triggers reject source/snapshot UPDATE/DELETE; ancestry
foreign keys bind files to the same tenant/repository's job and snapshot. SQLite fixtures use
equivalent insert/mutation triggers. Retention/deletion requires a controlled privileged workflow
before deployment; dropping immutability triggers casually is not a supported delete API.

Celery/Redis carries JSON job/tenant identifiers only. PostgreSQL outbox events are published
before being marked dispatched; failed publication leaves events pending. Publication followed
by database failure can duplicate delivery, which the job claim/fencing handles. Still-queued
jobs can be republished after 30 seconds, including dispatched events. Dispatchers lock event
rows on PostgreSQL with skip-locked; SQLite is test-only for this guarantee. Acks are late,
worker loss rejects messages, prefetch is one, broker IO has timeouts, and Redis visibility is
90 seconds. Database leases/fences, not broker state, govern writes. Expired jobs are reclaimed
only by reconciliation. A periodic dispatcher is required even after a broker redelivery was
acknowledged while an old lease remained active. Transient transport failures retry at most
three attempts with bounded exponential delay; policy/integrity errors are terminal.

Fault evidence distinguishes a real killed controlled Celery worker from simulated time: the
worker is killed after a pin is persisted; the test expires its lease in the database instead
of waiting 60 seconds. Recovery retains the pin. This is not proof against arbitrary host or
network failures. Docker image export later failed due read-only containerd storage; no reset
or destructive cleanup was attempted. Phase 1 cannot be marked verified on this evidence alone.

References consulted: https://pyjwt.readthedocs.io/en/stable/usage.html,
https://cryptography.io/en/latest/fernet/ and
https://docs.celeryq.dev/en/stable/userguide/tasks.html.
