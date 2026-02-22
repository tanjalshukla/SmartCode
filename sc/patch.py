from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable


class PatchError(RuntimeError):
    pass


class PatchValidationError(PatchError):
    pass


def validate_touched_files(
    repo_root: Path, touched_files: Iterable[str], allowed_files: set[str]
) -> None:
    """Fail closed if proposed file paths escape repo or exceed approved scope."""
    for path in touched_files:
        if os.path.isabs(path):
            raise PatchValidationError(f"Patch references absolute path: {path}")
        norm = os.path.normpath(path)
        if norm.startswith(".."):
            raise PatchValidationError(f"Patch path escapes repo: {path}")
        if path not in allowed_files:
            raise PatchValidationError(f"Patch touches unapproved file: {path}")
        if not (repo_root / path).resolve().is_relative_to(repo_root.resolve()):
            raise PatchValidationError(f"Patch path escapes repo: {path}")
