"""Development seed data. FOR LOCAL DEMOS ONLY -- never run against a production database.
Usage (from backend/):  python -m app.seed"""
import os
from datetime import timedelta

from .database import SessionLocal
from .db_objects import init_db
from .models import Category, Event, Registration, Role, User
from .security import hash_password
from .services.events import utcnow

DEMO_PASSWORD = os.environ.get("SEED_PASSWORD") or "DemoPass123"

ORGANIZERS = [("Priya Sharma", "organizer@eventvault.demo"), ("Rahul Verma", "organizer2@eventvault.demo")]
PARTICIPANTS = [("Ananya Singh", "participant@eventvault.demo"), ("Karan Mehta", "karan@eventvault.demo"),
                ("Sara Khan", "sara@eventvault.demo"), ("Dev Patel", "dev@eventvault.demo")]

EVENTS = [  # (title, description, location, days_from_now, hours, capacity, category, organizer_index)
    ("Intro to Python Workshop", "A hands-on beginner workshop covering variables, loops and functions. Bring your laptop.", "Computer Lab 2", 5, 3, 30, "Workshop", 0),
    ("AI & Society Seminar", "A guest seminar on how machine learning is reshaping industries, with a Q&A session.", "Main Auditorium", 9, 2, 120, "Seminar", 0),
    ("Inter-College Hackathon", "A 24-hour team hackathon. Build something useful, win prizes, and meet mentors.", "Innovation Centre", 14, 24, 60, "Competition", 1),
    ("Annual Cultural Evening", "Music, dance and drama performances by student clubs. Everyone is welcome.", "Open Air Theatre", 20, 4, 300, "Cultural", 1),
    ("Resume & Interview Clinic", "One-to-one resume reviews and mock interviews with alumni volunteers.", "Placement Cell", 3, 4, 3, "Networking", 0),
    ("Campus 5K Fun Run", "A relaxed 5-kilometre run around campus. All fitness levels, medals for finishers.", "Sports Ground", 12, 2, 100, "Sports", 1),
]


def run() -> None:
    init_db()
    with SessionLocal() as db:
        if db.query(User).filter(User.email.like("%@eventvault.demo")).first():
            print("Seed data already present - nothing to do.")
            return
        roles = {r.name: r.id for r in db.query(Role)}
        cats = {c.name: c.id for c in db.query(Category)}
        pw = hash_password(DEMO_PASSWORD)
        orgs = [User(full_name=n, email=e, password_hash=pw, role_id=roles["organizer"]) for n, e in ORGANIZERS]
        parts = [User(full_name=n, email=e, password_hash=pw, role_id=roles["participant"]) for n, e in PARTICIPANTS]
        db.add_all(orgs + parts)
        db.flush()
        now = utcnow().replace(minute=0, second=0, microsecond=0)
        events = []
        for title, desc, loc, days, hrs, cap, cat, oi in EVENTS:
            start = now + timedelta(days=days, hours=2)
            events.append(Event(title=title, description=desc, location=loc, start_time=start, end_time=start + timedelta(hours=hrs),
                                capacity=cap, category_id=cats[cat], organizer_id=orgs[oi].id, status="published"))
        db.add_all(events)
        db.flush()
        # a few registrations so analytics has data; the clinic (capacity 3) is nearly full
        plan = {0: [0, 1, 2], 1: [0, 1, 2, 3], 2: [1, 3], 4: [0, 1, 2], 5: [2]}
        for ei, pis in plan.items():
            for pi in pis:
                db.add(Registration(user_id=parts[pi].id, event_id=events[ei].id, status="registered"))
        db.commit()
        print(f"Seeded {len(orgs)} organizers, {len(parts)} participants, {len(events)} events.")
        print(f"Demo logins (password: {DEMO_PASSWORD}): organizer@eventvault.demo, participant@eventvault.demo")


if __name__ == "__main__":
    run()
