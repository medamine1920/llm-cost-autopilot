from app.main import create_app
from fastapi.testclient import TestClient

def test_health_returns_ok():
    app=create_app()
    client=TestClient(app)
    response=client.get("/health")
    assert response.status_code==200
    assert response.json()=={"status":"ok","version":"0.1.0","environment":"development"}