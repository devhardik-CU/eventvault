import pytest

from app.config import INSECURE_DEV_KEY, Settings
from app.services import storage
from app.services.storage import StorageError
from .helpers import make_event, signup

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 64


def _org_event(client):
    org, _ = signup(client, "o@example.com", "organizer")
    return org, make_event(client, org)


def test_upload_and_fetch_poster_roundtrip(client):
    org, ev = _org_event(client)
    r = client.post(f"/api/events/{ev['id']}/poster", files={"file": ("p.png", PNG, "image/png")}, headers=org)
    assert r.status_code == 200 and r.json()["has_poster"] is True
    got = client.get(f"/api/events/{ev['id']}/poster")
    assert got.status_code == 200 and got.content == PNG and got.headers["content-type"] == "image/png"
    assert got.headers["x-content-type-options"] == "nosniff"


def test_replacing_poster_removes_old_file(client):
    org, ev = _org_event(client)
    client.post(f"/api/events/{ev['id']}/poster", files={"file": ("p.png", PNG, "image/png")}, headers=org)
    import os
    from app.config import get_settings
    before = set(os.listdir(get_settings().upload_dir))
    client.post(f"/api/events/{ev['id']}/poster", files={"file": ("p.jpg", JPG, "image/jpeg")}, headers=org)
    after = set(os.listdir(get_settings().upload_dir))
    assert len(after) == 1 and before != after


def test_fake_image_rejected_by_content_not_header(client):
    org, ev = _org_event(client)
    r = client.post(f"/api/events/{ev['id']}/poster", files={"file": ("evil.png", b"<script>alert(1)</script>", "image/png")}, headers=org)
    assert r.status_code == 415


def test_oversized_upload_rejected(client):
    org, ev = _org_event(client)
    r = client.post(f"/api/events/{ev['id']}/poster", files={"file": ("big.png", PNG + b"0" * (2 * 1024 * 1024), "image/png")}, headers=org)
    assert r.status_code == 413


def test_missing_poster_404(client):
    _, ev = _org_event(client)
    assert client.get(f"/api/events/{ev['id']}/poster").status_code == 404


def test_storage_failure_is_reported_not_faked(client, monkeypatch):
    org, ev = _org_event(client)
    class Broken:
        def save(self, *a): raise StorageError("down")
        def delete(self, *a): pass
    monkeypatch.setattr("app.routers.events.get_storage", lambda: Broken())
    r = client.post(f"/api/events/{ev['id']}/poster", files={"file": ("p.png", PNG, "image/png")}, headers=org)
    assert r.status_code == 502
    assert client.get(f"/api/events/{ev['id']}").json()["has_poster"] is False


def test_local_storage_blocks_path_traversal(tmp_path):
    s = storage.LocalStorage(str(tmp_path / "up"))
    (tmp_path / "secret.txt").write_text("secret")
    with pytest.raises(StorageError):
        s.read("../secret.txt")


def test_azure_backend_without_connection_string_fails_fast():
    with pytest.raises(RuntimeError, match="AZURE_STORAGE_CONNECTION_STRING"):
        Settings(storage_backend="azure", azure_storage_connection_string="", _env_file=None).validate_for_runtime()


def test_production_rejects_default_secret_and_wildcard_cors():
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        Settings(environment="production", secret_key=INSECURE_DEV_KEY, _env_file=None).validate_for_runtime()
    with pytest.raises(RuntimeError, match="CORS"):
        Settings(environment="production", secret_key="x" * 40, cors_origins="*", _env_file=None).validate_for_runtime()
    Settings(environment="production", secret_key="x" * 40, cors_origins="https://app.example.com", _env_file=None).validate_for_runtime()


def test_security_headers_and_cors(client):
    r = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    assert r.headers["x-content-type-options"] == "nosniff" and r.headers["x-frame-options"] == "DENY"
    assert r.headers["access-control-allow-origin"] == "http://localhost:5173"
    evil = client.get("/api/health", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in evil.headers


def test_unhandled_error_hides_details(client):
    from app.main import app
    @app.get("/api/_boom")
    def boom(): raise ValueError("secret-connection-string-xyz")
    from fastapi.testclient import TestClient
    r = TestClient(app, raise_server_exceptions=False).get("/api/_boom")
    assert r.status_code == 500 and r.json() == {"detail": "Internal server error."}
    assert "secret" not in r.text
