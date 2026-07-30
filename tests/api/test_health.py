from fastapi.testclient import TestClient


def test_client_startup_completes_with_mocked_models(client: TestClient) -> None:
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok', 'service': 'enterprise-support-agent'}
