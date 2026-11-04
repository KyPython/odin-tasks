# Harbor Signal Evaluation

This synthetic project evaluates a binary alert score at a fixed set of candidate
thresholds. It is intentionally small and uses only the Python standard library.

## Setup

Python 3.11 or newer is sufficient; there are no third-party dependencies.

```bash
cd threshold-evaluation
PYTHONPATH=src python -m unittest discover -s tests -v
```

## Generate the baseline report

```bash
PYTHONPATH=src python -m threshold_lab.cli \
  --observations fixtures/observations.json \
  --policy fixtures/policy.json
```

The command prints JSON to standard output, so it can also be saved for
inspection:

```bash
PYTHONPATH=src python -m threshold_lab.cli \
  --observations fixtures/observations.json \
  --policy fixtures/policy.json > report.json
```

## Evaluation contract

- An observation is predicted positive when its score is greater than or equal
  to the candidate threshold.
- `true_positive`, `true_negative`, `false_positive`, and `false_negative` use
  their conventional meanings relative to the observation's `actual` label.
- A candidate's total cost is
  `(false_negative * false_negative_cost) +
  (false_positive * false_positive_cost)`.
- The selected candidate is the one with the lowest total cost. If candidates
  tie, choose the numerically lowest threshold.
- The report must be deterministic and list every configured candidate in
  ascending threshold order.

The fixture values and names are fabricated for this exercise.
