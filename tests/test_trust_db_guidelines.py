from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sc.trust_db import TrustDB


class TrustDBGuidelineTests(unittest.TestCase):
    def test_guideline_candidates_from_repeated_feedback(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db = TrustDB(Path(tmpdir) / "trust.db")
            repo = "/tmp/repo"
            for session_id in ("s1", "s2", "s3"):
                db.record_trace(
                    repo_root=repo,
                    session_id=session_id,
                    task="task",
                    stage="apply",
                    action_type="write_request",
                    file_path="a.py",
                    change_type="error_handling",
                    diff_size=2,
                    blast_radius=1,
                    existing_lease=False,
                    lease_type=None,
                    prior_approvals=0,
                    prior_denials=0,
                    policy_action="check_in",
                    policy_score=-0.2,
                    user_decision="deny",
                    user_feedback_text="Use AppError with codes.",
                )

            candidates = db.guideline_candidates(repo, min_count=2)
            self.assertEqual(len(candidates), 1)
            self.assertEqual(candidates[0].guideline, "Use AppError with codes.")
            self.assertEqual(candidates[0].count, 3)

    def test_add_behavioral_guidelines_is_deduplicated(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db = TrustDB(Path(tmpdir) / "trust.db")
            repo = "/tmp/repo"
            inserted = db.add_behavioral_guidelines(
                repo,
                source="feedback_auto",
                guidelines=["Use AppError.", "Use AppError.", "Run tests before merge."],
            )
            self.assertEqual(inserted, 2)
            inserted_again = db.add_behavioral_guidelines(
                repo,
                source="feedback_auto",
                guidelines=["Use AppError."],
            )
            self.assertEqual(inserted_again, 0)

    def test_guideline_candidates_ignore_non_corrective_feedback(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db = TrustDB(Path(tmpdir) / "trust.db")
            repo = "/tmp/repo"
            db.record_trace(
                repo_root=repo,
                session_id="s1",
                task="task",
                stage="planning",
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
                user_feedback_text="Use option 2 with float return type.",
            )
            candidates = db.guideline_candidates(repo, min_count=1)
            self.assertEqual(candidates, [])


if __name__ == "__main__":
    unittest.main()
