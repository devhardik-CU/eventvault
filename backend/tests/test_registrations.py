import threading
from datetime import timedelta

from app.database import SessionLocal
from app.models import Event
from app.services.events import utcnow
from .helpers import make_event, signup


def _setup(client, capacity=10):
    org, _ = signup(client, "o@example.com", "organizer")
    return org, make_event(client, org, capacity=capacity)


def test_register_and_view(client):
    org, ev = _setup(client)
    p, _ = signup(client, "p@example.com")
    r = client.post(f"/api/events/{ev['id']}/register", headers=p)
    assert r.status_code == 201 and r.json()["status"] == "registered"
    mine = client.get("/api/registrations/mine", headers=p).json()
    assert len(mine) == 1 and mine[0]["event_title"] == "Python Workshop"
    detail = client.get(f"/api/events/{ev['id']}", headers=p).json()
    assert detail["registered_count"] == 1 and detail["spots_left"] == 9 and detail["is_registered"] is True
    assert client.get(f"/api/events/{ev['id']}").json()["is_registered"] is False  # anonymous view


def test_duplicate_registration_rejected(client):
    org, ev = _setup(client)
    p, _ = signup(client, "p@example.com")
    assert client.post(f"/api/events/{ev['id']}/register", headers=p).status_code == 201
    r = client.post(f"/api/events/{ev['id']}/register", headers=p)
    assert r.status_code == 409 and "already registered" in r.json()["detail"]
    assert client.get(f"/api/events/{ev['id']}").json()["registered_count"] == 1


def test_cancel_and_reregister_reuses_row(client):
    org, ev = _setup(client)
    p, _ = signup(client, "p@example.com")
    client.post(f"/api/events/{ev['id']}/register", headers=p)
    c = client.delete(f"/api/events/{ev['id']}/register", headers=p)
    assert c.status_code == 200 and c.json()["status"] == "cancelled" and c.json()["cancelled_at"]
    assert client.get(f"/api/events/{ev['id']}").json()["registered_count"] == 0
    assert client.delete(f"/api/events/{ev['id']}/register", headers=p).status_code == 404  # already cancelled
    r = client.post(f"/api/events/{ev['id']}/register", headers=p)
    assert r.status_code == 201
    assert len(client.get("/api/registrations/mine", headers=p).json()) == 1


def test_cancel_without_registration_404(client):
    org, ev = _setup(client)
    p, _ = signup(client, "p@example.com")
    assert client.delete(f"/api/events/{ev['id']}/register", headers=p).status_code == 404


def test_cannot_cancel_someone_elses_registration(client):
    org, ev = _setup(client)
    p1, _ = signup(client, "p1@example.com")
    p2, _ = signup(client, "p2@example.com")
    client.post(f"/api/events/{ev['id']}/register", headers=p1)
    assert client.delete(f"/api/events/{ev['id']}/register", headers=p2).status_code == 404
    assert client.get(f"/api/events/{ev['id']}").json()["registered_count"] == 1


def test_full_event_rejects_then_frees_spot_after_cancel(client):
    org, ev = _setup(client, capacity=2)
    users = [signup(client, f"p{i}@example.com")[0] for i in range(3)]
    assert client.post(f"/api/events/{ev['id']}/register", headers=users[0]).status_code == 201
    assert client.post(f"/api/events/{ev['id']}/register", headers=users[1]).status_code == 201
    r = client.post(f"/api/events/{ev['id']}/register", headers=users[2])
    assert r.status_code == 409 and "full" in r.json()["detail"]
    client.delete(f"/api/events/{ev['id']}/register", headers=users[0])
    assert client.post(f"/api/events/{ev['id']}/register", headers=users[2]).status_code == 201


def test_register_unknown_event_404(client):
    p, _ = signup(client, "p@example.com")
    assert client.post("/api/events/999/register", headers=p).status_code == 404


def test_cancelled_event_not_registrable(client):
    org, ev = _setup(client)
    p, _ = signup(client, "p@example.com")
    client.post(f"/api/events/{ev['id']}/cancel", headers=org)
    assert client.post(f"/api/events/{ev['id']}/register", headers=p).status_code == 409


def test_started_event_closed_for_registration_and_cancellation(client):
    org, ev = _setup(client)
    p, _ = signup(client, "p@example.com")
    client.post(f"/api/events/{ev['id']}/register", headers=p)
    with SessionLocal() as db:  # move the event into the past directly
        e = db.get(Event, ev["id"])
        e.start_time, e.end_time = utcnow() - timedelta(hours=2), utcnow() + timedelta(hours=1)
        db.commit()
    assert client.delete(f"/api/events/{ev['id']}/register", headers=p).status_code == 409
    p2, _ = signup(client, "p2@example.com")
    assert client.post(f"/api/events/{ev['id']}/register", headers=p2).status_code == 409


def test_attendee_list_for_owner(client):
    org, ev = _setup(client)
    p, _ = signup(client, "p@example.com", name="Pat Participant")
    client.post(f"/api/events/{ev['id']}/register", headers=p)
    rows = client.get(f"/api/events/{ev['id']}/attendees", headers=org).json()
    assert [r["full_name"] for r in rows] == ["Pat Participant"]


def test_concurrent_double_click_creates_one_registration(client):
    org, ev = _setup(client)
    p, _ = signup(client, "p@example.com")
    codes = []
    def go():
        codes.append(client.post(f"/api/events/{ev['id']}/register", headers=p).status_code)
    threads = [threading.Thread(target=go) for _ in range(6)]
    [t.start() for t in threads]; [t.join() for t in threads]
    assert codes.count(201) == 1, codes
    assert set(codes) <= {201, 409}, codes
    assert client.get(f"/api/events/{ev['id']}").json()["registered_count"] == 1


def test_concurrent_registrations_never_exceed_capacity(client):
    org, ev = _setup(client, capacity=3)
    users = [signup(client, f"p{i}@example.com")[0] for i in range(8)]
    codes = []
    def go(h):
        codes.append(client.post(f"/api/events/{ev['id']}/register", headers=h).status_code)
    threads = [threading.Thread(target=go, args=(h,)) for h in users]
    [t.start() for t in threads]; [t.join() for t in threads]
    assert codes.count(201) == 3, codes
    assert client.get(f"/api/events/{ev['id']}").json()["registered_count"] == 3
