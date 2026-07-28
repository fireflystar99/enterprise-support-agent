

from app.evaluation.metrics import aggregate


def test_aggregate_reports_ticket_routing_precision() -> None:
    report = aggregate([
        {"must_route_to_ticket": True, "route": "ticket"},
        {"must_route_to_ticket": False, "route": "answer"},
    ])
    assert report["ticket_routing_precision"] == 1.0
    assert report["ticket_routing_recall"] == 1.0


def test_aggregate_handles_empty() -> None:
    report = aggregate([])
    assert report["total_cases"] == 0
    assert report["ticket_routing_precision"] == 0.0
