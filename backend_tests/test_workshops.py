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

def make_workshop(client, h, capacity=10):
    r = client.post("/api/v1/workshops", headers=h, json={"title":"Spin101","workshop_type":"spinning","capacity":capacity,"fee":500})
    return r.get_json()["data"]["workshop"]["id"]

def make_customer(client):
    client.post("/api/v1/auth/register", json={"name":"Cust","email":"cust@test.com","password":"pass123","role":"customer"})
    return login(client, "cust@test.com", "pass123")

# CREATE
def test_create_workshop(client):
    h = login(client)
    r = client.post("/api/v1/workshops", headers=h, json={"title":"Weave101","workshop_type":"weaving","capacity":15,"fee":300})
    assert r.status_code == 201
    assert r.get_json()["data"]["workshop"]["workshop_type"] == "weaving"

def test_create_workshop_invalid_type(client):
    h = login(client)
    r = client.post("/api/v1/workshops", headers=h, json={"title":"X","workshop_type":"knitting","capacity":10})
    assert r.status_code == 400

def test_create_workshop_missing_fields(client):
    h = login(client)
    assert client.post("/api/v1/workshops", headers=h, json={"title":"X"}).status_code == 400

def test_create_workshop_zero_capacity(client):
    h = login(client)
    assert client.post("/api/v1/workshops", headers=h, json={"title":"X","workshop_type":"dyeing","capacity":0}).status_code == 400

def test_create_workshop_forbidden(client):
    make_customer(client)
    ch = make_customer(client)
    assert client.post("/api/v1/workshops", headers=ch, json={"title":"X","workshop_type":"spinning","capacity":5}).status_code == 403

# LIST
def test_list_workshops(client):
    h = login(client)
    make_workshop(client, h)
    r = client.get("/api/v1/workshops", headers=h)
    assert r.status_code == 200
    assert r.get_json()["data"]["count"] >= 1

def test_filter_by_type(client):
    h = login(client)
    make_workshop(client, h)
    r = client.get("/api/v1/workshops?workshop_type=spinning", headers=h)
    assert all(w["workshop_type"] == "spinning" for w in r.get_json()["data"]["workshops"])

# GET
def test_get_workshop(client):
    h = login(client)
    wid = make_workshop(client, h)
    r = client.get(f"/api/v1/workshops/{wid}", headers=h)
    assert r.status_code == 200
    assert "registrations" in r.get_json()["data"]

def test_get_workshop_not_found(client):
    h = login(client)
    assert client.get("/api/v1/workshops/bad", headers=h).status_code == 404

# UPDATE
def test_update_workshop(client):
    h = login(client)
    wid = make_workshop(client, h)
    r = client.put(f"/api/v1/workshops/{wid}", headers=h, json={"venue":"Chennai Studio","fee":600})
    assert r.status_code == 200
    assert r.get_json()["data"]["workshop"]["fee"] == 600

# REGISTER
def test_register_for_workshop(client):
    h = login(client)
    wid = make_workshop(client, h)
    ch = make_customer(client)
    r = client.post(f"/api/v1/workshops/{wid}/register", headers=ch)
    assert r.status_code == 201
    assert r.get_json()["data"]["registration"]["confirmation_sent"] is True

def test_register_duplicate(client):
    h = login(client)
    wid = make_workshop(client, h)
    ch = make_customer(client)
    client.post(f"/api/v1/workshops/{wid}/register", headers=ch)
    assert client.post(f"/api/v1/workshops/{wid}/register", headers=ch).status_code == 400

def test_register_full_workshop(client):
    h = login(client)
    wid = make_workshop(client, h, capacity=1)
    ch = make_customer(client)
    client.post(f"/api/v1/workshops/{wid}/register", headers=ch)
    # second customer
    client.post("/api/v1/auth/register", json={"name":"C2","email":"c2@test.com","password":"pass123","role":"customer"})
    ch2 = login(client,"c2@test.com","pass123")
    assert client.post(f"/api/v1/workshops/{wid}/register", headers=ch2).status_code == 400

# PAYMENT STATUS
def test_update_registration_payment(client):
    h = login(client)
    wid = make_workshop(client, h)
    ch = make_customer(client)
    rid = client.post(f"/api/v1/workshops/{wid}/register", headers=ch).get_json()["data"]["registration"]["id"]
    r = client.patch(f"/api/v1/workshops/registrations/{rid}/payment", headers=h, json={"payment_status":"paid"})
    assert r.status_code == 200
    assert r.get_json()["data"]["registration"]["payment_status"] == "paid"

def test_update_payment_invalid_status(client):
    h = login(client)
    wid = make_workshop(client, h)
    ch = make_customer(client)
    rid = client.post(f"/api/v1/workshops/{wid}/register", headers=ch).get_json()["data"]["registration"]["id"]
    assert client.patch(f"/api/v1/workshops/registrations/{rid}/payment", headers=h, json={"payment_status":"free"}).status_code == 400
