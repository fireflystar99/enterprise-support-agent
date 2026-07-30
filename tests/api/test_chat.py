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


def test_chat_stream_emits_tokens_then_metadata(client, monkeypatch):
    from app.api import main

    monkeypatch.setattr(
        main.support_agent,
        "stream",
        lambda *_args, **_kwargs: iter(
            [
                ("token", {"text": "报销"}),
                ("token", {"text": "须在 30 天内提交。[1]"}),
                (
                    "metadata",
                    {
                        "route": "answer",
                        "citations": [],
                        "trace_id": "t1",
                        "latency_ms": 1,
                    },
                ),
            ]
        ),
        raising=False,
    )

    response = client.post("/chat/stream", json={"question": "如何报销？"})

    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.text.index("event: token") < response.text.index("event: metadata")


# reuse test_ingestion fixtures to multi-chunk
