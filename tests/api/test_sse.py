from app.api.sse import encode_sse


def test_encode_sse_emits_named_json_event() -> None:
    assert encode_sse("token", {"text": "你好"}) == (
        'event: token\ndata: {"text":"你好"}\n\n'
    )
