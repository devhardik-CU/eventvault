from .helpers import make_event, signup


def test_analytics_empty_organizer(client):
    org, _ = signup(client, "o@example.com", "organizer")
    d = client.get("/api/analytics/organizer", headers=org).json()
    assert d["total_events"] == 0 and d["total_registrations"] == 0 and d["average_fill_rate_percent"] == 0.0
    assert d["events"] == [] and len(d["registrations_last_14_days"]) == 14


def test_analytics_calculations_match_persisted_data(client):
    org, _ = signup(client, "o@example.com", "organizer")
    e1 = make_event(client, org, title="Event One", capacity=4, category_id=1)     # will have 2 active, 1 cancelled
    e2 = make_event(client, org, title="Event Two", capacity=10, category_id=3)    # will have 1 active
    e3 = make_event(client, org, title="Event Three", capacity=5, category_id=1)   # will be cancelled by organizer
    ps = [signup(client, f"p{i}@example.com")[0] for i in range(3)]
    for h in ps[:3]:
        client.post(f"/api/events/{e1['id']}/register", headers=h)
    client.delete(f"/api/events/{e1['id']}/register", headers=ps[2])
    client.post(f"/api/events/{e2['id']}/register", headers=ps[0])
    client.post(f"/api/events/{e3['id']}/cancel", headers=org)

    d = client.get("/api/analytics/organizer", headers=org).json()
    assert d["total_events"] == 3
    assert d["cancelled_events"] == 1
    assert d["upcoming_events"] == 2
    assert d["total_registrations"] == 3          # 2 on e1 + 1 on e2
    assert d["total_cancellations"] == 1
    # fill rates: e1 = 2/4 = 50%, e2 = 1/10 = 10%  -> mean of the two non-cancelled events = 30%
    assert d["average_fill_rate_percent"] == 30.0
    by_title = {e["title"]: e for e in d["events"]}
    assert by_title["Event One"]["registered_count"] == 2 and by_title["Event One"]["fill_rate_percent"] == 50.0
    assert by_title["Event One"]["cancelled_count"] == 1
    cats = {c["category_name"]: c for c in d["by_category"]}
    assert cats["Workshop"] == {"category_name": "Workshop", "events": 1, "registrations": 2}
    assert cats["Competition"]["registrations"] == 1
    assert sum(x["registrations"] for x in d["registrations_last_14_days"]) == 3


def test_analytics_only_counts_own_events(client):
    a, _ = signup(client, "a@example.com", "organizer")
    b, _ = signup(client, "b@example.com", "organizer")
    ev = make_event(client, a)
    p, _ = signup(client, "p@example.com")
    client.post(f"/api/events/{ev['id']}/register", headers=p)
    assert client.get("/api/analytics/organizer", headers=b).json()["total_events"] == 0
    assert client.get("/api/analytics/organizer", headers=a).json()["total_registrations"] == 1
