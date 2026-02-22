from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

CONFIG_DIR_NAME = ".sc"
CONFIG_FILE_NAME = "config.json"


def default_region() -> str:
    return os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"


def env_model_id() -> str | None:
    return os.getenv("SA_MODEL_ID")


@dataclass
class SAConfig:
    model_id: str
    aws_region: str = field(default_factory=default_region)
    max_tokens: int = 2500
    temperature: float = 0.0
    lease_ttl_hours: int = 72
    scope_budget_files: int = 12
    permanent_approval_threshold: int = 3
    read_max_chars: int = 12000
    adaptive_policy_enabled: bool = True
    policy_proceed_threshold: float = 0.9
    policy_flag_threshold: float = 0.2
    policy_recent_denials_window_sec: int = 3600
    strict_plan_gate: bool = False
    plan_checkpoint_max_files: int = 1
    max_plan_revisions: int = 2
    verification_enabled: bool = True
    verification_timeout_sec: int = 20
    verification_command: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SAConfig":
        return cls(
            model_id=data["model_id"],
            aws_region=data.get("aws_region", default_region()),
            max_tokens=int(data.get("max_tokens", 2500)),
            temperature=float(data.get("temperature", 0.0)),
            lease_ttl_hours=int(data.get("lease_ttl_hours", 72)),
            scope_budget_files=int(data.get("scope_budget_files", 12)),
            permanent_approval_threshold=int(data.get("permanent_approval_threshold", 3)),
            read_max_chars=int(data.get("read_max_chars", 12000)),
            adaptive_policy_enabled=bool(data.get("adaptive_policy_enabled", True)),
            policy_proceed_threshold=float(data.get("policy_proceed_threshold", 0.9)),
            policy_flag_threshold=float(data.get("policy_flag_threshold", 0.2)),
            policy_recent_denials_window_sec=int(data.get("policy_recent_denials_window_sec", 3600)),
            strict_plan_gate=bool(data.get("strict_plan_gate", False)),
            plan_checkpoint_max_files=int(data.get("plan_checkpoint_max_files", 1)),
            max_plan_revisions=int(data.get("max_plan_revisions", 2)),
            verification_enabled=bool(data.get("verification_enabled", True)),
            verification_timeout_sec=int(data.get("verification_timeout_sec", 20)),
            verification_command=data.get("verification_command"),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def config_dir(repo_root: Path) -> Path:
    """Return the .sc directory path under the repository root."""
    return repo_root / CONFIG_DIR_NAME


def config_path(repo_root: Path) -> Path:
    """Return the config file path under the repository root."""
    return config_dir(repo_root) / CONFIG_FILE_NAME


def load_config(repo_root: Path) -> SAConfig | None:
    """Load repo-local config if present."""
    path = config_path(repo_root)
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    return SAConfig.from_dict(data)


def save_config(repo_root: Path, config: SAConfig) -> Path:
    """Persist repo-local config and return the written path."""
    path = config_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config.to_dict(), indent=2))
    return path
