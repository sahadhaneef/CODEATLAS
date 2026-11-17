"""Initial canonical inventory schema; RLS enabled and forced for all tenant tables."""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None


def upgrade():
    op.create_table(
        "repositories",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("remote_url", sa.String(512), nullable=False),
        sa.Column("requested_ref", sa.String(256), nullable=False),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.UniqueConstraint("organization_id", "id"),
    )
    op.create_table(
        "index_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("repository_id", sa.String(36), nullable=False),
        sa.Column("requested_by", sa.String(36), nullable=False),
        sa.Column("requested_ref", sa.String(256), nullable=False),
        sa.Column("commit_sha", sa.String(40)),
        sa.Column("tree_sha", sa.String(40)),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("stage", sa.String(32), nullable=False),
        sa.Column("error_code", sa.String(64)),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("request_digest", sa.String(64), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.UniqueConstraint("organization_id", "id"),
        sa.UniqueConstraint("organization_id", "requested_by", "idempotency_key"),
        sa.ForeignKeyConstraint(
            ["organization_id", "repository_id"],
            ["repositories.organization_id", "repositories.id"],
        ),
    )
    op.create_table(
        "files",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("repository_id", sa.String(36), nullable=False),
        sa.Column("job_id", sa.String(36), nullable=False),
        sa.Column("path", sa.String(2048), nullable=False),
        sa.Column("blob_sha", sa.String(40), nullable=False),
        sa.Column("byte_count", sa.Integer(), nullable=False),
        sa.Column("inventory_status", sa.String(32), nullable=False),
        sa.Column("exclusion_reason", sa.String(128)),
        sa.UniqueConstraint("organization_id", "id"),
        sa.UniqueConstraint("organization_id", "job_id", "path"),
        sa.ForeignKeyConstraint(
            ["organization_id", "repository_id"],
            ["repositories.organization_id", "repositories.id"],
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "job_id"], ["index_jobs.organization_id", "index_jobs.id"]
        ),
    )
    for table in ("repositories", "index_jobs", "files"):
        op.create_index(f"ix_{table}_organization_id", table, ["organization_id"])
        if op.get_bind().dialect.name == "postgresql":
            op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
            op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
            op.execute(
                f"CREATE POLICY tenant_scope ON {table} USING "
                "(organization_id = current_setting('app.tenant', true)) "
                "WITH CHECK (organization_id = current_setting('app.tenant', true))"
            )


def downgrade():
    for table in ("files", "index_jobs", "repositories"):
        op.drop_table(table)
