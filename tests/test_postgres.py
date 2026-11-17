"""Real RLS checks; never substitute SQLite for this guarantee."""

import os
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from codeatlas.db import make_engine, repositories, transaction
from codeatlas.main import TENANT_A, TENANT_B
from codeatlas.db import snapshots


@pytest.mark.skipif(
    not os.getenv("CODEATLAS_TEST_POSTGRES"), reason="Real PostgreSQL URL not configured"
)
def test_rls_and_pool_reuse(monkeypatch):
    url = os.environ["CODEATLAS_TEST_POSTGRES"]
    monkeypatch.setenv("CODEATLAS_DATABASE_URL", url)
    command.upgrade(Config("alembic.ini"), "head")
    engine = make_engine(url)
    role = "fixture_" + uuid4().hex
    repo_id = str(uuid4())
    with engine.begin() as c:
        c.execute(text(f"CREATE ROLE {role} NOLOGIN NOSUPERUSER NOBYPASSRLS"))
        c.execute(text(f"GRANT USAGE ON SCHEMA public TO {role}"))
        c.execute(text(f"GRANT SELECT, INSERT ON repositories TO {role}"))
    try:
        with transaction(engine, TENANT_A) as c:
            c.execute(text(f"SET LOCAL ROLE {role}"))
            c.execute(
                repositories.insert().values(
                    id=repo_id,
                    organization_id=TENANT_A,
                    remote_url="https://github.com/a/b",
                    owner_id=TENANT_A,
                    requested_ref="main",
                )
            )
        with transaction(engine, TENANT_B) as c:
            c.execute(text(f"SET LOCAL ROLE {role}"))
            assert (
                c.execute(text("SELECT id FROM repositories WHERE id=:id"), {"id": repo_id}).first()
                is None
            )
        with pytest.raises(DBAPIError):
            with transaction(engine, TENANT_B) as c:
                c.execute(text(f"SET LOCAL ROLE {role}"))
                c.execute(
                    repositories.insert().values(
                        id=str(uuid4()),
                        organization_id=TENANT_A,
                        remote_url="https://github.com/a/b",
                        owner_id=TENANT_A,
                        requested_ref="main",
                    )
                )
        with engine.begin() as c:
            c.execute(text(f"SET LOCAL ROLE {role}"))
            assert (
                c.execute(text("SELECT id FROM repositories WHERE id=:id"), {"id": repo_id}).first()
                is None
            )
        with transaction(engine, TENANT_A) as c:
            c.execute(text(f"SET LOCAL ROLE {role}"))
            assert (
                c.execute(
                    text("SELECT id FROM repositories WHERE id=:id"), {"id": repo_id}
                ).scalar()
                == repo_id
            )
    finally:
        with engine.begin() as c:
            c.execute(text("DELETE FROM repositories WHERE id=:id"), {"id": repo_id})
            c.execute(text(f"DROP OWNED BY {role}"))
            c.execute(text(f"DROP ROLE {role}"))
        engine.dispose()


@pytest.mark.skipif(
    not os.getenv("CODEATLAS_TEST_POSTGRES"), reason="Real PostgreSQL URL not configured"
)
def test_postgres_snapshot_mutation_rejected(monkeypatch):
    monkeypatch.setenv("CODEATLAS_DATABASE_URL", os.environ["CODEATLAS_TEST_POSTGRES"])
    command.upgrade(Config("alembic.ini"), "head")
    engine = make_engine(os.environ["CODEATLAS_TEST_POSTGRES"])
    try:
        with engine.connect() as c:
            outer = c.begin()
            repo = str(uuid4())
            snapshot = str(uuid4())
            c.execute(
                repositories.insert().values(
                    id=repo,
                    organization_id=TENANT_A,
                    remote_url="https://github.com/a/b",
                    owner_id=TENANT_A,
                    requested_ref="main",
                )
            )
            c.execute(
                snapshots.insert().values(
                    id=snapshot,
                    organization_id=TENANT_A,
                    repository_id=repo,
                    commit_sha="a" * 40,
                    tree_sha="b" * 40,
                    requested_ref="main",
                )
            )
            with pytest.raises(DBAPIError):
                with c.begin_nested():
                    c.execute(
                        snapshots.update()
                        .where(snapshots.c.id == snapshot)
                        .values(commit_sha="c" * 40)
                    )
            outer.rollback()
    finally:
        engine.dispose()
