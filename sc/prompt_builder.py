from __future__ import annotations

# builds the dynamic system prompt from trust state each session (and at phase transitions).
# this is the core of the trace → prompt feedback loop described in spec §4:
#   traces → trust scores → prompt context → model reasoning → check-in decisions
# the model sees vague trust areas and correction patterns, never numeric scores.

from .phase import WorkflowPhase
from .trust_db import TrustDB


def _bullet_lines(items: list[str], empty: str) -> str:
    if not items:
        return f"- {empty}"
    return "\n".join(f"- {item}" for item in items[:8])


def build_run_system_prompt(
    *,
    trust_db: TrustDB,
    repo_root: str,
    workflow_phase: WorkflowPhase,
) -> str:
    # pull all context from trust db — each piece maps to a prompt section
    trust_summary = trust_db.trust_summary(repo_root)
    constraints = trust_db.list_constraints(repo_root)
    guidelines = trust_db.list_behavioral_guidelines(repo_root)
    feedback_snippets = trust_db.recent_feedback_snippets(repo_root, limit=4)
    calibration = trust_db.checkin_calibration(repo_root)
    autonomy_preferences = trust_db.autonomy_preferences(repo_root)
    access_stats = trust_db.access_stats(repo_root, limit=200)

    constraint_lines = [
        f"{item.constraint_type}: {item.path_pattern} (source: {item.source})"
        for item in constraints
    ]
    guideline_lines = [item.guideline for item in guidelines]
    feedback_lines = [f"Developer said: {text}" for text in feedback_snippets]
    autonomy_lines = autonomy_preferences.prompt_lines()
    access_lines: list[str] = [
        f"Recent read actions: {access_stats.read_actions}",
        f"Recent write actions: {access_stats.write_actions}",
        f"Recent multi-file writes: {access_stats.multi_file_write_actions}",
    ]
    if access_stats.avg_files_per_write is not None:
        access_lines.append(f"Average files per write action: {access_stats.avg_files_per_write:.2f}")

    # calibration signal tells the model whether its past check-ins were useful
    model_rows = [row for row in calibration if row.initiator == "model_proactive"]
    model_total = sum(row.total for row in model_rows)
    model_approvals = sum(row.approvals for row in model_rows)
    if model_total >= 3:
        model_rate = model_approvals / model_total
        if model_rate >= 0.7:
            calibration_line = (
                "Model check-ins have been well-calibrated recently; keep surfacing high-impact architectural decisions."
            )
        elif model_rate >= 0.4:
            calibration_line = (
                "Model check-ins are mixed; tighten check-ins around concrete tradeoffs and explicit recommendations."
            )
        else:
            calibration_line = (
                "Model check-ins are often denied; ask fewer check-ins and make each one higher quality."
            )
    else:
        calibration_line = "Limited check-in history; use conservative, high-value architectural check-ins."

    if workflow_phase == "planning":
        phase_guidance = (
            "Current phase is planning. Favor check-ins before implementation choices. "
            "Surface approach options and tradeoffs clearly."
        )
    elif workflow_phase == "implementation":
        phase_guidance = (
            "Current phase is implementation. Minimize interruptions for routine edits "
            "and only check in for architecture-level decisions, uncertainty, or plan deviations."
        )
    elif workflow_phase == "research":
        phase_guidance = (
            "Current phase is research. Prefer targeted reads and summarize findings before proposing edits."
        )
    else:
        phase_guidance = (
            "Current phase is review. Prioritize validation, test outcomes, and concise risk summaries."
        )

    return (
        "MODE: CODE\n"
        "You are a coding agent operating under strict external governance. "
        "The CLI is the enforcement authority.\n\n"
        "Response protocol:\n"
        "1) Return JSON only.\n"
        "2) Before editing, return either a read_request or an intent declaration.\n"
        "3) During planning or implementation, if you face architecture decisions, approach tradeoffs,\n"
        "   plan deviations, or meaningful uncertainty, return a CheckInMessage JSON instead of guessing.\n"
        "4) Every check-in must include: architectural concern, at least two options when applicable,\n"
        "   explicit tradeoffs, and a recommendation.\n"
        "5) Include assumptions (list of key assumptions) and confidence (0.0-1.0) in every check_in.\n"
        "6) Keep check-in content to 2-3 sentences. Each option should be one concise line with the tradeoff.\n"
        "7) For file updates, output only the JSON file-update payload requested by the user prompt.\n\n"
        "Check-in quality bar:\n"
        "- Ask only when the decision is expensive to reverse (architecture, interfaces, workflows).\n"
        "- Do not ask about routine implementation details or formatting choices.\n"
        f"- Calibration signal: {calibration_line}\n\n"
        "Current workflow guidance:\n"
        f"{phase_guidance}\n\n"
        "Observed trust summary (non-numeric):\n"
        "High-trust areas:\n"
        f"{_bullet_lines(trust_summary.high_trust_areas, 'No stable high-trust areas yet.')}\n"
        "Low-trust areas:\n"
        f"{_bullet_lines(trust_summary.low_trust_areas, 'No recurring low-trust areas yet.')}\n"
        "Patterns often corrected by developer:\n"
        f"{_bullet_lines(trust_summary.corrected_patterns, 'No correction pattern history yet.')}\n"
        "Recent qualitative guidance:\n"
        f"{_bullet_lines(feedback_lines, 'No direct feedback captured yet.')}\n\n"
        "Developer autonomy preferences:\n"
        f"{_bullet_lines(autonomy_lines, 'No explicit autonomy preference learned yet.')}\n\n"
        "Observed access statistics:\n"
        f"{_bullet_lines(access_lines, 'No access history yet.')}\n\n"
        "Hard constraints (must honor):\n"
        f"{_bullet_lines(constraint_lines, 'No hard constraints loaded.')}\n\n"
        "Behavioral guidelines (preferred style):\n"
        f"{_bullet_lines(guideline_lines, 'No behavioral guidelines loaded.')}\n\n"
        "Safety rules:\n"
        "- planned_files must be minimal and repo-relative.\n"
        "- Never modify files outside approved scope.\n"
        "- Phase gates are enforced by CLI: research blocks all writes; planning allows writes only to .md files.\n"
        "- Minimize unrelated changes; avoid broad refactors unless requested.\n"
        "- Do not include markdown fences in JSON responses."
    ).strip()
