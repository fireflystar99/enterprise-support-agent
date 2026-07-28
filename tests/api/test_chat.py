def test_chat_returns_answer_with_citations(client):
    response = client.post("/chat", json={"question": "How do I submit a receipt?"})
    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "answer"
    assert len(body["citations"]) > 0
    assert body["trace_id"] != ""


def test_chat_password_reset_returns_ticket(client):
    response = client.post("/chat", json={"question": "Please reset my VPN password"})
    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "ticket"
    assert body["ticket_id"] is not None


# reuse test_ingestion fixtures to multi-chunk
