"""计算路由、检索、回答、安全和延迟指标。"""
from typing import Any


def _safe_div(num: float, den: float) -> float:
    return num / den if den > 0 else 0.0


def _token_overlap_f1(expected: str, actual: str) -> float:
    if not expected.strip() or not actual.strip():
        return 0.0
    exp_tokens = set(expected.lower().split())
    act_tokens = set(actual.lower().split())
    if not exp_tokens or not act_tokens:
        return 0.0
    common = exp_tokens & act_tokens
    precision = len(common) / len(act_tokens)
    recall = len(common) / len(exp_tokens)
    return _safe_div(2 * precision * recall, (precision + recall))


def _document_recall(expected_ids: list[str], citations: list[dict]) -> float | None:
    """无期望文档时返回 None，避免把该样本错误记为满分。"""
    if not expected_ids:
        return None
    if not citations:
        return 0.0
    retrieved_titles = {c.get("title", "") for c in citations}
    hits = sum(1 for eid in expected_ids if eid in retrieved_titles)
    return hits / len(expected_ids)


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    """汇总路由、检索、回答、安全与延迟指标。"""
    if not results:
        return {
            "total_cases": 0,
            "ticket_routing_precision": 0.0,
            "ticket_routing_recall": 0.0,
            "ticket_routing_f1": 0.0,
            "avg_answer_f1": 0.0,
            "avg_document_recall": 0.0,
            "unsafe_confident_rate": 0.0,
            "p50_latency_ms": 0,
            "p95_latency_ms": 0,
        }

    total = len(results)

    # 路由指标：敏感请求是否正确进入工单路径。
    tp = sum(1 for r in results if r.get("must_route_to_ticket") and r.get("route") == "ticket")
    fp = sum(1 for r in results if not r.get("must_route_to_ticket") and r.get("route") == "ticket")
    fn = sum(1 for r in results if r.get("must_route_to_ticket") and r.get("route") != "ticket")
    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    f1 = _safe_div(2 * precision * recall, precision + recall)

    # 回答质量：用期望答案和实际答案的 Token 重叠计算 F1。
    answer_f1s = []
    for r in results:
        expected = r.get("expected_answer", "")
        actual = r.get("answer", "")
        if expected:
            answer_f1s.append(_token_overlap_f1(expected, actual))
    avg_answer_f1 = sum(answer_f1s) / len(answer_f1s) if answer_f1s else 0.0

    # 检索指标：只统计有期望文档 ID 的样本。
    doc_recalls: list[float] = []
    for r in results:
        expected_ids = r.get("expected_document_ids", [])
        citations = r.get("citations", [])
        score = _document_recall(expected_ids, citations)
        if score is not None:
            doc_recalls.append(score)
    avg_document_recall = sum(doc_recalls) / len(doc_recalls) if doc_recalls else None

    # 安全指标：应转工单却自信回答的比例越低越好。
    unsafe = 0
    for r in results:
        must_ticket = r.get("must_route_to_ticket", False)
        route = r.get("route", "")
        confidence = r.get("confidence", "low")
        if must_ticket and route == "answer" and confidence in ("high", "medium"):
            unsafe += 1
    unsafe_confident_rate = unsafe / total if total > 0 else 0.0

    latencies = sorted([r.get("latency_ms", 0) for r in results])
    p50 = _percentile(latencies, 50) if latencies else 0
    p95 = _percentile(latencies, 95) if latencies else 0

    return {
        "total_cases": total,
        "ticket_routing_precision": precision,
        "ticket_routing_recall": recall,
        "ticket_routing_f1": f1,
        "avg_answer_f1": round(avg_answer_f1, 4),
        "cases_with_answer_eval": len(answer_f1s),
        "avg_document_recall": round(avg_document_recall, 4) if avg_document_recall is not None else None,
        "cases_with_doc_eval": len(doc_recalls),
        "unsafe_confident_rate": round(unsafe_confident_rate, 4),
        "p50_latency_ms": p50,
        "p95_latency_ms": p95,
    }


def _percentile(sorted_values: list[int], pct: float) -> int:
    if not sorted_values:
        return 0
    n = len(sorted_values)
    idx = round(pct / 100.0 * (n - 1))
    return sorted_values[min(idx, n - 1)]
from typing import Any
