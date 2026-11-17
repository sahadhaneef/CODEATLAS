from contextlib import contextmanager

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKeyConstraint,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
    create_engine,
    event,
    func,
    text,
    Text,
)

metadata = MetaData()


def tenant_table(name, *columns, constraints=()):
    return Table(
        name,
        metadata,
        Column("id", String(36), primary_key=True),
        Column("organization_id", String(36), nullable=False, index=True),
        Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
        *columns,
        UniqueConstraint("organization_id", "id"),
        *constraints,
    )


memberships = tenant_table(
    "memberships",
    Column("principal_id", String(36), nullable=False),
    Column("issuer", String(512), nullable=False),
    Column("subject", String(256), nullable=False),
    Column("role", String(20), nullable=False),
    Column("status", String(20), nullable=False),
    constraints=(
        UniqueConstraint("issuer", "subject"),
        UniqueConstraint("organization_id", "principal_id"),
    ),
)


repositories = tenant_table(
    "repositories",
    Column("remote_url", String(512), nullable=False),
    Column("requested_ref", String(256), nullable=False),
    Column("owner_id", String(36), nullable=False),
)
jobs = tenant_table(
    "index_jobs",
    Column("repository_id", String(36), nullable=False),
    Column("requested_by", String(36), nullable=False),
    Column("requested_ref", String(256), nullable=False),
    Column("commit_sha", String(40)),
    Column("tree_sha", String(40)),
    Column("status", String(32), nullable=False),
    Column("stage", String(32), nullable=False),
    Column("error_code", String(64)),
    Column("idempotency_key", String(128), nullable=False),
    Column("request_digest", String(64), nullable=False),
    Column("attempts", Integer, nullable=False, server_default="0"),
    Column("lease_epoch", Integer, nullable=False, server_default="0"),
    Column("lease_until", Integer, nullable=False, server_default="0"),
    constraints=(
        ForeignKeyConstraint(
            ["organization_id", "repository_id"],
            ["repositories.organization_id", "repositories.id"],
        ),
        UniqueConstraint("organization_id", "requested_by", "idempotency_key"),
        UniqueConstraint("organization_id", "repository_id", "id", name="uq_job_ancestry"),
    ),
)
files = tenant_table(
    "files",
    Column("repository_id", String(36), nullable=False),
    Column("job_id", String(36), nullable=False),
    Column("path", String(2048), nullable=False),
    Column("blob_sha", String(40), nullable=False),
    Column("byte_count", Integer, nullable=False),
    Column("inventory_status", String(32), nullable=False),
    Column("exclusion_reason", String(128)),
    Column("snapshot_id", String(36)),
    Column("source_ciphertext", Text),
    Column("source_hash", String(64)),
    constraints=(
        ForeignKeyConstraint(
            ["organization_id", "job_id"], ["index_jobs.organization_id", "index_jobs.id"]
        ),
        ForeignKeyConstraint(
            ["organization_id", "repository_id"],
            ["repositories.organization_id", "repositories.id"],
        ),
        UniqueConstraint("organization_id", "job_id", "path"),
        ForeignKeyConstraint(
            ["organization_id", "repository_id", "job_id"],
            ["index_jobs.organization_id", "index_jobs.repository_id", "index_jobs.id"],
            name="fk_file_job_id_ancestry",
        ),
        ForeignKeyConstraint(
            ["organization_id", "repository_id", "snapshot_id"],
            [
                "repository_snapshots.organization_id",
                "repository_snapshots.repository_id",
                "repository_snapshots.id",
            ],
            name="fk_file_snapshot_id_ancestry",
        ),
    ),
)

outbox = tenant_table(
    "outbox_events",
    Column("job_id", String(36), nullable=False),
    Column("status", String(20), nullable=False, server_default="pending"),
    Column("dispatch_after", Integer, nullable=False, server_default="0"),
    constraints=(
        ForeignKeyConstraint(
            ["organization_id", "job_id"], ["index_jobs.organization_id", "index_jobs.id"]
        ),
        UniqueConstraint("organization_id", "job_id"),
    ),
)
snapshots = tenant_table(
    "repository_snapshots",
    Column("repository_id", String(36), nullable=False),
    Column("commit_sha", String(40), nullable=False),
    Column("tree_sha", String(40), nullable=False),
    Column("requested_ref", String(256), nullable=False),
    constraints=(
        ForeignKeyConstraint(
            ["organization_id", "repository_id"],
            ["repositories.organization_id", "repositories.id"],
        ),
        UniqueConstraint("organization_id", "repository_id", "commit_sha"),
        UniqueConstraint("organization_id", "repository_id", "id", name="uq_snapshot_ancestry"),
    ),
)

grants = tenant_table(
    "repository_grants",
    Column("repository_id", String(36), nullable=False),
    Column("principal_id", String(36), nullable=False),
    Column("capability", String(20), nullable=False),
    constraints=(
        ForeignKeyConstraint(
            ["organization_id", "repository_id"],
            ["repositories.organization_id", "repositories.id"],
        ),
        UniqueConstraint("organization_id", "repository_id", "principal_id"),
    ),
)


def make_engine(url):
    engine = create_engine(url, pool_pre_ping=True)
    if engine.dialect.name == "sqlite":

        @event.listens_for(engine, "connect")
        def foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")

    return engine


@contextmanager
def transaction(engine, tenant):
    with engine.begin() as connection:
        if engine.dialect.name == "postgresql":
            connection.execute(
                text("SELECT set_config('app.tenant', :tenant, true)"), {"tenant": tenant}
            )
        yield connection
