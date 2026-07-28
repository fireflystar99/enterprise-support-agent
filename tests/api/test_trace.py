def test_trace_requires_admin_token(client):
    chat = client.post("/chat", json={"question": "How do I submit a receipt?"}).json()
    trace_id = chat["trace_id"]
    # without token → 403
    response = client.get(f"/traces/{trace_id}")
    assert response.status_code == 403


def test_trace_with_valid_token(client):
    chat = client.post("/chat", json={"question": "How do I submit a receipt?"}).json()
    trace_id = chat["trace_id"]
    headers = {"X-Admin-Token": "test-admin-token"}
    response = client.get(f"/traces/{trace_id}", headers=headers)
    # With mock DB returning a chunk, agent calls handle() → _persist_trace → SessionLocal
    # The mock session's query returns None (not found), so we get 200 only with full DB mock
    assert response.status_code == 200
    body = response.json()
    assert body["route"] in ("answer", "ticket")
    assert isinstance(body["latency_ms"], int)
