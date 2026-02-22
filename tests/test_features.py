from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sc.features import classify_change_pattern, estimate_blast_radius, is_security_sensitive


class FeatureTests(unittest.TestCase):
    def test_change_pattern_classification(self) -> None:
        self.assertEqual(
            classify_change_pattern("tests/test_cli.py", "", "def test_x():\n    assert True\n"),
            "test_generation",
        )
        self.assertEqual(
            classify_change_pattern("settings/config.toml", "", "x = 1\n"),
            "config_change",
        )
        self.assertEqual(
            classify_change_pattern("src/api/routes.py", "", "def handler():\n    pass\n"),
            "api_change",
        )

    def test_security_detection(self) -> None:
        self.assertTrue(is_security_sensitive("src/auth/token.py", "def f():\n    pass\n"))
        self.assertTrue(is_security_sensitive("src/core.py", "uses oauth token"))
        self.assertFalse(is_security_sensitive("src/core.py", "plain helper"))

    def test_blast_radius_estimate(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "pkg").mkdir()
            (root / "pkg" / "a.py").write_text("def run():\n    return 1\n")
            (root / "pkg" / "b.py").write_text("from pkg.a import run\n")
            (root / "pkg" / "c.py").write_text("import pkg.a\n")
            radius = estimate_blast_radius(root, "pkg/a.py")
            self.assertGreaterEqual(radius, 2)


if __name__ == "__main__":
    unittest.main()
