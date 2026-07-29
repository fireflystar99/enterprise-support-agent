

from pathlib import Path

from app.evaluation.dataset import load_golden, split_dataset
from app.evaluation.metrics import aggregate


def test_chinese_golden_set_keeps_stable_splits() -> None:
    cases = load_golden(Path("data/eval/golden.jsonl"))

    assert len(cases) == 18
    assert {case.id for case in cases} == {f"case-{i:03d}" for i in range(1, 19)}
    assert all(any("\u4e00" <= char <= "\u9fff" for char in case.question) for case in cases)
    assert len(split_dataset(cases, "development")) == 14
    assert len(split_dataset(cases, "holdout")) == 4


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
