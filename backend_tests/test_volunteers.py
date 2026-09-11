import pytest
from app import create_app, db

CFG = {"TESTING":True,"SQLALCHEMY_DATABASE_URI":"sqlite:///:memory:","JWT_SECRET_KEY":"test-secret-key-long-enough-32ch"}

@pytest.fixture
def client():
    app = create_app(CFG)
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.drop_all()

def login(client, email="admin@tulaindia.org", pwd="admin123"):
    r = client.post("/api/v1/auth/login", json={"email":email,"password":pwd})
    return {"Authorization": f"Bearer {r.get_json()['data']['access_token']}"}

def make_vol(client):
    client.post("/api/v1/auth/register", json={"name":"Vol","email":"vol@t.com","password":"pass123","role":"volunteer"})
    return login(client,"vol@t.com","pass123")

def make_event(client, h):
    r = client.post("/api/v1/events", headers=h, json={"title":"Expo","event_type":"exhibition","city":"Chennai"})
    return r.get_json()["data"]["event"]["id"]

# AVAILABILITY
def test_submit_availability(client):
    h = login(client); vh = make_vol(client); eid = make_event(client, h)
    r = client.post("/api/v1/volunteers/availability", headers=vh, json={"event_id":eid,"preferred_slots":"morning,afternoon"})
    assert r.status_code == 201
    assert r.get_json()["data"]["availability"]["preferred_slots"] == "morning,afternoon"

def test_submit_availability_duplicate(client):
    h = login(client); vh = make_vol(client); eid = make_event(client, h)
    client.post("/api/v1/volunteers/availability", headers=vh, json={"event_id":eid})
    assert client.post("/api/v1/volunteers/availability", headers=vh, json={"event_id":eid}).status_code == 400

def test_submit_availability_bad_event(client):
    vh = make_vol(client)
    assert client.post("/api/v1/volunteers/availability", headers=vh, json={"event_id":"bad"}).status_code == 404

def test_submit_availability_missing_event_id(client):
    vh = make_vol(client)
    assert client.post("/api/v1/volunteers/availability", headers=vh, json={}).status_code == 400

def test_list_availability(client):
    h = login(client); vh = make_vol(client); eid = make_event(client, h)
    client.post("/api/v1/volunteers/availability", headers=vh, json={"event_id":eid})
    r = client.get(f"/api/v1/volunteers/availability?event_id={eid}", headers=h)
    assert r.status_code == 200
    assert r.get_json()["data"]["count"] == 1

# SHIFTS
def test_assign_shift(client):
    h = login(client); vh = make_vol(client); eid = make_event(client, h)
    from app.models.user import User
    from app import db as _db
    with client.application.app_context():
        vol = User.query.filter_by(email="vol@t.com").first()
        vid = vol.id
    r = client.post("/api/v1/volunteers/shifts", headers=h, json={"volunteer_id":vid,"event_id":eid,"time_slot":"morning"})
    assert r.status_code == 201

def test_assign_shift_duplicate(client):
    h = login(client); make_vol(client); eid = make_event(client, h)
    with client.application.app_context():
        from app.models.user import User
        vid = User.query.filter_by(email="vol@t.com").first().id
    client.post("/api/v1/volunteers/shifts", headers=h, json={"volunteer_id":vid,"event_id":eid,"time_slot":"morning"})
    assert client.post("/api/v1/volunteers/shifts", headers=h, json={"volunteer_id":vid,"event_id":eid,"time_slot":"afternoon"}).status_code == 400

def test_assign_shift_bad_event(client):
    h = login(client)
    assert client.post("/api/v1/volunteers/shifts", headers=h, json={"volunteer_id":"v","event_id":"bad","time_slot":"morning"}).status_code == 404

def test_assign_shift_missing_fields(client):
    h = login(client)
    assert client.post("/api/v1/volunteers/shifts", headers=h, json={"volunteer_id":"v"}).status_code == 400

def test_assign_shift_forbidden(client):
    make_vol(client); vh = make_vol(client)
    assert client.post("/api/v1/volunteers/shifts", headers=vh, json={"volunteer_id":"v","event_id":"e","time_slot":"m"}).status_code == 403

def test_list_shifts(client):
    h = login(client); make_vol(client); eid = make_event(client, h)
    with client.application.app_context():
        from app.models.user import User
        vid = User.query.filter_by(email="vol@t.com").first().id
    client.post("/api/v1/volunteers/shifts", headers=h, json={"volunteer_id":vid,"event_id":eid,"time_slot":"morning"})
    r = client.get(f"/api/v1/volunteers/shifts?event_id={eid}", headers=h)
    assert r.status_code == 200
    assert r.get_json()["data"]["count"] == 1

def test_update_shift_status(client):
    h = login(client); make_vol(client); eid = make_event(client, h)
    with client.application.app_context():
        from app.models.user import User
        vid = User.query.filter_by(email="vol@t.com").first().id
    sid = client.post("/api/v1/volunteers/shifts", headers=h, json={"volunteer_id":vid,"event_id":eid,"time_slot":"morning"}).get_json()["data"]["shift"]["id"]
    r = client.patch(f"/api/v1/volunteers/shifts/{sid}", headers=h, json={"status":"confirmed"})
    assert r.status_code == 200
    assert r.get_json()["data"]["shift"]["status"] == "confirmed"
    assert r.get_json()["data"]["shift"]["confirmed_at"] is not None

def test_update_shift_invalid_status(client):
    h = login(client); make_vol(client); eid = make_event(client, h)
    with client.application.app_context():
        from app.models.user import User
        vid = User.query.filter_by(email="vol@t.com").first().id
    sid = client.post("/api/v1/volunteers/shifts", headers=h, json={"volunteer_id":vid,"event_id":eid,"time_slot":"morning"}).get_json()["data"]["shift"]["id"]
    assert client.patch(f"/api/v1/volunteers/shifts/{sid}", headers=h, json={"status":"done"}).status_code == 400

def test_volunteer_dashboard(client):
    h = login(client); make_vol(client); eid = make_event(client, h)
    with client.application.app_context():
        from app.models.user import User
        vid = User.query.filter_by(email="vol@t.com").first().id
    client.post("/api/v1/volunteers/shifts", headers=h, json={"volunteer_id":vid,"event_id":eid,"time_slot":"morning"})
    r = client.get(f"/api/v1/volunteers/dashboard/{eid}", headers=h)
    assert r.status_code == 200
    data = r.get_json()["data"]
    assert "shifts" in data and "availabilities" in data

def test_dashboard_bad_event(client):
    h = login(client)
    assert client.get("/api/v1/volunteers/dashboard/bad", headers=h).status_code == 404
