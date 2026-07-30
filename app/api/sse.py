"""Server-Sent Events 编码工具。"""
import json


def encode_sse(event: str, payload: dict[str, object]) -> str:
    """将命名 JSON 事件编码为 SSE 文本帧。"""
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event}\ndata: {data}\n\n"
