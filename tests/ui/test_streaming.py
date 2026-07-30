"""流式 SSE 事件解析的单元测试。"""

from app.ui.streaming import parse_sse_lines


def test_parse_sse_lines_preserves_token_and_metadata_events() -> None:
    lines = [
        "event: token",
        'data: {"text":"差旅"}',
        "",
        "event: metadata",
        'data: {"route":"answer","latency_ms":120}',
        "",
    ]

    assert list(parse_sse_lines(lines)) == [
        ("token", {"text": "差旅"}),
        ("metadata", {"route": "answer", "latency_ms": 120}),
    ]
