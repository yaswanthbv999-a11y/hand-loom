import pytest
from app import create_app, db

CFG = {"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "JWT_SECRET_KEY": "test-secret-key-long-enough-32ch"}

@pytest.fixture
def client():
    app = create_app(CFG)
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.drop_all()

def login(client):
    r = client.post("/api/v1/auth/login", json={"email":"admin@tulaindia.org","password":"admin123"})
    return {"Authorization": f"Bearer {r.get_json()['data']['access_token']}"}

def make_batch(client, h):
    r = client.post("/api/v1/batches", headers=h, json={"farmer_id":"f1"})
    return r.get_json()["data"]["batch"]["id"]

# CREATE
def test_create_payment_success(client):
    h = login(client)
    r = client.post("/api/v1/payments", headers=h, json={"payee_id":"farmer-1","payee_type":"farmer","amount":5000,"mode":"upi"})
    assert r.status_code == 201
    assert r.get_json()["data"]["payment"]["amount"] == 5000

def test_create_payment_with_batch(client):
    h = login(client)
    bid = make_batch(client, h)
    r = client.post("/api/v1/payments", headers=h, json={"payee_id":"artisan-1","payee_type":"artisan","amount":2000,"mode":"bank_transfer","batch_id":bid})
    assert r.status_code == 201
    assert r.get_json()["data"]["payment"]["batch_id"] == bid

def test_create_payment_invalid_batch(client):
    h = login(client)
    r = client.post("/api/v1/payments", headers=h, json={"payee_id":"a1","payee_type":"artisan","amount":100,"mode":"cash","batch_id":"bad-id"})
    assert r.status_code == 404

def test_create_payment_missing_fields(client):
    h = login(client)
    r = client.post("/api/v1/payments", headers=h, json={"payee_id":"f1"})
    assert r.status_code == 400

def test_create_payment_invalid_payee_type(client):
    h = login(client)
    r = client.post("/api/v1/payments", headers=h, json={"payee_id":"x","payee_type":"vendor","amount":100,"mode":"upi"})
    assert r.status_code == 400

def test_create_payment_invalid_mode(client):
    h = login(client)
    r = client.post("/api/v1/payments", headers=h, json={"payee_id":"x","payee_type":"farmer","amount":100,"mode":"crypto"})
    assert r.status_code == 400

def test_create_payment_negative_amount(client):
    h = login(client)
    r = client.post("/api/v1/payments", headers=h, json={"payee_id":"x","payee_type":"farmer","amount":-100,"mode":"upi"})
    assert r.status_code == 400

def test_create_payment_zero_amount(client):
    h = login(client)
    r = client.post("/api/v1/payments", headers=h, json={"payee_id":"x","payee_type":"farmer","amount":0,"mode":"cash"})
    assert r.status_code == 400

# LIST
def test_list_payments(client):
    h = login(client)
    client.post("/api/v1/payments", headers=h, json={"payee_id":"f1","payee_type":"farmer","amount":1000,"mode":"upi"})
    r = client.get("/api/v1/payments", headers=h)
    assert r.status_code == 200
    assert r.get_json()["data"]["count"] >= 1

def test_list_filter_by_payee_type(client):
    h = login(client)
    client.post("/api/v1/payments", headers=h, json={"payee_id":"f1","payee_type":"farmer","amount":500,"mode":"cash"})
    r = client.get("/api/v1/payments?payee_type=farmer", headers=h)
    assert all(p["payee_type"] == "farmer" for p in r.get_json()["data"]["payments"])

def test_list_filter_by_status(client):
    h = login(client)
    client.post("/api/v1/payments", headers=h, json={"payee_id":"f1","payee_type":"farmer","amount":500,"mode":"cash"})
    r = client.get("/api/v1/payments?status=pending", headers=h)
    assert r.status_code == 200

# GET
def test_get_payment_by_id(client):
    h = login(client)
    pid = client.post("/api/v1/payments", headers=h, json={"payee_id":"f1","payee_type":"farmer","amount":300,"mode":"upi"}).get_json()["data"]["payment"]["id"]
    r = client.get(f"/api/v1/payments/{pid}", headers=h)
    assert r.status_code == 200
    assert r.get_json()["data"]["payment"]["id"] == pid

def test_get_payment_not_found(client):
    h = login(client)
    assert client.get("/api/v1/payments/bad-id", headers=h).status_code == 404

# STATUS UPDATE
def test_update_status_completed(client):
    h = login(client)
    pid = client.post("/api/v1/payments", headers=h, json={"payee_id":"f1","payee_type":"farmer","amount":300,"mode":"upi"}).get_json()["data"]["payment"]["id"]
    r = client.patch(f"/api/v1/payments/{pid}/status", headers=h, json={"status":"completed"})
    assert r.status_code == 200
    assert r.get_json()["data"]["payment"]["status"] == "completed"

def test_update_status_invalid(client):
    h = login(client)
    pid = client.post("/api/v1/payments", headers=h, json={"payee_id":"f1","payee_type":"farmer","amount":300,"mode":"upi"}).get_json()["data"]["payment"]["id"]
    assert client.patch(f"/api/v1/payments/{pid}/status", headers=h, json={"status":"approved"}).status_code == 400

def test_update_status_not_found(client):
    h = login(client)
    assert client.patch("/api/v1/payments/bad/status", headers=h, json={"status":"completed"}).status_code == 404

# SUMMARY
def test_payee_summary(client):
    h = login(client)
    client.post("/api/v1/payments", headers=h, json={"payee_id":"farmer-99","payee_type":"farmer","amount":1000,"mode":"upi"})
    client.post("/api/v1/payments", headers=h, json={"payee_id":"farmer-99","payee_type":"farmer","amount":2000,"mode":"cash"})
    r = client.get("/api/v1/payments/summary/farmer/farmer-99", headers=h)
    assert r.status_code == 200
    assert r.get_json()["data"]["summary"]["total_records"] == 2

def test_payee_summary_invalid_type(client):
    h = login(client)
    assert client.get("/api/v1/payments/summary/vendor/x", headers=h).status_code == 400

def test_no_token(client):
    assert client.get("/api/v1/payments").status_code == 401
