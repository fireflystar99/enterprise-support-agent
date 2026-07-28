"""Experiment configuration loader."""
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel


class RetrievalConfig(BaseModel):
    mode: Literal["vector", "hybrid"] = "vector"
    top_k: int = 3
    rerank_top_n: int = 3


class GroundingConfig(BaseModel):
    enabled: bool = False
    mandatory_citations: bool = False
    access_filter: bool = False


class ExperimentConfig(BaseModel):
    version: str
    description: str = ""
    retrieval: RetrievalConfig = RetrievalConfig()
    grounding: GroundingConfig = GroundingConfig()


@lru_cache(maxsize=8)
def load_config(version: str, configs_dir: Path | None = None) -> ExperimentConfig:
    """Load and validate a versioned experiment configuration."""
    config_path = (configs_dir or Path("configs")) / f"{version}.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration not found: {config_path}")
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return ExperimentConfig(**raw)
