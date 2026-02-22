from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sc.trust_db import TrustDB


class TrustDBCheckInUsefulnessTests(unittest.TestCase):
    def test_usefulness_summary_splits_useful_and_wasted(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db = TrustDB(Path(tmpdir) / "trust.db")
            repo = "/tmp/repo"

            # Useful model check-in: denial + feedback.
            db.record_trace(
                repo_root=repo,
                session_id="s1",
                task="task",
                stage="planning",
                action_type="check_in",
                file_path="__session__",
                change_type="decision_point",
                diff_size=None,
                blast_radius=1,
                existing_lease=False,
                lease_type=None,
                prior_approvals=0,
                prior_denials=0,
                policy_action="check_in",
                policy_score=0.0,
                user_decision="deny",
                response_time_ms=3200,
                user_feedback_text="Need a safer migration plan.",
                check_in_initiator="model_proactive",
            )
            # Wasted model check-in: immediate approval, no feedback.
            db.record_trace(
                repo_root=repo,
                session_id="s1",
                task="task",
                stage="implementation",
                action_type="check_in",
                file_path="__session__",
                change_type="progress_update",
                diff_size=None,
                blast_radius=1,
                existing_lease=False,
                lease_type=None,
                prior_approvals=0,
                prior_denials=0,
                policy_action="check_in",
                policy_score=0.0,
                user_decision="approve",
                response_time_ms=200,
                user_feedback_text=None,
                check_in_initiator="model_proactive",
            )

            rows = db.checkin_usefulness_summary(repo, quick_approve_ms=1500)
            self.assertEqual(len(rows), 1)
            summary = rows[0]
            self.assertEqual(summary.initiator, "model_proactive")
            self.assertEqual(summary.total, 2)
            self.assertEqual(summary.useful, 1)
            self.assertEqual(summary.wasted, 1)


if __name__ == "__main__":
    unittest.main()
