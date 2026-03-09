from __future__ import annotations

import unittest

from sc.autonomy import (
    AutonomyPreferences,
    adjusted_policy_thresholds,
    preferences_from_model_payload,
)


class AutonomyPreferenceTests(unittest.TestCase):
    def test_adjusted_thresholds_when_prefers_fewer_checkins(self) -> None:
        prefs = AutonomyPreferences(prefer_fewer_checkins=True)
        proceed, flag = adjusted_policy_thresholds(0.9, 0.2, prefs)
        self.assertLess(proceed, 0.9)
        self.assertLess(flag, 0.2)

    def test_preferences_from_model_payload(self) -> None:
        payload = {
            "prefer_fewer_checkins": True,
            "allowed_checkin_topics": ["api", "signature", "bogus"],
            "skip_low_risk_plan_checkpoint": True,
            "scoped_paths": ["demo/checkin/*"],
        }
        prefs = preferences_from_model_payload(payload)
        self.assertTrue(prefs.prefer_fewer_checkins)
        self.assertEqual(prefs.allowed_checkin_topics, ("api", "signature"))
        self.assertTrue(prefs.skip_low_risk_plan_checkpoint)
        self.assertEqual(prefs.scoped_paths, ("demo/checkin/*",))

    def test_adjusted_thresholds_scope_aware(self) -> None:
        prefs = AutonomyPreferences(
            prefer_fewer_checkins=True,
            scoped_paths=("demo/checkin/*",),
        )
        proceed_scoped, flag_scoped = adjusted_policy_thresholds(
            0.9, 0.2, prefs, file_path="demo/checkin/service.py"
        )
        proceed_other, flag_other = adjusted_policy_thresholds(
            0.9, 0.2, prefs, file_path="demo/feature.py"
        )
        self.assertLess(proceed_scoped, 0.9)
        self.assertLess(flag_scoped, 0.2)
        self.assertEqual(proceed_other, 0.9)
        self.assertEqual(flag_other, 0.2)

    def test_calibration_can_tighten_thresholds(self) -> None:
        prefs = AutonomyPreferences(prefer_fewer_checkins=True)
        proceed, flag = adjusted_policy_thresholds(
            0.9,
            0.2,
            prefs,
            model_checkin_approval_rate=0.2,
            model_checkin_total=8,
        )
        self.assertGreater(proceed, 0.55)
        self.assertGreater(flag, -0.1)

    def test_scope_matches_does_not_match_prefix_overlap(self) -> None:
        prefs = AutonomyPreferences(
            prefer_fewer_checkins=True,
            scoped_paths=("src",),
        )
        proceed_src, flag_src = adjusted_policy_thresholds(0.9, 0.2, prefs, file_path="src/main.py")
        proceed_overlap, flag_overlap = adjusted_policy_thresholds(
            0.9, 0.2, prefs, file_path="src_backup/main.py"
        )
        self.assertLess(proceed_src, 0.9)
        self.assertLess(flag_src, 0.2)
        self.assertEqual(proceed_overlap, 0.9)
        self.assertEqual(flag_overlap, 0.2)

    def test_adjusted_thresholds_never_go_below_floor(self) -> None:
        prefs = AutonomyPreferences(prefer_fewer_checkins=True)
        proceed, flag = adjusted_policy_thresholds(-5.0, -5.0, prefs)
        self.assertEqual(proceed, -0.5)
        self.assertEqual(flag, -0.5)


if __name__ == "__main__":
    unittest.main()
