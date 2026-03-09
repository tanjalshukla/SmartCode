from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sc.config import SAConfig, autonomy_profile, load_config, normalize_autonomy_mode, save_config


class ConfigModeTests(unittest.TestCase):
    def test_normalize_autonomy_mode_defaults_to_balanced(self) -> None:
        self.assertEqual(normalize_autonomy_mode(None), "balanced")
        self.assertEqual(normalize_autonomy_mode("unknown"), "balanced")

    def test_autonomy_profile_adjusts_thresholds_by_mode(self) -> None:
        base = SAConfig(model_id="model", autonomy_mode="balanced")
        strict = autonomy_profile(SAConfig(model_id="model", autonomy_mode="strict"))
        milestone = autonomy_profile(SAConfig(model_id="model", autonomy_mode="milestone"))
        autonomous = autonomy_profile(SAConfig(model_id="model", autonomy_mode="autonomous"))

        self.assertGreater(strict.proceed_threshold, base.policy_proceed_threshold)
        self.assertTrue(strict.strict_plan_gate)
        self.assertLess(milestone.proceed_threshold, base.policy_proceed_threshold)
        self.assertLess(autonomous.proceed_threshold, milestone.proceed_threshold)

    def test_save_and_load_config_persists_autonomy_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            save_config(repo_root, SAConfig(model_id="model", autonomy_mode="milestone"))
            loaded = load_config(repo_root)
            self.assertIsNotNone(loaded)
            assert loaded is not None
            self.assertEqual(loaded.autonomy_mode, "milestone")


if __name__ == "__main__":
    unittest.main()
