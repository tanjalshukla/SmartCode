from __future__ import annotations

import unittest

from sc.policy import PolicyInput, decide_action


class PolicyTests(unittest.TestCase):
    def test_high_trust_proceeds(self) -> None:
        decision = decide_action(
            PolicyInput(
                prior_approvals=8,
                prior_denials=0,
                avg_response_ms=1200,
                avg_edit_distance=0.0,
                diff_size=12,
                blast_radius=1,
                is_new_file=False,
                is_security_sensitive=False,
                change_pattern="test_generation",
                recent_denials=0,
                files_in_action=1,
            ),
            proceed_threshold=1.2,
            flag_threshold=0.3,
        )
        self.assertEqual(decision.action, "proceed")

    def test_security_sensitive_checks_in(self) -> None:
        decision = decide_action(
            PolicyInput(
                prior_approvals=3,
                prior_denials=0,
                avg_response_ms=2000,
                avg_edit_distance=0.0,
                diff_size=10,
                blast_radius=1,
                is_new_file=False,
                is_security_sensitive=True,
                change_pattern="security_sensitive",
                recent_denials=0,
                files_in_action=1,
            ),
            proceed_threshold=1.2,
            flag_threshold=0.3,
        )
        self.assertEqual(decision.action, "check_in")

    def test_medium_score_flags(self) -> None:
        decision = decide_action(
            PolicyInput(
                prior_approvals=2,
                prior_denials=0,
                avg_response_ms=5000,
                avg_edit_distance=0.1,
                diff_size=25,
                blast_radius=2,
                is_new_file=False,
                is_security_sensitive=False,
                change_pattern="general_change",
                recent_denials=0,
                files_in_action=1,
            ),
            proceed_threshold=1.2,
            flag_threshold=0.3,
        )
        self.assertEqual(decision.action, "proceed_flag")

    def test_verification_failure_penalizes_score(self) -> None:
        decision = decide_action(
            PolicyInput(
                prior_approvals=3,
                prior_denials=0,
                avg_response_ms=9000,
                avg_edit_distance=0.0,
                diff_size=5,
                blast_radius=1,
                is_new_file=False,
                is_security_sensitive=False,
                change_pattern="general_change",
                recent_denials=0,
                files_in_action=1,
                verification_failure_rate=0.6,
            ),
            proceed_threshold=1.2,
            flag_threshold=0.3,
        )
        self.assertNotEqual(decision.action, "proceed")
        self.assertTrue(any("verification failure rate" in reason for reason in decision.reasons))

    def test_low_model_confidence_penalizes_score_when_samples_sufficient(self) -> None:
        decision = decide_action(
            PolicyInput(
                prior_approvals=3,
                prior_denials=0,
                avg_response_ms=9000,
                avg_edit_distance=0.0,
                diff_size=5,
                blast_radius=1,
                is_new_file=False,
                is_security_sensitive=False,
                change_pattern="general_change",
                recent_denials=0,
                files_in_action=1,
                model_confidence_avg=0.2,
                model_confidence_samples=4,
            ),
            proceed_threshold=1.2,
            flag_threshold=0.3,
        )
        self.assertNotEqual(decision.action, "proceed")
        self.assertTrue(any("low model confidence" in reason for reason in decision.reasons))


if __name__ == "__main__":
    unittest.main()
