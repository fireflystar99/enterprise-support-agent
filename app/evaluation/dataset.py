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
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(GoldenCase(**json.loads(line)))
    return cases


def split_dataset(cases: list[GoldenCase], split_name: str) -> list[GoldenCase]:
    return [c for c in cases if c.split == split_name]
