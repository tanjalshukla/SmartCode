from __future__ import annotations

import unittest

from sc.session import ClaudeSession


class SessionTests(unittest.TestCase):
    def test_trim_messages_to_limit(self) -> None:
        session = ClaudeSession("base", max_messages=4)
        for idx in range(6):
            session.add_user(f"u{idx}")
        self.assertEqual(len(session.messages), 4)
        self.assertEqual(session.messages[0]["content"], "u0")

    def test_first_message_pinned_during_trim(self) -> None:
        session = ClaudeSession("base", max_messages=3)
        session.add_user("task")
        session.add_assistant("a1")
        session.add_user("u2")
        session.add_assistant("a3")
        self.assertEqual(len(session.messages), 3)
        self.assertEqual(session.messages[0]["content"], "task")
        self.assertEqual(session.messages[-1]["content"], "a3")

    def test_effective_prompt_includes_memory_and_context(self) -> None:
        session = ClaudeSession("base")
        session.add_memory_note("Use AppError for failures.")
        session.set_session_context("- 1 denied action in recent session steps.")
        prompt = session.effective_system_prompt()
        self.assertIn("## Pinned Memory", prompt)
        self.assertIn("Use AppError for failures.", prompt)
        self.assertIn("## This Session", prompt)


if __name__ == "__main__":
    unittest.main()
