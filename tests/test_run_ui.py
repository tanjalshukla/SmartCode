from __future__ import annotations

import unittest
from unittest.mock import patch

from sc.run.ui import _prompt_read


class RunUiPromptTests(unittest.TestCase):
    @patch("sc.run.ui.Prompt.ask")
    def test_prompt_read_approve_once(self, ask_mock) -> None:
        ask_mock.return_value = "a"
        approved, remembered, note = _prompt_read(["task_api/api.py"], "Need to inspect the handler.")
        self.assertTrue(approved)
        self.assertFalse(remembered)
        self.assertIsNone(note)

    @patch("sc.run.ui.Prompt.ask")
    def test_prompt_read_approve_and_remember(self, ask_mock) -> None:
        ask_mock.return_value = "r"
        approved, remembered, note = _prompt_read(["task_api/api.py"], "Need to inspect the handler.")
        self.assertTrue(approved)
        self.assertTrue(remembered)
        self.assertIsNone(note)

    @patch("sc.run.ui.Prompt.ask")
    def test_prompt_read_deny(self, ask_mock) -> None:
        ask_mock.side_effect = ["d", "not this time"]
        approved, remembered, note = _prompt_read(["task_api/api.py"], "Need to inspect the handler.")
        self.assertFalse(approved)
        self.assertFalse(remembered)
        self.assertEqual(note, "not this time")


if __name__ == "__main__":
    unittest.main()
