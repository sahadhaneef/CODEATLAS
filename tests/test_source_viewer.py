from uuid import uuid4

import pytest
from sqlalchemy import delete, select, update
from sqlalchemy.exc import DBAPIError

from codeatlas.db import files, memberships, snapshots, transaction
from codeatlas.ingestion import run_job
from codeatlas.main import TENANT_A
from test_foundation import ControlledSource, register, enqueue


def test_encrypted_immutable_scoped_source(application, auth_a, auth_b, monkeypatch):
    client, engine = application
    repo = register(client, auth_a)
    job = enqueue(client, auth_a, repo).json()["id"]
    source = ControlledSource()
    source.contents["wide.txt"] = ("x" * 700 + "\n").encode() * 120
    assert run_job(engine, TENANT_A, job, source)
    listing = client.get(f"/api/v1/index-jobs/{job}/files", headers=auth_a).json()
    row = next(r for r in listing if r["path"] == "hello.py")
    excluded_row = next(r for r in listing if r["path"] == ".env")
    wide_row = next(r for r in listing if r["path"] == "wide.txt")
    assert "source_ciphertext" not in row
    url = f"/api/v1/files/{row['id']}/content?snapshot_id={row['snapshot_id']}"
    result = client.get(url, headers=auth_a)
    assert result.status_code == 200 and "def hello" in result.json()["content"]
    assert client.get(url, headers=auth_b).status_code == 404
    assert (
        client.get(
            f"/api/v1/files/{row['id']}/content?snapshot_id={uuid4()}", headers=auth_a
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/v1/files/{excluded_row['id']}/content?snapshot_id={excluded_row['snapshot_id']}",
            headers=auth_a,
        ).status_code
        == 409
    )
    assert (
        client.get(
            f"/api/v1/files/{wide_row['id']}/content?snapshot_id={wide_row['snapshot_id']}&start_line=1&end_line=120",
            headers=auth_a,
        ).status_code
        == 422
    )
    assert client.get(url + "&end_line=501", headers=auth_a).status_code == 422
    assert client.get(url + "&start_line=10000&end_line=10010", headers=auth_a).status_code == 422
    with monkeypatch.context() as m:
        m.delenv("CODEATLAS_SOURCE_KEY", raising=False)
        assert client.get(url, headers=auth_a).status_code == 503
    with transaction(engine, TENANT_A) as c:
        encrypted = c.execute(
            select(files.c.source_ciphertext).where(files.c.id == row["id"])
        ).scalar()
        assert "def hello" not in encrypted
    with pytest.raises(DBAPIError):
        with transaction(engine, TENANT_A) as c:
            c.execute(update(files).where(files.c.id == row["id"]).values(path="changed.py"))
    with pytest.raises(DBAPIError):
        with transaction(engine, TENANT_A) as c:
            c.execute(delete(files).where(files.c.id == row["id"]))
    with pytest.raises(DBAPIError):
        with transaction(engine, TENANT_A) as c:
            c.execute(delete(snapshots).where(snapshots.c.id == row["snapshot_id"]))
    with transaction(engine, TENANT_A) as c:
        c.execute(
            update(memberships)
            .where(memberships.c.principal_id == TENANT_A)
            .values(status="revoked")
        )
    assert client.get(url, headers=auth_a).status_code == 401
