"""Persist server-provisioned tenant membership and external subject binding."""

from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"


def upgrade():
    op.create_table(
        "memberships",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("principal_id", sa.String(36), nullable=False),
        sa.Column("issuer", sa.String(512), nullable=False),
        sa.Column("subject", sa.String(256), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.UniqueConstraint("organization_id", "id"),
        sa.UniqueConstraint("issuer", "subject"),
        sa.UniqueConstraint("organization_id", "principal_id"),
    )
    op.create_index("ix_memberships_organization_id", "memberships", ["organization_id"])
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE memberships ENABLE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE memberships FORCE ROW LEVEL SECURITY")
        op.execute(
            "CREATE POLICY tenant_scope ON memberships USING (organization_id=current_setting('app.tenant',true)) WITH CHECK (organization_id=current_setting('app.tenant',true))"
        )


def downgrade():
    op.drop_table("memberships")
