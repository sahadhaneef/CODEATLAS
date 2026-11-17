import time
from uuid import uuid4

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from fastapi.testclient import TestClient
from sqlalchemy import update

import pytest
from codeatlas.config import Settings
from codeatlas.db import memberships, transaction
from codeatlas.main import TENANT_A, TENANT_B, create_app


def test_verified_oidc_binding_revocation_and_claim_failures(application):
    _, engine = application
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = (
        key.public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )
    with pytest.raises(ValueError, match="Development identities must be absent"):
        Settings(
            str(engine.url),
            "a" * 32,
            "",
            "production",
            auth_mode="oidc",
            oidc_issuer="https://issuer.example",
            oidc_audience="codeatlas",
            oidc_keys={"one": public},
        ).validate()
    settings = Settings(
        str(engine.url),
        "",
        "",
        "production",
        auth_mode="oidc",
        oidc_issuer="https://issuer.example",
        oidc_audience="codeatlas",
        oidc_keys={"one": public},
    )
    with transaction(engine, TENANT_A) as c:
        c.execute(
            memberships.insert().values(
                id=str(uuid4()),
                organization_id=TENANT_A,
                principal_id="oidc-admin",
                issuer=settings.oidc_issuer,
                subject="external-subject",
                role="admin",
                status="active",
            )
        )
    now = int(time.time())
    claims = dict(
        iss=settings.oidc_issuer,
        aud="codeatlas",
        sub="external-subject",
        iat=now,
        exp=now + 300,
        organization_id=TENANT_A,
    )

    def headers(values, jwt_headers=None):
        return {
            "Authorization": "Bearer "
            + jwt.encode(values, key, algorithm="RS256", headers=jwt_headers or {"kid": "one"})
        }

    with TestClient(create_app(settings, engine)) as client:
        assert client.get("/api/v1/repositories", headers=headers(claims)).status_code == 200
        for replacement in (
            {"aud": "wrong"},
            {"iss": "https://evil.example"},
            {"exp": now - 10},
            {"exp": now + 3601},
            {"iat": now + 60},
            {"sub": "unprovisioned-subject"},
            {"organization_id": TENANT_B},
        ):
            assert (
                client.get(
                    "/api/v1/repositories", headers=headers({**claims, **replacement})
                ).status_code
                == 401
            )
        assert (
            client.get(
                "/api/v1/repositories",
                headers=headers(claims, {"kid": "one", "jku": "https://evil.example/jwks.json"}),
            ).status_code
            == 401
        )
        assert (
            client.get(
                "/api/v1/repositories",
                headers=headers(claims, {"kid": "unknown-kid"}),
            ).status_code
            == 401
        )
        with transaction(engine, TENANT_A) as c:
            c.execute(
                update(memberships)
                .where(memberships.c.principal_id == "oidc-admin")
                .values(status="revoked")
            )
        assert client.get("/api/v1/repositories", headers=headers(claims)).status_code == 401


def test_development_revocation_is_not_recreated(application, auth_a):
    client, engine = application
    assert client.get("/api/v1/repositories", headers=auth_a).status_code == 200
    with transaction(engine, TENANT_A) as c:
        c.execute(
            update(memberships)
            .where(memberships.c.principal_id == TENANT_A)
            .values(status="revoked")
        )
    assert client.get("/api/v1/repositories", headers=auth_a).status_code == 401
