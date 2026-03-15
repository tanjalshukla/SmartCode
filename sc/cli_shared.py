from __future__ import annotations

from pathlib import Path

import typer

from .config import SAConfig, default_region, env_model_id, load_config


def resolve_config(repo_root: Path, model_id: str | None, region: str | None) -> SAConfig:
    config = load_config(repo_root)
    if config is None:
        env_model = env_model_id()
        if not model_id and not env_model:
            raise typer.BadParameter("Missing model id. Run `hw init` or pass --model-id.")
        return SAConfig(
            model_id=model_id or env_model,  # type: ignore[arg-type]
            aws_region=region or default_region(),
        )
    if model_id:
        config.model_id = model_id
    if region:
        config.aws_region = region
    return config


def truncate_content(content: str, max_chars: int) -> str:
    if len(content) <= max_chars:
        return content
    head = content[: max_chars // 2]
    tail = content[-max_chars // 2 :]
    return f"{head}\n\n... [truncated] ...\n\n{tail}"


def read_file_context(repo_root: Path, files: list[str], max_chars: int) -> dict[str, str]:
    context: dict[str, str] = {}
    for path in files:
        file_path = repo_root / path
        try:
            content = file_path.read_text()
        except Exception:
            content = ""
        context[path] = truncate_content(content, max_chars)
    return context


def is_approval_decision(decision: str) -> bool:
    return decision in {
        "approve",
        "approve_and_remember",
        "auto_approve",
        "auto_approve_flag",
        "auto_approve_lease",
        "auto_approve_read_lease",
    }
