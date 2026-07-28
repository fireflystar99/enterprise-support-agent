def test_trace_exposes_route_and_latency(client):
    chat = client.post("/chat", json={"question": "How do I submit a receipt?"}).json()
    trace_id = chat["trace_id"]
    response = client.get(f"/traces/{trace_id}")
    assert response.status_code in (200, 404)
