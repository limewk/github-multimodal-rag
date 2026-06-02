from fastapi.testclient import TestClient

from src.api.main import app


def test_routes_are_registered():
    client = TestClient(app)

    health = client.get("/health")

    assert health.status_code == 200
    paths = {route.path for route in app.routes}
    assert "/chat" in paths
    assert "/repos/index" in paths
