from __future__ import annotations

import unittest

from threshold_lab.evaluation import Observation, Policy, build_report, evaluate_threshold


class EvaluationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = Policy((0.25, 0.75), false_negative_cost=4, false_positive_cost=1)
        self.observations = (
            Observation("north", 0.9, True),
            Observation("south", 0.1, False),
        )

    def test_clear_predictions_are_counted_as_correct(self) -> None:
        result = evaluate_threshold(self.observations, 0.5, self.policy)

        self.assertEqual(result.true_positive, 1)
        self.assertEqual(result.true_negative, 1)
        self.assertEqual(result.accuracy, 1.0)

    def test_report_sorts_candidates_and_retains_cost_configuration(self) -> None:
        report = build_report(self.observations, Policy((0.75, 0.25), 4, 1))

        self.assertEqual(
            [candidate["threshold"] for candidate in report["candidates"]],
            [0.25, 0.75],
        )
        self.assertEqual(report["costs"], {"false_negative": 4, "false_positive": 1})

    def test_empty_observations_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least one observation"):
            build_report((), self.policy)


if __name__ == "__main__":
    unittest.main()
