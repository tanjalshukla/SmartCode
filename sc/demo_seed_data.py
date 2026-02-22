from __future__ import annotations

import time

from .trust_db import TrustDB


def seed_demo_data(
    *,
    trust_db: TrustDB,
    repo_root: str,
    reset: bool,
) -> tuple[int, int]:
    session_id = f"demo-{int(time.time())}"
    task = "demo seeded session"
    cleared_traces = 0
    cleared_revisions = 0

    if reset:
        cleared_traces = trust_db.clear_traces(repo_root)
        cleared_revisions = trust_db.clear_plan_revisions(repo_root)

    trust_db.record_plan_revision(
        repo_root=repo_root,
        session_id=session_id,
        task=task,
        revision_round=1,
        plan_hash="demo-plan-v1",
        intent_json='{"planned_files":["demo/feature.py","demo/checkin/service.py"]}',
        reasons=("plan touches 2 files", "constrained files: demo/checkin/service.py"),
        developer_feedback="Keep API contract unchanged and add only one helper.",
        approved=False,
    )
    trust_db.record_plan_revision(
        repo_root=repo_root,
        session_id=session_id,
        task=task,
        revision_round=2,
        plan_hash="demo-plan-v2",
        intent_json='{"planned_files":["demo/feature.py","demo/checkin/service.py"]}',
        reasons=("plan touches 2 files",),
        developer_feedback="Approved after narrowing scope.",
        approved=True,
    )

    trust_db.record_trace(
        repo_root=repo_root,
        session_id=session_id,
        task=task,
        stage="planning",
        action_type="check_in",
        file_path="__session__",
        change_type="decision_point",
        diff_size=None,
        blast_radius=2,
        existing_lease=False,
        lease_type=None,
        prior_approvals=1,
        prior_denials=0,
        policy_action="check_in",
        policy_score=0.0,
        policy_reasons=["model proactively requested architectural guidance"],
        user_decision="approve",
        response_time_ms=9200,
        user_feedback_text="Use option B to keep compatibility for existing callers.",
        model_confidence_self_report=0.64,
        model_assumptions=[
            "Service callers depend on stable payload keys.",
            "Pagination should remain backward compatible.",
        ],
        check_in_initiator="model_proactive",
    )
    trust_db.record_trace(
        repo_root=repo_root,
        session_id=session_id,
        task=task,
        stage="implementation",
        action_type="check_in",
        file_path="__session__",
        change_type="progress_update",
        diff_size=None,
        blast_radius=1,
        existing_lease=False,
        lease_type=None,
        prior_approvals=2,
        prior_denials=0,
        policy_action="check_in",
        policy_score=0.0,
        policy_reasons=["model proactively requested progress confirmation"],
        user_decision="approve",
        response_time_ms=420,
        user_feedback_text=None,
        model_confidence_self_report=0.92,
        model_assumptions=[],
        check_in_initiator="model_proactive",
    )
    trust_db.record_trace(
        repo_root=repo_root,
        session_id=session_id,
        task=task,
        stage="apply",
        action_type="write_request",
        file_path="demo/checkin/service.py",
        change_type="api_change",
        diff_size=18,
        blast_radius=4,
        existing_lease=False,
        lease_type=None,
        prior_approvals=0,
        prior_denials=1,
        policy_action="check_in",
        policy_score=-1.2,
        policy_reasons=["-risk:interface change", "-risk:multi-file blast radius"],
        user_decision="deny",
        response_time_ms=6400,
        user_feedback_text="Do not alter response envelope shape.",
        check_in_initiator="policy",
    )
    trust_db.record_trace(
        repo_root=repo_root,
        session_id=session_id,
        task=task,
        stage="apply",
        action_type="write_request",
        file_path="demo/docs/notes.md",
        change_type="documentation",
        diff_size=2,
        blast_radius=1,
        existing_lease=False,
        lease_type=None,
        prior_approvals=4,
        prior_denials=0,
        policy_action="check_in",
        policy_score=0.1,
        policy_reasons=["-risk:medium diff", "+history:prior approvals"],
        user_decision="approve",
        response_time_ms=500,
        user_feedback_text=None,
        check_in_initiator="policy",
    )
    trust_db.record_trace(
        repo_root=repo_root,
        session_id=session_id,
        task=task,
        stage="apply",
        action_type="write_request",
        file_path="demo/feature.py",
        change_type="general_change",
        diff_size=7,
        blast_radius=1,
        existing_lease=False,
        lease_type=None,
        prior_approvals=3,
        prior_denials=0,
        policy_action="proceed",
        policy_score=1.4,
        policy_reasons=["+history:fast approvals", "+risk:low impact change"],
        user_decision="auto_approve",
        verification_passed=True,
        verification_checks_json='[{"name":"python_syntax","passed":true,"output":"ok"}]',
        expected_behavior="Add helper that keeps behavior intact.",
        check_in_initiator=None,
    )
    trust_db.record_trace(
        repo_root=repo_root,
        session_id=session_id,
        task=task,
        stage="apply",
        action_type="write_request",
        file_path="demo/checkin/service.py",
        change_type="api_change",
        diff_size=9,
        blast_radius=2,
        existing_lease=False,
        lease_type=None,
        prior_approvals=1,
        prior_denials=1,
        policy_action="proceed_flag",
        policy_score=0.5,
        policy_reasons=["-risk:interface change", "+history:approvals"],
        user_decision="auto_approve_flag",
        verification_passed=False,
        verification_checks_json='[{"name":"python_syntax","passed":false,"output":"syntax error"}]',
        expected_behavior="Refactor service while preserving envelope.",
        check_in_initiator=None,
    )

    return cleared_traces, cleared_revisions
