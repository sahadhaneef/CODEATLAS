"""Explicit tenant-scoped one-pass worker; database is the durable queue for this slice."""

import argparse

from codeatlas.config import Settings
from codeatlas.db import make_engine
from codeatlas.lifecycle import recover
from codeatlas.ingestion import run_job
from codeatlas.main import TENANT_A, TENANT_B
from codeatlas.source import GitHubSource


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant", choices=(TENANT_A, TENANT_B), required=True)
    args = parser.parse_args()
    settings = Settings.from_env()
    engine = make_engine(settings.database_url)
    pending = recover(engine, args.tenant)
    for job_id in pending:
        success = run_job(engine, args.tenant, job_id, GitHubSource())
        print(
            f"{job_id}: {'inventory complete' if success else 'not completed; inspect job status'}"
        )


if __name__ == "__main__":
    main()
