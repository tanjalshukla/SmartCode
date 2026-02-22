from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


WorkflowPhase = Literal["research", "planning", "implementation", "review"]


@dataclass(frozen=True)
class PhaseGateResult:
    allowed: bool
    blocked_files: list[str]
    reason: str | None = None


def evaluate_write_phase_gate(phase: WorkflowPhase, touched_files: list[str]) -> PhaseGateResult:
    """Enforce phase-based write boundaries before policy/approval logic."""
    if not touched_files:
        return PhaseGateResult(allowed=True, blocked_files=[])

    if phase == "research":
        return PhaseGateResult(
            allowed=False,
            blocked_files=sorted(touched_files),
            reason="Research phase blocks all file writes.",
        )

    if phase == "planning":
        blocked = sorted(
            path for path in touched_files if Path(path).suffix.lower() != ".md"
        )
        if blocked:
            return PhaseGateResult(
                allowed=False,
                blocked_files=blocked,
                reason="Planning phase allows writes only to .md files.",
            )

    return PhaseGateResult(allowed=True, blocked_files=[])
