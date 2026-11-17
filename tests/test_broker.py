import os
from pathlib import Path
import subprocess
import sys
import time
from uuid import uuid4

import pytest
from sqlalchemy import select, update

from codeatlas.db import outbox, jobs, transaction
from codeatlas.main import TENANT_A
from codeatlas.queue import app, ingest, dispatch
from codeatlas.ingestion import run_job
from codeatlas.lifecycle import recover
from codeatlas.source import SourceError
from test_foundation import register, enqueue, ControlledSource


def test_publish_failure_keeps_outbox_pending(application, auth_a):
    client, engine = application
    job = enqueue(client, auth_a, register(client, auth_a)).json()["id"]

    def failure(*args):
        raise ConnectionError("broker down")

    with pytest.raises(ConnectionError):
        dispatch(engine, TENANT_A, failure)
    with transaction(engine, TENANT_A) as c:
        assert (
            c.execute(select(outbox.c.status).where(outbox.c.job_id == job)).scalar() == "pending"
        )


def test_transient_retry_limit(application, auth_a):
    client, engine = application
    job = enqueue(client, auth_a, register(client, auth_a)).json()["id"]

    class Broken(ControlledSource):
        def inventory(self, *args):
            raise SourceError("provider_transport_error")

    for _ in range(3):
        assert not run_job(engine, TENANT_A, job, Broken())
    row = client.get(f"/api/v1/index-jobs/{job}", headers=auth_a).json()
    assert row["attempts"] == 3 and row["status"] == "failed"
    assert not run_job(engine, TENANT_A, job, ControlledSource())


def test_transient_retry_recovery_and_outbox_republish(application, auth_a):
    client, engine = application
    repo = register(client, auth_a)
    job = enqueue(client, auth_a, repo, key="transient-recover").json()["id"]
    published = []
    assert dispatch(engine, TENANT_A, lambda t, j: published.append((t, j))) == 1
    assert published == [(TENANT_A, job)]
    # Still within 30s dispatch_after window: no premature duplicate dispatch.
    assert dispatch(engine, TENANT_A, lambda t, j: published.append((t, j))) == 0

    class FlakyOnce(ControlledSource):
        failed = False

        def inventory(self, *args):
            if not self.failed:
                self.failed = True
                raise SourceError("provider_transport_error")
            return super().inventory(*args)

    flaky = FlakyOnce()
    assert not run_job(engine, TENANT_A, job, flaky)
    mid = client.get(f"/api/v1/index-jobs/{job}", headers=auth_a).json()
    assert mid["status"] == "queued" and mid["attempts"] == 1
    # Simulate backoff elapsed so outbox republishes.
    with transaction(engine, TENANT_A) as c:
        c.execute(update(outbox).where(outbox.c.job_id == job).values(dispatch_after=0))
    assert dispatch(engine, TENANT_A, lambda t, j: published.append((t, j))) == 1
    assert len(published) == 2
    assert run_job(engine, TENANT_A, job, flaky)
    done = client.get(f"/api/v1/index-jobs/{job}", headers=auth_a).json()
    assert done["status"] == "succeeded" and done["attempts"] == 2


@pytest.mark.skipif(
    not os.getenv("CODEATLAS_TEST_BROKER"), reason="Real Redis broker not configured"
)
def test_real_broker_duplicate_delivery_and_worker_restart(application, auth_a):
    client, engine = application
    job = enqueue(client, auth_a, register(client, auth_a)).json()["id"]
    queue_name = "phase1_" + uuid4().hex
    app.conf.broker_url = os.environ["CODEATLAS_TEST_BROKER"]
    env = {
        **os.environ,
        "CODEATLAS_BROKER_URL": os.environ["CODEATLAS_TEST_BROKER"],
        "CODEATLAS_TEST_QUEUE": queue_name,
        "CODEATLAS_DEV_TOKEN_A": "a" * 32,
        "CODEATLAS_DEV_TOKEN_B": "b" * 32,
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "services/api"),
    }
    marker = Path(engine.url.database).parent / "worker-checkpoint"
    env["CODEATLAS_TEST_CRASH_MARKER"] = str(marker)
    script = str(Path(__file__).with_name("broker_worker.py"))

    def start():
        return subprocess.Popen(
            [sys.executable, script], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

    worker = start()
    try:
        # Force process death, then publish while no worker is available.
        time.sleep(1)
        worker.kill()
        worker.wait(timeout=10)

        def publish(t, j):
            return ingest.apply_async(args=[t, j], queue=queue_name, retry=False)

        assert dispatch(engine, TENANT_A, publish) == 1
        publish(TENANT_A, job)
        worker = start()
        checkpoint_deadline = time.monotonic() + 15
        while not marker.exists() and time.monotonic() < checkpoint_deadline:
            time.sleep(0.1)
        assert marker.exists(), "worker never reached pinned inventory checkpoint"
        worker.kill()
        worker.wait(timeout=10)
        pinned = client.get(f"/api/v1/index-jobs/{job}", headers=auth_a).json()
        assert pinned["status"] == "running" and pinned["commit_sha"] == "1" * 40
        # Controlled clock expiry after real process death; no need to wait a full lease.
        with transaction(engine, TENANT_A) as c:
            c.execute(update(jobs).where(jobs.c.id == job).values(lease_until=0))
        assert job in recover(engine, TENANT_A)
        publish(TENANT_A, job)
        worker = start()
        deadline = time.monotonic() + 25
        while time.monotonic() < deadline:
            result = client.get(f"/api/v1/index-jobs/{job}", headers=auth_a).json()
            if result["status"] == "succeeded":
                break
            time.sleep(0.2)
        assert result["status"] == "succeeded", result
        assert result["attempts"] == 2
    finally:
        if worker.poll() is None:
            worker.kill()
            worker.wait(timeout=10)
        with app.connection_for_write() as connection:
            connection.channel().queue_delete(queue_name)
