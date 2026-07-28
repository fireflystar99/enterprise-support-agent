import json
from datetime import UTC, datetime
from pathlib import Path

from app.evaluation.dataset import load_golden, split_dataset
from app.evaluation.metrics import aggregate
from app.support.agent import support_agent


def run_experiment(
    version: str,
    split: str = "development",
    golden_path: Path = Path("data/eval/golden.jsonl"),
    output_dir: Path = Path("artifacts"),
) -> dict:
    cases = load_golden(golden_path)
    filtered = split_dataset(cases, split)

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    run_dir = output_dir / version / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []
    for case in filtered:
        try:
            response = support_agent.handle(case.question)
            case_result = {
                "case_id": case.id,
                "question": case.question,
                "category": case.category,
                "expected_answer": case.expected_answer,
                "must_route_to_ticket": case.must_route_to_ticket,
                "route": response.route,
                "answer": response.answer,
                "ticket_id": response.ticket_id,
                "confidence": response.confidence,
                "latency_ms": response.latency_ms,
                "citation_count": len(response.citations),
            }
        except Exception as exc:  # noqa: BLE001
            case_result = {
                "case_id": case.id,
                "question": case.question,
                "category": case.category,
                "expected_answer": case.expected_answer,
                "must_route_to_ticket": case.must_route_to_ticket,
                "route": "error",
                "answer": "",
                "ticket_id": None,
                "confidence": "low",
                "latency_ms": 0,
                "citation_count": 0,
                "error": str(exc),
            }
        results.append(case_result)

    cases_path = run_dir / "cases.jsonl"
    with open(cases_path, "w") as f:
        f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in results)

    summary = aggregate(results)
    summary["version"] = version
    summary["split"] = split
    summary["timestamp"] = timestamp
    summary["judge_not_configured"] = True

    summary_path = run_dir / "summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"Evaluation complete: {summary['total_cases']} cases, "
          f"accuracy={summary['accuracy']:.2%}, "
          f"precision={summary['ticket_routing_precision']:.2%}, "
          f"recall={summary['ticket_routing_recall']:.2%}")

    return summary
