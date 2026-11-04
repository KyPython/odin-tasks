"""Portable real DeepEval metrics for synthetic document-QA controls."""

from __future__ import annotations
import json
from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase
import document_qa

DIMENSIONS = ("exact_answer", "citation_support", "insufficient_evidence")


class DocumentQAMetric(BaseMetric):
    """Exact synthetic contract checks; never calls a model or semantic judge."""

    def __init__(self, case_id: str, dimension: str):
        if dimension not in DIMENSIONS:
            raise ValueError("Unknown document-QA dimension")
        self.case_id = case_id
        self.dimension = dimension
        self.threshold = 1.0
        self.async_mode = False
        self.verbose_mode = False
        self.evaluation_cost = 0
        self.evaluation_model = "deterministic-synthetic-oracle"

    def measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        expected = document_qa.get_case(self.case_id)
        if test_case.input != expected["question"]:
            raise ValueError("Metric input must match the synthetic case")
        result = document_qa.score_response(self.case_id, test_case.actual_output)
        dimension = result["dimensions"][self.dimension]
        if not dimension["applicable"]:
            raise ValueError("This dimension is not applicable to this case")
        self.score = dimension["score"]
        self.reason = dimension["reason"]
        self.success = self.is_successful()
        return self.score

    async def a_measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        return self.measure(test_case, *args, **kwargs)

    @property
    def __name__(self):
        return f"Synthetic document QA: {self.dimension}"


def score_cases(responses: dict[str, dict]) -> list[dict]:
    _, cases = document_qa.load_suite()
    rows = []
    for case_id, case in cases.items():
        test_case = LLMTestCase(
            input=case["question"],
            actual_output=json.dumps(responses[case_id], ensure_ascii=False),
        )
        dimensions = {}
        for dimension in DIMENSIONS:
            if dimension == "insufficient_evidence" and case["evidence"]:
                dimensions[dimension] = {
                    "applicable": False,
                    "score": None,
                    "passed": None,
                }
                continue
            metric = DocumentQAMetric(case_id, dimension)
            score = metric.measure(test_case)
            dimensions[dimension] = {
                "applicable": True,
                "score": score,
                "passed": metric.is_successful(),
                "reason": metric.reason,
            }
        rows.append(
            {
                "case_id": case_id,
                "passed": all(
                    item["passed"] for item in dimensions.values() if item["applicable"]
                ),
                "dimensions": dimensions,
            }
        )
    return rows
