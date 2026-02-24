from __future__ import annotations

# heuristic policy engine — scores each file action to decide
# whether to auto-approve, flag for review, or force a check-in.
# weights are initial guesses from spec §5.1, tuned against real data later.

from dataclasses import dataclass
from typing import Iterable, Literal


PolicyAction = Literal["check_in", "proceed", "proceed_flag"]


@dataclass(frozen=True)
class PolicyInput:
    # effective approvals (rubber-stamps are 0.5x weighted via PolicyHistory)
    prior_approvals: float
    prior_denials: int
    avg_response_ms: float | None
    avg_edit_distance: float
    diff_size: int
    blast_radius: int
    is_new_file: bool
    is_security_sensitive: bool
    change_pattern: str | None
    recent_denials: int
    files_in_action: int
    verification_failure_rate: float | None = None
    model_confidence_avg: float | None = None
    model_confidence_samples: int = 0


@dataclass(frozen=True)
class PolicyDecision:
    action: PolicyAction
    score: float
    reasons: tuple[str, ...]


def decide_action(
    policy_input: PolicyInput,
    proceed_threshold: float,
    flag_threshold: float,
) -> PolicyDecision:
    score = 0.0
    reasons: list[str] = []

    # --- history signals (strongest influence) ---
    if policy_input.prior_approvals:
        score += policy_input.prior_approvals * 0.4
        reasons.append(f"+history:{policy_input.prior_approvals:.1f} weighted approvals")
    if policy_input.prior_denials:
        score -= policy_input.prior_denials * 0.7
        reasons.append(f"-history:{policy_input.prior_denials} denials")

    # review pace: fast approvals noted but not penalized here —
    # the rubber-stamp discount happens upstream in PolicyHistory.effective_approvals
    if policy_input.avg_response_ms is not None:
        if policy_input.avg_response_ms < 5000:
            reasons.append("~history:quick approvals are down-weighted")
        elif policy_input.avg_response_ms > 15000:
            score += 0.15
            reasons.append("+history:deliberate review pace")

    # edit distance: high corrections → developer heavily modifies agent output
    if policy_input.avg_edit_distance > 0:
        score -= min(policy_input.avg_edit_distance, 1.0) * 0.5
        reasons.append(f"-quality:edit distance {policy_input.avg_edit_distance:.2f}")

    # --- risk signals ---
    if policy_input.diff_size > 80:
        score -= 0.8
        reasons.append("-risk:large diff")
    elif policy_input.diff_size > 30:
        score -= 0.4
        reasons.append("-risk:medium diff")

    if policy_input.blast_radius > 3:
        score -= 0.8
        reasons.append("-risk:multi-file blast radius")

    if policy_input.files_in_action > 4:
        score -= 0.9
        reasons.append("-risk:large multi-file action")
    elif policy_input.files_in_action > 1:
        score -= 0.35
        reasons.append("-risk:multi-file action")

    if policy_input.is_new_file:
        score -= 0.6
        reasons.append("-risk:new file")

    if policy_input.is_security_sensitive:
        score -= 2.0
        reasons.append("-risk:security sensitive")

    # full pattern scoring for semantic risk calibration.
    if policy_input.change_pattern in {"api_change", "data_model_change"}:
        score -= 0.8
        reasons.append("-risk:interface change")
    elif policy_input.change_pattern in {"test_generation", "documentation"}:
        score += 0.3
        reasons.append("+risk:low impact change")
    elif policy_input.change_pattern == "config_change":
        score -= 0.4
        reasons.append("-risk:config change")
    elif policy_input.change_pattern == "dependency_update":
        score -= 0.5
        reasons.append("-risk:dependency update")
    elif policy_input.change_pattern == "error_handling":
        score += 0.1
        reasons.append("+risk:error handling is usually localized")

    # --- session momentum ---
    if policy_input.recent_denials:
        score -= min(policy_input.recent_denials, 3) * 0.7
        reasons.append("-session:recent denials")

    # --- trace-derived quality signals ---
    if policy_input.verification_failure_rate is not None and policy_input.verification_failure_rate > 0.30:
        score -= 0.6
        reasons.append(
            f"-quality:verification failure rate {policy_input.verification_failure_rate:.0%}"
        )

    if (
        policy_input.model_confidence_avg is not None
        and policy_input.model_confidence_samples >= 3
        and policy_input.model_confidence_avg < 0.40
    ):
        score -= 0.3
        reasons.append(
            f"-quality:low model confidence {policy_input.model_confidence_avg:.2f} "
            f"({policy_input.model_confidence_samples} samples)"
        )

    # --- threshold comparison ---
    if score >= proceed_threshold:
        return PolicyDecision("proceed", score, tuple(reasons))
    if score >= flag_threshold:
        return PolicyDecision("proceed_flag", score, tuple(reasons))
    return PolicyDecision("check_in", score, tuple(reasons))


def within_scope_budget(files: Iterable[str], scope_budget_files: int) -> bool:
    return len(list(files)) <= scope_budget_files
