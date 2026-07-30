import pytest


def test_stream_answer_uses_configured_client_and_evidence(monkeypatch) -> None:
    from app.llm.deepseek import stream_answer

    captured = {}

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            delta = type("Delta", (), {"content": "答案"})()
            choice = type("Choice", (), {"delta": delta})()
            return [type("Chunk", (), {"choices": [choice]})()]

    class FakeClient:
        chat = type("Chat", (), {"completions": FakeCompletions()})()

    monkeypatch.setattr("app.llm.deepseek._get_client", lambda: FakeClient())
    monkeypatch.setattr("app.llm.deepseek.settings.llm_api_key", "sk-test-key")

    assert list(stream_answer("如何报销？", ["报销须在 30 天内提交。 "])) == ["答案"]
    assert captured["stream"] is True
    assert "30 天内提交" in captured["messages"][1]["content"]


def test_stream_answer_rejects_missing_api_key(monkeypatch) -> None:
    from app.llm.deepseek import DeepSeekError, stream_answer

    monkeypatch.setattr("app.llm.deepseek.settings.llm_api_key", "")

    with pytest.raises(DeepSeekError, match="not configured"):
        list(stream_answer("问题", ["证据"]))
