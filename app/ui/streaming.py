"""Streamlit 前端使用的 SSE 事件解析工具。"""

import json
from collections.abc import Iterable, Iterator


def parse_sse_lines(lines: Iterable[str]) -> Iterator[tuple[str, dict[str, object]]]:
    """将 FastAPI 的 SSE 行解析为 ``(event, payload)`` 事件。"""
    event = "message"
    for line in lines:
        if not line:
            continue
        if line.startswith("event: "):
            event = line.removeprefix("event: ")
            continue
        if line.startswith("data: "):
            payload = json.loads(line.removeprefix("data: "))
            if isinstance(payload, dict):
                yield event, payload
