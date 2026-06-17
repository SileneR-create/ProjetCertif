from fastapi.testclient import TestClient
from backend.app_api import app

client = TestClient(app)


def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "online", "message": "Welcome to TravelMatch API"}
