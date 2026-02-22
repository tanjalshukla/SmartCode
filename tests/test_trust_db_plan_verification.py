from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sc.trust_db import TrustDB


class TrustDBPlanVerificationTests(unittest.TestCase):
    def test_plan_revision_summary_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db = TrustDB(Path(tmpdir) / "trust.db")
            repo = "/tmp/repo"
            db.record_plan_revision(
                repo_root=repo,
                session_id="s1",
                task="task",
                revision_round=1,
                plan_hash="h1",
                intent_json='{"task":"x"}',
                reasons=("low trust",),
                developer_feedback=None,
                approved=False,
            )
            db.record_plan_revision(
                repo_root=repo,
                session_id="s1",
                task="task",
                revision_round=2,
                plan_hash="h2",
                intent_json='{"task":"x"}',
                reasons=("low trust",),
                developer_feedback="Narrow to one file.",
                approved=False,
            )
            db.record_plan_revision(
                repo_root=repo,
                session_id="s1",
                task="task",
                revision_round=3,
                plan_hash="h3",
                intent_json='{"task":"x"}',
                reasons=("low trust",),
                developer_feedback="Looks good.",
                approved=True,
            )

            summary = db.plan_revision_summary(repo)
            self.assertEqual(summary.total, 3)
            self.assertEqual(summary.approved, 1)
            self.assertEqual(summary.revisions_requested, 1)
            self.assertEqual(summary.denied, 1)

    def test_attach_verification_updates_apply_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db = TrustDB(Path(tmpdir) / "trust.db")
            repo = "/tmp/repo"
            session_id = "s1"
            db.record_trace(
                repo_root=repo,
                session_id=session_id,
                task="task",
                stage="apply",
                action_type="write_request",
                file_path="a.py",
                change_type="logic",
                diff_size=1,
                blast_radius=1,
                existing_lease=False,
                lease_type=None,
                prior_approvals=0,
                prior_denials=0,
                policy_action="proceed",
                policy_score=1.0,
                user_decision="approve",
            )
            db.attach_verification_result(
                repo_root=repo,
                session_id=session_id,
                files=["a.py"],
                verification_passed=True,
                verification_checks_json='[{"name":"python_syntax","passed":true}]',
                expected_behavior="Update a.py",
            )

            rows = db.list_traces(repo, limit=5)
            self.assertEqual(rows[0]["verification_passed"], 1)
            self.assertEqual(rows[0]["expected_behavior"], "Update a.py")

    def test_trace_by_id_includes_policy_reasons(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db = TrustDB(Path(tmpdir) / "trust.db")
            repo = "/tmp/repo"
            db.record_trace(
                repo_root=repo,
                session_id="s1",
                task="task",
                stage="apply",
                action_type="write_request",
                file_path="a.py",
                change_type="logic",
                diff_size=1,
                blast_radius=1,
                existing_lease=False,
                lease_type=None,
                prior_approvals=0,
                prior_denials=0,
                policy_action="check_in",
                policy_score=-0.2,
                policy_reasons=["-risk:large diff"],
                user_decision="deny",
            )
            rows = db.list_traces(repo, limit=1)
            trace = db.trace_by_id(repo, int(rows[0]["id"]))
            assert trace is not None
            self.assertIn("large diff", trace["policy_reasons_json"])


if __name__ == "__main__":
    unittest.main()
