from __future__ import annotations

import json
import time
from pathlib import Path

import typer
from rich import print
from rich.table import Table

from ..commands.shared import open_trust_db, require_repo_root
from ..cli_shared import is_approval_decision as _is_approval_decision
from ..demo_seed_data import seed_demo_data

def _format_expiry(expires_at: int | None) -> str:
    if expires_at is None:
        return "permanent"
    now = int(time.time())
    delta = expires_at - now
    if delta <= 0:
        return "expired"
    minutes = delta // 60
    hours = minutes // 60
    days = hours // 24
    if days > 0:
        return f"in {days}d {hours % 24}h"
    if hours > 0:
        return f"in {hours}h {minutes % 60}m"
    return f"in {minutes}m"


def _format_timestamp(epoch_seconds: int) -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(epoch_seconds))


def _truncate_text(value: str | None, *, max_len: int) -> str:
    if not value:
        return "-"
    text = str(value)
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _format_verify_cell(value: int | None) -> str:
    if value == 1:
        return "pass"
    if value == 0:
        return "fail"
    return "-"


def _format_trace_row(row: dict) -> list[str]:
    return [
        str(row["id"]),
        _format_timestamp(int(row["created_at"])),
        row["stage"],
        row["file_path"],
        row["check_in_initiator"] or "-",
        (
            f"{float(row['model_confidence_self_report']):.2f}"
            if row["model_confidence_self_report"] is not None
            else "-"
        ),
        f"{row['policy_action']} ({row['policy_score']:.2f})",
        row["user_decision"],
        _truncate_text(row["user_feedback_text"], max_len=40),
        _format_verify_cell(row["verification_passed"]),
        str(row["diff_size"] if row["diff_size"] is not None else "-"),
        (
            f"{float(row['review_duration_seconds']):.1f}"
            if row["review_duration_seconds"] is not None
            else "-"
        ),
        "rubber"
        if row["rubber_stamp"] == 1 and _is_approval_decision(str(row["user_decision"]))
        else "-",
        str(row["response_time_ms"] if row["response_time_ms"] is not None else "-"),
    ]


def leases(
    json_out: bool = typer.Option(False, "--json", help="Output leases as JSON."),
):
    """List active leases for this repo."""
    repo_root = require_repo_root()
    trust_db = open_trust_db(repo_root)
    leases = trust_db.list_active_leases(str(repo_root))
    if not leases:
        print("[yellow]No active leases.[/yellow]")
        return

    if json_out:
        payload = [
            {
                "file_path": lease.file_path,
                "expires_at": lease.expires_at,
                "type": lease.lease_type,
            }
            for lease in leases
        ]
        print(json.dumps(payload, indent=2))
        return

    table = Table(title="Active Leases")
    table.add_column("Type")
    table.add_column("File")
    table.add_column("Expires")
    for lease in leases:
        table.add_row(lease.lease_type, lease.file_path, _format_expiry(lease.expires_at))
    print(table)


def traces(
    limit: int = typer.Option(30, "--limit", help="Number of recent trace rows to show."),
    json_out: bool = typer.Option(False, "--json", help="Output traces as JSON."),
):
    """List recent governance traces for this repo."""
    repo_root = require_repo_root()
    trust_db = open_trust_db(repo_root)
    rows = trust_db.list_traces(str(repo_root), limit=limit)
    if not rows:
        print("[yellow]No traces recorded yet.[/yellow]")
        return

    if json_out:
        payload = [dict(row) for row in rows]
        print(json.dumps(payload, indent=2))
        return

    columns = [
        "ID",
        "Time",
        "Stage",
        "File",
        "Initiator",
        "MConf",
        "Policy",
        "Decision",
        "Feedback",
        "Verify",
        "Diff",
        "Rev(s)",
        "QS",
        "Resp(ms)",
    ]
    table = Table(title="Recent Traces")
    for column in columns:
        table.add_column(column)
    for row in rows:
        table.add_row(*_format_trace_row(dict(row)))
    print(table)


def explain(
    trace_id: int = typer.Argument(..., help="Trace row id from `sc traces`."),
):
    """Explain why a specific decision happened using stored trace context."""
    repo_root = require_repo_root()
    trust_db = open_trust_db(repo_root)
    row = trust_db.trace_by_id(str(repo_root), trace_id)
    if row is None:
        print(f"[red]Trace id {trace_id} not found for this repo.[/red]")
        raise typer.Exit(code=1)

    reasons: list[str] = []
    if row["policy_reasons_json"]:
        try:
            parsed = json.loads(row["policy_reasons_json"])
            reasons = [str(item) for item in parsed if str(item).strip()]
        except Exception:
            reasons = []

    assumptions: list[str] = []
    if row["model_assumptions_json"]:
        try:
            parsed = json.loads(row["model_assumptions_json"])
            assumptions = [str(item) for item in parsed if str(item).strip()]
        except Exception:
            assumptions = []

    print(f"[bold]Trace {trace_id}[/bold]")
    print(f"Time: {_format_timestamp(int(row['created_at']))}")
    print(f"Stage/action: {row['stage']} / {row['action_type']}")
    print(f"File: {row['file_path']}")
    print(f"Policy decision: {row['policy_action']} (score={row['policy_score']:.2f})")
    print(f"User decision: {row['user_decision']}")
    print(
        "Context: "
        f"prior approvals={row['prior_approvals']}, "
        f"prior denials={row['prior_denials']}, "
        f"existing lease={'yes' if row['existing_lease'] else 'no'}"
    )
    if row["diff_size"] is not None or row["blast_radius"] is not None:
        print(
            "Risk: "
            f"diff_size={row['diff_size'] if row['diff_size'] is not None else '-'}, "
            f"blast_radius={row['blast_radius'] if row['blast_radius'] is not None else '-'}, "
            f"change_type={row['change_type'] or '-'}"
        )
    if reasons:
        print("Policy reasons:")
        for reason in reasons:
            print(f"  - {reason}")
    if row["check_in_initiator"]:
        print(f"Check-in initiator: {row['check_in_initiator']}")
    if row["review_duration_seconds"] is not None:
        duration = float(row["review_duration_seconds"])
        label = " (rubber-stamp)" if row["rubber_stamp"] == 1 and _is_approval_decision(str(row["user_decision"])) else ""
        print(f"Review duration: {duration:.2f}s{label}")
    if row["model_confidence_self_report"] is not None:
        print(f"Model confidence: {float(row['model_confidence_self_report']):.2f}")
    if assumptions:
        print("Model assumptions:")
        for assumption in assumptions:
            print(f"  - {assumption}")
    if row["user_feedback_text"]:
        print(f"Developer feedback: {row['user_feedback_text']}")
    if row["verification_passed"] is not None:
        state = "pass" if row["verification_passed"] == 1 else "fail"
        print(f"Verification: {state}")
    if row["expected_behavior"]:
        print(f"Expected behavior: {row['expected_behavior']}")


def checkin_stats(
    json_out: bool = typer.Option(False, "--json", help="Output check-in calibration stats as JSON."),
):
    """Show check-in calibration metrics grouped by initiator and stage."""
    repo_root = require_repo_root()
    trust_db = open_trust_db(repo_root)
    rows = trust_db.checkin_calibration(str(repo_root))
    if not rows:
        print("[yellow]No check-in calibration data yet.[/yellow]")
        return

    if json_out:
        payload = [
            {
                "initiator": row.initiator,
                "stage": row.stage,
                "total": row.total,
                "approvals": row.approvals,
                "denials": row.denials,
                "approval_rate": row.approval_rate,
                "avg_response_ms": row.avg_response_ms,
            }
            for row in rows
        ]
        print(json.dumps(payload, indent=2))
        return

    table = Table(title="Check-in Calibration")
    table.add_column("Initiator")
    table.add_column("Stage")
    table.add_column("Total")
    table.add_column("Approvals")
    table.add_column("Denials")
    table.add_column("Approval %")
    table.add_column("Avg Resp(ms)")
    for row in rows:
        table.add_row(
            row.initiator,
            row.stage,
            str(row.total),
            str(row.approvals),
            str(row.denials),
            f"{row.approval_rate * 100:.1f}",
            f"{row.avg_response_ms:.0f}" if row.avg_response_ms is not None else "-",
        )
    print(table)


def preferences(
    json_out: bool = typer.Option(False, "--json", help="Output learned autonomy preferences as JSON."),
):
    """Show currently learned autonomy preferences."""
    repo_root = require_repo_root()
    trust_db = open_trust_db(repo_root)
    prefs = trust_db.autonomy_preferences(str(repo_root))
    payload = {
        "prefer_fewer_checkins": prefs.prefer_fewer_checkins,
        "allowed_checkin_topics": list(prefs.allowed_checkin_topics),
        "skip_low_risk_plan_checkpoint": prefs.skip_low_risk_plan_checkpoint,
        "scoped_paths": list(prefs.scoped_paths),
    }

    if json_out:
        print(json.dumps(payload, indent=2))
        return

    table = Table(title="Autonomy Preferences")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Prefer fewer check-ins", "yes" if prefs.prefer_fewer_checkins else "no")
    table.add_row(
        "Allowed check-in topics",
        ", ".join(prefs.allowed_checkin_topics) if prefs.allowed_checkin_topics else "-",
    )
    table.add_row(
        "Skip low-risk plan checkpoints",
        "yes" if prefs.skip_low_risk_plan_checkpoint else "no",
    )
    table.add_row("Scoped paths", ", ".join(prefs.scoped_paths) if prefs.scoped_paths else "-")
    print(table)


def preferences_clear(
    yes: bool = typer.Option(False, "--yes", help="Confirm deleting learned autonomy preferences."),
):
    """Delete learned autonomy preferences for this repo."""
    if not yes:
        print("[red]Refusing to clear preferences without --yes.[/red]")
        raise typer.Exit(code=1)
    repo_root = require_repo_root()
    trust_db = open_trust_db(repo_root)
    removed = trust_db.delete_autonomy_preferences(str(repo_root))
    if removed:
        print("[green]Cleared learned autonomy preferences.[/green]")
    else:
        print("[yellow]No learned autonomy preferences found.[/yellow]")


def report(
    json_out: bool = typer.Option(False, "--json", help="Output report as JSON."),
):
    """Show a compact governance report for demo/readiness checks."""
    repo_root = require_repo_root()
    trust_db = open_trust_db(repo_root)
    repo_root_str = str(repo_root)
    rows = trust_db.list_traces(repo_root_str, limit=5000)
    checkins = trust_db.checkin_calibration(repo_root_str)
    checkin_quality = trust_db.checkin_usefulness_summary(repo_root_str)
    plan_summary = trust_db.plan_revision_summary(repo_root_str)
    verification_total, verification_passed = trust_db.verification_summary(repo_root_str)

    stage_counts: dict[str, int] = {}
    decision_counts: dict[str, int] = {}
    rubber_stamp_approvals = 0
    thoughtful_approvals = 0
    for row in rows:
        stage = str(row["stage"])
        stage_counts[stage] = stage_counts.get(stage, 0) + 1
        decision = str(row["user_decision"])
        decision_counts[decision] = decision_counts.get(decision, 0) + 1
        if _is_approval_decision(decision):
            if row["rubber_stamp"] == 1:
                rubber_stamp_approvals += 1
            else:
                thoughtful_approvals += 1

    model_confidence_values = [
        float(row["model_confidence_self_report"])
        for row in rows
        if row["check_in_initiator"] == "model_proactive"
        and row["model_confidence_self_report"] is not None
    ]

    payload = {
        "trace_rows": len(rows),
        "stage_counts": stage_counts,
        "decision_counts": decision_counts,
        "checkin_calibration": [
            {
                "initiator": item.initiator,
                "stage": item.stage,
                "total": item.total,
                "approval_rate": item.approval_rate,
            }
            for item in checkins
        ],
        "checkin_usefulness": [
            {
                "initiator": row.initiator,
                "total": row.total,
                "useful": row.useful,
                "wasted": row.wasted,
                "useful_rate": row.useful_rate,
            }
            for row in checkin_quality
        ],
        "model_confidence": {
            "count": len(model_confidence_values),
            "avg": (
                (sum(model_confidence_values) / len(model_confidence_values))
                if model_confidence_values
                else None
            ),
        },
        "review_quality": {
            "rubber_stamp_approvals": rubber_stamp_approvals,
            "thoughtful_approvals": thoughtful_approvals,
            "rubber_stamp_threshold_seconds": 5.0,
        },
        "plan_revisions": {
            "total": plan_summary.total,
            "approved": plan_summary.approved,
            "revisions_requested": plan_summary.revisions_requested,
            "denied": plan_summary.denied,
        },
        "verification": {
            "total": verification_total,
            "passed": verification_passed,
            "pass_rate": (verification_passed / verification_total) if verification_total else None,
        },
    }
    if json_out:
        print(json.dumps(payload, indent=2))
        return

    print("[bold]Governance report[/bold]")
    print(f"Trace rows: {payload['trace_rows']}")
    print("Stage counts:")
    for key in sorted(stage_counts):
        print(f"  - {key}: {stage_counts[key]}")
    print("Decision counts:")
    for key in sorted(decision_counts):
        print(f"  - {key}: {decision_counts[key]}")
    if checkin_quality:
        print("Check-in usefulness:")
        for row in checkin_quality:
            print(
                f"  - {row.initiator}: useful={row.useful}/{row.total} "
                f"({row.useful_rate * 100:.1f}%), wasted={row.wasted}"
            )
    if model_confidence_values:
        avg_conf = sum(model_confidence_values) / len(model_confidence_values)
        print(
            f"Model confidence (model-proactive check-ins): "
            f"n={len(model_confidence_values)}, avg={avg_conf:.2f}"
        )
    print(
        "Review quality: "
        f"thoughtful approvals={thoughtful_approvals}, "
        f"rubber-stamp approvals (<5s)={rubber_stamp_approvals}"
    )
    print(
        "Plan revisions: "
        f"total={plan_summary.total}, approved={plan_summary.approved}, "
        f"revise={plan_summary.revisions_requested}, denied={plan_summary.denied}"
    )
    if verification_total:
        rate = verification_passed / verification_total
        print(
            "Verification: "
            f"{verification_passed}/{verification_total} passed ({rate * 100:.1f}%)"
        )
    else:
        print("Verification: no recorded verification runs yet")

    if checkins:
        table = Table(title="Check-in Calibration Snapshot")
        table.add_column("Initiator")
        table.add_column("Stage")
        table.add_column("Total")
        table.add_column("Approval %")
        for row in checkins:
            table.add_row(
                row.initiator,
                row.stage,
                str(row.total),
                f"{row.approval_rate * 100:.1f}",
            )
        print(table)


def demo_seed(
    reset: bool = typer.Option(
        True,
        "--reset/--no-reset",
        help="Reset existing traces and plan revisions for deterministic demo output.",
    ),
):
    """Seed deterministic trace data for a no-network advisor demo."""
    repo_root = require_repo_root()

    repo_root_str = str(repo_root)
    trust_db = open_trust_db(repo_root)
    cleared_traces, cleared_revisions = seed_demo_data(
        trust_db=trust_db,
        repo_root=repo_root_str,
        reset=reset,
    )
    if reset:
        print(
            f"[yellow]Cleared {cleared_traces} traces and {cleared_revisions} plan revisions.[/yellow]"
        )
    print("[green]Seeded deterministic demo traces.[/green]")
    print("Run `python -m sc report` and `python -m sc traces --limit 20`.")


def revoke(
    path: str | None = typer.Argument(None, help="Repo-relative file path to revoke."),
    all: bool = typer.Option(False, "--all", help="Revoke all leases for this repo."),
):
    """Revoke leases for a file (or all)."""
    if not path and not all:
        print("[red]Provide a path or --all.[/red]")
        raise typer.Exit(code=1)

    repo_root = require_repo_root()
    trust_db = open_trust_db(repo_root)
    normalized = None
    if path:
        normalized = str(Path(path))
    removed_leases, removed_decisions = trust_db.revoke(
        str(repo_root),
        file_path=normalized if not all else None,
        reset_counts=True,
    )
    print(f"[green]Revoked {removed_leases} leases.[/green]")
    if removed_decisions:
        print(f"[green]Cleared {removed_decisions} approval records.[/green]")
