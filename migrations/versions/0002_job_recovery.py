"""Durable delivery, immutable snapshot records and fenced job leases."""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"


def upgrade():
    op.add_column(
        "index_jobs", sa.Column("lease_epoch", sa.Integer(), nullable=False, server_default="0")
    )
    op.add_column(
        "index_jobs", sa.Column("lease_until", sa.Integer(), nullable=False, server_default="0")
    )
    for name, columns, constraints in (
        (
            "outbox_events",
            [
                sa.Column("job_id", sa.String(36), nullable=False),
                sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
            ],
            [
                sa.ForeignKeyConstraint(
                    ["organization_id", "job_id"], ["index_jobs.organization_id", "index_jobs.id"]
                ),
                sa.UniqueConstraint("organization_id", "job_id"),
            ],
        ),
        (
            "repository_snapshots",
            [
                sa.Column("repository_id", sa.String(36), nullable=False),
                sa.Column("commit_sha", sa.String(40), nullable=False),
                sa.Column("tree_sha", sa.String(40), nullable=False),
                sa.Column("requested_ref", sa.String(256), nullable=False),
            ],
            [
                sa.ForeignKeyConstraint(
                    ["organization_id", "repository_id"],
                    ["repositories.organization_id", "repositories.id"],
                ),
                sa.UniqueConstraint("organization_id", "repository_id", "commit_sha"),
            ],
        ),
    ):
        op.create_table(
            name,
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("organization_id", sa.String(36), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            *columns,
            sa.UniqueConstraint("organization_id", "id"),
            *constraints,
        )
        op.create_index(f"ix_{name}_organization_id", name, ["organization_id"])
        if op.get_bind().dialect.name == "postgresql":
            op.execute(f"ALTER TABLE {name} ENABLE ROW LEVEL SECURITY")
            op.execute(f"ALTER TABLE {name} FORCE ROW LEVEL SECURITY")
            op.execute(
                f"CREATE POLICY tenant_scope ON {name} USING (organization_id=current_setting('app.tenant',true)) WITH CHECK (organization_id=current_setting('app.tenant',true))"
            )
    # Existing queued/running jobs must also be recoverable through the outbox.
    op.execute(
        "INSERT INTO outbox_events (id,organization_id,job_id,status) SELECT id,organization_id,id,'pending' FROM index_jobs WHERE status IN ('queued','running')"
    )


def downgrade():
    op.drop_table("repository_snapshots")
    op.drop_table("outbox_events")
    op.drop_column("index_jobs", "lease_until")
    op.drop_column("index_jobs", "lease_epoch")
