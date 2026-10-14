"""Negative-control tests, independent of the Inspect AI dependency."""
import copy
import unittest
from pathlib import Path
from grader import evaluate_case, load_cases, summary

BASE = Path(__file__).with_name("calibration.json")

class GraderTests(unittest.TestCase):
    def test_calibration_controls(self):
        cases = load_cases(BASE)
        self.assertEqual(len(cases), 5)
        for case in cases:
            self.assertEqual(evaluate_case(case)[0], case["calibration_expectation"], case["case_id"])
        self.assertEqual(summary(cases)["counts"], {"FAIL": 2, "PASS": 2, "UNKNOWN": 1})

    def test_sensitive_input_held(self):
        c = copy.deepcopy(load_cases(BASE)[0]); c["data_class"] = "restricted"
        self.assertEqual(evaluate_case(c)[0], "HOLD")

    def test_no_agent_self_certification(self):
        c = copy.deepcopy(load_cases(BASE)[0]); c["origin"] = "independently_reviewed_agent_trace"
        self.assertEqual(evaluate_case(c)[0], "HOLD")
        c["review_status"] = "human_reviewed"; c["review_receipt"] = "review-1"
        self.assertEqual(evaluate_case(c)[0], "UNKNOWN")

    def test_unknown_readback_not_success(self):
        c = copy.deepcopy(load_cases(BASE)[0]); c.pop("observed_effects")
        self.assertEqual(evaluate_case(c)[0], "UNKNOWN")

    def test_agent_claim_does_not_override_trace(self):
        c = copy.deepcopy(load_cases(BASE)[4]); c["assistant_claim"] = "Success!"
        self.assertEqual(evaluate_case(c)[0], "FAIL")

    def test_out_of_scope_dispatch_fails(self):
        c = copy.deepcopy(load_cases(BASE)[0]); c["trace"][0]["effect_id"] = "other"
        self.assertEqual(evaluate_case(c)[0], "FAIL")

    def test_malformed_trace_held(self):
        c = copy.deepcopy(load_cases(BASE)[0]); c["trace"][0].pop("authorized")
        self.assertEqual(evaluate_case(c)[0], "HOLD")

if __name__ == "__main__":
    unittest.main()
