import json
from pathlib import Path

from pydantic import BaseModel


class GoldenCase(BaseModel):
    id: str
    question: str
    category: str
    expected_answer: str
    expected_document_ids: list[str]
    must_route_to_ticket: bool
    risk_level: str
    split: str


def load_golden(path: Path) -> list[GoldenCase]:
    cases = []
    with open(path, encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                cases.append(GoldenCase(**json.loads(line)))
            except (json.JSONDecodeError, Exception) as exc:  # noqa: BLE001
                print(f"Warning: skipping malformed line {line_num} in {path}: {exc}")
    return cases


def split_dataset(cases: list[GoldenCase], split_name: str) -> list[GoldenCase]:
    return [c for c in cases if c.split == split_name]
