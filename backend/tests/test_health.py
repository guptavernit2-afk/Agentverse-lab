from importlib.metadata import version

from fastapi.testclient import TestClient

from agentverse.api.main import create_app


def test_health_reports_the_installed_service_version(tmp_path) -> None:
    with TestClient(create_app(tmp_path / 'health.db'), base_url='http://127.0.0.1', client=('127.0.0.1', 51000)) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": version("agentverse-lab")}
