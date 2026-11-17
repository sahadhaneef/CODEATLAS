from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"


def upgrade():
    op.add_column(
        "outbox_events",
        sa.Column("dispatch_after", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade():
    op.drop_column("outbox_events", "dispatch_after")
