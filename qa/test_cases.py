"""Derive promptfoo cases from the shared synthetic case manifest."""

from document_qa import load_suite


def generate_tests(config=None):
    _, cases = load_suite()
    return [
        {
            "description": f"Synthetic QA: {case['id']}",
            "vars": {"case_id": case["id"], "question": case["question"]},
        }
        for case in cases.values()
    ]
