from fastapi.testclient import TestClient

from codeatlas.config import Settings
from codeatlas.main import TENANT_A, TENANT_B, create_app
from test_foundation import register, enqueue


def test_roles_grants_and_revocation(application, auth_a):
    _, engine = application
    settings = Settings(
        str(engine.url),
        "a" * 32,
        "b" * 32,
        identities={
            "v" * 32: [TENANT_A, "viewer", "viewer"],
            "d" * 32: [TENANT_A, "developer", "developer"],
            "x" * 32: [TENANT_B, "other-admin", "admin"],
        },
    )
    with TestClient(create_app(settings, engine)) as client:
        repo = register(client, auth_a)
        viewer = {"Authorization": "Bearer " + "v" * 32}
        developer = {"Authorization": "Bearer " + "d" * 32}
        assert client.get("/api/v1/repositories", headers=viewer).json() == []
        assert (
            client.post(
                "/api/v1/repositories",
                headers=developer,
                json={"remote_url": "https://github.com/a/b"},
            ).status_code
            == 403
        )
        for principal in ("viewer", "developer"):
            assert (
                client.put(
                    f"/api/v1/repositories/{repo}/grants",
                    headers=auth_a,
                    json={"principal_id": principal, "capability": "index"},
                ).status_code
                == 200
            )
        assert enqueue(client, viewer, repo).status_code == 403
        assert enqueue(client, developer, repo).status_code == 202
        assert len(client.get("/api/v1/repositories", headers=viewer).json()) == 1
        assert (
            client.put(
                f"/api/v1/repositories/{repo}/grants",
                headers=auth_a,
                json={"principal_id": "other-admin", "capability": "read"},
            ).status_code
            == 422
        )
        assert (
            client.delete(f"/api/v1/repositories/{repo}/grants/viewer", headers=auth_a).status_code
            == 204
        )
        assert client.get("/api/v1/repositories", headers=viewer).json() == []
