import hashlib
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select, text, update, delete
from sqlalchemy.exc import IntegrityError

from codeatlas.config import Settings
from codeatlas.db import files, jobs, make_engine, repositories, transaction, outbox, snapshots
from codeatlas.source import canonical_remote, valid_ref
from codeatlas.access import repository_access
from codeatlas.db import grants, memberships
from codeatlas.auth import authenticate, AuthenticationError

TENANT_A = "00000000-0000-0000-0000-000000000001"
TENANT_B = "00000000-0000-0000-0000-000000000002"


class Registration(BaseModel):
    model_config = ConfigDict(extra="forbid")
    remote_url: str = Field(max_length=512)
    requested_ref: str = Field(default="main", max_length=200)
    visibility_policy: str = Field(default="private", pattern="^private$")

    @field_validator("remote_url")
    @classmethod
    def remote(cls, value):
        return canonical_remote(value)

    @field_validator("requested_ref")
    @classmethod
    def ref(cls, value):
        return valid_ref(value)


class IndexRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ref: str = Field(default="main", max_length=200)

    @field_validator("ref")
    @classmethod
    def valid(cls, value):
        return valid_ref(value)


def create_app(settings=None, engine=None):
    settings = settings or Settings.from_env()
    settings.validate()
    engine = engine or make_engine(settings.database_url)
    app = FastAPI(title="CodeAtlas foundation", version="0.1.0")
    app.state.engine = engine

    @app.middleware("http")
    async def request_id(request, call_next):
        request.state.request_id = str(uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    def error(request, status, code, message):
        return JSONResponse(
            status_code=status,
            content={
                "code": code,
                "message": message,
                "request_id": request.state.request_id,
                "retryable": status == 503,
                "details": {},
            },
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        return error(request, exc.status_code, str(exc.detail), str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        return error(request, 422, "invalid_request", "Invalid request parameters")

    def identity(authorization: str = Header(default="")):
        try:
            return authenticate(settings, engine, authorization)
        except AuthenticationError:
            raise HTTPException(401, "unauthenticated") from None

    def authorized(connection, tenant, principal, repo_id):
        record = (
            connection.execute(
                select(repositories).where(
                    repositories.c.organization_id == tenant,
                    repositories.c.id == repo_id,
                    repository_access(tenant, principal),
                )
            )
            .mappings()
            .first()
        )
        if record is None:
            raise HTTPException(404, "repository_not_found")
        return record

    def role(actor):
        with transaction(engine, actor[0]) as c:
            return c.execute(
                select(memberships.c.role).where(
                    memberships.c.organization_id == actor[0],
                    memberships.c.principal_id == actor[1],
                    memberships.c.status == "active",
                )
            ).scalar()

    @app.get("/api/v1/health")
    def health():
        return {"status": "alive", "agents": False, "patches": False, "execution": False}

    @app.get("/api/v1/ready")
    def ready():
        try:
            with engine.connect() as connection:
                version = connection.execute(
                    text("SELECT version_num FROM alembic_version")
                ).scalar()
                if version != "0007":
                    raise ValueError("schema mismatch")
            return {"status": "ready", "scope": "database-backed inventory foundation"}
        except Exception:
            raise HTTPException(503, "database_or_migrations_unavailable") from None

    @app.post("/api/v1/repositories", status_code=201)
    def register(body: Registration, actor=Depends(identity)):
        if role(actor) not in ("admin", "owner"):
            raise HTTPException(403, "admin_required")
        tenant, principal = actor
        record = dict(
            id=str(uuid4()),
            organization_id=tenant,
            owner_id=principal,
            remote_url=body.remote_url,
            requested_ref=body.requested_ref,
        )
        with transaction(engine, tenant) as connection:
            connection.execute(repositories.insert().values(**record))
        return record

    @app.get("/api/v1/repositories")
    def list_repositories(
        actor=Depends(identity), limit: int = Query(50, ge=1, le=100), after: str = ""
    ):
        tenant, principal = actor
        with transaction(engine, tenant) as connection:
            return [
                dict(r)
                for r in connection.execute(
                    select(repositories)
                    .where(
                        repositories.c.organization_id == tenant,
                        repository_access(tenant, principal),
                        repositories.c.id > after,
                    )
                    .order_by(repositories.c.id)
                    .limit(limit)
                ).mappings()
            ]

    @app.post("/api/v1/repositories/{repo_id}/index", status_code=202)
    def index(
        repo_id: str,
        body: IndexRequest,
        actor=Depends(identity),
        idempotency_key: str = Header(min_length=1, max_length=128),
    ):
        tenant, principal = actor
        digest = hashlib.sha256((repo_id + "\0" + body.ref).encode()).hexdigest()
        with transaction(engine, tenant) as connection:
            authorized(connection, tenant, principal, repo_id)
            allowed = connection.execute(
                select(repositories.c.id).where(
                    repositories.c.id == repo_id,
                    repositories.c.organization_id == tenant,
                    repository_access(tenant, principal, "index"),
                )
            ).first()
            if not allowed or role(actor) == "viewer":
                raise HTTPException(403, "index_capability_required")
        record = dict(
            id=str(uuid4()),
            organization_id=tenant,
            repository_id=repo_id,
            requested_by=principal,
            requested_ref=body.ref,
            status="queued",
            stage="queued",
            idempotency_key=idempotency_key,
            request_digest=digest,
            attempts=0,
        )
        try:
            with transaction(engine, tenant) as connection:
                connection.execute(jobs.insert().values(**record))
                connection.execute(
                    outbox.insert().values(
                        id=str(uuid4()),
                        organization_id=tenant,
                        job_id=record["id"],
                        status="pending",
                    )
                )
        except IntegrityError:
            with transaction(engine, tenant) as connection:
                existing = (
                    connection.execute(
                        select(jobs).where(
                            jobs.c.organization_id == tenant,
                            jobs.c.requested_by == principal,
                            jobs.c.idempotency_key == idempotency_key,
                        )
                    )
                    .mappings()
                    .one()
                )
                if existing["request_digest"] != digest:
                    raise HTTPException(409, "idempotency_conflict") from None
                record = dict(existing)
        return {
            "id": record["id"],
            "status": record["status"],
            "status_url": "/api/v1/index-jobs/" + record["id"],
        }

    def authorized_job(connection, actor, job_id):
        tenant, principal = actor
        job = (
            connection.execute(
                select(jobs).where(
                    jobs.c.id == job_id,
                    jobs.c.organization_id == tenant,
                )
            )
            .mappings()
            .first()
        )
        if not job:
            raise HTTPException(404, "job_not_found")
        authorized(connection, tenant, principal, job["repository_id"])
        return job

    class GrantRequest(BaseModel):
        principal_id: str = Field(min_length=1, max_length=36)
        capability: str = Field(pattern="^(read|index)$")

    @app.put("/api/v1/repositories/{repo_id}/grants")
    def grant(repo_id: str, body: GrantRequest, actor=Depends(identity)):
        with transaction(engine, actor[0]) as connection:
            repo = authorized(connection, *actor, repo_id)
            if repo["owner_id"] != actor[1] or role(actor) not in ("owner", "admin"):
                raise HTTPException(403, "repository_admin_required")
            known = connection.execute(
                select(memberships.c.id).where(
                    memberships.c.organization_id == actor[0],
                    memberships.c.principal_id == body.principal_id,
                    memberships.c.status == "active",
                )
            ).first()
            if not known:
                raise HTTPException(422, "tenant_member_required")
            connection.execute(
                delete(grants).where(
                    grants.c.organization_id == actor[0],
                    grants.c.repository_id == repo_id,
                    grants.c.principal_id == body.principal_id,
                )
            )
            connection.execute(
                grants.insert().values(
                    id=str(uuid4()),
                    organization_id=actor[0],
                    repository_id=repo_id,
                    principal_id=body.principal_id,
                    capability=body.capability,
                )
            )
        return {"status": "granted"}

    @app.delete("/api/v1/repositories/{repo_id}/grants/{principal_id}", status_code=204)
    def revoke(repo_id: str, principal_id: str, actor=Depends(identity)):
        with transaction(engine, actor[0]) as connection:
            repo = authorized(connection, *actor, repo_id)
            if repo["owner_id"] != actor[1] or role(actor) not in ("owner", "admin"):
                raise HTTPException(403, "repository_admin_required")
            connection.execute(
                delete(grants).where(
                    grants.c.organization_id == actor[0],
                    grants.c.repository_id == repo_id,
                    grants.c.principal_id == principal_id,
                )
            )

    @app.get("/api/v1/index-jobs/{job_id}")
    def job_status(job_id: str, actor=Depends(identity)):
        with transaction(engine, actor[0]) as connection:
            return dict(authorized_job(connection, actor, job_id))

    @app.post("/api/v1/index-jobs/{job_id}/cancel")
    def cancel(job_id: str, actor=Depends(identity)):
        with transaction(engine, actor[0]) as connection:
            job = authorized_job(connection, actor, job_id)
            permitted = connection.execute(
                select(repositories.c.id).where(
                    repositories.c.organization_id == actor[0],
                    repositories.c.id == job["repository_id"],
                    repository_access(*actor, "index"),
                )
            ).first()
            if role(actor) == "viewer" or not permitted:
                raise HTTPException(403, "index_capability_required")
            connection.execute(
                update(jobs)
                .where(
                    jobs.c.id == job_id,
                    jobs.c.organization_id == actor[0],
                    jobs.c.status.in_(["queued", "running"]),
                )
                .values(status="cancelled", lease_epoch=jobs.c.lease_epoch + 1, lease_until=0)
            )
            return dict(authorized_job(connection, actor, job_id))

    @app.get("/api/v1/repositories/{repo_id}/snapshots")
    def list_snapshots(
        repo_id: str, actor=Depends(identity), limit: int = Query(50, ge=1, le=100), after: str = ""
    ):
        with transaction(engine, actor[0]) as connection:
            authorized(connection, *actor, repo_id)
            return [
                dict(r)
                for r in connection.execute(
                    select(snapshots)
                    .where(
                        snapshots.c.organization_id == actor[0],
                        snapshots.c.repository_id == repo_id,
                        snapshots.c.id > after,
                    )
                    .order_by(snapshots.c.id)
                    .limit(limit)
                ).mappings()
            ]

    @app.get("/api/v1/files/{file_id}/content")
    def source_content(
        file_id: str,
        snapshot_id: str,
        actor=Depends(identity),
        start_line: int = Query(1, ge=1),
        end_line: int = Query(100, ge=1),
    ):
        from codeatlas.storage import unseal

        if end_line < start_line or end_line - start_line >= 500:
            raise HTTPException(422, "source_line_limit")
        with transaction(engine, actor[0]) as connection:
            record = (
                connection.execute(
                    select(files).where(
                        files.c.id == file_id,
                        files.c.organization_id == actor[0],
                        files.c.snapshot_id == snapshot_id,
                    )
                )
                .mappings()
                .first()
            )
            if not record:
                raise HTTPException(404, "file_not_found")
            authorized(connection, *actor, record["repository_id"])
            snapshot = (
                connection.execute(
                    select(snapshots).where(
                        snapshots.c.organization_id == actor[0],
                        snapshots.c.id == snapshot_id,
                        snapshots.c.repository_id == record["repository_id"],
                    )
                )
                .mappings()
                .one()
            )
            if not record["source_ciphertext"]:
                raise HTTPException(409, "source_not_retained")
            try:
                content = unseal(record, snapshot["commit_sha"]).decode("utf-8")
            except Exception:
                raise HTTPException(503, "source_storage_unavailable") from None
            if start_line > max(1, len(content.splitlines())):
                raise HTTPException(422, "source_line_out_of_bounds")
            selected = "".join(content.splitlines(keepends=True)[start_line - 1 : end_line])
            if len(selected.encode()) > 65536:
                raise HTTPException(422, "source_byte_limit")
            return {
                "file_id": file_id,
                "snapshot_id": snapshot_id,
                "commit_sha": snapshot["commit_sha"],
                "path": record["path"],
                "start_line": start_line,
                "end_line": min(end_line, len(content.splitlines())),
                "content": selected,
                "source_hash": record["source_hash"],
            }

    @app.get("/api/v1/index-jobs/{job_id}/files")
    def inventory(
        job_id: str, actor=Depends(identity), limit: int = Query(50, ge=1, le=100), after: str = ""
    ):
        with transaction(engine, actor[0]) as connection:
            authorized_job(connection, actor, job_id)
            return [
                dict(r)
                for r in connection.execute(
                    select(*[col for col in files.c if col.name != "source_ciphertext"])
                    .where(
                        files.c.organization_id == actor[0],
                        files.c.job_id == job_id,
                        files.c.path > after,
                    )
                    .order_by(files.c.path)
                    .limit(limit)
                ).mappings()
            ]

    return app
