"""Explicit per-repository capabilities; roles alone do not grant source access."""

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"


def upgrade():
    op.create_table(
        "repository_grants",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("repository_id", sa.String(36), nullable=False),
        sa.Column("principal_id", sa.String(36), nullable=False),
        sa.Column("capability", sa.String(20), nullable=False),
        sa.UniqueConstraint("organization_id", "id"),
        sa.UniqueConstraint("organization_id", "repository_id", "principal_id"),
        sa.ForeignKeyConstraint(
            ["organization_id", "repository_id"],
            ["repositories.organization_id", "repositories.id"],
        ),
    )
    op.create_index(
        "ix_repository_grants_organization_id", "repository_grants", ["organization_id"]
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE repository_grants ENABLE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE repository_grants FORCE ROW LEVEL SECURITY")
        op.execute(
            "CREATE POLICY tenant_scope ON repository_grants USING (organization_id=current_setting('app.tenant',true)) WITH CHECK (organization_id=current_setting('app.tenant',true))"
        )


def downgrade():
    op.drop_table("repository_grants")
