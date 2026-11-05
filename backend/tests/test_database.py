"""Database-level behaviour (SQLite dev database). These do NOT prove SQL Server compatibility."""
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.database import SessionLocal, engine
from app.models import Event, Registration, User
from app.security import hash_password
from app.services.events import utcnow
from datetime import timedelta
from .helpers import make_event, signup


def _event_kwargs(**o):
    k = dict(title="T title", description="d" * 12, location="L", start_time=utcnow() + timedelta(days=1),
             end_time=utcnow() + timedelta(days=1, hours=1), capacity=2, organizer_id=1, category_id=1, status="published")
    k.update(o)
    return k


def _seed(client):
    org, _ = signup(client, "o@example.com", "organizer")
    return org, make_event(client, org, capacity=2)


def test_unique_constraint_blocks_duplicate_registration(client):
    _, ev = _seed(client)
    _, user = signup(client, "p@example.com")
    with SessionLocal() as db:
        db.add(Registration(user_id=user["id"], event_id=ev["id"], status="registered")); db.commit()
        db.add(Registration(user_id=user["id"], event_id=ev["id"], status="registered"))
        with pytest.raises(IntegrityError):
            db.commit()


def test_foreign_keys_enforced(client):
    with SessionLocal() as db:
        db.add(Registration(user_id=999, event_id=999, status="registered"))
        with pytest.raises(IntegrityError):
            db.commit()


def test_check_constraints(client):
    _seed(client)
    for bad in (dict(capacity=0), dict(end_time=utcnow()), dict(status="weird")):
        with SessionLocal() as db:
            db.add(Event(**_event_kwargs(**bad)))
            with pytest.raises(IntegrityError):
                db.commit()


def test_not_null_and_unique_email(client):
    signup(client, "p@example.com")
    with SessionLocal() as db:
        db.add(User(full_name="Dup", email="p@example.com", password_hash=hash_password("x1x1x1x1"), role_id=1))
        with pytest.raises(IntegrityError):
            db.commit()


def test_capacity_trigger_blocks_overbooking_even_bypassing_the_api(client):
    _, ev = _seed(client)  # capacity 2
    users = [signup(client, f"p{i}@example.com")[1] for i in range(3)]
    with SessionLocal() as db:
        for u in users[:2]:
            db.add(Registration(user_id=u["id"], event_id=ev["id"], status="registered"))
        db.commit()
        db.add(Registration(user_id=users[2]["id"], event_id=ev["id"], status="registered"))
        with pytest.raises(DBAPIError, match="capacity"):
            db.commit()


def test_view_matches_registration_table_and_uses_joins(client):
    org, ev = _seed(client)
    p1, _ = signup(client, "p1@example.com"); p2, _ = signup(client, "p2@example.com")
    client.post(f"/api/events/{ev['id']}/register", headers=p1)
    client.post(f"/api/events/{ev['id']}/register", headers=p2)
    client.delete(f"/api/events/{ev['id']}/register", headers=p2)
    with engine.connect() as c:
        row = c.execute(text("SELECT category_name, registered_count, cancelled_count FROM vw_event_stats WHERE event_id=:i"), {"i": ev["id"]}).one()
        direct = c.execute(text("SELECT COUNT(*) FROM registrations WHERE event_id=:i AND status='registered'"), {"i": ev["id"]}).scalar()
    assert tuple(row) == ("Workshop", 1, 1) and direct == 1


def test_event_with_no_registrations_appears_in_view_with_zero(client):
    _, ev = _seed(client)
    with engine.connect() as c:
        assert c.execute(text("SELECT registered_count FROM vw_event_stats WHERE event_id=:i"), {"i": ev["id"]}).scalar() == 0


def test_activity_log_records_important_actions(client):
    org, ev = _seed(client)
    p, _ = signup(client, "p@example.com")
    client.post(f"/api/events/{ev['id']}/register", headers=p)
    client.delete(f"/api/events/{ev['id']}/register", headers=p)
    with engine.connect() as c:
        actions = {r[0] for r in c.execute(text("SELECT action FROM activity_logs"))}
    assert {"user_registered", "event_created", "registration_created", "registration_cancelled"} <= actions


def test_failed_registration_rolls_back_cleanly(client):
    """A rejected registration must leave no registration row and no 'created' audit row."""
    org, ev = _seed(client)
    ps = [signup(client, f"p{i}@example.com")[0] for i in range(3)]
    for h in ps:
        client.post(f"/api/events/{ev['id']}/register", headers=h)  # third is rejected (capacity 2)
    with engine.connect() as c:
        regs = c.execute(text("SELECT COUNT(*) FROM registrations")).scalar()
        logs = c.execute(text("SELECT COUNT(*) FROM activity_logs WHERE action='registration_created'")).scalar()
    assert regs == 2 and logs == 2
