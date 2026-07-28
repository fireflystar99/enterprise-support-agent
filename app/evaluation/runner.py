import json
from pathlib import Path
from datetime import datetime, timezone
from app.evaluation.dataset import GoldenCase, load_golden, split_dataset
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

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_dir = output_dir / version / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []
    for case in filtered:
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
        results.append(case_result)

    cases_path = run_dir / "cases.jsonl"
    with open(cases_path, "w") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    summary = aggregate(results)
    summary["version"] = version
    summary["split"] = split
    summary["total_cases"] = len(results)
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
