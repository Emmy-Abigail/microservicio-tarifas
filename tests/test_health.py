def test_health_responde_ok_sin_api_key(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}