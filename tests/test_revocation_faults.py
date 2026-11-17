from fastapi.testclient import TestClient

from codeatlas.config import Settings
from codeatlas.main import TENANT_A, create_app
from codeatlas.ingestion import run_job
from test_foundation import ControlledSource, register, enqueue


def test_revocation_during_ingestion_prevents_source_persistence(application, auth_a):
    _, engine = application
    settings = Settings(
        str(engine.url),
        "a" * 32,
        "b" * 32,
        identities={"d" * 32: [TENANT_A, "developer", "developer"]},
    )
    dev = {"Authorization": "Bearer " + "d" * 32}
    with TestClient(create_app(settings, engine)) as client:
        repo = register(client, auth_a)
        assert (
            client.put(
                f"/api/v1/repositories/{repo}/grants",
                headers=auth_a,
                json={"principal_id": "developer", "capability": "index"},
            ).status_code
            == 200
        )
        job = enqueue(client, dev, repo).json()["id"]

        class Revoked(ControlledSource):
            def blob(self, *args):
                client.delete(f"/api/v1/repositories/{repo}/grants/developer", headers=auth_a)
                return super().blob(*args)

        assert not run_job(engine, TENANT_A, job, Revoked())
        assert client.get(f"/api/v1/index-jobs/{job}", headers=dev).status_code == 404
        result = client.get(f"/api/v1/index-jobs/{job}", headers=auth_a).json()
        assert result["error_code"] == "authorization_revoked"
        assert client.get(f"/api/v1/index-jobs/{job}/files", headers=auth_a).json() == []
