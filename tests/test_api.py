import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
def test_health():
    r=client.get('/api/health'); assert r.status_code==200 and r.json()['status']=='ok'
def test_public_tracking_not_found():
    r=client.get('/api/reports/not-a-real-id'); assert r.status_code==404
def test_staff_routes_require_login():
    r=client.get('/api/dashboard/stats'); assert r.status_code==401
def test_login_and_dashboard():
    r=client.post('/api/auth/login',json={'username':'admin','password':'ChangeMe123!'})
    assert r.status_code==200
    assert client.get('/api/dashboard/stats').status_code==200
    client.post('/api/auth/logout')
