"""Enforce source ancestry independently of service authorization."""

from alembic import op

revision = "0007"
down_revision = "0006"


def upgrade():
    if op.get_bind().dialect.name == "postgresql":
        for table, name in (("index_jobs", "job"), ("repository_snapshots", "snapshot")):
            op.create_unique_constraint(
                f"uq_{name}_ancestry", table, ["organization_id", "repository_id", "id"]
            )
        for target, column in (("index_jobs", "job_id"), ("repository_snapshots", "snapshot_id")):
            op.create_foreign_key(
                f"fk_file_{column}_ancestry",
                "files",
                target,
                ["organization_id", "repository_id", column],
                ["organization_id", "repository_id", "id"],
            )
    else:
        op.execute(
            "CREATE TRIGGER source_ancestry BEFORE INSERT ON files WHEN NOT EXISTS (SELECT 1 FROM index_jobs j WHERE j.id=NEW.job_id AND j.organization_id=NEW.organization_id AND j.repository_id=NEW.repository_id) OR (NEW.snapshot_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM repository_snapshots s WHERE s.id=NEW.snapshot_id AND s.organization_id=NEW.organization_id AND s.repository_id=NEW.repository_id)) BEGIN SELECT RAISE(ABORT, 'source ancestry mismatch'); END"
        )


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        for column in ("job_id", "snapshot_id"):
            op.drop_constraint(f"fk_file_{column}_ancestry", "files", type_="foreignkey")
        op.drop_constraint("uq_snapshot_ancestry", "repository_snapshots", type_="unique")
        op.drop_constraint("uq_job_ancestry", "index_jobs", type_="unique")
    else:
        op.execute("DROP TRIGGER source_ancestry")
