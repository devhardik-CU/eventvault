from datetime import datetime, timedelta, timezone

PASSWORD = "TestPass123"


def future(days=7, hours=0):
    return (datetime.now(timezone.utc) + timedelta(days=days, hours=hours)).replace(microsecond=0).isoformat()


def signup(client, email, role="participant", name="Test User", password=PASSWORD):
    r = client.post("/api/auth/register", json={"full_name": name, "email": email, "password": password, "role": role})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}, r.json()["user"]


def event_payload(**over):
    p = {"title": "Python Workshop", "description": "Learn the basics of Python.", "location": "Lab 1",
         "start_time": future(7), "end_time": future(7, 2), "capacity": 10, "category_id": 1}
    p.update(over)
    return p


def make_event(client, headers, **over):
    r = client.post("/api/events", json=event_payload(**over), headers=headers)
    assert r.status_code == 201, r.text
    return r.json()
