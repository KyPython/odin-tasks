"""Promptfoo uses the same deterministic oracle as the DeepEval sidecar."""

from document_qa import score_response


def get_assert(output, context):
    try:
        result = score_response(context["vars"]["case_id"], output)
    except (ValueError, TypeError, KeyError):
        return {
            "pass": False,
            "score": 0,
            "reason": "Malformed synthetic QA response or case",
        }
    applicable = {
        key: value for key, value in result["dimensions"].items() if value["applicable"]
    }
    return {
        "pass": result["passed"],
        "score": min(item["score"] for item in applicable.values()),
        "reason": "; ".join(
            f"{key}: {'pass' if item['passed'] else 'fail'}"
            for key, item in applicable.items()
        )
        + "; exact synthetic oracle, no semantic judge",
        "namedScores": {key: item["score"] for key, item in applicable.items()},
    }
