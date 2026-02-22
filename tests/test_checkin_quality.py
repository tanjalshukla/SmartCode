from __future__ import annotations

import unittest

from sc.checkin_quality import evaluate_checkin_quality
from sc.schema import CheckInMessage


class CheckInQualityTests(unittest.TestCase):
    def test_accepts_architectural_tradeoff_checkin(self) -> None:
        message = CheckInMessage(
            type="check_in",
            check_in_type="decision_point",
            reason="Pagination strategy impacts API contract and cache consistency.",
            content=(
                "Option A keeps offset pagination with minimal schema changes but has drift risk at scale. "
                "Option B moves to cursor pagination, improves consistency, and reduces duplicate rows under writes. "
                "The tradeoff is client migration cost and added token parsing logic. "
                "I recommend Option B because it is safer for future throughput and aligns with the existing streaming workflow design."
            ),
            options=["Keep offset pagination", "Migrate to cursor pagination"],
            assumptions=[
                "Existing clients support cursor tokens.",
                "Write volume will increase over the next quarter.",
            ],
            confidence=0.71,
        )
        result = evaluate_checkin_quality(message)
        self.assertTrue(result.valid)

    def test_rejects_shallow_checkin(self) -> None:
        message = CheckInMessage(
            type="check_in",
            check_in_type="decision_point",
            reason="Need input",
            content="Should we do A or B?",
            options=["A"],
        )
        result = evaluate_checkin_quality(message)
        self.assertFalse(result.valid)
        self.assertGreaterEqual(len(result.issues), 3)


if __name__ == "__main__":
    unittest.main()
