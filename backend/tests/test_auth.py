from sqlalchemy import text

from app.database import engine
from .helpers import PASSWORD, signup


def test_register_and_me(client):
    h, user = signup(client, "a@example.com")
    assert user["role_name"] == "participant"
    r = client.get("/api/auth/me", headers=h)
    assert r.status_code == 200 and r.json()["email"] == "a@example.com"


def test_password_is_hashed_in_database(client):
    signup(client, "a@example.com")
    with engine.connect() as c:
        stored = c.execute(text("SELECT password_hash FROM users")).scalar()
    assert stored != PASSWORD and stored.startswith("$2")


def test_duplicate_email_rejected_case_insensitive(client):
    signup(client, "a@example.com")
    r = client.post("/api/auth/register", json={"full_name": "X Y", "email": "A@Example.com", "password": PASSWORD})
    assert r.status_code == 409


def test_login_success_and_failures(client):
    signup(client, "a@example.com")
    ok = client.post("/api/auth/login", json={"email": "a@example.com", "password": PASSWORD})
    assert ok.status_code == 200 and ok.json()["access_token"]
    bad = client.post("/api/auth/login", json={"email": "a@example.com", "password": "WrongPass123"})
    unknown = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": PASSWORD})
    assert bad.status_code == 401 and unknown.status_code == 401
    assert bad.json() == unknown.json()  # same message: doesn't reveal which emails exist


def test_invalid_registration_input(client):
    base = {"full_name": "Valid Name", "email": "a@example.com", "password": PASSWORD}
    for override in ({"password": "short1"}, {"password": "allletters"}, {"password": "12345678"},
                     {"email": "not-an-email"}, {"full_name": "A"}, {"role": "admin"}, {"password": "a1" * 40}):
        r = client.post("/api/auth/register", json={**base, **override})
        assert r.status_code == 422, override
        assert r.json()["detail"] == "Validation failed."


def test_missing_or_bad_token(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_token_for_deleted_user_rejected(client):
    h, user = signup(client, "a@example.com")
    with engine.begin() as c:
        c.execute(text("DELETE FROM activity_logs"))
        c.execute(text("DELETE FROM users WHERE id=:i"), {"i": user["id"]})
    assert client.get("/api/auth/me", headers=h).status_code == 401
