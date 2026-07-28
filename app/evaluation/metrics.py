from statistics import quantiles
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


def _document_recall(expected_ids: list[str], citations: list[dict]) -> float:
    if not expected_ids:
        return 1.0  # no expected docs → skip
    if not citations:
        return 0.0
    retrieved_titles = {c.get("title", "") for c in citations}
    hits = sum(1 for eid in expected_ids if eid in retrieved_titles)
    return hits / len(expected_ids)


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute routing, retrieval, answer, safety, and latency metrics."""
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

    # --- routing ---
    tp = sum(1 for r in results if r.get("must_route_to_ticket") and r.get("route") == "ticket")
    fp = sum(1 for r in results if not r.get("must_route_to_ticket") and r.get("route") == "ticket")
    fn = sum(1 for r in results if r.get("must_route_to_ticket") and r.get("route") != "ticket")
    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    f1 = _safe_div(2 * precision * recall, precision + recall)

    # --- answer quality (token-overlap F1) ---
    answer_f1s = []
    for r in results:
        expected = r.get("expected_answer", "")
        actual = r.get("answer", "")
        if expected:
            answer_f1s.append(_token_overlap_f1(expected, actual))
    avg_answer_f1 = sum(answer_f1s) / len(answer_f1s) if answer_f1s else 0.0

    # --- retrieval recall ---
    doc_recalls = []
    for r in results:
        expected_ids = r.get("expected_document_ids", [])
        citations = r.get("citations", [])
        doc_recalls.append(_document_recall(expected_ids, citations))
    avg_document_recall = sum(doc_recalls) / len(doc_recalls) if doc_recalls else 0.0

    # --- safety: unsafe confident-answer rate ---
    unsafe = 0
    for r in results:
        must_ticket = r.get("must_route_to_ticket", False)
        route = r.get("route", "")
        confidence = r.get("confidence", "low")
        if must_ticket and route == "answer" and confidence in ("high", "medium"):
            unsafe += 1
    unsafe_confident_rate = unsafe / total if total > 0 else 0.0

    # --- latency ---
    latencies = sorted([r.get("latency_ms", 0) for r in results])
    p50 = _percentile(latencies, 50) if latencies else 0
    p95 = _percentile(latencies, 95) if latencies else 0

    return {
        "total_cases": total,
        # routing
        "ticket_routing_precision": precision,
        "ticket_routing_recall": recall,
        "ticket_routing_f1": f1,
        # answer
        "avg_answer_f1": round(avg_answer_f1, 4),
        "cases_with_answer_eval": len(answer_f1s),
        # retrieval
        "avg_document_recall": round(avg_document_recall, 4),
        # safety
        "unsafe_confident_rate": round(unsafe_confident_rate, 4),
        # latency
        "p50_latency_ms": p50,
        "p95_latency_ms": p95,
    }


def _percentile(sorted_values: list[int], pct: float) -> int:
    if not sorted_values:
        return 0
    n = len(sorted_values)
    idx = int(round(pct / 100.0 * (n - 1)))
    return sorted_values[min(idx, n - 1)]
