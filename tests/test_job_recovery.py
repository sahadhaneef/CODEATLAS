from sqlalchemy import select, update

from codeatlas.db import jobs, outbox, transaction
from codeatlas.ingestion import run_job
from codeatlas.lifecycle import recover
from codeatlas.main import TENANT_A
from test_foundation import ControlledSource, enqueue, register


def test_outbox_pin_survives_crash_and_branch_move(application, auth_a):
    client, engine = application
    repo = register(client, auth_a)
    job_id = enqueue(client, auth_a, repo).json()["id"]
    with transaction(engine, TENANT_A) as c:
        assert (
            c.execute(select(outbox.c.status).where(outbox.c.job_id == job_id)).scalar()
            == "pending"
        )

    class Crash(ControlledSource):
        def inventory(self, *args):
            raise KeyboardInterrupt("simulated worker death after pin")

    import pytest

    with pytest.raises(KeyboardInterrupt):
        run_job(engine, TENANT_A, job_id, Crash())
    with transaction(engine, TENANT_A) as c:
        c.execute(update(jobs).where(jobs.c.id == job_id).values(lease_until=0))
    assert recover(engine, TENANT_A) == [job_id]

    class Resumed(ControlledSource):
        def resolve(self, *args):
            raise AssertionError("must not resolve a moving branch again")

    assert run_job(engine, TENANT_A, job_id, Resumed())
    assert not run_job(engine, TENANT_A, job_id, Resumed())
    result = client.get(f"/api/v1/repositories/{repo}/snapshots", headers=auth_a).json()
    assert len(result) == 1 and result[0]["commit_sha"] == "1" * 40


def test_cancellation_fences_inflight_worker(application, auth_a, auth_b):
    client, engine = application
    repo = register(client, auth_a)
    job_id = enqueue(client, auth_a, repo).json()["id"]
    assert client.post(f"/api/v1/index-jobs/{job_id}/cancel", headers=auth_b).status_code == 404

    class Cancelled(ControlledSource):
        def inventory(self, *args):
            assert (
                client.post(f"/api/v1/index-jobs/{job_id}/cancel", headers=auth_a).json()["status"]
                == "cancelled"
            )
            return super().inventory(*args)

    assert not run_job(engine, TENANT_A, job_id, Cancelled())
    assert (
        client.get(f"/api/v1/index-jobs/{job_id}", headers=auth_a).json()["status"] == "cancelled"
    )
    assert client.get(f"/api/v1/index-jobs/{job_id}/files", headers=auth_a).json() == []
    assert recover(engine, TENANT_A) == []


def test_cancellation_races_before_claim_and_during_blob(application, auth_a):
    client, engine = application
    repo = register(client, auth_a)

    # 1. Cancel before worker claims queued job.
    queued_job = enqueue(client, auth_a, repo, key="cancel-queued").json()["id"]
    assert (
        client.post(f"/api/v1/index-jobs/{queued_job}/cancel", headers=auth_a).json()["status"]
        == "cancelled"
    )
    assert not run_job(engine, TENANT_A, queued_job, ControlledSource())
    assert client.get(f"/api/v1/index-jobs/{queued_job}/files", headers=auth_a).json() == []

    # 2. Cancel mid-blob-read after inventory completed.
    blob_job = enqueue(client, auth_a, repo, key="cancel-blob").json()["id"]

    class CancelDuringBlob(ControlledSource):
        def blob(self, *args):
            assert (
                client.post(f"/api/v1/index-jobs/{blob_job}/cancel", headers=auth_a).json()[
                    "status"
                ]
                == "cancelled"
            )
            return super().blob(*args)

    assert not run_job(engine, TENANT_A, blob_job, CancelDuringBlob())
    assert (
        client.get(f"/api/v1/index-jobs/{blob_job}", headers=auth_a).json()["status"] == "cancelled"
    )
    assert client.get(f"/api/v1/index-jobs/{blob_job}/files", headers=auth_a).json() == []
    assert client.get(f"/api/v1/repositories/{repo}/snapshots", headers=auth_a).json() == []


def test_expired_worker_cannot_overwrite_replacement(application, auth_a):
    client, engine = application
    repo = register(client, auth_a)
    job_id = enqueue(client, auth_a, repo).json()["id"]

    class Stale(ControlledSource):
        def inventory(self, *args):
            with transaction(engine, TENANT_A) as c:
                c.execute(update(jobs).where(jobs.c.id == job_id).values(lease_until=0))
            recover(engine, TENANT_A)
            assert run_job(engine, TENANT_A, job_id, ControlledSource())
            return super().inventory(*args)

    assert not run_job(engine, TENANT_A, job_id, Stale())
    assert (
        client.get(f"/api/v1/index-jobs/{job_id}", headers=auth_a).json()["status"] == "succeeded"
    )


def test_ingestion_never_executes_source_and_reuses_snapshot(application, auth_a, monkeypatch):
    import subprocess

    client, engine = application
    repo = register(client, auth_a)

    def forbidden(*args, **kwargs):
        raise AssertionError("ingestion must never spawn a repository command")

    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    for key in ("one", "two"):
        source = ControlledSource()
        source.contents["hello.py"] = b"raise RuntimeError('imported code executed')\n"
        job_id = enqueue(client, auth_a, repo, key=key).json()["id"]
        assert run_job(engine, TENANT_A, job_id, source)
    assert len(client.get(f"/api/v1/repositories/{repo}/snapshots", headers=auth_a).json()) == 1


def test_concurrent_worker_claim_is_exclusive(application, auth_a):
    client, engine = application
    repo = register(client, auth_a)
    job_id = enqueue(client, auth_a, repo, key="exclusive-claim").json()["id"]

    # First worker claims successfully
    source1 = ControlledSource()
    source2 = ControlledSource()
    assert run_job(engine, TENANT_A, job_id, source1)
    # Second worker trying to claim the same job returns False
    assert not run_job(engine, TENANT_A, job_id, source2)


def test_recovery_fences_exhausted_attempts(application, auth_a):
    client, engine = application
    repo = register(client, auth_a)
    job_id = enqueue(client, auth_a, repo, key="attempt-exhaustion").json()["id"]

    # Manually simulate 3 failed attempts that expired leases
    with transaction(engine, TENANT_A) as c:
        c.execute(
            update(jobs)
            .where(jobs.c.id == job_id)
            .values(status="running", attempts=3, lease_until=0)
        )
    # recover() should transition status="running" -> status="queued" -> status="failed", error_code="attempt_limit"
    requeued = recover(engine, TENANT_A)
    assert job_id not in requeued
    record = client.get(f"/api/v1/index-jobs/{job_id}", headers=auth_a).json()
    assert record["status"] == "failed"
    assert record["error_code"] == "attempt_limit"


def test_cancelled_job_not_dispatched(application, auth_a):
    from codeatlas.queue import dispatch

    client, engine = application
    repo = register(client, auth_a)
    job_id = enqueue(client, auth_a, repo, key="cancel-before-dispatch").json()["id"]

    # Cancel while still queued
    assert (
        client.post(f"/api/v1/index-jobs/{job_id}/cancel", headers=auth_a).json()["status"]
        == "cancelled"
    )

    published = []
    assert dispatch(engine, TENANT_A, lambda t, j: published.append((t, j))) == 0
    assert published == []
