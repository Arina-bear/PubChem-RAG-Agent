from fastapi.testclient import TestClient

from app.main import create_app


def test_health_endpoint_returns_status() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["cache_backend"] == "memory"

