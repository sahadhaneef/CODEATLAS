import time
from uuid import uuid4

from sqlalchemy import delete, select, update

from codeatlas.db import files, jobs, transaction, outbox, snapshots
from codeatlas.source import SourceError, classify, sha
from codeatlas.access import repository_access
from codeatlas.storage import seal


def run_job(engine, tenant, job_id, source):
    """Atomic claim; immutable pin persists before inventory; no code or files written to disk."""
    with transaction(engine, tenant) as connection:
        claimed = connection.execute(
            update(jobs)
            .where(
                jobs.c.id == job_id,
                jobs.c.organization_id == tenant,
                jobs.c.status == "queued",
                jobs.c.attempts < 3,
            )
            .values(
                status="running",
                stage="fetching",
                attempts=jobs.c.attempts + 1,
                lease_epoch=jobs.c.lease_epoch + 1,
                lease_until=int(time.time()) + 60,
            )
        )
        if claimed.rowcount != 1:
            return False
        job = (
            connection.execute(
                select(jobs).where(
                    jobs.c.id == job_id,
                    jobs.c.organization_id == tenant,
                )
            )
            .mappings()
            .one()
        )
        from codeatlas.db import repositories

        repo = (
            connection.execute(
                select(repositories).where(
                    repositories.c.id == job["repository_id"],
                    repositories.c.organization_id == tenant,
                    repository_access(tenant, job["requested_by"], "index"),
                )
            )
            .mappings()
            .first()
        )
        if repo is None:
            connection.execute(
                update(jobs)
                .where(jobs.c.id == job_id, jobs.c.organization_id == tenant)
                .values(status="failed", error_code="authorization_revoked")
            )
            return False
        connection.execute(
            update(outbox)
            .where(outbox.c.organization_id == tenant, outbox.c.job_id == job_id)
            .values(status="delivered")
        )
    epoch = job["lease_epoch"]

    def fence(connection):
        permitted = connection.execute(
            select(repositories.c.id).where(
                repositories.c.id == repo["id"],
                repositories.c.organization_id == tenant,
                repository_access(tenant, job["requested_by"], "index"),
            )
        ).first()
        if not permitted:
            raise SourceError("authorization_revoked")
        changed = connection.execute(
            update(jobs)
            .where(
                jobs.c.id == job_id,
                jobs.c.organization_id == tenant,
                jobs.c.status == "running",
                jobs.c.lease_epoch == epoch,
                jobs.c.lease_until >= int(time.time()),
            )
            .values(lease_until=int(time.time()) + 60)
        )
        if changed.rowcount != 1:
            raise SourceError("lease_lost_or_cancelled")

    try:
        if job["commit_sha"]:
            commit, tree = job["commit_sha"], job["tree_sha"]
        else:
            commit, tree = source.resolve(repo["remote_url"], job["requested_ref"])
        sha(commit)
        sha(tree)
        with transaction(engine, tenant) as connection:
            fence(connection)
            connection.execute(
                update(jobs)
                .where(
                    jobs.c.id == job_id,
                    jobs.c.organization_id == tenant,
                )
                .values(commit_sha=commit, tree_sha=tree, stage="inventory")
            )
        entries = source.inventory(repo["remote_url"], commit, tree)
        if len(entries) > 100000 or sum(e.size for e in entries) > 1024**3:
            raise SourceError("inventory_size_limit")
        records = []
        deadline = time.monotonic() + 1800
        for entry in entries:
            with transaction(engine, tenant) as connection:
                fence(connection)
            if time.monotonic() > deadline:
                raise SourceError("ingestion_deadline")
            status, reason = classify(entry)
            ciphertext, digest = None, None
            if status == "inventoried":
                content = source.blob(repo["remote_url"], entry)
                if len(content) > 1024 * 1024:
                    raise SourceError("blob_size_limit")
                try:
                    content.decode("utf-8")
                    if b"\0" in content:
                        status, reason = "binary", "nul_byte"
                except UnicodeDecodeError:
                    status, reason = "binary", "not_utf8"
                if status == "inventoried":
                    ciphertext, digest = seal(content, tenant, repo["id"], commit, entry.path)
            records.append(
                dict(
                    id=str(uuid4()),
                    organization_id=tenant,
                    repository_id=repo["id"],
                    job_id=job_id,
                    path=entry.path,
                    blob_sha=entry.blob_sha,
                    byte_count=entry.size,
                    inventory_status=status,
                    exclusion_reason=reason,
                    source_ciphertext=ciphertext,
                    source_hash=digest,
                )
            )
        with transaction(engine, tenant) as connection:
            fence(connection)
            existing = (
                connection.execute(
                    select(snapshots).where(
                        snapshots.c.organization_id == tenant,
                        snapshots.c.repository_id == repo["id"],
                        snapshots.c.commit_sha == commit,
                    )
                )
                .mappings()
                .first()
            )
            if existing is None:
                snapshot_id = str(uuid4())
                connection.execute(
                    snapshots.insert().values(
                        id=snapshot_id,
                        organization_id=tenant,
                        repository_id=repo["id"],
                        commit_sha=commit,
                        tree_sha=tree,
                        requested_ref=job["requested_ref"],
                    )
                )
            elif existing["tree_sha"] != tree:
                raise SourceError("snapshot_integrity_error")
            else:
                snapshot_id = existing["id"]
            for record in records:
                record["snapshot_id"] = snapshot_id
            connection.execute(
                delete(files).where(files.c.job_id == job_id, files.c.organization_id == tenant)
            )
            if records:
                connection.execute(files.insert(), records)
            connection.execute(
                update(jobs)
                .where(
                    jobs.c.id == job_id,
                    jobs.c.organization_id == tenant,
                    jobs.c.status == "running",
                    jobs.c.lease_epoch == epoch,
                )
                .values(status="succeeded", stage="inventory_complete")
            )
        return True
    except Exception as exc:
        code = str(exc) if isinstance(exc, SourceError) else "ingestion_internal_error"
        retryable = code == "provider_transport_error" and job["attempts"] < 3
        with transaction(engine, tenant) as connection:
            connection.execute(
                update(jobs)
                .where(
                    jobs.c.id == job_id,
                    jobs.c.organization_id == tenant,
                    jobs.c.status == "running",
                    jobs.c.lease_epoch == epoch,
                )
                .values(status="queued" if retryable else "failed", error_code=code, lease_until=0)
            )
            if retryable:
                connection.execute(
                    update(outbox)
                    .where(outbox.c.organization_id == tenant, outbox.c.job_id == job_id)
                    .values(dispatch_after=int(time.time()) + 2 ** job["attempts"])
                )
        return False
