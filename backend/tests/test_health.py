from importlib.metadata import version

from fastapi.testclient import TestClient

from agentverse.api.main import app


def test_health_reports_the_installed_service_version() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": version("agentverse-lab")}
