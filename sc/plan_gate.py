from __future__ import annotations

from dataclasses import dataclass

from .features import is_security_sensitive
from .schema import IntentDeclaration
from .trust_db import TrustDB


@dataclass(frozen=True)
class PlanCheckpointDecision:
    required: bool
    reasons: tuple[str, ...]


def decide_plan_checkpoint(
    *,
    trust_db: TrustDB,
    repo_root: str,
    declaration: IntentDeclaration,
    strict: bool,
    max_auto_files: int,
) -> PlanCheckpointDecision:
    """Decide whether implementation must pause for explicit plan approval."""
    reasons: list[str] = []
    planned_files = declaration.planned_files

    if strict:
        reasons.append("strict plan gate enabled")

    if len(planned_files) > max(max_auto_files, 0):
        reasons.append(f"plan touches {len(planned_files)} files")

    if len(set(declaration.planned_actions)) > 1:
        reasons.append("plan includes multiple action types")

    low_trust_files: list[str] = []
    constrained_files: list[str] = []
    security_files: list[str] = []
    for path in planned_files:
        history = trust_db.policy_history(repo_root, path, stage="apply")
        if history.denials > 0 and history.approvals <= history.denials:
            low_trust_files.append(path)

        constraint = trust_db.strongest_constraint(repo_root, path)
        if constraint and constraint.constraint_type in {"always_check_in", "always_deny"}:
            constrained_files.append(path)

        if is_security_sensitive(path, ""):
            security_files.append(path)

    if low_trust_files:
        preview = ", ".join(low_trust_files[:3])
        if len(low_trust_files) > 3:
            preview += ", ..."
        reasons.append(f"low-trust files: {preview}")

    if constrained_files:
        preview = ", ".join(constrained_files[:3])
        if len(constrained_files) > 3:
            preview += ", ..."
        reasons.append(f"constrained files: {preview}")

    if security_files:
        preview = ", ".join(security_files[:3])
        if len(security_files) > 3:
            preview += ", ..."
        reasons.append(f"security-sensitive paths: {preview}")

    if declaration.workflow_phase == "research":
        reasons.append("declared phase is research")
    elif declaration.workflow_phase == "planning" and len(planned_files) > 1:
        reasons.append("declared phase is planning with multi-file scope")

    return PlanCheckpointDecision(required=bool(reasons), reasons=tuple(reasons))
