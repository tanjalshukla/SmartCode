from __future__ import annotations

import unittest

from sc.session_feedback import SessionFeedback


class SessionFeedbackTests(unittest.TestCase):
    def test_context_includes_denials_and_corrections(self) -> None:
        feedback = SessionFeedback(current_phase="planning")
        feedback.note_decision(True)
        feedback.note_decision(
            False,
            change_patterns=["new_file:api_change"],
            response_time_ms=4200,
            feedback_text="Prefer reusing existing API contracts.",
        )
        feedback.set_phase("implementation")

        context = feedback.build_and_consume_context()
        self.assertIn("denied actions", context)
        self.assertIn("api_change", context)
        self.assertIn("approval rate", context)
        self.assertIn("Average recent review latency", context)
        self.assertIn("Prefer reusing existing API contracts.", context)
        self.assertIn("Phase transition: now in implementation.", context)

        next_context = feedback.build_and_consume_context()
        self.assertNotIn("Phase transition", next_context)

    def test_context_includes_approval_streak(self) -> None:
        feedback = SessionFeedback(current_phase="implementation")
        for _ in range(5):
            feedback.note_decision(True)
        context = feedback.build_and_consume_context()
        self.assertIn("consecutive approvals", context)


if __name__ == "__main__":
    unittest.main()
