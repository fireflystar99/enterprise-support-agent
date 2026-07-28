def aggregate(results: list[dict]) -> dict:
    if not results:
        return {
            "total_cases": 0,
            "ticket_routing_precision": 0.0,
            "ticket_routing_recall": 0.0,
            "accuracy": 0.0,
            "avg_latency_ms": 0,
        }

    total = len(results)
    tp = sum(1 for r in results if r.get("must_route_to_ticket") and r.get("route") == "ticket")
    fp = sum(1 for r in results if not r.get("must_route_to_ticket") and r.get("route") == "ticket")
    fn = sum(1 for r in results if r.get("must_route_to_ticket") and r.get("route") != "ticket")
    correct = sum(1 for r in results if r.get("must_route_to_ticket") == (r.get("route") == "ticket"))

    latencies = [r.get("latency_ms", 0) for r in results]
    avg_latency = int(sum(latencies) / len(latencies)) if latencies else 0

    return {
        "total_cases": total,
        "ticket_routing_precision": tp / (tp + fp) if (tp + fp) > 0 else 0.0,
        "ticket_routing_recall": tp / (tp + fn) if (tp + fn) > 0 else 0.0,
        "accuracy": correct / total if total > 0 else 0.0,
        "avg_latency_ms": avg_latency,
    }
