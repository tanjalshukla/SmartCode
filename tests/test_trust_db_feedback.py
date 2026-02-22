from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sc.trust_db import TrustDB


class TrustDBFeedbackTests(unittest.TestCase):
    def test_recent_feedback_snippets_returns_unique_recent_values(self) -> None:
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
                diff_size=4,
                blast_radius=1,
                existing_lease=False,
                lease_type=None,
                prior_approvals=0,
                prior_denials=0,
                policy_action="check_in",
                policy_score=-0.4,
                user_decision="deny",
                user_feedback_text="Use the existing error wrapper.",
            )
            db.record_trace(
                repo_root=repo,
                session_id="s2",
                task="task",
                stage="apply",
                action_type="write_request",
                file_path="b.py",
                change_type="logic",
                diff_size=2,
                blast_radius=1,
                existing_lease=False,
                lease_type=None,
                prior_approvals=0,
                prior_denials=0,
                policy_action="check_in",
                policy_score=-0.3,
                user_decision="deny",
                user_feedback_text="Use the existing error wrapper.",
            )
            db.record_trace(
                repo_root=repo,
                session_id="s3",
                task="task",
                stage="check_in",
                action_type="check_in",
                file_path="__session__",
                change_type="decision_point",
                diff_size=None,
                blast_radius=None,
                existing_lease=False,
                lease_type=None,
                prior_approvals=0,
                prior_denials=0,
                policy_action="check_in",
                policy_score=0.0,
                user_decision="approve",
                user_feedback_text="Prefer cursor pagination for API consistency.",
            )

            snippets = db.recent_feedback_snippets(repo, limit=4)
            self.assertEqual(len(snippets), 2)
            self.assertIn("Prefer cursor pagination for API consistency.", snippets)
            self.assertIn("Use the existing error wrapper.", snippets)


if __name__ == "__main__":
    unittest.main()
