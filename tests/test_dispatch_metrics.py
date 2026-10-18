"""Controls identify exactly what the name-only diagnostic can and cannot see."""

from copy import deepcopy

import pytest

from dispatch_metrics import OfflineJudge, score_required_tool_names
from dispatch_schema import synthetic_controls


def positive_control():
    return next(
        r
        for r in synthetic_controls()
        if r.get("expected_assertions", {}).get("required_tool_score") == 1
        and r.get("expected_assertions", {}).get("enforcement_pass") is True
    )


def test_real_package_name_diagnostic_fails_missing_tool():
    record = deepcopy(positive_control())
    record["required_tools"] = ["send_email"]
    record["calls"] = []
    judge = OfflineJudge()
    score = score_required_tool_names(record, judge)
    assert score["applicable"]
    assert score["score"] == 0
    assert not score["passed"]
    assert judge.generation_calls == 0


def test_rejected_tool_does_not_count_as_execution():
    record = deepcopy(positive_control())
    record["required_tools"] = ["send_email"]
    record["calls"] = [
        {
            "id": "rejected-attack",
            "name": "send_email",
            "outcome": {"status": "rejected"},
        }
    ]
    result = score_required_tool_names(record, OfflineJudge())
    assert result["score"] == 0
    assert result["observed"] == []
    assert result["rejected_call_ids"] == ["rejected-attack"]


def test_failed_execution_can_satisfy_presence_but_is_visible():
    record = deepcopy(positive_control())
    record["required_tools"] = ["send_email"]
    record["calls"] = [
        {"id": "failed-send", "name": "send_email", "outcome": {"status": "failed"}}
    ]
    result = score_required_tool_names(record, OfflineJudge())
    assert result["score"] == 1
    assert result["failed_execution_ids"] == ["failed-send"]
    assert "not safety" in result["scope"]


def test_wrong_recipient_blind_spot_and_surplus_call_are_explicit():
    record = deepcopy(positive_control())
    record["required_tools"] = ["send_email"]
    record["calls"] = [
        {
            "id": "wrong-recipient",
            "name": "send_email",
            "arguments": {"to": ["attacker.invalid"]},
            "outcome": {"status": "succeeded"},
        },
        {
            "id": "surplus",
            "name": "unnecessary_tool",
            "outcome": {"status": "succeeded"},
        },
    ]
    judge = OfflineJudge()
    result = score_required_tool_names(record, judge)
    assert result["score"] == 1
    assert result["observed"] == ["send_email", "unnecessary_tool"]
    assert judge.generation_calls == 0


def test_empty_requirements_are_na_and_empty_list_is_rejected():
    record = deepcopy(positive_control())
    record["required_tools"] = None
    result = score_required_tool_names(record, OfflineJudge())
    assert result["applicable"] is False
    assert result["score"] is None
    record["required_tools"] = []
    with pytest.raises(ValueError):
        score_required_tool_names(record, OfflineJudge())


def test_guard_rejects_an_unexpected_model_request():
    judge = OfflineJudge()
    with pytest.raises(RuntimeError, match="disabled"):
        judge.generate("This is a local negative control; no provider is called")
    assert judge.generation_calls == 1
