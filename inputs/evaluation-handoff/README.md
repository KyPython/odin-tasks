# Evaluation handoff

This self-contained Python project models a small submission intake and grading
pipeline. It uses only the Python standard library.

Run the local verification sequence from this directory:

```sh
./scripts/verify.sh
```

Run the pipeline directly against the valid fixture:

```sh
python3 -m grader.pipeline fixtures/valid/manifest.json
```

The evaluation rules are documented in `docs/evaluation-contract.md`. The
intake stage owns pre-grading validation; the grader only receives an accepted
submission and produces a deterministic score.
