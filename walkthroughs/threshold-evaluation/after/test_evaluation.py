from __future__ import annotations

import unittest
from pathlib import Path

from threshold_lab.evaluation import Evaluation, Observation, Policy, build_report, evaluate_threshold
from threshold_lab.io import load_observations, load_policy


EXPECTED_REPORT = {
    "costs": {"false_negative": 9, "false_positive": 2},
    "candidates": [
        {"threshold": 0.3, "true_positive": 2, "true_negative": 0, "false_positive": 5,
         "false_negative": 1, "accuracy": 0.25, "total_cost": 19},
        {"threshold": 0.5, "true_positive": 2, "true_negative": 2, "false_positive": 3,
         "false_negative": 1, "accuracy": 0.5, "total_cost": 15},
        {"threshold": 0.7, "true_positive": 1, "true_negative": 3, "false_positive": 2,
         "false_negative": 2, "accuracy": 0.5, "total_cost": 22},
        {"threshold": 0.85, "true_positive": 1, "true_negative": 5, "false_positive": 0,
         "false_negative": 2, "accuracy": 0.75, "total_cost": 18},
    ],
    "selected_threshold": 0.5,
}


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


    def fixture_inputs(self):
        root = Path(__file__).resolve().parents[1]
        return (load_observations(root / "fixtures/observations.json"),
                load_policy(root / "fixtures/policy.json"))

    def test_all_four_cells_and_inclusive_score_boundary(self) -> None:
        rows = (
            Observation("tp", 0.5, True),
            Observation("tn", 0.49, False),
            Observation("fp-boundary", 0.5, False),
            Observation("fp-high", 0.9, False),
            Observation("fn", 0.49, True),
        )
        result = evaluate_threshold(rows, 0.5, Policy((0.5,), 9, 2))
        self.assertEqual(result, Evaluation(0.5, 1, 1, 2, 1, 0.4, 13))

    def test_fixture_candidate_counts_and_costs(self) -> None:
        rows, policy = self.fixture_inputs()
        self.assertEqual(build_report(rows, policy)["candidates"], EXPECTED_REPORT["candidates"])

    def test_fixture_selects_cost_over_accuracy(self) -> None:
        rows, policy = self.fixture_inputs()
        report = build_report(rows, policy)
        self.assertEqual(report["selected_threshold"], 0.5)
        self.assertEqual(report["candidates"][-1]["accuracy"], 0.75)
        self.assertEqual(report["candidates"][1]["accuracy"], 0.5)

    def test_equal_cost_prefers_lowest_threshold_not_accuracy(self) -> None:
        rows = (Observation("positive", 0.9, True), Observation("negative", 0.6, False))
        report = build_report(rows, Policy((0.7, 0.5), 0, 0))
        self.assertEqual([candidate["threshold"] for candidate in report["candidates"]], [0.5, 0.7])
        self.assertEqual([candidate["total_cost"] for candidate in report["candidates"]], [0, 0])
        self.assertEqual(report["selected_threshold"], 0.5)

    def test_policy_weights_change_selection(self) -> None:
        rows, _ = self.fixture_inputs()
        for false_negative_cost, false_positive_cost, selected in ((9, 2, 0.5), (1, 9, 0.85)):
            with self.subTest(costs=(false_negative_cost, false_positive_cost)):
                report = build_report(rows, Policy((0.85, 0.7, 0.5, 0.3), false_negative_cost, false_positive_cost))
                self.assertEqual(report["selected_threshold"], selected)

    def test_empty_candidate_thresholds_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least one candidate threshold"):
            build_report(self.observations, Policy((), 9, 2))

    def test_generator_input_matches_complete_expected_report(self) -> None:
        rows, policy = self.fixture_inputs()
        self.assertEqual(build_report((row for row in rows), policy), EXPECTED_REPORT)


if __name__ == "__main__":
    unittest.main()
