def test_password_reset_creates_ticket(client):
    response = client.post("/chat", json={"question": "Please reset my VPN password"})
    body = response.json()
    assert body["route"] == "ticket"
    assert body["ticket_id"] is not None
    assert body["citations"] == []
