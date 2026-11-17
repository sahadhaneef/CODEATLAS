"""Explicit operator provisioning. Requires migration-owner DB credentials and a JSON record."""

import argparse
import json
from uuid import uuid4

from sqlalchemy import select
from codeatlas.config import Settings
from codeatlas.db import make_engine, memberships, transaction


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "record", help="JSON file with organization_id, principal_id, issuer, subject, role"
    )
    args = parser.parse_args()
    with open(args.record, encoding="utf-8") as handle:
        record = json.load(handle)
    if record["role"] not in ("owner", "admin", "developer", "viewer"):
        raise SystemExit("Invalid role")
    engine = make_engine(Settings.from_env().database_url)
    with transaction(engine, record["organization_id"]) as c:
        if c.execute(
            select(memberships.c.id).where(
                memberships.c.organization_id == record["organization_id"],
                memberships.c.principal_id == record["principal_id"],
            )
        ).first():
            raise SystemExit(
                "Membership exists; use an audited operator change rather than implicit overwrite"
            )
        c.execute(memberships.insert().values(id=str(uuid4()), status="active", **record))
    print("Membership provisioned")


if __name__ == "__main__":
    main()
