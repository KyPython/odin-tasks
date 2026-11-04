from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from threshold_lab.io import load_observations, load_policy


class InputTests(unittest.TestCase):
    def test_loads_synthetic_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            observations_path = root / "observations.json"
            policy_path = root / "policy.json"
            observations_path.write_text(
                '[{"id":"sample","score":0.6,"actual":true}]', encoding="utf-8"
            )
            policy_path.write_text(
                '{"candidate_thresholds":[0.5],"false_negative_cost":7,'
                '"false_positive_cost":2}',
                encoding="utf-8",
            )

            observations = load_observations(observations_path)
            policy = load_policy(policy_path)

        self.assertEqual(observations[0].id, "sample")
        self.assertEqual(policy.candidate_thresholds, (0.5,))


if __name__ == "__main__":
    unittest.main()
