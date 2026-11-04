"""Offline DeepEval tool-name diagnostic; authorization is scored separately."""

from __future__ import annotations

import json
import time
from typing import Any

from deepeval.metrics import ToolCorrectnessMetric
from deepeval.models import DeepEvalBaseLLM
from deepeval.test_case import LLMTestCase, ToolCall


class OfflineJudge(DeepEvalBaseLLM):
    """A supported model interface that makes any judge request an error."""

    def __init__(self) -> None:
        self.generation_calls = 0
        super().__init__(model="offline-no-judge")

    def load_model(self) -> "OfflineJudge":
        return self

    def get_model_name(self) -> str:
        return "offline-no-judge"

    def generate(self, prompt: str, schema: Any = None, **kwargs: Any) -> str:
        self.generation_calls += 1
        raise RuntimeError("Judge inference is disabled in this offline pilot")

    async def a_generate(self, prompt: str, schema: Any = None, **kwargs: Any) -> str:
        self.generation_calls += 1
        raise RuntimeError("Judge inference is disabled in this offline pilot")


def score_required_tool_names(
    record: dict[str, Any], judge: OfflineJudge
) -> dict[str, Any]:
    required = record["required_tools"]
    executed = [
        call
        for call in record["calls"]
        if call["outcome"]["status"] in ("succeeded", "failed")
    ]
    evidence = {
        "metric": "DeepEval required business-tool name presence",
        "scope": "name presence only; not safety, successful execution or completion",
        "required": required,
        "observed": [call["name"] for call in executed],
        "failed_execution_ids": [
            call["id"] for call in executed if call["outcome"]["status"] == "failed"
        ],
        "rejected_call_ids": [
            call["id"]
            for call in record["calls"]
            if call["outcome"]["status"] == "rejected"
        ],
    }
    if required is None:
        return {
            **evidence,
            "applicable": False,
            "score": None,
            "passed": None,
            "reason": "No independently required business tools for this case",
            "wall_time_seconds": 0.0,
        }
    if not required:
        raise ValueError("Required tools must be a nonempty list or null")

    metric = ToolCorrectnessMetric(
        model=judge,
        eval_mode="llm",
        async_mode=False,
        strict_mode=False,
        threshold=1.0,
        should_exact_match=False,
        should_consider_ordering=False,
        evaluation_params=[],
        available_tools=None,
        verbose_mode=False,
    )
    test_case = LLMTestCase(
        input=(
            record["input"]
            if isinstance(record["input"], str)
            else json.dumps(record["input"], ensure_ascii=False)
        ),
        actual_output=record["actual_output"],
        tools_called=[ToolCall(name=call["name"]) for call in executed],
        expected_tools=[ToolCall(name=name) for name in required],
    )
    started = time.perf_counter()
    metric.measure(test_case, _show_indicator=False)
    elapsed = time.perf_counter() - started
    if judge.generation_calls:
        raise RuntimeError("An offline metric attempted judge inference")
    return {
        **evidence,
        "applicable": True,
        "score": metric.score,
        "passed": metric.is_successful(),
        "reason": metric.reason,
        "wall_time_seconds": elapsed,
    }
