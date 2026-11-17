"""Encrypted immutable source envelopes and snapshot associations."""

from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"


def upgrade():
    for column in (
        sa.Column("snapshot_id", sa.String(36)),
        sa.Column("source_ciphertext", sa.Text()),
        sa.Column("source_hash", sa.String(64)),
    ):
        op.add_column("files", column)
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            "CREATE FUNCTION reject_source_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'immutable source record'; END $$"
        )
        for table in ("files", "repository_snapshots"):
            op.execute(
                f"CREATE TRIGGER immutable_source BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION reject_source_mutation()"
            )
    else:
        for table in ("files", "repository_snapshots"):
            for operation in ("UPDATE", "DELETE"):
                op.execute(
                    f"CREATE TRIGGER immutable_{table}_{operation} BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT, 'immutable source record'); END"
                )


def downgrade():
    for table in ("files", "repository_snapshots"):
        if op.get_bind().dialect.name == "postgresql":
            op.execute(f"DROP TRIGGER immutable_source ON {table}")
        else:
            for operation in ("UPDATE", "DELETE"):
                op.execute(f"DROP TRIGGER immutable_{table}_{operation}")
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP FUNCTION reject_source_mutation()")
    for name in ("source_hash", "source_ciphertext", "snapshot_id"):
        op.drop_column("files", name)
