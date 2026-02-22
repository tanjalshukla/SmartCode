from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

from sc.verification import run_verification


class VerificationTests(unittest.TestCase):
    def test_python_syntax_check_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            path = root / "ok.py"
            path.write_text("x = 1\n")
            result = run_verification(
                repo_root=root,
                touched_files=["ok.py"],
                expected_behavior="Set x",
                timeout_sec=5,
            )
            self.assertTrue(result.passed)
            self.assertEqual(result.checks[0].name, "python_syntax")

    def test_python_syntax_check_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            path = root / "bad.py"
            path.write_text("def broken(:\n")
            result = run_verification(
                repo_root=root,
                touched_files=["bad.py"],
                expected_behavior="Broken syntax",
                timeout_sec=5,
            )
            self.assertFalse(result.passed)
            self.assertEqual(result.checks[0].name, "python_syntax")

    def test_custom_verification_command_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            result = run_verification(
                repo_root=root,
                touched_files=[],
                expected_behavior="noop",
                timeout_sec=5,
                command=f"{sys.executable} -c \"print('ok')\"",
            )
            check_names = [item.name for item in result.checks]
            self.assertIn("custom_verification", check_names)


if __name__ == "__main__":
    unittest.main()
