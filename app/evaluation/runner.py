import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from app.core.experiment_config import load_config
from app.evaluation.dataset import load_golden, split_dataset
from app.evaluation.judge import judge_answer_faithfulness
from app.evaluation.metrics import aggregate
from app.support.agent import SupportAgent


def _git_sha() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _file_sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except (OSError, subprocess.CalledProcessError):
        return None


def run_experiment(
    version: str,
    split: str = "development",
    golden_path: Path = Path("data/eval/golden.jsonl"),
    output_dir: Path = Path("artifacts"),
    judge_enabled: bool = False,
) -> dict:
    cfg = load_config(version)
    agent = SupportAgent()

    cases = load_golden(golden_path)
    filtered = split_dataset(cases, split)

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    run_dir = output_dir / version / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []
    for case in filtered:
        try:
            response = agent.handle(case.question, config=cfg)
            case_result = {
                "case_id": case.id,
                "question": case.question,
                "category": case.category,
                "expected_answer": case.expected_answer,
                "expected_document_ids": case.expected_document_ids,
                "must_route_to_ticket": case.must_route_to_ticket,
                "route": response.route,
                "answer": response.answer,
                "ticket_id": response.ticket_id,
                "confidence": response.confidence,
                "latency_ms": response.latency_ms,
                "citation_count": len(response.citations),
                "citations": [
                    {"chunk_id": c.chunk_id, "title": c.title, "excerpt": c.excerpt}
                    for c in response.citations
                ],
            }
            if judge_enabled and case.expected_answer:
                case_result["judge_score"] = judge_answer_faithfulness(
                    case.expected_answer, response.answer
                )
        except Exception as exc:  # noqa: BLE001
            case_result = {
                "case_id": case.id,
                "question": case.question,
                "category": case.category,
                "expected_answer": case.expected_answer,
                "expected_document_ids": case.expected_document_ids,
                "must_route_to_ticket": case.must_route_to_ticket,
                "route": "error",
                "answer": "",
                "ticket_id": None,
                "confidence": "low",
                "latency_ms": 0,
                "citation_count": 0,
                "citations": [],
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
    summary["git_sha"] = _git_sha()
    summary["dataset_sha256"] = _file_sha256(golden_path)
    summary["config"] = cfg.model_dump()
    summary["judge_enabled"] = judge_enabled

    summary_path = run_dir / "summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"Evaluation complete: {summary['total_cases']} cases, "
          f"f1_routing={summary['ticket_routing_f1']:.2%}, "
          f"answer_f1={summary['avg_answer_f1']:.2%}, "
          f"doc_recall={summary['avg_document_recall']:.2%}, "
          f"unsafe_rate={summary['unsafe_confident_rate']:.2%}")

    return summary
