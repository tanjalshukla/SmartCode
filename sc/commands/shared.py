from __future__ import annotations

"""Shared helpers for command modules."""

from pathlib import Path

import typer
from rich import print

from ..config import config_dir
from ..repo import RepoError, get_repo_root
from ..trust_db import TrustDB


def require_repo_root() -> Path:
    """Return repo root or exit with a user-facing error."""
    try:
        return get_repo_root()
    except RepoError as exc:
        print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)


def try_repo_root() -> Path | None:
    """Best-effort repo root lookup without user-facing errors."""
    try:
        return get_repo_root()
    except RepoError:
        return None


def open_trust_db(repo_root: Path) -> TrustDB:
    return TrustDB(config_dir(repo_root) / "trust.db")
