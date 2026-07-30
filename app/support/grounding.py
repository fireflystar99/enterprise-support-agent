import re

from app.retrieval.types import RetrievedChunk


def validate_grounding(answer: str, citations: list[str]) -> bool:
    """仅当回答有内容且包含引用标记时返回 True。"""
    if not answer.strip():
        return False
    if not citations:
        return False
    has_citation_marker = bool(re.search(r'\[\d+\]|\[source-\d+\]', answer))
    return has_citation_marker


def filter_by_access_level(chunks: list[RetrievedChunk], user_access: str) -> list[RetrievedChunk]:
    """按最小访问级别过滤 Chunk。"""
    access_order = {"public": 0, "internal": 1, "confidential": 2, "restricted": 3}
    user_level = access_order.get(user_access, 0)
    return [
        c for c in chunks
        if access_order.get(c.access_level, 0) <= user_level
    ]


def resolve_access_level(department: str | None) -> str:
    """根据部门映射访问级别。"""
    if department in ("Finance", "IT", "HR"):
        return "internal"
    if department in ("Legal", "Executive"):
        return "confidential"
    return "public"
