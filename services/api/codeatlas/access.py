from sqlalchemy import exists, or_, select

from codeatlas.db import grants, repositories, memberships


def repository_access(tenant, principal, capability="read"):
    permitted = select(grants.c.id).where(
        grants.c.organization_id == tenant,
        grants.c.repository_id == repositories.c.id,
        grants.c.principal_id == principal,
    )
    if capability == "index":
        permitted = permitted.where(grants.c.capability == "index")
    member = select(memberships.c.id).where(
        memberships.c.organization_id == tenant,
        memberships.c.principal_id == principal,
        memberships.c.status == "active",
    )
    if capability == "index":
        member = member.where(memberships.c.role.in_(["owner", "admin", "developer"]))
    return exists(member) & or_(repositories.c.owner_id == principal, exists(permitted))
