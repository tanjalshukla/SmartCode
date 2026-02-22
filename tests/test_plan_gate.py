from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sc.plan_gate import decide_plan_checkpoint
from sc.schema import IntentDeclaration
from sc.trust_db import HardConstraint, TrustDB


class PlanGateTests(unittest.TestCase):
    def test_strict_mode_always_requires_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db = TrustDB(Path(tmpdir) / "trust.db")
            declaration = IntentDeclaration(
                task_summary="Update docs",
                planned_files=["README.md"],
                planned_actions=["edit_code"],
                planned_commands=[],
            )
            decision = decide_plan_checkpoint(
                trust_db=db,
                repo_root="/tmp/repo",
                declaration=declaration,
                strict=True,
                max_auto_files=2,
            )
            self.assertTrue(decision.required)
            self.assertIn("strict plan gate enabled", decision.reasons)

    def test_low_risk_trusted_single_file_skips_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db = TrustDB(Path(tmpdir) / "trust.db")
            repo = "/tmp/repo"
            for _ in range(3):
                db.record_trace(
                    repo_root=repo,
                    session_id="s1",
                    task="task",
                    stage="apply",
                    action_type="write_request",
                    file_path="docs/readme.md",
                    change_type="documentation",
                    diff_size=2,
                    blast_radius=1,
                    existing_lease=False,
                    lease_type=None,
                    prior_approvals=0,
                    prior_denials=0,
                    policy_action="proceed",
                    policy_score=1.0,
                    user_decision="auto_approve",
                )
            declaration = IntentDeclaration(
                task_summary="Add one doc line",
                planned_files=["docs/readme.md"],
                planned_actions=["edit_code"],
                planned_commands=[],
            )
            decision = decide_plan_checkpoint(
                trust_db=db,
                repo_root=repo,
                declaration=declaration,
                strict=False,
                max_auto_files=1,
            )
            self.assertFalse(decision.required)

    def test_constraints_require_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db = TrustDB(Path(tmpdir) / "trust.db")
            repo = "/tmp/repo"
            db.replace_constraints(
                repo_root=repo,
                source="AGENTS.md",
                constraints=[
                    HardConstraint(
                        path_pattern="src/auth/*",
                        constraint_type="always_check_in",
                        source="AGENTS.md",
                        overridable=False,
                    )
                ],
            )
            declaration = IntentDeclaration(
                task_summary="Auth changes",
                planned_files=["src/auth/login.py"],
                planned_actions=["edit_code"],
                planned_commands=[],
            )
            decision = decide_plan_checkpoint(
                trust_db=db,
                repo_root=repo,
                declaration=declaration,
                strict=False,
                max_auto_files=3,
            )
            self.assertTrue(decision.required)
            self.assertTrue(any("constrained files" in reason for reason in decision.reasons))


if __name__ == "__main__":
    unittest.main()
