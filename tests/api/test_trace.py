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
    assert response.status_code in (200, 404)
