"""At-least-once broker delivery. PostgreSQL remains job truth and fences all effects."""

import argparse
import os
import time

from celery import Celery
from sqlalchemy import select, update

from codeatlas.config import Settings
from codeatlas.db import jobs, outbox, make_engine, transaction
from codeatlas.ingestion import run_job
from codeatlas.lifecycle import recover
from codeatlas.source import GitHubSource

app = Celery(
    "codeatlas", broker=os.environ.get("CODEATLAS_BROKER_URL", "redis://127.0.0.1:56379/0")
)
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_connection_timeout=3,
    broker_transport_options={
        "visibility_timeout": 90,
        "socket_timeout": 3,
        "socket_connect_timeout": 3,
    },
    task_ignore_result=True,
    task_time_limit=1800,
    task_publish_retry=False,
)


@app.task(name="codeatlas.ingest")
def ingest(tenant, job_id):
    engine = make_engine(Settings.from_env().database_url)
    try:
        return run_job(engine, tenant, job_id, GitHubSource())
    finally:
        engine.dispose()


def dispatch(engine, tenant, publisher=None):
    recover(engine, tenant)
    publish = publisher or (lambda t, j: ingest.apply_async(args=[t, j], retry=False))
    count = 0
    with transaction(engine, tenant) as c:
        query = select(outbox.c.id, outbox.c.job_id).join(
            jobs,
            (jobs.c.id == outbox.c.job_id) & (jobs.c.organization_id == outbox.c.organization_id),
        )
        query = (
            query.where(
                outbox.c.organization_id == tenant,
                jobs.c.status == "queued",
                outbox.c.dispatch_after <= int(time.time()),
            )
            .order_by(outbox.c.created_at)
            .limit(10)
        )
        if engine.dialect.name == "postgresql":
            query = query.with_for_update(skip_locked=True, of=outbox)
        for event in c.execute(query).mappings():
            publish(tenant, event["job_id"])
            c.execute(
                update(outbox)
                .where(outbox.c.id == event["id"], outbox.c.organization_id == tenant)
                .values(status="dispatched", dispatch_after=int(time.time()) + 30)
            )
            count += 1
    return count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant", required=True)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    engine = make_engine(Settings.from_env().database_url)
    while True:
        try:
            dispatch(engine, args.tenant)
        except Exception:
            if args.once:
                raise
            # Keep durable events pending; never log URLs, credentials or source payloads.
            print("Dispatch unavailable; retrying durable outbox in 2 seconds", flush=True)
        if args.once:
            return
        time.sleep(2)


if __name__ == "__main__":
    main()
