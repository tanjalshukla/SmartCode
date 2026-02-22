from __future__ import annotations

"""Low-level helpers shared across run orchestration modules."""

import difflib
import hashlib
import json
from pathlib import Path

from ..cli_shared import (
    read_file_context as _read_file_context,
    resolve_config as _resolve_config,
    truncate_content as _truncate_content,
)
from ..policy import PolicyDecision, PolicyInput, decide_action
from ..schema import IntentDeclaration
from ..session import ClaudeSession
from ..trust_db import HardConstraint, PolicyHistory, TrustDB


def _append_file_context(
    session: ClaudeSession,
    files: list[str],
    repo_root: Path,
    max_chars: int,
) -> None:
    blocks: list[str] = []
    for path in files:
        file_path = repo_root / path
        try:
            content = file_path.read_text()
        except Exception:
            content = ""
        content = _truncate_content(content, max_chars)
        blocks.append(f"FILE: {path}\n-----\n{content}\n-----")
    if blocks:
        session.add_user("Requested file contents:\n" + "\n\n".join(blocks))


def _line_delta_size(old_text: str, new_text: str) -> int:
    matcher = difflib.SequenceMatcher(a=old_text.splitlines(), b=new_text.splitlines())
    delta = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag in {"replace", "delete"}:
            delta += i2 - i1
        if tag in {"replace", "insert"}:
            delta += j2 - j1
    return delta


def _plan_hash(declaration: IntentDeclaration) -> str:
    payload = json.dumps(
        declaration.model_dump(exclude_none=False, mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _collect_change_metrics(repo_root: Path, updates: dict[str, str]) -> dict[str, tuple[int, bool]]:
    metrics: dict[str, tuple[int, bool]] = {}
    for path, new_content in updates.items():
        file_path = repo_root / path
        old_content = ""
        if file_path.exists():
            try:
                old_content = file_path.read_text()
            except Exception:
                old_content = ""
        delta_size = _line_delta_size(_normalize_line_endings(old_content), _normalize_line_endings(new_content))
        metrics[path] = (delta_size, not file_path.exists())
    return metrics


def _policy_decision_for_file(
    *,
    history: PolicyHistory,
    diff_size: int,
    blast_radius: int,
    is_new_file: bool,
    is_security_sensitive: bool,
    change_pattern: str | None,
    recent_denials: int,
    proceed_threshold: float,
    flag_threshold: float,
) -> PolicyDecision:
    return decide_action(
        PolicyInput(
            prior_approvals=history.effective_approvals,
            prior_denials=history.denials,
            avg_response_ms=history.avg_response_ms,
            avg_edit_distance=history.avg_edit_distance or 0.0,
            diff_size=diff_size,
            blast_radius=blast_radius,
            is_new_file=is_new_file,
            is_security_sensitive=is_security_sensitive,
            change_pattern=change_pattern,
            recent_denials=recent_denials,
        ),
        proceed_threshold=proceed_threshold,
        flag_threshold=flag_threshold,
    )


def _build_patch_from_updates(
    repo_root: Path,
    updates: dict[str, str],
) -> tuple[str, list[str]]:
    diffs: list[str] = []
    touched: list[str] = []
    for path, new_content in updates.items():
        file_path = repo_root / path
        old_content = ""
        if file_path.exists():
            try:
                old_content = file_path.read_text()
            except Exception:
                old_content = ""
        old_norm = _normalize_line_endings(old_content)
        new_norm = _normalize_line_endings(new_content)
        old_has_trailing_newline = old_content.endswith("\n") or old_content.endswith("\r\n")
        if old_has_trailing_newline and new_norm and not new_norm.endswith("\n"):
            new_norm += "\n"
        if new_norm == old_norm:
            continue
        fromfile = "/dev/null" if not file_path.exists() else f"a/{path}"
        tofile = f"b/{path}"
        old_lines = old_norm.splitlines(keepends=True)
        new_lines = new_norm.splitlines(keepends=True)
        diff_lines = list(
            difflib.unified_diff(
                old_lines,
                new_lines,
                fromfile=fromfile,
                tofile=tofile,
                lineterm="",
            )
        )
        if diff_lines:
            diffs.append("\n".join(diff_lines))
            touched.append(path)
    patch_text = "\n".join(diffs).strip()
    if patch_text and not patch_text.endswith("\n"):
        patch_text += "\n"
    return patch_text, touched


def _normalize_line_endings(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _normalize_new_content(old_content: str, new_content: str) -> str:
    old_has_trailing_newline = old_content.endswith("\n") or old_content.endswith("\r\n")
    new_norm = _normalize_line_endings(new_content)
    if old_has_trailing_newline and new_norm and not new_norm.endswith("\n"):
        new_norm += "\n"
    if "\r\n" in old_content:
        return new_norm.replace("\n", "\r\n")
    return new_norm


def _constraint_index(
    trust_db: TrustDB,
    repo_root: str,
    files: list[str],
) -> dict[str, HardConstraint | None]:
    return {path: trust_db.strongest_constraint(repo_root, path) for path in files}


def _auto_read_user_decision(
    path: str,
    read_leases: dict[str, str | None],
    read_policies: dict[str, PolicyDecision],
) -> str:
    if read_leases[path] is not None:
        return "auto_approve_read_lease"
    return "auto_approve_flag" if read_policies[path].action == "proceed_flag" else "auto_approve"
