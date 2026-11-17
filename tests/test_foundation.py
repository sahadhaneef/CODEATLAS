import hashlib
import socket

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import select

from codeatlas.config import Settings
from codeatlas.db import jobs, transaction
from codeatlas.ingestion import run_job
from codeatlas.main import TENANT_A
from codeatlas.source import (
    Entry,
    GitHubSource,
    PinnedHTTPS,
    SourceError,
    canonical_remote,
    classify,
)


class ControlledSource:
    """First-party tiny repository object fixture; no production URL exceptions."""

    commit = "1" * 40
    tree = "2" * 40

    def __init__(self):
        self.contents = {
            "hello.py": b"def hello():\r\n    return 'hello'\r\n",
            "README.md": b"# Controlled first-party fixture\n",
            ".env": b"never fetch me",
            "link.py": b"../../secret",
            "binary.ts": b"\0\xff",
            "large.py": b"",
            "unknown.xyz": b"unsupported",
        }
        self.requested = []

    def resolve(self, remote, ref):
        return self.commit, self.tree

    def inventory(self, remote, commit, tree):
        assert (commit, tree) == ("1" * 40, "2" * 40)
        return [
            Entry(
                path,
                hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest(),
                1048577 if path == "large.py" else len(data),
                "120000" if path == "link.py" else "100644",
            )
            for path, data in self.contents.items()
        ]

    def blob(self, remote, entry):
        self.requested.append(entry.path)
        return self.contents[entry.path]


def register(client, auth):
    response = client.post(
        "/api/v1/repositories",
        headers=auth,
        json={
            "remote_url": "https://github.com/codeatlas/controlled",
            "requested_ref": "main",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def enqueue(client, auth, repo, key="fixture-key", ref="main"):
    return client.post(
        f"/api/v1/repositories/{repo}/index",
        headers={**auth, "Idempotency-Key": key},
        json={"ref": ref},
    )


def test_vertical_slice_and_two_tenants(application, auth_a, auth_b):
    client, engine = application
    assert client.get("/api/v1/health").json()["execution"] is False
    assert client.get("/api/v1/ready").status_code == 200
    assert client.get("/api/v1/repositories").status_code == 401
    repo = register(client, auth_a)
    assert client.get("/api/v1/repositories", headers=auth_b).json() == []
    assert enqueue(client, auth_b, repo).status_code == 404
    response = enqueue(client, auth_a, repo)
    assert response.status_code == 202
    job_id = response.json()["id"]
    assert enqueue(client, auth_a, repo).json()["id"] == job_id
    assert enqueue(client, auth_a, repo, ref="other").status_code == 409
    assert client.get(f"/api/v1/index-jobs/{job_id}", headers=auth_b).status_code == 404
    source = ControlledSource()
    assert run_job(engine, TENANT_A, job_id, source)
    source.commit = "3" * 40  # Moving branch cannot alter the already pinned inventory.
    assert not run_job(engine, TENANT_A, job_id, source)
    job = client.get(f"/api/v1/index-jobs/{job_id}", headers=auth_a).json()
    assert job["commit_sha"] == "1" * 40
    assert job["stage"] == "inventory_complete" and job["status"] == "succeeded"
    records = client.get(f"/api/v1/index-jobs/{job_id}/files", headers=auth_a).json()
    statuses = {r["path"]: r["inventory_status"] for r in records}
    assert statuses == {
        "hello.py": "inventoried",
        "README.md": "inventoried",
        ".env": "excluded",
        "link.py": "excluded",
        "binary.ts": "binary",
        "large.py": "oversized",
        "unknown.xyz": "unsupported",
    }
    assert set(source.requested) == {"hello.py", "README.md", "binary.ts"}
    assert client.get(f"/api/v1/index-jobs/{job_id}/files", headers=auth_b).status_code == 404
    assert len(client.get(f"/api/v1/index-jobs/{job_id}/files?limit=2", headers=auth_a).json()) == 2


@pytest.mark.parametrize(
    "url",
    [
        "file:///tmp/repo",
        "https://localhost/a/b",
        "https://127.0.0.1/a/b",
        "ssh://github.com/a/b",
        "git://github.com/a/b",
        "https://github.com:443/a/b",
        "https://token@github.com/a/b",
        "https://github.com/a/b?q=1",
        "https://github.com/a/..",
        "https://github.com/a/b#fragment",
        "https://github.com/a/b/extra",
        "https://github.com.evil.com/a/b",
        "https://github.com/a/%2e%2e",
    ],
)
def test_url_rejection(url):
    with pytest.raises(ValueError):
        canonical_remote(url)


@pytest.mark.parametrize("path", ["../a.py", "/a.py", "a\\b.py", "C:/a.py", "a/../../b.py"])
def test_path_rejection(path):
    with pytest.raises(SourceError):
        classify(Entry(path, "1" * 40, 2, "100644"))


def test_failed_fetch_is_explicit(application, auth_a):
    client, engine = application
    repo = register(client, auth_a)
    job_id = enqueue(client, auth_a, repo).json()["id"]

    class BrokenSource(ControlledSource):
        def inventory(self, *args):
            raise SourceError("truncated_tree")

    assert not run_job(engine, TENANT_A, job_id, BrokenSource())
    result = client.get(f"/api/v1/index-jobs/{job_id}", headers=auth_a).json()
    assert result["status"] == "failed" and result["error_code"] == "truncated_tree"
    assert client.get(f"/api/v1/index-jobs/{job_id}/files", headers=auth_a).json() == []


def test_dns_private_and_rebinding_boundary(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *a, **kw: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443)),
        ],
    )
    with pytest.raises(SourceError, match="denied_destination"):
        PinnedHTTPS("api.github.com").connect()


def test_redirect_is_not_followed(monkeypatch):
    class Connection:
        def __init__(self, *args, **kwargs):
            pass

        def request(self, *args, **kwargs):
            pass

        def getresponse(self):
            return type("Response", (), {"status": 302})()

        def close(self):
            pass

    monkeypatch.setattr("codeatlas.source.PinnedHTTPS", Connection)
    with pytest.raises(SourceError, match="provider_unavailable_or_denied"):
        GitHubSource().resolve("https://github.com/a/b", "main")


def test_production_refused():
    with pytest.raises(ValueError, match="production startup refused"):
        Settings("sqlite://", "a" * 32, "b" * 32, "production").validate()


def test_migration_round_trip(application):
    client, engine = application
    command.downgrade(Config("alembic.ini"), "base")
    assert client.get("/api/v1/ready").status_code == 503
    command.upgrade(Config("alembic.ini"), "head")
    assert client.get("/api/v1/ready").status_code == 200


def test_worker_cannot_claim_other_tenant(application, auth_a):
    client, engine = application
    job_id = enqueue(client, auth_a, register(client, auth_a)).json()["id"]
    assert not run_job(engine, "00000000-0000-0000-0000-000000000002", job_id, ControlledSource())
    with transaction(engine, TENANT_A) as connection:
        assert (
            connection.execute(select(jobs.c.status).where(jobs.c.id == job_id)).scalar()
            == "queued"
        )
