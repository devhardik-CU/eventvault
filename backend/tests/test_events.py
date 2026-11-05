from .helpers import event_payload, future, make_event, signup


def test_create_edit_and_list(client):
    org, _ = signup(client, "o@example.com", "organizer")
    ev = make_event(client, org)
    assert ev["registered_count"] == 0 and ev["spots_left"] == 10 and ev["category_name"] == "Workshop"
    r = client.put(f"/api/events/{ev['id']}", json=event_payload(title="Renamed Workshop", capacity=20), headers=org)
    assert r.status_code == 200 and r.json()["title"] == "Renamed Workshop" and r.json()["capacity"] == 20
    assert [e["title"] for e in client.get("/api/events").json()] == ["Renamed Workshop"]
    assert len(client.get("/api/events/mine", headers=org).json()) == 1


def test_invalid_event_input(client):
    org, _ = signup(client, "o@example.com", "organizer")
    bad_cases = [
        {"title": "ab"}, {"title": "   "}, {"capacity": 0}, {"capacity": -5}, {"capacity": 10**7},
        {"start_time": future(-1), "end_time": future(1)},          # starts in the past
        {"start_time": future(7, 3), "end_time": future(7)},        # ends before it starts
        {"start_time": "not-a-date"}, {"description": "short"},
    ]
    for over in bad_cases:
        r = client.post("/api/events", json=event_payload(**over), headers=org)
        assert r.status_code == 422, over
    r = client.post("/api/events", json=event_payload(category_id=999), headers=org)
    assert r.status_code == 422
    missing = event_payload(); del missing["location"]
    assert client.post("/api/events", json=missing, headers=org).status_code == 422


def test_get_missing_event_404(client):
    assert client.get("/api/events/12345").status_code == 404


def test_search_and_category_filter(client):
    org, _ = signup(client, "o@example.com", "organizer")
    make_event(client, org, title="Python Workshop", category_id=1)
    make_event(client, org, title="Robotics Contest", description="Build and race robots.", category_id=3, location="Main Hall")
    assert len(client.get("/api/events", params={"q": "python"}).json()) == 1
    assert len(client.get("/api/events", params={"q": "main hall"}).json()) == 1
    assert len(client.get("/api/events", params={"category_id": 3}).json()) == 1
    assert client.get("/api/events", params={"q": "zzz"}).json() == []


def test_search_treats_sql_and_wildcards_as_plain_text(client):
    org, _ = signup(client, "o@example.com", "organizer")
    make_event(client, org)
    for evil in ("'; DROP TABLE events; --", "%", "_", "' OR '1'='1"):
        r = client.get("/api/events", params={"q": evil})
        assert r.status_code == 200 and r.json() == [], evil
    assert len(client.get("/api/events").json()) == 1  # table still intact


def test_cancelled_event_hidden_from_listing_but_viewable(client):
    org, _ = signup(client, "o@example.com", "organizer")
    ev = make_event(client, org)
    r = client.post(f"/api/events/{ev['id']}/cancel", headers=org)
    assert r.status_code == 200 and r.json()["status"] == "cancelled"
    assert client.get("/api/events").json() == []
    assert client.get(f"/api/events/{ev['id']}").json()["status"] == "cancelled"
    assert client.post(f"/api/events/{ev['id']}/cancel", headers=org).status_code == 409
    assert client.put(f"/api/events/{ev['id']}", json=event_payload(), headers=org).status_code == 409


def test_cannot_reduce_capacity_below_registrations(client):
    org, _ = signup(client, "o@example.com", "organizer")
    ev = make_event(client, org, capacity=5)
    for i in range(3):
        p, _ = signup(client, f"p{i}@example.com")
        assert client.post(f"/api/events/{ev['id']}/register", headers=p).status_code == 201
    assert client.put(f"/api/events/{ev['id']}", json=event_payload(capacity=2), headers=org).status_code == 409
    assert client.put(f"/api/events/{ev['id']}", json=event_payload(capacity=3), headers=org).status_code == 200


def test_user_cannot_see_other_organizers_events_in_mine(client):
    a, _ = signup(client, "a@example.com", "organizer")
    b, _ = signup(client, "b@example.com", "organizer")
    make_event(client, a)
    assert client.get("/api/events/mine", headers=b).json() == []
