"""Explicitly approved public live verification; prints metadata evidence, never source or keys."""

import argparse
import json
import time
from collections import Counter
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from codeatlas.config import Settings
from codeatlas.ingestion import run_job
from codeatlas.main import TENANT_A, create_app
from codeatlas.queue import dispatch
from codeatlas.source import GitHubSource


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--approved-octocat-hello-world", action="store_true", required=True)
    parser.add_argument(
        "--via-broker",
        action="store_true",
        help="Dispatch through transactional outbox and wait for a running Celery worker",
    )
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()
    assert args.approved_octocat_hello_world
    settings = Settings.from_env()
    remote = "https://github.com/octocat/Hello-World"
    commit, tree = GitHubSource().resolve(remote, "master")
    with TestClient(create_app(settings)) as client:
        headers = {"Authorization": "Bearer " + settings.token_a}
        registered = client.post(
            "/api/v1/repositories",
            headers=headers,
            json={"remote_url": remote, "requested_ref": commit},
        )
        registered.raise_for_status()
        repo = registered.json()["id"]
        queued = client.post(
            f"/api/v1/repositories/{repo}/index",
            headers={**headers, "Idempotency-Key": "live-" + commit},
            json={"ref": commit},
        )
        queued.raise_for_status()
        job = queued.json()["id"]
        if args.via_broker:
            dispatched = dispatch(client.app.state.engine, TENANT_A)
            if dispatched != 1:
                raise SystemExit(f"Expected 1 outbox dispatch, got {dispatched}")
            deadline = time.monotonic() + args.timeout
            status = client.get(f"/api/v1/index-jobs/{job}", headers=headers).json()
            while status["status"] in ("queued", "running") and time.monotonic() < deadline:
                time.sleep(0.25)
                status = client.get(f"/api/v1/index-jobs/{job}", headers=headers).json()
            success = status["status"] == "succeeded"
        else:
            success = run_job(client.app.state.engine, TENANT_A, job, GitHubSource())
            status = client.get(f"/api/v1/index-jobs/{job}", headers=headers).json()
        inventory = client.get(f"/api/v1/index-jobs/{job}/files", headers=headers).json()
        view_status = []
        for row in inventory:
            if row["inventory_status"] == "inventoried":
                response = client.get(
                    f"/api/v1/files/{row['id']}/content",
                    headers=headers,
                    params={"snapshot_id": row["snapshot_id"], "start_line": 1, "end_line": 10},
                )
                view_status.append(response.status_code)
        evidence = dict(
            kind="live_public_https",
            delivery_path="outbox_celery_worker" if args.via_broker else "direct_ingestion",
            remote=remote,
            requested_ref=commit,
            commit_sha=status["commit_sha"],
            tree_sha=tree,
            status=status["status"],
            error_code=status["error_code"],
            file_count=len(inventory),
            inventory_counts=dict(Counter(r["inventory_status"] for r in inventory)),
            source_view_statuses=view_status,
            timestamp=datetime.now(timezone.utc).isoformat(),
            repository_id=repo,
            job_id=job,
            executed_imported_code=False,
        )
        print(json.dumps(evidence, indent=2))
        if not success or any(s != 200 for s in view_status):
            raise SystemExit(1)


if __name__ == "__main__":
    main()
