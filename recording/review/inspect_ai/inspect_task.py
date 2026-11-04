"""Inspect AI scoring of independently reviewed trace replay, with zero model calls."""
from pathlib import Path
from inspect_ai import Task, task
from inspect_ai.dataset import Sample
from inspect_ai.scorer import Score, accuracy, scorer
from inspect_ai.solver import solver
from review.inspect_ai.grader import evaluate_case, load_cases

@solver
def replay_without_model():
    async def solve(state, generate):
        # Do not invoke generate() or any external actions.
        return state
    return solve

@scorer(metrics=[accuracy()])
def independent_effect_oracle():
    async def score(state, target):
        verdict, reason = evaluate_case(state.metadata["case"])
        if verdict in ("UNKNOWN", "HOLD"):
            return Score.unscored(reason=reason, metadata={"verdict": verdict, "reason": reason})
        expected = state.metadata["case"].get("calibration_expectation")
        correct = (verdict == expected) if expected is not None else (verdict == "PASS")
        return Score(value="C" if correct else "I", explanation=reason,
                     metadata={"verdict": verdict, "reason": reason, "calibration": expected is not None})
    return score

@task
def odin_inspect_replay():
    cases = load_cases(Path(__file__).with_name("calibration.json"))
    return Task(dataset=[Sample(input="Inspect synthetic trace " + c["case_id"],
                                target=str(c.get("calibration_expectation", "PASS")),
                                id=c["case_id"], metadata={"case": c}) for c in cases],
                solver=replay_without_model(), scorer=independent_effect_oracle())
