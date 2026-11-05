from .helpers import event_payload, make_event, signup


def test_unauthenticated_cannot_create_event(client):
    assert client.post("/api/events", json=event_payload()).status_code == 401


def test_participant_cannot_create_event(client):
    h, _ = signup(client, "p@example.com", "participant")
    assert client.post("/api/events", json=event_payload(), headers=h).status_code == 403


def test_organizer_cannot_register_for_events(client):
    org, _ = signup(client, "o@example.com", "organizer")
    ev = make_event(client, org)
    assert client.post(f"/api/events/{ev['id']}/register", headers=org).status_code == 403


def test_other_organizer_cannot_modify_event(client):
    a, _ = signup(client, "a@example.com", "organizer")
    b, _ = signup(client, "b@example.com", "organizer")
    ev = make_event(client, a)
    assert client.put(f"/api/events/{ev['id']}", json=event_payload(title="Hacked title"), headers=b).status_code == 403
    assert client.post(f"/api/events/{ev['id']}/cancel", headers=b).status_code == 403
    assert client.get(f"/api/events/{ev['id']}/attendees", headers=b).status_code == 403
    assert client.post(f"/api/events/{ev['id']}/poster", files={"file": ("p.png", b"x", "image/png")}, headers=b).status_code == 403
    assert client.get(f"/api/events/{ev['id']}").json()["title"] == "Python Workshop"


def test_participant_blocked_from_organizer_endpoints(client):
    h, _ = signup(client, "p@example.com", "participant")
    assert client.get("/api/analytics/organizer", headers=h).status_code == 403
    assert client.get("/api/events/mine", headers=h).status_code == 403


def test_organizer_blocked_from_participant_endpoints(client):
    o, _ = signup(client, "o@example.com", "organizer")
    assert client.get("/api/registrations/mine", headers=o).status_code == 403


def test_role_cannot_be_forged_via_token_claims(client):
    """The backend re-reads the role from the database, not from the token."""
    import jwt
    from app.config import get_settings
    h, user = signup(client, "p@example.com", "participant")
    forged = jwt.encode({"sub": str(user["id"]), "role": "organizer", "exp": 9999999999}, get_settings().secret_key, algorithm="HS256")
    r = client.post("/api/events", json=event_payload(), headers={"Authorization": f"Bearer {forged}"})
    assert r.status_code == 403


def test_token_signed_with_wrong_key_rejected(client):
    import jwt
    forged = jwt.encode({"sub": "1", "exp": 9999999999}, "some-other-key-that-is-long-enough-123456", algorithm="HS256")
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {forged}"}).status_code == 401
