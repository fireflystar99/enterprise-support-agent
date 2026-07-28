#!/usr/bin/env python3
"""Run a support agent evaluation experiment."""
import sys
import argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.evaluation.runner import run_experiment

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run evaluation experiment")
    parser.add_argument("--version", required=True, help="Experiment version (v1, v2, etc.)")
    parser.add_argument("--split", default="development", help="Dataset split (development/holdout)")
    args = parser.parse_args()

    summary = run_experiment(
        version=args.version,
        split=args.split,
        golden_path=Path("data/eval/golden.jsonl"),
        output_dir=Path("artifacts"),
    )
    print(f"\nResults saved to artifacts/{args.version}/")
