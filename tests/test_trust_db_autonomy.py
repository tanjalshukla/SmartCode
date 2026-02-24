from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sc.autonomy import AutonomyPreferences
from sc.trust_db import TrustDB


class TrustDBAutonomyTests(unittest.TestCase):
    def test_learn_autonomy_preferences_from_feedback(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db = TrustDB(Path(tmpdir) / "trust.db")
            repo = "/tmp/repo"
            learned = db.learn_autonomy_preferences(
                repo,
                "Proceed autonomously for low-risk refactors. Only check in for API/signature/schema/security changes.",
            )
            self.assertGreaterEqual(len(learned), 1)
            prefs = db.autonomy_preferences(repo)
            self.assertTrue(prefs.prefer_fewer_checkins)
            self.assertIn("api", prefs.allowed_checkin_topics)
            self.assertTrue(prefs.skip_low_risk_plan_checkpoint)

    def test_merge_autonomy_preferences_unions_topics(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db = TrustDB(Path(tmpdir) / "trust.db")
            repo = "/tmp/repo"
            db.merge_autonomy_preferences(
                repo,
                AutonomyPreferences(
                    prefer_fewer_checkins=True,
                    allowed_checkin_topics=("api",),
                ),
            )
            db.merge_autonomy_preferences(
                repo,
                AutonomyPreferences(
                    allowed_checkin_topics=("signature", "security"),
                ),
            )
            prefs = db.autonomy_preferences(repo)
            self.assertEqual(prefs.allowed_checkin_topics, ("api", "security", "signature"))

    def test_delete_autonomy_preferences(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db = TrustDB(Path(tmpdir) / "trust.db")
            repo = "/tmp/repo"
            db.learn_autonomy_preferences(repo, "Proceed autonomously for low-risk changes.")
            self.assertTrue(db.autonomy_preferences(repo).prefer_fewer_checkins)
            removed = db.delete_autonomy_preferences(repo)
            self.assertEqual(removed, 1)
            self.assertFalse(db.autonomy_preferences(repo).prefer_fewer_checkins)

    def test_verification_failure_rate_and_model_confidence_stats(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db = TrustDB(Path(tmpdir) / "trust.db")
            repo = "/tmp/repo"

            db.record_trace(
                repo_root=repo,
                session_id="s1",
                task="task",
                stage="apply",
                action_type="write_request",
                file_path="demo/feature.py",
                change_type="general_change",
                diff_size=2,
                blast_radius=1,
                existing_lease=False,
                lease_type=None,
                prior_approvals=0,
                prior_denials=0,
                policy_action="proceed",
                policy_score=1.0,
                user_decision="approve",
                verification_passed=True,
            )
            db.record_trace(
                repo_root=repo,
                session_id="s2",
                task="task",
                stage="apply",
                action_type="write_request",
                file_path="demo/feature.py",
                change_type="general_change",
                diff_size=2,
                blast_radius=1,
                existing_lease=False,
                lease_type=None,
                prior_approvals=1,
                prior_denials=0,
                policy_action="proceed",
                policy_score=0.8,
                user_decision="approve",
                verification_passed=False,
            )
            db.record_trace(
                repo_root=repo,
                session_id="s3",
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
                model_confidence_self_report=0.25,
                check_in_initiator="model_proactive",
            )

            failure_rate = db.verification_failure_rate(repo, "demo/feature.py")
            self.assertEqual(failure_rate, 0.5)
            confidence = db.model_confidence_stats(repo, file_path="demo/feature.py")
            self.assertEqual(confidence.samples, 1)
            assert confidence.average is not None
            self.assertAlmostEqual(confidence.average, 0.25, places=2)


if __name__ == "__main__":
    unittest.main()
