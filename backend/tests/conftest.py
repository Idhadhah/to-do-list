
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("DB_PATH", str(db_file))
    monkeypatch.setenv("JWT_SECRET", "cd616e3220c0446ba38cc495cff0cf3efb61ec53655659b053d8d59156f405a")

    sys.modules.pop("main", None)
    import main as main_module

    with TestClient(main_module.app) as test_client:
        yield test_client

    main_module.engine.dispose()


def signup(client, email="user@example.com", password="a-good-password"):
    """Helper: sign up a user and return their bearer token."""
    resp = client.post("/signup", json={"email": email, "password": password})
    assert resp.status_code == 201, resp.text
    return resp.json()["access_token"]


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}