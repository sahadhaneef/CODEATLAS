"""Verified bearer claims never create memberships or establish organization authority."""

import secrets
import time
from uuid import uuid4

import jwt
from sqlalchemy import select

from codeatlas.db import memberships, transaction


class AuthenticationError(Exception):
    pass


def authenticate(settings, engine, authorization):
    if not authorization.startswith("Bearer "):
        raise AuthenticationError()
    if settings.auth_mode == "oidc":
        try:
            token = authorization.removeprefix("Bearer ")
            if len(token) > 16384:
                raise AuthenticationError()
            header = jwt.get_unverified_header(token)
            if header.get("alg") != "RS256" or any(
                k in header for k in ("jku", "jwk", "x5u", "x5c")
            ):
                raise AuthenticationError()
            key = settings.oidc_keys[header["kid"]]
            claims = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=settings.oidc_audience,
                issuer=settings.oidc_issuer,
                options={"require": ["exp", "iat", "sub", "iss", "aud"]},
            )
            if (
                not isinstance(claims["sub"], str)
                or not claims["sub"]
                or claims["exp"] - claims["iat"] > 3600
                or claims["iat"] > time.time()
            ):
                raise AuthenticationError()
            # tenant is only a selector; an independently provisioned binding grants authority.
            tenant = claims.get("organization_id", "")
            with transaction(engine, tenant) as c:
                row = (
                    c.execute(
                        select(memberships).where(
                            memberships.c.organization_id == tenant,
                            memberships.c.issuer == settings.oidc_issuer,
                            memberships.c.subject == claims["sub"],
                            memberships.c.status == "active",
                        )
                    )
                    .mappings()
                    .first()
                )
                if not row:
                    raise AuthenticationError()
                return tenant, row["principal_id"]
        except (jwt.PyJWTError, KeyError, ValueError, TypeError):
            raise AuthenticationError() from None
    identities = {
        settings.token_a: ["00000000-0000-0000-0000-000000000001"] * 2 + ["admin"],
        settings.token_b: ["00000000-0000-0000-0000-000000000002"] * 2 + ["admin"],
        **settings.identities,
    }
    # Bootstrap all configured dev members, once. Never overwrite persisted role/revocation.
    for tenant, principal, role in identities.values():
        with transaction(engine, tenant) as c:
            if not c.execute(
                select(memberships.c.id).where(
                    memberships.c.organization_id == tenant, memberships.c.principal_id == principal
                )
            ).first():
                c.execute(
                    memberships.insert().values(
                        id=str(uuid4()),
                        organization_id=tenant,
                        principal_id=principal,
                        issuer="development",
                        subject=tenant + ":" + principal,
                        role=role,
                        status="active",
                    )
                )
    for token, (tenant, principal, _) in identities.items():
        if secrets.compare_digest(authorization, "Bearer " + token):
            with transaction(engine, tenant) as c:
                if c.execute(
                    select(memberships.c.id).where(
                        memberships.c.organization_id == tenant,
                        memberships.c.principal_id == principal,
                        memberships.c.status == "active",
                    )
                ).first():
                    return tenant, principal
    raise AuthenticationError()
