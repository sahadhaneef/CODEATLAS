import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from codeatlas.config import Settings
from codeatlas.db import make_engine
from codeatlas.main import create_app


@pytest.fixture
def application(tmp_path, monkeypatch):
    from cryptography.fernet import Fernet

    monkeypatch.setenv("CODEATLAS_SOURCE_KEY", Fernet.generate_key().decode())
    url = "sqlite:///" + (tmp_path / "test.db").as_posix()
    monkeypatch.setenv("CODEATLAS_DATABASE_URL", url)
    command.upgrade(Config("alembic.ini"), "head")
    engine = make_engine(url)
    settings = Settings(url, "a" * 32, "b" * 32)
    with TestClient(create_app(settings, engine)) as client:
        yield client, engine
    engine.dispose()


@pytest.fixture
def auth_a():
    return {"Authorization": "Bearer " + "a" * 32}


@pytest.fixture
def auth_b():
    return {"Authorization": "Bearer " + "b" * 32}
