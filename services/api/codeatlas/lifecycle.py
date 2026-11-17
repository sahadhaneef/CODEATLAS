"""Database delivery and recovery primitives, independent of transport and web frameworks."""

import time

from sqlalchemy import or_, select, update

from codeatlas.db import jobs, outbox, transaction


def recover(engine, tenant):
    """Fence expired workers before requeueing. Never repin a recorded commit."""
    with transaction(engine, tenant) as c:
        c.execute(
            update(jobs)
            .where(
                jobs.c.organization_id == tenant,
                jobs.c.status == "running",
                jobs.c.lease_until < int(time.time()),
            )
            .values(status="queued", lease_epoch=jobs.c.lease_epoch + 1, lease_until=0)
        )
        c.execute(
            update(jobs)
            .where(
                jobs.c.organization_id == tenant, jobs.c.status == "queued", jobs.c.attempts >= 3
            )
            .values(status="failed", error_code="attempt_limit")
        )
        return list(
            c.execute(
                select(jobs.c.id)
                .join(
                    outbox,
                    (outbox.c.job_id == jobs.c.id)
                    & (outbox.c.organization_id == jobs.c.organization_id),
                )
                .where(
                    jobs.c.organization_id == tenant,
                    jobs.c.status == "queued",
                    or_(
                        outbox.c.status == "pending",
                        outbox.c.status == "delivered",
                        outbox.c.status == "dispatched",
                    ),
                )
                .order_by(jobs.c.created_at)
                .limit(10)
            ).scalars()
        )
